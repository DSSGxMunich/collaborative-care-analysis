import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR
    / "13_Hölzel_2018"
    / "Daten"
    / "20231120_German_IMPACT_f__r_IPD_MA.sav",
) -> pd.DataFrame:
    """
    The SPSS and Stata file in the folder have the same shape and the columns contain the same information,
    however the column names and the variable coding in the former is clearer, so only this is considered.
    """
    return pd.read_spss(
        path=file_path,
        usecols=None,
        convert_categoricals=True,
        # dtype_backend: 'DtypeBackend | lib.NoDefault' = <no_default>,
    )
