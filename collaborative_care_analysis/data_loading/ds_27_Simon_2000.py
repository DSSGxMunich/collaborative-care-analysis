import pandas as pd
import pyreadstat

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "27_Simon_2000" / "simon2000.sav"):
    # Read the SPSS .sav file and return its data as a pandas DataFrame.
    # Metadata returned by pyreadstat is not used.
    df, _ = pyreadstat.read_sav(file_path)
    return df
