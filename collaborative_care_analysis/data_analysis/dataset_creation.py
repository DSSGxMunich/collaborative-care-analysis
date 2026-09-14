from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import DATA_DIR


def _report(msg, df):
    logger.info(f"{msg:<70}{df.shape!s:>10}")


def _drop_patients_matching(df, mask, msg):
    """Drop every row belonging to any patient with >=1 row matching `mask`."""
    to_drop = df.loc[mask, ["STUDY_ID", "patient_id"]]
    df = df.merge(to_drop.assign(_drop=True), on=["STUDY_ID", "patient_id"], how="left")
    df = df.loc[df["_drop"].isna()].drop(columns="_drop")
    _report(msg, df)
    return df


def _keep_patients_with_any(df, mask, msg):
    """Keep only patients with >=1 row matching `mask`; drop everyone else entirely."""
    keep_ids = df.loc[mask, ["STUDY_ID", "patient_id"]].drop_duplicates()
    df = df.merge(keep_ids.assign(_keep=True), on=["STUDY_ID", "patient_id"], how="left")
    df = df.loc[df["_keep"].notna()].drop(columns="_keep")
    _report(msg, df)
    return df


def _broadcast_within_patient(df, col):
    """Forward/back-fill a time-invariant column across all of a patient's rows."""
    df[col] = (
        df.groupby(["STUDY_ID", "patient_id"])[col]
        .transform(lambda s: s.ffill().bfill())
        .infer_objects(copy=False)
    )
    return df


def _clean() -> pd.DataFrame:
    """Shared cleaning pipeline, producing the long-format analysis dataset
    (baseline row + 12mo row per patient). Used as the basis for both
    create_long() and create_wide()."""
    df = pd.read_csv(
        DATA_DIR / "interim" / "enriched_dataset" / "enriched_dataset.csv", low_memory=False
    )
    _report("original shape of merged_df", df)

    # convert phq9_total to int and drop rows that would be truncated
    df = df[df["phq9_total"].mod(1).eq(0)].astype({"phq9_total": "int32"})
    _report("shape after truncation-safe int conversion of phq9_total", df)

    # drop studies which have no phq9_total
    df = df.groupby("STUDY_ID").filter(lambda g: g["phq9_total"].notna().any())
    _report("shape after dropping studies with no phq9_total", df)

    # drop patients with no valid baseline phq9_total row at all
    df = _keep_patients_with_any(
        df,
        df["follow_up_months"] == 0.0,
        "shape after dropping patients with no baseline phq9_total",
    )

    # drop patients with no follow-up row in [11.5, 12.5] at all
    df = _keep_patients_with_any(
        df,
        df["follow_up_months"].between(11.5, 12.5),
        "shape after dropping patients with no follow_up at 12mo",
    )

    # drop follow-ups outside of [11.5, 12.5] or != 0 months post-randomization
    df = df.loc[df["follow_up_months"].between(11.5, 12.5) | (df["follow_up_months"] == 0.0)]
    _report("shape after restricting to 11.5-12.5 month window", df)

    # drop patients with a missing age for all follow-up timepoints
    # broadcast age if present at at least one follow-up (we assume age is age at baseline)
    df = _broadcast_within_patient(df, "age")
    df = df.groupby(["STUDY_ID", "patient_id"]).filter(lambda g: g["age"].notna().any())
    _report("shape after dropping patients with missing age", df)

    # broadcast sex within patient if present at >=1 timepoint
    df = _broadcast_within_patient(df, "sex")

    # drop patients missing sex at every timepoint
    df = df.groupby(["STUDY_ID", "patient_id"]).filter(lambda g: g["sex"].notna().any())

    # now safe to convert to category, after fill/drop
    logger.debug(f"sex labels: {df['sex'].unique()}")  # sanity check labels before casting
    df["sex"] = df["sex"].astype("category")
    _report("shape after dropping patients with missing sex", df)

    # drop patients with missing study_arm
    df = _broadcast_within_patient(df, "study_arm")
    df = _drop_patients_matching(
        df,
        df["study_arm"].isna(),
        "shape after dropping patients with missing study_arm",
    )

    # drop patients with missing gad7_total at baseline
    df = _drop_patients_matching(
        df,
        df["gad7_total"].isna() & (df["follow_up_months"] == 0.0),
        "shape after dropping patients with missing gad7_total at baseline",
    )

    # drop patients with sex=Other
    df = _drop_patients_matching(
        df,
        df["sex"] == "Other",
        "shape after dropping patients with sex=Other",
    )

    return df


def create_long(save: bool = True) -> pd.DataFrame:
    """Long-format analysis dataset: baseline row + 12mo row per patient."""
    df = _clean()

    if save:
        path = DATA_DIR / "interim" / "analysis_datasets" / "analysis_dataset.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        logger.info(f"saved long-format dataset to {path}")

    return df


def create_wide(save: bool = True) -> pd.DataFrame:
    """Wide-format analysis dataset: one row per patient, baseline predictors
    as columns, 12mo phq9_total as the outcome (phq9_12mo). Suitable for orm()."""
    df = _clean()

    baseline = (
        df.loc[df["follow_up_months"] == 0.0]
        .drop(columns=["follow_up_months"])
        .rename(columns={"phq9_total": "baseline_phq9"})
        .set_index(["STUDY_ID", "patient_id"])
    )
    outcome = (
        df.loc[
            df["follow_up_months"].between(11.5, 12.5), ["STUDY_ID", "patient_id", "phq9_total"]
        ]
        .rename(columns={"phq9_total": "phq9_12mo"})
        .set_index(["STUDY_ID", "patient_id"])
    )
    wide = baseline.join(outcome, how="inner").reset_index()
    _report("shape after reshaping to wide (one row per patient)", wide)

    n_dropped_by_join = baseline.shape[0] - wide.shape[0]
    if n_dropped_by_join:
        logger.warning(
            f"inner join dropped {n_dropped_by_join} patients who had a baseline row "
            "but no matching 12mo row -- this shouldn't happen given the earlier "
            "_keep_patients_with_any filters; investigate if nonzero"
        )

    if save:
        path = DATA_DIR / "interim" / "analysis_datasets" / "analysis_dataset_wide.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        wide.to_csv(path, index=False)
        logger.info(f"saved wide-format dataset to {path}")

    return wide


if __name__ == "__main__":
    create_long()
    create_wide()
