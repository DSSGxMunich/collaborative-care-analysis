from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import labeled_variables


def load(
    file_path=RAW_DATASETS_DIR / "08_Coventry_2015" / "coincide5_v12.dta",
):
    id_col = "patientid"
    baseline_date_col = "datecompleted2"
    followup_date_col = "datecompfollowup"

    admin_cols = {
        "patientid",
        "datecompleted2",
        "datecompfollowup",
        "datecompleted",
        "followup",
        "datefollowupdue",
        "timingoffollowup",
        "datecompaddsheet",
        "addsheet",
        "fup",
        "fupcomp",
        "fdatecompleted",
        "fdatecompleted2",
        "fupstartdate",
        "fupenddate",
        "lenfup",
    }

    df = pd.read_stata(file_path)
    # both date columns are stored as strings like "14-Jun-13" (DD-Mon-YY);
    # an explicit format avoids the dateutil fallback warning and any
    # ambiguity.
    date_format = "%d-%b-%y"
    df[baseline_date_col] = pd.to_datetime(
        df[baseline_date_col], format=date_format, errors="raise"
    )
    df[followup_date_col] = pd.to_datetime(
        df[followup_date_col], format=date_format, errors="raise"
    )

    # --- auto-detect baseline <-> follow-up column pairs -----------------
    pairs = {}  # baseline_col -> followup_col
    for col in df.columns:
        if col in admin_cols or not col.startswith("f"):
            continue
        base = col[1:]
        if base in df.columns and base not in admin_cols:
            pairs[base] = col

    baseline_cols = list(pairs.keys())
    followup_cols = list(pairs.values())
    logger.info(f"Auto-matched {len(pairs)} baseline/follow-up column pairs.")

    # --- columns with no baseline/follow-up pair --------------------------
    # non-"f" unpaired columns are treated as time-invariant (demographics,
    # randomisation arm, etc.) and broadcast to every row for a patient;
    # "f"-prefixed unpaired columns (e.g. fmult*, fpacic*, fsuq*) are
    # follow-up-only measures and only populated on the follow-up row --
    # pd.concat fills them with NaN on the baseline rows automatically since
    # base_df won't have these columns at all.
    unpaired_cols = [
        c
        for c in df.columns
        if c != id_col and c not in admin_cols and c not in pairs and c not in pairs.values()
    ]
    # drop undocumented unpaired columns: keep only those that also have a
    # non-null variable_label in the .dta file's own metadata (columns that
    # did auto-match via the f-prefix pairing above are always kept
    # regardless of label)
    labeled_vars = labeled_variables(file_path)
    undocumented = [c for c in unpaired_cols if c not in labeled_vars]
    unpaired_cols = [c for c in unpaired_cols if c in labeled_vars]
    logger.info(
        f"Dropped {len(undocumented)} unpaired columns with no variable_label "
        "in the source file's metadata."
    )
    logger.trace(undocumented)

    static_cols = [c for c in unpaired_cols if not c.startswith("f")]
    followup_only_cols = [c for c in unpaired_cols if c.startswith("f")]
    logger.trace(
        f"{len(static_cols)} time-invariant columns broadcast to all rows; "
        f"{len(followup_only_cols)} follow-up-only columns (NaN at baseline)."
    )

    # --- baseline rows -----------------------------------------------------
    base_df = df[[id_col] + baseline_cols + static_cols].copy()
    base_df["follow_up_months"] = 0.0

    # --- follow-up rows ------------------------------------------------
    fu_df = df[
        [id_col, baseline_date_col, followup_date_col]
        + followup_cols
        + static_cols
        + followup_only_cols
    ].copy()
    fu_df["follow_up_months"] = (
        fu_df[followup_date_col] - fu_df[baseline_date_col]
    ).dt.days / 30.4368

    # drop rows where the follow-up date is before the baseline date
    before_drop = len(fu_df)
    fu_df = fu_df[fu_df["follow_up_months"] >= 0]
    logger.trace(
        f"{before_drop - len(fu_df)} rows are dropped because follow-up date is before baseline date."
    )

    # give follow-up columns the same names as their baseline counterparts
    fu_df = fu_df.rename(columns={v: k for k, v in pairs.items()})
    fu_df = fu_df.drop(columns=[baseline_date_col, followup_date_col])

    # patients with no completed follow-up date only get a baseline row
    fu_df = fu_df.dropna(subset=["follow_up_months"])

    long_df = pd.concat([base_df, fu_df], ignore_index=True, sort=False)
    long_df = long_df.rename(columns={id_col: "patient_id"})

    dupes = long_df.duplicated(subset=["patient_id", "follow_up_months"], keep=False)
    if dupes.any():
        n_patients = long_df.loc[dupes, "patient_id"].nunique()
        logger.warning(
            f"Dropping {dupes.sum()} row(s) sharing a duplicated (patient_id, "
            f"follow_up_months) ({n_patients} patient(s) affected)."
        )
        long_df = long_df[~dupes]

    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)

    # convert to nullable types
    long_df = long_df.convert_dtypes()

    return long_df[
        ["patient_id", "follow_up_months"]
        + [col for col in list(long_df.columns) if col not in ["patient_id", "follow_up_months"]]
    ]
