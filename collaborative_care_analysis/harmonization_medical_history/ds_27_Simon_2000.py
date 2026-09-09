import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # NOTE: the study's Excel codebook lists this as LTC_0/LTCsev_0, but those
    # names don't exist in the actual .sav file. The real column, confirmed via
    # the file's own metadata, is cdstcsta.
    harmonized_df["chronic_disease_score"] = pd.to_numeric(
        harmonized_df["cdstcsta"], errors="raise"
    )

    return harmonized_df[["STUDY_ID", "patient_id", "follow_up_months", "chronic_disease_score"]]
