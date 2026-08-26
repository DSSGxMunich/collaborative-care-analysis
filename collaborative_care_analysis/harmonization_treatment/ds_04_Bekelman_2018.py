import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # rename the column and change the values to categorical
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "control",
            2: "intervention",
        },
        "arm",
    )

    # all rows that were in the intervention group had nurses involved
    harmonized_df["is_nurse_involved"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "no",
            2: "yes",
        },
        "arm",
    )

    # all rows that were in the intervention group had social worker involved
    harmonized_df["is_social_worker_involved"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "no",
            2: "yes",
        },
        "arm",
    )

    # all rows that were in the intervention group had
    # palliative care specialist involved
    harmonized_df["is_palliative_care_specialist_involved"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "no",
            2: "yes",
        },
        "arm",
    )

    # all rows that were in the intervention group had cardiologists involved
    harmonized_df["is_cardiologist_involved"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "no",
            2: "yes",
        },
        "arm",
    )

    # all rows that were in the intervention group had scheduled visits
    # while those in control had visits as needed
    harmonized_df["visit_schedule"] = map_with_check(
        harmonized_df["arm"],
        {
            1: "as_needed",
            2: "scheduled",
        },
        "arm",
    )

    # all rows that were in the intervention group had 2 visits per month,
    # but the ones in control had no specified amount of visits.
    # The actual number of visits for each patient in the control group
    # was not specified, so I kept it as a missing value.
    harmonized_df["visits_per_month"] = map_with_check(
        harmonized_df["arm"],
        {
            1: pd.NA,
            2: 2,
        },
        "arm",
    ).astype("Int64")

    # ------------------------------------------------------------------
    # MEDICATIONS
    # ------------------------------------------------------------------
    # All medication variables use the same raw coding:
    # 0 = no
    # 1 = yes
    # 99 = missing / unknown
    #
    # map_with_check() makes sure that if another unexpected value
    # appears, such as 2 or 3, the harmonization fails loudly instead
    # of silently converting that value to missing.
    medication_mapping = {
        0: "no",
        1: "yes",
        99: pd.NA,
    }

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_angiotensin-converting_enzyme_inhibitor_(ACE Inhibitor)"] = (
        map_with_check(
            harmonized_df["med_acein"],
            medication_mapping,
            "med_acein",
        )
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_angiotensin_II_receptor_blockers_(ARBS)"] = map_with_check(
        harmonized_df["med_arb"],
        medication_mapping,
        "med_arb",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_beta-blocker"] = map_with_check(
        harmonized_df["med_betab"],
        medication_mapping,
        "med_betab",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_antidepressant"] = map_with_check(
        harmonized_df["med_antid"],
        medication_mapping,
        "med_antid",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_opiate"] = map_with_check(
        harmonized_df["med_opi"],
        medication_mapping,
        "med_opi",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_loop_diuretic"] = map_with_check(
        harmonized_df["med_lpdiur"],
        medication_mapping,
        "med_lpdiur",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_aldosterone_receptor_antagonist"] = map_with_check(
        harmonized_df["med_aldrcnt"],
        medication_mapping,
        "med_aldrcnt",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_digitalis_glycoside"] = map_with_check(
        harmonized_df["med_dgxn"],
        medication_mapping,
        "med_dgxn",
    )

    # changes the name to a more descriptive name and values to categorical
    harmonized_df["medications_statin_or_lipid-lowering_agent"] = map_with_check(
        harmonized_df["med_statn"],
        medication_mapping,
        "med_statn",
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
