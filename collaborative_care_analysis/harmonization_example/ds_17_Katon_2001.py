import pandas as pd


def harmonize_example(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Todo: Harmonize ✨
    # Example: Select first three columns (you will want to change all this)
    harmonized_df = harmonized_df[harmonized_df.columns[[0, 1, 2]]]

    return harmonized_df


# For development: Load data and run this harmonization function
if __name__ == "__main__":
    # Get the correct load() function (note the dataset id in the import path)
    from collaborative_care_analysis.data_loading.ds_17_Katon_2001 import load

    df = load()
    harmonized_df = harmonize_example(df)
    print(harmonized_df.head())
