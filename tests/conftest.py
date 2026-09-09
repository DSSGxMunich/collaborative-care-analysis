import pandas as pd
import pytest

from collaborative_care_analysis.config import (
    ENRICHED_DATASET_DIR,
    MERGED_DATASET_DIR,
)
from collaborative_care_analysis.enrichment import TREATMENT_COL_PREFIX

ENRICHED_CSV = ENRICHED_DATASET_DIR / "enriched_dataset.csv"
MERGED_CSV = MERGED_DATASET_DIR / "merged_dataset.csv"


@pytest.fixture(scope="module")
def merged_df() -> pd.DataFrame:

    if not MERGED_CSV.exists():
        pytest.skip(f"{MERGED_CSV} not found. Run the 'merge' pipeline step first.")
    return pd.read_csv(MERGED_CSV)


@pytest.fixture(scope="module")
def enriched_df() -> pd.DataFrame:

    if not ENRICHED_CSV.exists():
        pytest.skip(f"{ENRICHED_CSV} not found. Run the 'enrich' pipeline step first.")
    return pd.read_csv(ENRICHED_CSV)


@pytest.fixture(scope="module")
def treatment_cols(enriched_df: pd.DataFrame) -> list[str]:

    return [c for c in enriched_df.columns if c.startswith(TREATMENT_COL_PREFIX)]
