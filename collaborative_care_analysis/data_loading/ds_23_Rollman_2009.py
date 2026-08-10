from pathlib import Path
import pandas as pd


# Repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent

# Raw data directory
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"


def load(file_path):
    """Load data based on the file format."""

    file_path = RAW_DATA_DIR / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()

    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(file_path, sheet_name=None)

    elif ext == ".dta":
        return pd.read_stata(file_path)

    elif ext == ".csv":
        return pd.read_csv(file_path)

    elif ext == ".sav":
        return pd.read_spss(file_path)

    else:
        raise ValueError(f"Unsupported file format: {ext}")