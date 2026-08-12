import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR
    / "23_Rollman_2009"
    / "24_25_Rollman_OT_and_RELAX_trials_data_for_meta_analysis"
    / "OT Meta Data_ Munich.xlsx",
):
    # Read and return the "PARTICIPANTS" sheet as a pandas DataFrame.
    # Other available sheets are not imported: "PHQ-9", "GAD-7", "PROMIS Anxiety",
    # "PROMIS Depression", "SF-12", "PHYS_COMORBIDS", and "SelectNotes".
    return pd.read_excel(file_path, sheet_name="PARTICIPANTS")
