import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   Codebook_Srinivasan et al. (2022).xlsx -> variable/column definitions (reference only, not loaded here)
#   Hope Codebook.xlsx                     -> additional codebook for the "HOPE" study variables
#   HOPE vars for MA all waves, no ID.sav  -> all-waves data, used below (SPSS format)
#   HOPE vars for MA all waves, no ID.xlsx -> same data, Excel format (not used here)
#   Srinivasan 2022.pdf                    -> the published trial paper


def load(
    file_path=RAW_DATASETS_DIR / "30_Srinivasan_2022" / "HOPE vars for MA all waves, no ID.sav",
):
    return pd.read_spss(file_path)
