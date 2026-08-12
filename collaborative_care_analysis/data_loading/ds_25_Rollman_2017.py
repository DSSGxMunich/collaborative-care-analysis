import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "25_Rollman_2017" / "OT Meta Data_ Munich.xlsx",
):
    # Read all Excel sheets into a dictionary: {sheet_name: pandas.DataFrame}.
    data = pd.read_excel(file_path, sheet_name=None)
    return list(data.keys())