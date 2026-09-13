# Column Harmonization Task — All Risk-Dimension Clusters

## Objective
Harmonize columns across all collaborative-care studies that have a `load()` function
and are exported to `data/interim/exported_datasets/`, covering the full set of risk
dimensions below (not just socioeconomic status), to support downstream regression
modeling of health outcomes.

Iezzoni's dimensions of risk that should be captured by predictor variables:
1. age
2. sex
3. acute clinical stability
4. principal diagnosis
5. severity of principal diagnosis
6. extent and severity of comorbidities
7. physical functional status
8. psychological, cognitive, and psychosocial functioning
9. cultural, ethnic, and socioeconomic attributes and behaviors
10. health status and quality of life
11. patient attitudes and preferences for outcomes

Baseline covariates to also capture where present:
1. a baseline measurement of the response variable
2. the subject's most recent status
3. the subject's trajectory as of time zero / past levels of a key variable
4. variables explaining much of the variation in the response
5. subtler predictors whose distributions differ strongly between levels of a key
   exposure/comparison variable

Goal: reduce the number of related raw columns while minimizing sparsity. The final
number of harmonized variables per cluster is determined by your analysis of what can
be meaningfully consolidated — not a preset target.

## Additional required scope: measurement instruments across all follow-up points

Beyond the 11 Iezzoni dimensions and 5 baseline-covariate points above, **explicitly harmonize the
standardized measurement instruments used across studies** — e.g. PHQ-9 (both
item-level, `phq9_1`…`phq9_9`, and the summed/total score), GAD-7, SCL-20, and any
other repeated instrument that appears in more than one study. This doesn't map onto
a single Iezzoni dimension (an instrument can feed outcome severity, comorbidity, or
functional status depending on the study) and isn't fully covered by the existing
`harmonization_outcomes/*.py` scripts either, since those are per-study and only at
whatever follow-up points that one study's script happens to handle — so treat it as
its **own explicit target cluster**, run through the same Step 2 → Step 3 (checkpoint)
→ Step 4 process as every other cluster, not an afterthought bundled into another one.

Key requirement: harmonize each instrument **consistently across every follow-up point
it was administered at**, not just baseline — `follow_up_months` already carries the
timing, so a harmonized `phq9_total` (for example) should be populated for every row
where any study recorded a PHQ-9 at that visit, using the same item-level → total
scoring logic everywhere it applies. Check for and flag: studies that only report the
total (no items), studies with a different item count/wording for a "same-named"
instrument, and studies whose total was pre-computed with a different formula (e.g.
mean vs. sum, as with `scl20_mean`) — surface these as judgment calls at the Step 3
checkpoint, don't silently normalize them.

## Additional required scope: clinical override / censoring events

Beyond the 11 Iezzoni dimensions, the 5 baseline-covariate points and the
measurement-instruments cluster, **explicitly harmonize clinically-driven events that
override or truncate a patient's observed trajectory** — death, hospitalization, and
any recorded reason for leaving the study (withdrawal, loss to follow-up, clinician
or investigator decision, transfer, ineligibility discovered post-randomization).

Rationale for making this its own cluster rather than folding it into an existing one:
the Iezzoni dimensions describe a patient's risk **at time zero**, whereas these are
events occurring **during follow-up**. They are neither baseline risk factors nor
outcome instrument scores, but they determine whether a later measurement is missing
for an ignorable reason or a clinically informative one — which directly affects any
downstream regression of health outcomes (informative censoring, competing risks).
Leaving them in `unclustered_columns.json` as "triage later" would under-serve them.

Note the one genuine overlap to resolve at the Step 3 checkpoint rather than silently:
a **baseline-measured** hospitalization history (e.g. "admitted in the 6 months before
enrollment") is a *risk factor* and belongs to dimension 3 (acute clinical stability)
or dimension 6 (comorbidity burden), **not** here. Only the during-follow-up event
belongs in this cluster. Where a study's column is ambiguous about timing, surface it
as a judgment call.

Target harmonized variables (final set determined by the Step 2 inventory):
- vital status / death, and where available its timing relative to baseline
- hospitalization occurrence during follow-up, and where available count/timing
- study discontinuation flag plus a harmonized, descriptive discontinuation reason
  (descriptive labels, not numeric codes, per `HARMONIZATION_CONVENTIONS.md`)

Run this through the same Step 2 → Step 3 (checkpoint) → Step 4 process as every
other cluster.

## Additional required scope: study eligibility criteria

Each study's inclusion/exclusion criteria (from its paper/protocol, not the IPD) are
its own cluster too. They're study-level facts, joined onto the concatenated frame by
`STUDY_ID` -- like `enrichment.py`'s `study_level_extra_infos` -- not authored per row.

Source: `data/raw/annotations/study_eligibility_criteria.csv` (tracked; one row per
study/criterion, columns: `study_id, domain, polarity, criterion, structured_check,
source, verified, notes`). Only `verified: yes` rows feed the harmonized cluster.
Split by `domain` (age, comorbidity_substance, psychiatric, cognitive, ...), not by
polarity -- the same criterion is often phrased as either.

Also useful to the OTHER clusters: a raw column's "0% prevalence" can mean "not
measured" or "excluded by design" -- criteria disambiguate that before those clusters
are harmonized.

## Ground rules — read first

- **Strictly follow `AGENTS.md`** at the repo root for data-privacy handling. In short:
  never print, log, `head()`, `sample()`, or otherwise view row-level/patient-level
  data; only schema/metadata and aggregates are allowed. Use
  `uv run python -m collaborative_care_analysis.agent.inspect_metadata <id> [--values|--stats|--grep]`
  to inspect columns/codes/aggregates instead of opening raw files.
- **Strictly follow `HARMONIZATION_CONVENTIONS.md`** at the repo root for naming and
  formatting conventions already used in this repo (snake_case descriptive names,
  long/row-wise format, numeric codes → descriptive categorical labels with missing
  staying missing, `follow_up_months` with baseline = 0, consistent outcome-scale
  naming). Match this style even though you're writing to a new location.
- **Do not modify any `load()` function** in `collaborative_care_analysis/data_loading/`,
  and do not modify the existing `harmonization_baseline/medical_history/outcomes/treatment`
  scripts. Treat the output of each study's `load()` (already reshaped to long format)
  as valid, as-is.
- **`STUDY_ID` is not present in the raw exported CSVs.** It's only added later in the
  existing `harmonize` pipeline, derived from the loader script's filename stem (e.g.
  `ds_17_Katon_2001.py` → `"17_Katon_2001"`). In `data/interim/exported_datasets/`, the
  only identifier is the **export filename itself**
  (`exported_datasets/ds_17_Katon_2001.csv`). When you concatenate, derive `STUDY_ID`
  for each row the same way (from the export filename stem) — do not invent a
  different scheme, and do not go back and add `STUDY_ID` inside `load()`.
- Code you write will eventually be committed to GitHub. Write it as you would any
  reviewable PR: clear docstrings, comments explaining *why* a mapping/harmonization
  decision was made (not just what), no leftover debug/print statements, no dead code.
  Where reasonable, mirror the structure already used in `harmonization_*/*.py`
  (e.g. `map_with_check()` from `collaborative_care_analysis/utils.py` for coded→label
  mapping, an explicit ID-columns list, per-study comments citing the study/codebook).
- **Study the existing `harmonization_baseline/medical_history/outcomes/treatment`
  scripts before designing anything** — they're not just a style reference, they
  encode real prior harmonization decisions and error-checking conventions you should
  reuse rather than reinvent:
  - `map_with_check(series, mapping)` (`collaborative_care_analysis/utils.py`) maps a
    coded column through a dict and **asserts every non-null value is covered** by
    the mapping, raising loudly instead of silently turning an unexpected code into
    NaN (see `harmonization_baseline/ds_17_Katon_2001.py`'s `SEX_MAPPING`). Use it for
    every coded→label mapping in this task, including new clusters.
  - Numeric fields are coerced with `pd.to_numeric(col, errors="raise")`, not
    `errors="coerce"` — an unparseable value should fail the run, not silently become
    NaN (same file, `age`).
  - Continuous/composite scores are kept continuous, not forced into bins, when the
    instrument itself is continuous — e.g. `harmonization_medical_history/ds_17_Katon_2001.py`
    keeps `chronic_disease_score` as a numeric Von Korff/Clark score with a comment
    explaining it's "not a simple count." Apply the same judgment to any composite
    functional-status/comorbidity index you harmonize.
  - `harmonization_outcomes/*.py` comments explicitly state which instrument/scale a
    column is (e.g. "Depression severity = SCL-20 (mean of the 20 depression items of
    the SCL-90, 0-4 scale)") and call out **which other studies use the exact same
    construct/column name** so cross-study equivalence is documented, not assumed.
    Do this for every harmonized variable you create.
  - `harmonization_treatment/*.py` shows how to turn a free-text/coded trial-arm
    column into a small set of **descriptive** values (`control`,
    `intervention_feedback`, `intervention`, not `0`/`1`/`2`), with a comment
    explaining what each arm clinically means. Use the same descriptive-value
    convention for any categorical harmonized variable.
  - Every script returns **only** `ID_COLS + <its own cluster's columns>` — it does
    not carry along unrelated columns. Keep the same discipline: don't let one
    cluster's implementation pull in columns that belong to another cluster.

## Studies in scope

**All studies that have a `load()` function are in scope — not a year-filtered
subset.** Discover them the same way the pipeline does: every `*.py` file (other than
`__init__.py`) under `collaborative_care_analysis/data_loading/` defines a `load()`,
and gets exported to `data/interim/exported_datasets/` as `ds_<NN>_<Author>_<Year>.csv`.
As of writing there are 30 such studies (IDs 02–33, with gaps), spanning 1995–2022, but
**derive the list programmatically from `data_loading/` rather than hardcoding it** —
new studies may be added to the repo later.

If `data/interim/exported_datasets/` doesn't already contain a CSV for every loader
script, run:
```bash
uv run collaborative_care_analysis/dataset.py export
```

## Step 1 — Concatenate raw exports

- Load every CSV in `data/interim/exported_datasets/` (one per study with a `load()`).
- Derive `STUDY_ID` per file from its filename stem (see "Ground rules" above) and
  insert it as the first column.
- Concatenate vertically (already long format) into one dataframe.
- Confirm join keys are present: `STUDY_ID`, `patient_id`, `follow_up_months`.
- Do **not** apply any existing `harmonization_*` script — work from the raw columns.

## Step 2 — Inventory columns per cluster

For each of the 11 Iezzoni dimensions, 5 baseline-covariate points, **the
measurement-instruments cluster, and the clinical-override/censoring-events cluster**
(see above), identify the raw columns across all
in-scope studies that plausibly belong to it. A column may belong to more than one
candidate cluster — note that rather than forcing a single bucket. For instruments
specifically, inventory item-level and total/summed columns separately, and record
which follow-up points (`follow_up_months` values) each study has them at.

Keep a running **"unclustered" list**: every raw column (per study) that does not
plausibly fit any of the 11 Iezzoni dimensions, 5 baseline-covariate points, or the measurement-instruments cluster. You'll need this for Step 4a.

For each candidate column, document:
1. Column name in the concatenated dataframe
2. Which studies have it populated vs. missing
3. Data type and coding scheme (use `inspect_metadata --values`, not raw rows)
4. % missing (sparsity)
5. Cardinality / unique values

**Resources**:
- Per-study codebook/paper: `data/raw/Individual Datasets/<NN>_<Author>_<Year>/`
  (contains `Codebook_<Author et al.> (<Year>).xlsx` and a loose `<Author> <Year>.pdf`).
- Machine-generated codebook (variable/value labels extracted from `.sav`/`.dta`
  metadata, no row data): `data/interim/generated_codebooks/<NN>_<Author>_<Year>/*_metadata.xlsx`.
- Use the original papers to understand what an instrument/item was actually measuring
  before assuming two similarly-named columns are the same construct.

## Step 3 — Per-cluster design proposal — MANDATORY CHECKPOINT

This is the most important process rule in this task, and it replaces any instinct to
harmonize everything in one continuous pass:

**For each cluster, before writing any harmonization code or columns:**
1. Present your inventory from Step 2 for that cluster (coverage, sparsity, coding
   schemes across studies).
2. Propose a concrete harmonization design: target variable(s), categories/levels,
   the mapping logic from each raw column, and what evidence from the codebook/paper
   supports treating two raw columns as the same construct.
3. Explicitly flag any decision that is a judgment call rather than a mechanical
   mapping (e.g. "these two employment codings differ in whether 'student' counts as
   'not working' — I'm treating them as equivalent unless you say otherwise").
4. **Stop and wait for my explicit approval or edits before implementing that
   cluster.** Do not proceed to the next cluster's inventory until the current one is
   approved and implemented.

This is deliberately interactive — prioritize getting my domain guidance right over
speed. Where studies take genuinely different approaches to a concept (e.g. very
different comorbidity indices), surface that as a decision point rather than silently
picking one.

## Step 4 — Implement approved cluster

Once a cluster's design is approved:
- Create the new harmonized column(s) using `map_with_check()` (from
  `collaborative_care_analysis/utils.py`) or clearly documented direct logic.
- Keep `STUDY_ID`, `patient_id`, `follow_up_months` on every row.
- Optionally retain original raw columns, prefixed `raw_`, for reference.
- Apply the same mapping logic uniformly across the whole concatenated dataframe —
  no per-study special-casing beyond what's needed to normalize differing raw codes
  into the same target scheme.
- Log progress as you go (see "Checkpointing" below) so a later run can pick up
  exactly where this one left off, without redoing approved clusters.
- **Immediately after implementing, append this cluster's section to
  `harmonization_report.md`** (create the file on the first cluster). Do this as part
  of Step 4 itself, not deferred to the end of the whole task — see Step 5 for the
  exact section format. The report should always be a truthful, complete account of
  every cluster implemented so far, never a stale draft waiting to be "written up
  properly" later.

## Step 4a — Strategy for columns outside the 19 target clusters

Not every raw column will fit one of the 11 Iezzoni dimensions or 5 baseline-covariate
points (e.g. study logistics, site/clinic identifiers, follow-up-specific process
variables). Don't force these into a cluster, and don't silently drop them either —
this run should leave a clean on-ramp for a **follow-on harmonization pass** that
covers whatever's left over:

- Maintain `unclustered_columns.json` in the output folder: a dict keyed by raw column
  name (or `<study_id>::<column_name>` where names collide across studies with
  different meanings) → `{studies_present: [...], dtype, pct_missing, sample_notes}`.
  Populate it from the "unclustered" list you kept in Step 2.
- For each entry, add a short one-line guess at why it didn't fit a dimension (e.g.
  "site-level indicator, not patient-level risk factor" or "possibly principal
  diagnosis-adjacent but coding scheme unclear — needs codebook review"), so a future
  session can triage quickly instead of starting from zero.
- This file's schema should be treated as a stable contract: a future harmonization
  task should be able to `json.load()` it and start its own Step 2 (inventory) from
  its keys directly.

## Step 5 — Save results

Output location: new folder `data/interim/column_clusters_harmonized/`
(don't reuse or write into any existing `harmonization_*` folder).

- `harmonized_data.csv` — `STUDY_ID`, `patient_id`, `follow_up_months` + all approved
  harmonized columns (+ optional `raw_*` columns).
- `column_mapping.json` (or `.csv`) — for every harmonized column: which raw columns
  it consolidates, the mapping/transformation logic, which studies contributed data
  vs. had it missing.
- `unclustered_columns.json` — see Step 4a; the input for a future follow-on
  harmonization pass over whatever wasn't covered by the 19 target clusters (11
  Iezzoni dimensions, 5 baseline-covariate points, measurement instruments,
  clinical-override/censoring events).
- `harmonization_report.md` — **built incrementally, one section appended per cluster
  as it's implemented (Step 4), not written once at the end.** Each run that
  implements a cluster must leave this file up to date for every cluster implemented
  so far. Structure:
  - A short **status header at the top** (rewritten each time, not appended):
    clusters implemented so far / 19, last updated, at-a-glance table of cluster →
    harmonized column(s) → sparsity before → sparsity after.
  - One **section per implemented cluster**, in implementation order, each with:
    - definition and categories of the harmonized variable(s)
    - original columns consolidated, and which studies had each
    - **a succinct one-paragraph summary**: coverage/sparsity improvement (e.g.
      "sparsity dropped from 61% to 12% non-missing across 14/17 studies") and which
      raw columns mapped to which harmonized value(s) — this is what a reviewer reads
      first; the detail below it is for anyone who wants the full reasoning
    - sparsity before vs. after (% non-missing), per study if it varies notably
    - **which decisions were human judgment calls (and what was decided), vs.
      mechanical/uncontroversial mappings** — extensive enough that a reviewer can
      audit *why* the harmonization looks the way it does, not just what it produced
    - any information loss / edge cases
  - Once all 19 clusters are `implemented` (see Checkpointing), add a final overall-
    stats section: total columns reduced, overall sparsity improvement, cluster-by-
    cluster coverage across all in-scope studies, and a summary of what landed in
    `unclustered_columns.json`.

## Checkpointing — resuming across sessions/rate limits

This task spans 19 target clusters (11 Iezzoni dimensions, 5 baseline-covariate points, measurement instruments, clinical-override/censoring events, plus study eligibility criteria), each gated on my approval (Step 3) — it will
not finish in one sitting. Treat it as resumable from the start:

- Maintain a `progress.json` in the output folder: one entry per dimension/covariate,
  with status `not_started` / `inventoried` / `awaiting_approval` /
  `approved_pending_implementation` / `implemented`, plus the harmonized column names
  it produced once implemented.
- At the start of any session (including a fresh one after a restart), read
  `progress.json` first and resume from the first non-`implemented` entry — don't
  re-inventory or re-propose a cluster that's already `implemented`, and don't
  silently re-derive `harmonized_data.csv`/`column_mapping.json` from scratch each
  time; load and extend them.
- After each cluster reaches `implemented`, write out the current
  `harmonized_data.csv`, `column_mapping.json`, `progress.json`, **and the
  corresponding section in `harmonization_report.md`** so a stop at any point (rate
  limit, session end, manual interruption) loses at most one in-flight cluster, never
  earlier work — and the report is never behind the data.
- If a cluster is left `awaiting_approval` when a session ends, say so explicitly at
  the end of that session/turn, so it's obvious the next session should start by
  presenting that same proposal rather than moving on.

**How this gets re-invoked, operationally**: because each cluster needs my explicit
approval, this is not meant to run fully unattended end-to-end. The intended pattern
is: a scheduled/looped wake-up resumes the task, does inventory + proposes the next
un-approved cluster (Steps 2–3), then **stops and waits** — it cannot approve on its
own behalf — and I approve asynchronously between wake-ups; the next wake-up then
implements what was approved (Step 4) and moves to the following cluster.

If this session gets re-invoked as a **brand-new session** (e.g. after a rate-limit
reset via a scheduled task, rather than a resumed thread), it must **not** trust its
own memory/conversation history as the source of truth — `progress.json`, the current
`harmonized_data.csv`, and `column_mapping.json` on disk are authoritative. Re-read
them first, in every session, before doing anything else, even if this looks like a
continuation of a conversation you "remember."

## Step 6 — Validation

- All in-scope studies present (`STUDY_ID` values cover every loader in
  `data_loading/`)
- Row count matches the sum of all exports
- Each harmonized column has meaningfully fewer missing values than the raw columns
  it replaces
- Same mapping logic applied consistently across studies (no undocumented per-study
  branching)
- Nothing overwritten — raw exports and existing `harmonization_*` folders untouched

## Data privacy constraint (from AGENTS.md)

You MAY: query aggregate stats/value counts, check unique values/coding schemes via
`inspect_metadata`, read codebooks/protocols/papers, examine schema/structure.

You must NOT: view row-level/patient-level data, print or save sample records, look at
identifiable information, or compute subgroup summaries that could re-identify
individuals.

## Success criteria

- All studies with a `load()` function concatenated, `STUDY_ID` correctly derived
  from export filenames, no `load()` function modified
- All 11 Iezzoni dimensions + 5 baseline-covariate points addressed (or explicitly
  noted as "no usable raw columns found," not silently skipped)
- The measurement-instruments cluster (PHQ-9 item-level + total, GAD-7, SCL-20, and
  any other repeated instrument) is harmonized consistently across every follow-up
  point it was administered at, not just baseline
- Every cluster's design was proposed and approved by me before implementation
- Harmonized variables meaningfully reduce dimensionality and sparsity vs. raw columns
- Existing `harmonization_*/*.py` conventions reused: `map_with_check()` for coded
  mappings, `errors="raise"` numeric coercion, descriptive (not numeric-coded)
  category values, continuous scores kept continuous, per-variable comments citing
  the instrument/scale and cross-study equivalence
- `unclustered_columns.json` captures every raw column left out of the 19 target
  clusters, ready to seed a follow-on harmonization pass
- `progress.json` accurately reflects per-cluster status so the task is resumable
  after a rate limit or session restart without redoing approved clusters
- `harmonization_report.md` documents human-judgment decisions extensively enough to
  be auditable
- Code is documented and structured to the standard of a real PR to this repo (per
  `HARMONIZATION_CONVENTIONS.md` and the existing `harmonization_*/*.py` style)
- Output isolated to `data/interim/column_clusters_harmonized/`; nothing else touched
- No raw row-level data was ever viewed, printed, or saved (AGENTS.md compliance)
