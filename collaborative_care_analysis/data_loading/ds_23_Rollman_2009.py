import pandas as pd

from collaborative_care_analysis.config import RAW_DATA_DIR

FILE_PATH = (
    RAW_DATA_DIR
    / "Individual Datasets"
    / "23_Rollman_2009"
    / "24_25_Rollman_OT_and_RELAX_trials_data_for_meta_analysis"
    / "OT Meta Data_ Munich.xlsx"
)


def load():
    """Load the Rollman 2009 dataset."""

    if not FILE_PATH.exists():
        raise FileNotFoundError(f"File not found: {FILE_PATH}")

    return pd.read_excel(FILE_PATH, sheet_name=None)