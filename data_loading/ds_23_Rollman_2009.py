from pathlib import Path
import pandas as pd
def load(file_path):
    """Load all sheets from an Excel file into pandas DataFrames."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return pd.read_excel(file_path, sheet_name=None)