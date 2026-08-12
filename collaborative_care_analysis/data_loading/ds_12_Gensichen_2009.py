import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "12_Gensichen_2009" / "PRoMPT_Daten_T0_09082010_final.dta",
) -> pd.DataFrame:
    """
    There are many more files to load eventually.
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
