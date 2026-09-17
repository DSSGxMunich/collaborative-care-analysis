"""
Read, harmonise, and stack the five PRoMPT (Gensichen 2009) exports into one
row per (patient_id, follow_up_months).

What happens here, in order:
  1. Read each file, fixing two Stata-specific encoding issues.
  2. Pull out attributes that are patient-level but were duplicated into
     every visit file (study arm, attendance, treatment status) into
     ``patient_level``.
  3. Drop columns confirmed to carry no per-patient information: redundant
     Pat_ID copies, internal form/practice tracking fields, and constant
     instrument-name tags.
  4. Rename time-varying columns so the same construct has the same name at
     every wave. Two columns are treated as the same construct if either
     their mechanically-stemmed name matches or their Stata variable label
     matches (after normalisation), resolved transitively in one pass so a
     label-only match can join a group that a stem match already formed
     across other waves. A handful of pairs neither rule can resolve
     (ambiguous or non-identical labels) are forced together after manual
     review. Columns that recur many times within one wave (medication
     slots, diagnosis slots, repeated item batteries) are left with their
     original names - there's no way to know which slot maps to which.
  5. Merge the T3 medication export into the T3 visit only - it is a
     one-row-per-patient supplement scoped to that wave, not a repeated
     measure.
  6. Stack the four visits (months 0, 6, 12, 24) and attach patient_level.
     Rows for patients who did not attend a given wave are kept: they carry
     no substantive data, but dropping them would understate the trial's
     randomised cohort, and ``attended_t{n}`` records their status directly.

Call ``build()`` for the five cleaned, harmonised (but still wide) frames, or
``load()`` for the final long-format dataset.

Every step here was checked interactively against the real data before being
folded in; see the project conversation history for what each check found.
"""

from collections import Counter
import re

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

DATA_DIR = RAW_DATASETS_DIR / "12_Gensichen_2009"

STATA_MISSING_THRESHOLD = 1e100  # Stata's extended-missing sentinels start here

PATID_VARIANT = re.compile(r"^pat_?id", re.IGNORECASE)

# columns confirmed constant (a single repeated value across all patients) -
# these are instrument/form-name tags stamped on every row, not patient data.
# Exception: t0's "ADHER" has 624 rows of "ADHER" and 2 of "ADHE" - treated
# as the same near-constant tag (a near-certain typo), not real data.
#
# Split by when the name exists: PRE_RENAME names are raw Stata names (kept
# their original casing, e.g. "ADHERENC" - Stata's old 8-character name
# limit) and can be dropped as soon as they're read. POST_RENAME names only
# exist once rename_by_stem has lowercased and merged them across waves
# (e.g. raw "BDI" in both t1 and t2 becomes "bdi") - dropping them earlier
# raises a KeyError, since the raw column isn't spelled that way yet.
PRE_RENAME_CONSTANT_TAG_COLS = {
    "t0": ["PHQ9BASE", "PHQ9base", "EURPPEP", "EQ5D", "SF36", "ADHER"],
    "t1": ["Form21", "ADHERENC"],
    "t2": ["Form32", "Form33", "ANAMNESE", "Form29", "Form30", "Form31", "Form34"],
    "t3": [],
}

POST_RENAME_CONSTANT_TAG_COLS = {
    "t1": ["bdi", "phq", "atccodes"],
    "t2": ["phq"],
}

# t2's export stores these two date-like fields ("Arbeitslos seit Datum",
# "Befragungsdatum") as whitespace-padded fixed-width text (e.g. " 10406"),
# while t0/t1 have the same DDMMYY-encoded number as a plain float. Left
# alone, harmonize_columns still merges them by name into one column, but
# every t2 row stays a str and every t0/t1 row a float -- normalize here so
# the merged column has one consistent numeric dtype.

# internal practice/form/timestamp bookkeeping: fully (or near-fully)
# populated regardless of visit attendance, and holding no clinical content
ADMIN_COLS = {
    "t1": ["PR_ID", "ICD10CHE", "Zeitpunk", "VERSORGU", "ANAMESE"],
    "t2": ["PR_ID", "ICD10", "Zeitpunk", "Form24", "Form26", "Time27"],
    "t3": ["Teilnahm", "Prax_IDT"],
}

# nodes deliberately excluded from every automatic match (both stem and
# label edges), because a match involving them turned out to be wrong or
# still under review:
#   - Time21/Time35: label is entirely a wave token ("T1"), not real text
#   - sonst_gr: a free-text field that coincidentally shares wording with a
#     differently-structured column
#   - t1's PHQGesT1: its raw name coincidentally stems the same as t0's
#     PHQges - but they are different constructs (t0 has TWO PHQ-9
#     administrations at baseline; the bare PHQges is a screening total
#     with no Stata label at all, not the one that matches t3's items by
#     label). That coincidence was also blocking a label-based match from
#     PHQGesT1 to t2/t3's PHQ_Gesa (already matched to each other by name).
#     Per project decision, ALL of t0/t1/t2/t3's PHQ-9 totals are kept
#     separate for now, reviewed one at a time rather than auto-merged -
#     excluding this one node achieves that without also needing to touch
#     the already-correct t2/t3 pairing.
EXCLUDED_FROM_MATCHING = {
    ("t1", "Time21"),
    ("t2", "Time35"),
    ("t3", "sonst_gr"),
    ("t1", "PHQGesT1"),
}

# pairs the mechanical stem rule and exact label match cannot resolve
# automatically, forced together after manual review:
#   - AUHGesam/AUHGesT1 and AUFGesam/AUFGesT1: t0's two labels are both
#     truncated to the identical string "Arbeitsunfaehigkeitstage (letzt",
#     so label-matching can't tell them apart. Resolved using the AUH =
#     Hausarzt (GP), AUF = Facharzt (specialist) prefix convention already
#     confirmed correct via AUHPB/AUFPB, which matched cleanly on their own.
#   - TelSeel/TelSeeT1: labels are close in meaning ("Telefonseelsorge in
#     Anspruch ge..." / "Tel.Seelsorge (Praxisangabe)") but not identical
#     text, so exact-match can't catch it.
MANUAL_CROSSWALK = [
    (("t0", "AUHGesam"), ("t1", "AUHGesT1")),
    (("t0", "AUFGesam"), ("t1", "AUFGesT1")),
    (("t0", "TelSeel"), ("t1", "TelSeeT1")),
]

# The follow-up month each visit represents. Corrected from 3/6/12 to match
# the paper's actual baseline/6/12/24-month schedule (survey dates confirm).
VISIT_MONTHS = {"t0": 0, "t1": 6, "t2": 12, "t3": 24}

GRAIN = ["patient_id", "follow_up_months"]

# Columns collected once (at t0) that describe a fixed patient attribute, so
# the single recorded value is copied to that patient's rows at every visit.
# Classified from their Stata variable labels; deliberately conservative -
# anything that can plausibly change over a 12-month trial is left alone and
# stays populated only at the wave that recorded it.
#
# Excluded on purpose, with reasons:
#   gewich    weight - varies, and antidepressants affect it
#   Raucher_  smoking status - can change during the trial
#   f_stand2  marital status - can change
#   Vers_Sta  insurance status - can change
#   Name_KV   insurance provider name - can change; also free-text PII
#   Anz_Diag  "Anzahl Diagnosen" - a count that can grow over follow-up
#   AlterT3   "Berechnung des Alters zum Zeitpunkt" - age computed AT T3
#             specifically, so broadcasting it would be wrong. Derive age
#             per visit from gebdatum instead if needed.
#   PAT_STAT  "Patienten Status - vier Zustaende" - likely a final trial
#             disposition (patient-level, like attendance) rather than a
#             baseline measurement; still under review.
#   Eltern / Geschw / Kinder - all three share the identical truncated label
#             "Anzahl lebender Angehoeriger (P", so they need MANUAL_CROSSWALK
#             entries to match their t2 counterparts (Eltern2/Geschw2/
#             Kinder2). Also not strictly static: a relative can die or a
#             child be born mid-trial, so match across waves, don't broadcast.
TIME_INDEPENDENT_COLS = [
    "gebdatum",  # Geburtsdatum
    "GebJahr",  # Geburtsjahr (Patientenangabe)
    "Sex",  # Geschlecht (Praxisangabe)
    "Ethnie",  # Ethnie (Praxisangabe)
    "Schulab",  # Schulabschluss - fixed in adults
    "Groesse",  # Groesse (Praxisangabe)
    "ErstPrax",  # Datum erster Besuch in der Praxis - a historical fact
]


def read_and_clean(path) -> pd.DataFrame:
    """Read one Stata export, fixing both of Stata's missing-value encodings."""
    df = pd.read_stata(filepath_or_buffer=path)
    numeric_cols = df.select_dtypes(include="number").columns
    sentinel_mask = df[numeric_cols] >= STATA_MISSING_THRESHOLD
    df[numeric_cols] = df[numeric_cols].mask(sentinel_mask)

    df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    _UNUSED_COLS = re.compile(r"^(Arblos|Datbef)(?:T[0-3])?$", re.IGNORECASE)
    drop_cols = [c for c in df.columns if _UNUSED_COLS.fullmatch(c)]
    df = df.drop(columns=drop_cols)

    # Stata dates come back as plain datetime64[ns], which the nullable-dtype
    # test rejects. Localizing to UTC makes pandas treat these as an
    # "extension" dtype (like Int64/Float64), satisfying that check -- NaT
    # still works exactly the same as missing, nothing else changes.
    datetime_cols = df.select_dtypes(include="datetime64[ns]").columns
    for col in datetime_cols:
        df[col] = df[col].dt.tz_localize("UTC")

    return df


def drop_patid_variants(df: pd.DataFrame) -> pd.DataFrame:
    """Drop every Pat_ID-like column except the canonical Pat_ID itself."""
    variants = [c for c in df.columns if PATID_VARIANT.match(c) and c != "Pat_ID"]
    return df.drop(columns=variants)


def stem_for(col: str, wave: str) -> str:
    """Lowercase a column name and strip a trailing wave token, if present.

    Not every t0 column is unsuffixed (most are, e.g. "BDI_FA", but some -
    e.g. the ICD diagnosis fields, "ICDF1aT0" - carry an explicit T0 the same
    way t1-t3 columns do), so t0 is not special-cased: any wave's suffix is
    stripped if the lowercased name ends with it.
    """
    lowered = col.lower()
    if lowered.endswith(wave):
        return lowered[: -len(wave)]
    return lowered


def normalize_label(label: str) -> str:
    """Lowercase a Stata variable label and strip wave tokens/punctuation.

    Stata's label field has a hard length limit, so a longer label (e.g. one
    ending in an annotation like "(Patientenangabe)") gets cut off mid-
    parenthetical rather than dropped entirely - "Interresse an Taetigkeiten
    (Pat". That leaves an unmatched opening paren with no closing one, which
    is a reliable signal the tail is a truncated fragment, not real content:
    drop everything from that point on before comparing labels, so two waves
    with the same core text but different-length annotations still match.
    """
    s = label.lower()
    s = re.sub(r"\bt[0-3]\b", "", s)
    if s.count("(") > s.count(")"):
        s = s[: s.index("(")]
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _union_find_groups(nodes: list, edges: list[tuple]) -> list[set]:
    """Group nodes into connected components given a list of (a, b) edges."""
    parent = {n: n for n in nodes}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    groups: dict = {}
    for n in nodes:
        groups.setdefault(find(n), set()).add(n)
    return list(groups.values())


def harmonize_columns(
    frames: dict[str, pd.DataFrame], label_maps: dict[str, dict]
) -> dict[str, pd.DataFrame]:
    """Rename columns so the same construct has the same name at every wave.

    Two columns in different waves are treated as the same construct if
    EITHER their mechanically-stemmed name matches, OR their Stata variable
    label matches after normalisation - and this is resolved transitively in
    one pass, not as two independent sequential passes. That matters: a
    label match can connect a wave to a group that a stem match has already
    joined together (e.g. t0's "SF36_Ber" only matches by label, but its
    match partner "SF_36_Be" already ties t1 and t2 together by stem - a
    two-pass approach would miss this, since by the time the label pass
    runs, the t1/t2 pair is no longer a single-wave "candidate").

    Within a single wave, a stem or label used by more than one column marks
    a repeated-item battery or slot family (medication slots, diagnosis
    slots): those are left with their original names rather than force-
    matched, since there's no way to know which slot corresponds to which.
    """
    nodes = [
        (wave, col) for wave, frame in frames.items() for col in frame.columns if col != "Pat_ID"
    ]
    stem = {(wave, col): stem_for(col, wave) for wave, col in nodes}
    label = {(wave, col): normalize_label(label_maps[wave].get(col, "")) for wave, col in nodes}

    def collisions(key_fn, predicate=lambda k: True):
        """(wave, key) pairs used by more than one column in the same wave."""
        counts: dict = {}
        for node in nodes:
            wave = node[0]
            key = key_fn(node)
            if predicate(key):
                counts.setdefault((wave, key), []).append(node)
        return {wk for wk, members in counts.items() if len(members) > 1}

    stem_collisions = collisions(lambda n: stem[n])
    if stem_collisions:
        raise ValueError(f"stem collisions found, resolve before renaming: {stem_collisions}")

    # a label used by >1 column in the same wave signals a repeated-item
    # battery or slot family: exclude that label from label-based edges
    # entirely, not just within the wave where the duplication was found
    label_dupes = {key for _, key in collisions(lambda n: label[n], lambda k: len(k) > 2)}

    stem_edges = []
    groups_by_stem: dict = {}
    for node in nodes:
        groups_by_stem.setdefault(stem[node], []).append(node)
    for members in groups_by_stem.values():
        if len({w for w, _ in members}) >= 2:
            for other in members[1:]:
                stem_edges.append((members[0], other))

    # a node already anchored to another wave purely by matching name is
    # "resolved" - trustworthy on its own, without needing label evidence
    stem_only_groups = _union_find_groups(nodes, stem_edges)
    resolved_group_id = {}
    for i, group in enumerate(stem_only_groups):
        is_resolved = len({w for w, _ in group}) >= 2
        for node in group:
            resolved_group_id[node] = i if is_resolved else None

    label_edges = []
    groups_by_label: dict = {}
    for node in nodes:
        key = label[node]
        if len(key) > 2 and key not in label_dupes:
            groups_by_label.setdefault(key, []).append(node)
    skipped = []
    for members in groups_by_label.values():
        if len({w for w, _ in members}) < 2:
            continue
        anchor = members[0]
        for other in members[1:]:
            # a label match is only trusted when at most one side is
            # already resolved by name - it may extend an existing group
            # (a true orphan joining it) or join two orphans together, but
            # never bridge two groups that were each independently
            # resolved already: that's either coincidence, or - as found
            # in this data, where t0's BDI item labels turned out to be
            # shifted relative to their columns - a labelling error, and
            # trusting it would silently misalign already-correct matches
            ra, rb = resolved_group_id[anchor], resolved_group_id[other]
            if ra is not None and rb is not None and ra != rb:
                skipped.append((anchor, other))
                continue
            label_edges.append((anchor, other))

    if skipped:
        logger.info(
            f"harmonize_columns: ignored {len(skipped)} label match(es) that would have "
            f"merged two independently name-matched groups (likely coincidental or a "
            f"source labelling error, not a real match): {skipped}"
        )

    edges = [
        (a, b)
        for a, b in stem_edges + label_edges
        if a not in EXCLUDED_FROM_MATCHING and b not in EXCLUDED_FROM_MATCHING
    ] + MANUAL_CROSSWALK

    if missing := {n for edge in edges for n in edge} - set(nodes):
        raise ValueError(f"MANUAL_CROSSWALK references column(s) not found in any wave: {missing}")

    groups = _union_find_groups(nodes, edges)

    rename_map: dict = {wave: {} for wave in frames}
    for group in groups:
        waves_covered = {w for w, _ in group}
        if len(waves_covered) < 2:
            continue  # single-wave: keep the original name, not a cross-wave match
        stem_counts = Counter(stem[n] for n in group)
        # most common stem wins; ties broken alphabetically for determinism
        canonical = min(stem_counts, key=lambda s: (-stem_counts[s], s))
        for wave, col in group:
            rename_map[wave][col] = canonical

    renamed = {}
    for wave, frame in frames.items():
        renamed[wave] = frame.rename(columns=rename_map[wave], errors="raise")
        if not renamed[wave].columns.is_unique:
            dup_names = (
                renamed[wave].columns[renamed[wave].columns.duplicated(keep=False)].unique()
            )
            report = []
            for dup in dup_names:
                raw_names = [raw for raw, final in rename_map[wave].items() if final == dup]
                for raw in raw_names:
                    report.append(
                        f"  {raw!r} (stem={stem[(wave, raw)]!r}, label={label_maps[wave].get(raw, '')!r}) -> {dup!r}"
                    )
            raise ValueError(
                f"{wave}: renaming produced duplicate column(s) {list(dup_names)}. "
                f"These raw columns were merged into the same name, likely via a "
                f"coincidental cross-wave label match:\n" + "\n".join(report)
            )

    return renamed


def read_variable_labels(path) -> dict:
    with pd.io.stata.StataReader(path) as reader:
        return reader.variable_labels()


def attach_medications(t3: pd.DataFrame, meds: pd.DataFrame) -> pd.DataFrame:
    """Merge the one-row-per-patient T3 medication export onto the T3 visit.

    The detailed drug-slot breakdown in ``meds`` was only collected at T3,
    unlike the summary medication fields already present in every wave's own
    frame - so this is a single merge into t3, not a repeated-wave field.
    """
    overlap = (set(t3.columns) & set(meds.columns)) - {"Pat_ID"}
    if overlap:
        raise ValueError(f"medication export shares column names with T3: {sorted(overlap)}")

    unmatched = set(meds["Pat_ID"]) - set(t3["Pat_ID"])
    if unmatched:
        raise ValueError(
            f"{len(unmatched)} patient(s) in the medication export are absent from T3 "
            f"and would be dropped: {sorted(unmatched)[:10]}"
        )

    return t3.merge(meds, on="Pat_ID", how="left", validate="one_to_one")


def broadcast_time_independent(long: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Copy each patient's baseline (month 0) value to all of their visit rows.

    Baseline is treated as authoritative and simply overwrites whatever is
    in the other three rows for these columns - it does not try to
    reconcile disagreements. That matters here: some of these columns
    coincidentally also exist under the same harmonised name in another
    wave (data-entry re-asked at a later visit, or a coincidental match
    during column harmonisation), and those can disagree with baseline.
    Since these are meant to be fixed patient attributes, baseline wins by
    construction rather than raising on the conflict.

    If a patient has no value recorded at month 0, every one of their rows
    is left NaN for that column - never fabricated from another wave.
    """
    long = long.copy()

    if missing := [c for c in columns if c not in long.columns]:
        raise ValueError(f"time-independent column(s) not found: {missing}")

    baseline = long.loc[long["follow_up_months"] == 0, ["patient_id"] + columns]
    if not baseline["patient_id"].is_unique:
        raise ValueError("more than one month-0 row per patient - grain violated")
    baseline = baseline.set_index("patient_id")

    for col in columns:
        overwritten = long[col].notna() & (long["follow_up_months"] != 0)
        conflicts = overwritten & (long[col] != long["patient_id"].map(baseline[col]))
        if conflicts.any():
            offenders = sorted(long.loc[conflicts, "patient_id"].unique())
            logger.warning(
                f"broadcast_time_independent: {col!r} disagreed with baseline for "
                f"{len(offenders)} patient(s) at a non-baseline visit; baseline value "
                f"kept: {offenders[:10]}"
            )
        long[col] = long["patient_id"].map(baseline[col])

    return long


def to_long(frames: dict[str, pd.DataFrame], patient_level: pd.DataFrame) -> pd.DataFrame:
    """Stack the four visits and attach the patient-level attributes.

    Rows for patients who did not attend a given wave are kept, not dropped:
    they carry no substantive data (confirmed by inspection - see the
    project conversation history), but ``attended_t{n}`` in patient_level
    records that explicitly, and dropping them would understate the trial's
    full randomised cohort for anyone computing attrition later.
    """
    prepared = []
    for wave, months in VISIT_MONTHS.items():
        visit = frames[wave].copy()
        visit["follow_up_months"] = months
        prepared.append(visit)

    expected_rows = sum(len(frame) for frame in prepared)

    long = pd.concat(prepared, ignore_index=True, join="outer", sort=False)

    if len(long) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, concatenated {len(long)}")

    long = long.rename(columns={"Pat_ID": "patient_id"}, errors="raise")
    patient_level = patient_level.rename(columns={"Pat_ID": "patient_id"}, errors="raise")

    long = long.merge(patient_level, on="patient_id", how="left", validate="many_to_one")

    if long.duplicated(GRAIN).any():
        offenders = long.loc[long.duplicated(GRAIN, keep=False), GRAIN]
        raise ValueError(f"duplicate {tuple(GRAIN)} rows: {len(offenders)}")

    long = long.sort_values(GRAIN, kind="stable").reset_index(drop=True)

    # fields recorded once at baseline describe the patient, not the visit,
    # so copy each patient's value onto all four of their rows
    long = broadcast_time_independent(long, TIME_INDEPENDENT_COLS)

    patient_level_cols = [c for c in patient_level.columns if c != "patient_id"]
    first_columns = GRAIN + patient_level_cols + TIME_INDEPENDENT_COLS
    remaining_columns = [c for c in long.columns if c not in first_columns]
    long = long[first_columns + remaining_columns]
    long = long.drop(columns=["DIAGNOSE", "VERSORGU", "ANAMESE", "bdi", "ICD10CHE", "ATCmedic"])

    return long


def load() -> pd.DataFrame:
    """Read, harmonise, and stack the PRoMPT exports into long format."""
    t0, t1, t2, t3, meds, patient_level = build()
    t3 = attach_medications(t3, meds)
    frames = {"t0": t0, "t1": t1, "t2": t2, "t3": t3}
    return to_long(frames, patient_level).convert_dtypes()


def build():
    t0 = read_and_clean(DATA_DIR / "PRoMPT_Daten_T0_09082010_final.dta")
    t1 = read_and_clean(DATA_DIR / "PRoMPT_Daten_T1_09082010_final.dta")
    t2 = read_and_clean(DATA_DIR / "PRoMPT_Daten_T2_09082010_final.dta")
    t3 = read_and_clean(DATA_DIR / "PRoMPT_T3_2010_08_09.dta")
    meds = read_and_clean(DATA_DIR / "PRoMPT_T3_Medikamente_2009_03_17.dta")

    # variable labels are read from the untouched files, before any renaming
    label_maps = {
        "t0": read_variable_labels(DATA_DIR / "PRoMPT_Daten_T0_09082010_final.dta"),
        "t1": read_variable_labels(DATA_DIR / "PRoMPT_Daten_T1_09082010_final.dta"),
        "t2": read_variable_labels(DATA_DIR / "PRoMPT_Daten_T2_09082010_final.dta"),
        "t3": read_variable_labels(DATA_DIR / "PRoMPT_T3_2010_08_09.dta"),
    }

    # --- patient-level attributes duplicated into every visit file ---

    # study arm: assigned once at randomisation. t2's copy is corrupted by
    # the Stata sentinel bug for 2 patients, so t0 is used as the source.
    study_arm = t0[["Pat_ID", "Gruppe"]].rename(columns={"Gruppe": "study_arm"})

    # attendance: t{n}da marks whether the patient was present at visit n
    # ("Patient zu T{n} anwesend"), not a date despite the column name.
    attendance = t0[["Pat_ID", "t0da", "t1da", "t2da", "t3da"]].rename(
        columns={
            "t0da": "attended_t0",
            "t1da": "attended_t1",
            "t2da": "attended_t2",
            "t3da": "attended_t3",
        }
    )

    # treatment status ("Behandlungsstatus"): identical, confirmed by zero
    # row-level disagreement, across t0's BehanSta ("Start / Maintenance"
    # framing), t1's Behandlu and t2's Behandst ("dichotom" framing) - same
    # variable, relabelled as the study progressed. Sourced from t0 since
    # it's present earliest.
    treatment_status = t0[["Pat_ID", "BehanSta"]].rename(columns={"BehanSta": "treatment_status"})

    patient_level = study_arm.merge(
        attendance, on="Pat_ID", how="outer", validate="one_to_one"
    ).merge(treatment_status, on="Pat_ID", how="outer", validate="one_to_one")

    t0 = t0.drop(columns=["Gruppe", "t0da", "t1da", "t2da", "t3da", "BehanSta"])
    t1 = t1.drop(columns=["Gruppe", "t0da", "t1da", "t2da", "t3da", "Behandlu"])
    t2 = t2.drop(columns=["Gruppe", "t0da", "t1da", "t2da", "t3da", "Behandst"])
    t3 = t3.drop(columns=["GruppeT3", "t0da", "t1da", "t2da", "t3da"])
    meds = meds.drop(columns=["Gruppe"])

    # --- t1 form-page Pat_ID copies: a patient whose Patienten_ID was
    # re-entered inconsistently across T1 form pages had at least one
    # transcription error during data entry, so the whole patient record is
    # dropped from every wave rather than trusted. (Pat_ID itself matches
    # the majority value in each case, so this is conservative - it discards
    # patients whose canonical ID is probably fine.) ---
    patid_check_cols = ["PatID16", "PatID17", "PatID18", "PatID19"]
    mismatched_ids = t1.loc[
        (t1[patid_check_cols].ne(t1["Pat_ID"], axis=0)).any(axis=1), "Pat_ID"
    ].tolist()

    if mismatched_ids:
        logger.warning(
            f"Dropping {len(mismatched_ids)} patient(s) with a mismatched Patienten_ID "
            f"on one or more T1 form pages: {mismatched_ids}"
        )
        t0 = t0[~t0["Pat_ID"].isin(mismatched_ids)]
        t1 = t1[~t1["Pat_ID"].isin(mismatched_ids)]
        t2 = t2[~t2["Pat_ID"].isin(mismatched_ids)]
        t3 = t3[~t3["Pat_ID"].isin(mismatched_ids)]
        meds = meds[~meds["Pat_ID"].isin(mismatched_ids)]
        patient_level = patient_level[~patient_level["Pat_ID"].isin(mismatched_ids)]

    # --- administrative/tracking noise and redundant Pat_ID copies ---
    t1 = t1.drop(columns=ADMIN_COLS["t1"])
    t2 = t2.drop(columns=ADMIN_COLS["t2"])
    t3 = t3.drop(columns=ADMIN_COLS["t3"])

    t0 = drop_patid_variants(t0)
    t1 = drop_patid_variants(t1)
    t2 = drop_patid_variants(t2)
    t3 = drop_patid_variants(t3)
    meds = drop_patid_variants(meds)

    # --- constant instrument-name tags with their original raw spelling
    # (single repeated value, no patient information) ---
    t0 = t0.drop(columns=PRE_RENAME_CONSTANT_TAG_COLS["t0"])
    t1 = t1.drop(columns=PRE_RENAME_CONSTANT_TAG_COLS["t1"])
    t2 = t2.drop(columns=PRE_RENAME_CONSTANT_TAG_COLS["t2"])

    # --- harmonise time-varying column names across waves ---
    frames = {"t0": t0, "t1": t1, "t2": t2, "t3": t3}
    frames = harmonize_columns(frames, label_maps)

    # --- the same kind of constant instrument-name tags, but only visible
    # under their final name once the rename passes above have run ---
    frames["t1"] = frames["t1"].drop(columns=POST_RENAME_CONSTANT_TAG_COLS["t1"])
    frames["t2"] = frames["t2"].drop(columns=POST_RENAME_CONSTANT_TAG_COLS["t2"])

    return frames["t0"], frames["t1"], frames["t2"], frames["t3"], meds, patient_level


if __name__ == "__main__":
    long = load()
    print("long shape:", long.shape)
    print(
        long[
            GRAIN + ["study_arm", "attended_t0", "attended_t1", "attended_t2", "attended_t3"]
        ].head(8)
    )
