import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR
    / "23_Rollman_2009"
    / "24_25_Rollman_OT_and_RELAX_trials_data_for_meta_analysis"
    / "OT Meta Data_ Munich.xlsx",
):
    # Read all Excel sheets into a dictionary: {sheet_name: pandas.DataFrame}.
    data = pd.read_excel(file_path, sheet_name=None)
    return list(data.keys())