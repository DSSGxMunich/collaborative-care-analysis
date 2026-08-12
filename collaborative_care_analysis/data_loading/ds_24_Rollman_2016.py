import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "24_Rollman_2016" / "RELAX Meta Data_ Munich.xlsx",
):
    # Read and return the "PARTICIPANTS" sheet as a pandas DataFrame.
    # Other available sheets are not imported: "GADSS", "PDSS", "SIGHA", "PHQ9",
    # "SF36v2", "PHYS_COMORBIDS", and "SelectNotes".
    return pd.read_excel(file_path, sheet_name="PARTICIPANTS")