from pathlib import Path
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"


def load(file_path):
    """Load an Excel file from the data/raw directory."""

    file_path = RAW_DATA_DIR / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return pd.read_excel(file_path, sheet_name=None)