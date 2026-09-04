import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # cds = chronic disease score (a weighted pharmacy-based comorbidity score,
    # "Chronic Disease Score" of Von Korff / Clark). Not a simple count.
    harmonized_df["chronic_disease_score"] = pd.to_numeric(harmonized_df["cds"], errors="raise")

    return harmonized_df[["STUDY_ID", "patient_id", "follow_up_months", "chronic_disease_score"]]
