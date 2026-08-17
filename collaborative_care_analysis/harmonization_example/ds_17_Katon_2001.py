import pandas as pd


def harmonize_example(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Todo: Harmonize ✨
    # Example: Select first three columns (you will want to change all this)
    harmonized_df = harmonized_df[harmonized_df.columns[[0, 1, 2]]]

    return harmonized_df
