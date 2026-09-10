from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

RAW_DATASETS_DIR = RAW_DATA_DIR / "Individual Datasets"
RAW_ANNOTATIONS_DIR = RAW_DATA_DIR / "annotations"
STUDY_LEVEL_EXTRA_INFOS_CSV = (
    RAW_ANNOTATIONS_DIR / "study_level_extra_infos.xlsx - extra_infos.csv"
)
# Maps the POOL2 study number (StudyNo_POOL) to this project's dataset number
# (StudyNo_OURS). See collaborative_care_analysis/pool2.py.
DATASET_ID_CONVERSIONS_CSV = RAW_ANNOTATIONS_DIR / "dataset_id_conversions.csv"
# The POOL2 participant-level multi-study export (one row per patient), shipped
# as a zip that must be extracted into POOL2_DIR before use.
POOL2_DIR = RAW_DATA_DIR / "260810_POOL2"
POOL2_ZIP = RAW_DATA_DIR / "260810_POOL2.zip"
POOL2_CSV = POOL2_DIR / "POOL2_final.csv"
INTERIM_DATASETS_EXPORT_DIR = INTERIM_DATA_DIR / "exported_datasets"
HARMONIZED_DATASETS_DIR = INTERIM_DATA_DIR / "harmonized_datasets"
MERGED_DATASET_DIR = INTERIM_DATA_DIR / "merged_dataset"
ENRICHED_DATASET_DIR = INTERIM_DATA_DIR / "enriched_dataset"
GENERATED_CODEBOOKS_DIR = INTERIM_DATA_DIR / "generated_codebooks"

MODELS_DIR = PROJ_ROOT / "models"
REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

COLNAME_STUDYID = "STUDY_ID"

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
