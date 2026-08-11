import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   Codebook_Simon et al. (2004).xlsx -> variable/column definitions (reference only, not loaded here)
#   Simon 2004.pdf                    -> the published trial paper
#   Simon 2009.pdf                    -> related follow-up publication
#   simon2004.sav                     -> original SPSS data file
#   simon2004.CLEANEDsav.sav          -> cleaned SPSS data file (used below)


def load(file_path=RAW_DATASETS_DIR / "28_Simon_2004" / "simon2004.CLEANEDsav.sav"):
    return pd.read_spss(file_path)
