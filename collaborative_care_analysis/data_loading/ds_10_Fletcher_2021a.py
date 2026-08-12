import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "10_Fletcher_2021a" / "Link Me 6month_ForAnalysis.dta",
) -> pd.DataFrame:
    """
    "Link Me <n>month_CLEAR.dta" files are subsets of the corresponding "Link Me <n>month_ForAnalysis.dta" files, n = 6, 12, 18.
    Careful when joining: some patients only have measurements at some of the three timepoints.
    """
    return pd.read_stata(
        filepath_or_buffer=file_path,
        convert_dates=True,
        convert_categoricals=True,
        index_col=None,
        convert_missing=False,
        preserve_dtypes=False,  # numeric data are upcast to pd default types for foreign data (float64 or int64)
        columns=None,
        order_categoricals=True,
        chunksize=None,
        iterator=False,
        compression="infer",
        storage_options=None,
    )
