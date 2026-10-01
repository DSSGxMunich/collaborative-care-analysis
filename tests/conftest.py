import pandas as pd
import pytest

from collaborative_care_analysis.config import (
    ENRICHED_DATASET_DIR,
    MERGED_DATASET_DIR,
)
from collaborative_care_analysis.enrichment import TREATMENT_COL_PREFIX

ENRICHED_CSV = ENRICHED_DATASET_DIR / "enriched_dataset.csv"
MERGED_CSV = MERGED_DATASET_DIR / "merged_dataset.csv"

# Columns whose dtype doesn't survive a CSV round-trip on its own and must be
# restored explicitly on read -- category is the only one so far, but this is
# the place to add more (e.g. other categorical columns) if that changes.
_DTYPE_OVERRIDES = {"sex": "category"}


@pytest.fixture(scope="module")
def merged_df() -> pd.DataFrame:

    if not MERGED_CSV.exists():
        pytest.skip(f"{MERGED_CSV} not found. Run the 'merge' pipeline step first.")
    return pd.read_csv(MERGED_CSV, dtype=_DTYPE_OVERRIDES)


@pytest.fixture(scope="module")
def enriched_df() -> pd.DataFrame:

    if not ENRICHED_CSV.exists():
        pytest.skip(f"{ENRICHED_CSV} not found. Run the 'enrich' pipeline step first.")
    return pd.read_csv(ENRICHED_CSV, dtype=_DTYPE_OVERRIDES)


@pytest.fixture(scope="module")
def treatment_cols(enriched_df: pd.DataFrame) -> list[str]:

    return [c for c in enriched_df.columns if c.startswith(TREATMENT_COL_PREFIX)]
