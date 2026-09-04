import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # cds2 = count of chronic (physical) conditions.
    chronic = pd.to_numeric(harmonized_df["cds2"], errors="raise").astype("Int64")
    assert (chronic.dropna() >= 0).all(), "cds2 has negative values"
    harmonized_df["number_of_chronic_conditions"] = chronic

    return harmonized_df[
        ["STUDY_ID", "patient_id", "follow_up_months", "number_of_chronic_conditions"]
    ]
