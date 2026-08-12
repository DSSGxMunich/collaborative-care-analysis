import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "14_Katon_1995" / "katon1995.CLEANED.sav",
) -> pd.DataFrame:
    """
    There are two SPSS files, apparently containing different information.
    """
    return pd.read_spss(
        path=file_path,
        usecols=None,
        convert_categoricals=True,
        # dtype_backend: 'DtypeBackend | lib.NoDefault' = <no_default>,
    )
