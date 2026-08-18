import pandas as pd


def harmonize_treatment(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()
    # rename the column and change the values to categorical
    harmonized_df["study_arm"] = harmonized_df["arm"].map(
        {
            1: "control",
            2: "intervention",
        }
    )
    # all rows that were in the intervention group had nurses involved so it should be "1" for every "2" in arm column
    harmonized_df["nurse"] = (
        harmonized_df["arm"]
        .map(
            {
                1: 0,
                2: 1,
            }
        )
        .astype("Int64")
    )
    # all rows that were in the intervention group had social worker involved so it should be "1" for every "2" in arm column
    harmonized_df["social_worker"] = (
        harmonized_df["arm"]
        .map(
            {
                1: 0,
                2: 1,
            }
        )
        .astype("Int64")
    )
    # all rows that were in the intervention group had palliative specialist involved in the care team so it should be "1" for every "2" in arm column
    harmonized_df["palliative_care_specialist"] = (
        harmonized_df["arm"]
        .map(
            {
                1: 0,
                2: 1,
            }
        )
        .astype("Int64")
    )
    # all rows that were in the intervention group had cardiologists involved so it should be "1" for every "2" in arm column
    harmonized_df["cardiologist"] = (
        harmonized_df["arm"]
        .map(
            {
                1: 0,
                2: 1,
            }
        )
        .astype("Int64")
    )
    # all rows that were in the intervention group had scheduled visits while those in control had visits as needed
    harmonized_df["visit_schedule"] = harmonized_df["arm"].map(
        {
            1: "as_needed",
            2: "scheduled",
        }
    )
    # all rows that were in the intervention group had 2 visits per month but the ones in control had no specified amount of visits
    # and the actual number of visits for each patient in control group wasn´t specified so I kept it as a missing value
    harmonized_df["visits_per_month"] = (
        harmonized_df["arm"]
        .map(
            {
                1: pd.NA,  # set it as a missing value since its not explicitly stated
                2: 2,
            }
        )
        .astype("Int64")
    )

    # return the harmonized dataset which has only the values I want
    return harmonized_df[
        [
            "STUDY_ID",
            "ROW_ID",
            "studyid",
            "study_arm",
            "nurse",
            "social_worker",
            "palliative_care_specialist",
            "cardiologist",
            "visit_schedule",
            "visits_per_month",
            "med_acein",
            "med_arb",
            "med_betab",
            "med_antid",
            "med_opi",
            "med_lpdiur",
            "med_aldrcnt",
            "med_dgxn",
            "med_statn",
        ]
    ]
