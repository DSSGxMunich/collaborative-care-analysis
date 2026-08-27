import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import ensure_unzipped

_STUDY_DIR = RAW_DATASETS_DIR / "23_Rollman_2009"
_DATA_DIR_NAME = "24_25_Rollman_OT_and_RELAX_trials_data_for_meta_analysis"


def load(
    file_path=_STUDY_DIR / _DATA_DIR_NAME / "OT Meta Data_ Munich.xlsx",
):
    ensure_unzipped(
        zip_path=_STUDY_DIR / f"{_DATA_DIR_NAME}.zip",
        extract_dir=_STUDY_DIR / _DATA_DIR_NAME,
        marker_path=file_path,
    )
    # Read and return the "PARTICIPANTS" sheet as a pandas DataFrame.
    # Other available sheets are not imported: "PHQ-9", "GAD-7", "PROMIS Anxiety",
    # "PROMIS Depression", "SF-12", "PHYS_COMORBIDS", and "SelectNotes".
    return pd.read_excel(file_path, sheet_name="PARTICIPANTS")
