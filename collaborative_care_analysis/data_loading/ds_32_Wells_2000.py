import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import ensure_unzipped

_STUDY_DIR = RAW_DATASETS_DIR / "32_Wells_2000"

# Files in this study's raw folder:
#   Codebook_Wells et al. (2000)                       -> variable/column definitions (reference only)
#   31_Wells_Trial.zip                                  -> archived trial folder, auto-extracted into "Wells Trial/" below
#   Wells 2000.pdf                                      -> the published trial paper
#   Wells Trial/PIC_OVERALL, PIC_PAQ00, ..., PIC_PAQ96  -> per-wave raw data (0/6/12/18/24/48/96 months),
#                                                          not used directly here
#   Wells Trial/Wells 2000 screening.sav                -> screening-stage data only, not used here
#   Wells Trial/Wells 2000 CLEANEDn.sav                 -> cleaned data, possibly a subset of waves
#   Wells Trial/Wells 2000 full merged dataset.sav      -> all waves already merged into one file, used below
#   Wells Trial/Wells 2000.pdf / .xlsx                  -> duplicate paper / reference export


def load(
    file_path=_STUDY_DIR / "Wells Trial" / "Wells 2000 full merged dataset.sav",
):
    ensure_unzipped(
        zip_path=_STUDY_DIR / "31_Wells_Trial.zip",
        extract_dir=_STUDY_DIR,
        marker_path=file_path,
    )
    return pd.read_spss(file_path)
