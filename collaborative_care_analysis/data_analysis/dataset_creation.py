"""Analysis-ready cohorts derived from the enriched dataset.

A cohort is described by a ``CohortSpec`` and written to its own folder under
``data/interim/analysis_datasets/<name>/``, next to the spec that produced it
and the attrition table recording what each filter cost. Two cohorts can
therefore be compared, and any result traced back to the rule set behind it.

The knob that matters most is ``require_complete``: the 12-study PHQ-9 cohort
and the 8-study one differ only by whether ``gad7_total`` is in it.
"""

from dataclasses import asdict, dataclass, replace
import json

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import DATA_DIR

ANALYSIS_DIR = DATA_DIR / "interim" / "analysis_datasets"

GRAIN = ["STUDY_ID", "patient_id"]


@dataclass(frozen=True)
class CohortSpec:
    """One analysis cohort, as a set of rules rather than a copy of the code.

    ``broadcast`` and ``require_complete`` are deliberately separate. Only a
    genuinely time-invariant column belongs in ``broadcast``: filling a
    time-varying one within the patient would carry a follow-up measurement
    back onto the baseline row and silently invent a baseline value.
    """

    name: str
    instrument: str = "phq9_total"
    outcome_month: float = 12.0
    outcome_window: float = 0.5
    broadcast: tuple[str, ...] = ("age", "sex", "study_arm")
    require_complete: tuple[str, ...] = ("age", "sex", "study_arm")
    drop_sex_other: bool = True
    min_patients_per_study: int = 10

    @property
    def baseline_col(self) -> str:
        return f"{self.instrument}_baseline"

    @property
    def outcome_col(self) -> str:
        return f"{self.instrument}_outcome"

    @property
    def directory(self):
        return ANALYSIS_DIR / self.name


CORE = CohortSpec(name="phq9_12mo_core")

WITH_GAD7 = replace(
    CORE,
    name="phq9_12mo_gad7",
    require_complete=CORE.require_complete + ("gad7_total",),
)

WITH_PHQ9_ITEMS = replace(
    CORE,
    name="phq9_12mo_items",
    require_complete=CORE.require_complete + tuple(f"phq9_{item}" for item in range(1, 10)),
)

PRESETS = {spec.name: spec for spec in (CORE, WITH_GAD7, WITH_PHQ9_ITEMS)}
DEFAULT_PRESET = CORE.name


def _tally(df: pd.DataFrame, step: str) -> dict:
    return {
        "step": step,
        "rows": len(df),
        "patients": len(df[GRAIN].drop_duplicates()),
        "studies": df["STUDY_ID"].nunique(),
    }


def _keep_patients_with_any(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Keep every row of any patient with at least one row matching ``mask``."""
    keep = df.loc[mask, GRAIN].drop_duplicates().assign(_keep=True)
    merged = df.merge(keep, on=GRAIN, how="left")
    return merged.loc[merged["_keep"].notna()].drop(columns="_keep")


def _broadcast_within_patient(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Fill a time-invariant column across all of a patient's rows."""
    df[column] = (
        df.groupby(GRAIN)[column].transform(lambda s: s.ffill().bfill()).infer_objects(copy=False)
    )
    return df


def _nearest_visit(df: pd.DataFrame, target: float, label: str) -> pd.DataFrame:
    """One row per patient: the visit closest to ``target``.

    A tolerance window can match more than one row per patient -- ds_08 records
    follow-up as a near-continuous month rather than a scheduled visit -- and
    every such patient would otherwise be duplicated by the baseline/outcome
    join.
    """
    candidates = df.assign(_gap=(df["follow_up_months"] - target).abs())
    candidates = candidates.sort_values(GRAIN + ["_gap"])
    picked = candidates.drop_duplicates(GRAIN)
    if len(picked) < len(candidates):
        logger.info(
            f"{label}: {len(candidates) - len(picked)} extra row(s) inside the window; "
            "kept the visit nearest the target."
        )
    return picked.drop(columns="_gap")


def _clean(spec: CohortSpec) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long-format cohort (baseline row + outcome row per patient) and its attrition."""
    df = pd.read_csv(
        DATA_DIR / "interim" / "enriched_dataset" / "enriched_dataset.csv", low_memory=False
    )
    attrition = [_tally(df, "enriched dataset")]

    # A total that is not whole cannot be a sum of whole-numbered items. This
    # also drops every row where the instrument is missing outright, so from
    # here on a row's presence means the instrument was measured at that visit.
    df = df[df[spec.instrument].mod(1).eq(0)].astype({spec.instrument: "int32"})
    attrition.append(_tally(df, f"{spec.instrument} present and whole"))

    df = df.groupby("STUDY_ID").filter(lambda g: g[spec.instrument].notna().any())
    attrition.append(_tally(df, "study measures the instrument"))

    low, high = spec.outcome_month - spec.outcome_window, spec.outcome_month + spec.outcome_window

    df = _keep_patients_with_any(df, df["follow_up_months"] == 0.0)
    attrition.append(_tally(df, "has a baseline visit"))

    df = _keep_patients_with_any(df, df["follow_up_months"].between(low, high))
    attrition.append(_tally(df, f"has a visit in [{low:g}, {high:g}] months"))

    df = df.loc[(df["follow_up_months"] == 0.0) | df["follow_up_months"].between(low, high)]
    attrition.append(_tally(df, "baseline and outcome visits only"))

    for column in spec.broadcast:
        df = _broadcast_within_patient(df, column)

    for column in spec.require_complete:
        df = _keep_patients_with_any(df, (df["follow_up_months"] == 0.0) & df[column].notna())
        attrition.append(_tally(df, f"{column} present at baseline"))

    if spec.drop_sex_other:
        df = _keep_patients_with_any(df, df["sex"].ne("Other"))
        df = df.loc[df["sex"].ne("Other")]
        attrition.append(_tally(df, "sex is not 'Other'"))

    if "sex" in df.columns:
        df["sex"] = df["sex"].astype("category")

    per_study = df.drop_duplicates(GRAIN).groupby("STUDY_ID").size()
    big_enough = per_study[per_study >= spec.min_patients_per_study].index
    dropped = sorted(set(per_study.index) - set(big_enough))
    if dropped:
        logger.info(
            f"dropping {len(dropped)} study/studies under "
            f"{spec.min_patients_per_study} patients: {dropped}"
        )
    df = df.loc[df["STUDY_ID"].isin(big_enough)]
    attrition.append(_tally(df, f">= {spec.min_patients_per_study} patients per study"))

    attrition_df = pd.DataFrame(attrition)
    logger.info("\n" + attrition_df.to_string(index=False))
    return df, attrition_df


def _to_wide(df: pd.DataFrame, spec: CohortSpec) -> pd.DataFrame:
    """One row per patient: baseline columns plus the outcome score."""
    low, high = spec.outcome_month - spec.outcome_window, spec.outcome_month + spec.outcome_window

    baseline = _nearest_visit(df.loc[df["follow_up_months"] == 0.0], 0.0, "baseline")
    baseline = baseline.drop(columns=["follow_up_months"]).rename(
        columns={spec.instrument: spec.baseline_col}
    )

    outcome = _nearest_visit(
        df.loc[df["follow_up_months"].between(low, high)], spec.outcome_month, "outcome"
    )
    outcome = outcome[GRAIN + [spec.instrument, "follow_up_months"]].rename(
        columns={spec.instrument: spec.outcome_col, "follow_up_months": "outcome_month_actual"}
    )

    wide = baseline.merge(outcome, on=GRAIN, how="inner")
    if len(wide) != len(baseline):
        raise ValueError(
            f"{len(baseline) - len(wide)} patient(s) have a baseline row but no outcome row; "
            "the keep-filters in _clean should already guarantee both."
        )
    return wide


def build(spec: CohortSpec = CORE, save: bool = True) -> pd.DataFrame:
    """Build one cohort, returning the wide frame and writing the folder."""
    long_df, attrition = _clean(spec)
    wide_df = _to_wide(long_df, spec)
    logger.info(f"{spec.name}: {len(wide_df)} patients, {wide_df['STUDY_ID'].nunique()} studies")

    if save:
        spec.directory.mkdir(parents=True, exist_ok=True)
        long_df.to_csv(spec.directory / "long.csv", index=False)
        wide_df.to_csv(spec.directory / "wide.csv", index=False)
        attrition.to_csv(spec.directory / "attrition.csv", index=False)
        (spec.directory / "spec.json").write_text(json.dumps(asdict(spec), indent=2) + "\n")
        logger.success(f"saved cohort '{spec.name}' to {spec.directory}")

    return wide_df
