import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   Codebook_Simon et al. (2011).xlsx -> variable/column definitions (reference only, not loaded here)
#   Simon 2011.pdf                    -> the published trial paper
#   simon2011.sav                     -> original SPSS data file
#   simon2011.CLEANED.sav             -> cleaned SPSS data file (used below)


def load(file_path=RAW_DATASETS_DIR / "29_Simon_2011" / "simon2011.CLEANED.sav"):
    return pd.read_spss(file_path)
