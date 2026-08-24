import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # rename the column and change the values to categorical
    harmonized_df["study_arm"] = harmonized_df["arm"].map(
        {
            1: "control",
            2: "intervention",
        }
    )

    # all rows that were in the intervention group had nurses involved
    harmonized_df["is_nurse_involved"] = harmonized_df["arm"].map(
        {
            1: "no",
            2: "yes",
        }
    )
    # all rows that were in the intervention group had social worker involved
    harmonized_df["is_social_worker_involved"] = harmonized_df["arm"].map(
        {
            1: "no",
            2: "yes",
        }
    )
    # all rows that were in the intervention group had palliative specialist involved
    harmonized_df["is_palliative_care_specialist_involved"] = harmonized_df["arm"].map(
        {
            1: "no",
            2: "yes",
        }
    )
    # all rows that were in the intervention group had cardiologists involved
    harmonized_df["is_cardiologist_involved"] = harmonized_df["arm"].map(
        {
            1: "no",
            2: "yes",
        }
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

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_angiotensin-converting_enzyme_inhibitor_(ACE Inhibitor)"] = (
        harmonized_df["med_acein"].map({0: "no", 1: "yes"})
    )
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_angiotensin_II_receptor_blockers_(ARBS)"] = harmonized_df[
        "med_arb"
    ].map({0: "no", 1: "yes"})
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_beta-blocker"] = harmonized_df["med_betab"].map({0: "no", 1: "yes"})
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_antidepressant"] = harmonized_df["med_antid"].map(
        {0: "no", 1: "yes"}
    )
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_opiate"] = harmonized_df["med_opi"].map({0: "no", 1: "yes"})
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_loop_diuretic"] = harmonized_df["med_lpdiur"].map(
        {0: "no", 1: "yes"}
    )
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_aldosterone_receptor_antagonist"] = harmonized_df[
        "med_aldrcnt"
    ].map({0: "no", 1: "yes"})
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_digitalis_glycoside"] = harmonized_df["med_dgxn"].map(
        {0: "no", 1: "yes"}
    )
    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_statin_or_lipid-lowering_agent"] = harmonized_df["med_statn"].map(
        {0: "no", 1: "yes"}
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            "is_nurse_involved",
            "is_social_worker_involved",
            "is_palliative_care_specialist_involved",
            "is_cardiologist_involved",
            "visit_schedule",
            "visits_per_month",
            "medications_angiotensin-converting_enzyme_inhibitor_(ACE Inhibitor)",
            "medications_angiotensin_II_receptor_blockers_(ARBS)",
            "medications_beta-blocker",
            "medications_antidepressant",
            "medications_opiate",
            "medications_loop_diuretic",
            "medications_aldosterone_receptor_antagonist",
            "medications_digitalis_glycoside",
            "medications_statin_or_lipid-lowering_agent",
        ]
    ]
