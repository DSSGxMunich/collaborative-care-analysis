import warnings

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Fletcher 2021a = the Link-me trial (Australian primary care). A depression/
# anxiety severity prediction tool triaged patients; those predicted to have
# *minimal/mild* or *severe* symptoms were randomised to a matched-care
# intervention vs usual care. Assessments at baseline and 6, 12, 18 months.
# Primary outcome: K10 (Kessler-10) psychological distress at 6 months.
#
# The raw data ships as one Stata file per survey wave, each wide with every
# measure suffixed by the wave number (_1 screening/baseline, _2 six-month,
# _3 twelve-month, _4 eighteen-month). This loader strips the wave suffix from
# each file, tags it with follow_up_months, and stacks the four into long
# format. "*_CLEAR.dta" files in the same folder are column subsets of the
# corresponding "*_ForAnalysis.dta" and are not used.

_STUDY_DIR = RAW_DATASETS_DIR / "10_Fletcher_2021a"

# survey wave file -> (raw column suffix, follow_up_months)
WAVE_FILES = {
    "Link Me ScreeningBaseline_ForAnalysis.dta": ("_1", 0),
    "Link Me 6month_ForAnalysis.dta": ("_2", 6),
    "Link Me 12month_ForAnalysis.dta": ("_3", 12),
    "Link Me 18month_ForAnalysis.dta": ("_4", 18),
}

# Present (unsuffixed) and identical in every wave file.
TIME_INDEPENDENT_COLS = [
    "practice",
    "practice_rec",
    "phn",
    "group",
    "group_r_scr",
    "severity_r",
]

# Per-file bookkeeping markers (REDCap completion/consent timestamps that
# duplicate follow_up_months, or are administrative rather than clinical data).
_WAVE_MARKER_COLS = {
    "bas",
    "mnth6",
    "mnth12",
    "mnth18",
    "screening_complete",
    "external_data_consent_complete_1",
}


def load() -> pd.DataFrame:
    """Load the four Link-me survey waves and return one row per patient-visit."""
    frames = []

    for file_name, (suffix, months) in WAVE_FILES.items():
        # external_data_consent_complete_1 is a Stata %tC (datetime) column we
        # drop below; suppress the read-time warning about it rather than the
        # underlying value.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Encountered %tC format")
            wave = pd.read_stata(_STUDY_DIR / file_name, convert_categoricals=False)
        with pd.option_context("future.no_silent_downcasting", True):
            wave = wave.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
        wave.columns = wave.columns.str.strip()

        missing_id = wave["patient_id"].isna()
        if missing_id.any():
            logger.warning(
                f"{file_name}: dropped {int(missing_id.sum())} rows with missing patient_id"
            )
            wave = wave.loc[~missing_id]

        duplicated_id = wave["patient_id"].duplicated(keep=False)
        if duplicated_id.any():
            logger.warning(
                f"{file_name}: dropped {int(duplicated_id.sum())} rows with duplicated patient_id"
            )
            wave = wave.loc[~duplicated_id]

        keep = ["patient_id", *[c for c in TIME_INDEPENDENT_COLS if c in wave.columns]]
        wave_cols = [c for c in wave.columns if c not in _WAVE_MARKER_COLS]
        suffixed = [c for c in wave_cols if c.endswith(suffix)]
        unexpected = set(wave_cols) - set(keep) - set(suffixed)
        if unexpected:
            raise ValueError(f"{file_name}: columns with no wave suffix: {sorted(unexpected)}")

        renamed = wave[keep + suffixed].rename(columns={c: c[: -len(suffix)] for c in suffixed})
        renamed.insert(1, "follow_up_months", months)
        frames.append(renamed)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    return long.convert_dtypes()
