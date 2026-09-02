import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["age"] = pd.to_numeric(harmonized_df["age_0"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["gender_0"],
        mapping={
            0: "Male",
            1: "Female",
            2: pd.NA,
        },
    )

    harmonized_df["education_level"] = map_with_check(
        series=harmonized_df["education_0"],
        mapping={
            0: "No school degree",
            1: "Basic secondary school",
            2: "Basic secondary school",
            3: "Intermediate secondary school",
            4: "Higher education entrance qualification",
            5: "University degree",
        },
    )

    harmonized_df["employment_status"] = map_with_check(
        series=harmonized_df["employment_0"],
        mapping={
            0: "Employed/working",
            1: "Sheltered employment",
            2: "Unemployed and looking for work",
            3: "Unemployed",
        },
    )

    harmonized_df["student_status"] = map_with_check(
        series=harmonized_df["student_0"],
        mapping={
            0: "No",
            1: "Yes, part-time student",
            2: "Yes, full-time student",
        },
    )

    # yes/no map
    yes_no_map = {0: "No", 1: "Yes"}

    harmonized_df["live_alone"] = map_with_check(
        harmonized_df["live_alone_0"],
        yes_no_map,
    )
    harmonized_df["live_with_spouse"] = map_with_check(
        harmonized_df["live_spouse_0"],
        yes_no_map,
    )
    harmonized_df["live_with_defacto"] = map_with_check(
        harmonized_df["live_defacto_0"],
        yes_no_map,
    )
    harmonized_df["live_with_child"] = map_with_check(
        harmonized_df["live_child_0"],
        yes_no_map,
    )
    harmonized_df["live_with_stepchildren"] = map_with_check(
        harmonized_df["live_childpt_0"],
        yes_no_map,
    )
    harmonized_df["live_with_parent"] = map_with_check(
        harmonized_df["live_parent_0"],
        yes_no_map,
    )
    harmonized_df["live_with_flatmate"] = map_with_check(
        harmonized_df["live_flatmate_0"],
        yes_no_map,
    )
    harmonized_df["live_with_other"] = map_with_check(
        harmonized_df["live_other_0"],
        yes_no_map,
    )

    harmonized_df["self_rated_health_status"] = map_with_check(
        series=harmonized_df["health_0"],
        mapping={
            1: "Excellent",
            2: "Very good",
            3: "Good",
            4: "Fair",
            5: "Poor",
        },
    )

    harmonized_df["internet_use"] = map_with_check(
        series=harmonized_df["internetuse_0"],
        mapping={
            0: "Daily",
            1: "Weekly",
            2: "Fortnightly",
            3: "Monthly",
            4: "Less often",
        },
    )

    harmonized_df["has_disability"] = map_with_check(
        series=harmonized_df["disability"],
        mapping=yes_no_map,
    )

    harmonized_df["disability_name"] = harmonized_df["disabilityname"].astype("string")

    harmonized_df["activity_if_unemployed"] = map_with_check(
        series=harmonized_df["activities"],
        mapping={
            -1: "Other",
            0: "Unable to work due to sickness or disability",
            1: "Looking after ill or disabled person",
            2: "Home duties/child care",
            3: "Retired/voluntarily inactive",
            4: "Studying",
        },
    )

    # domestic violence worker visit
    harmonized_df["domestic_violence_worker_visit"] = map_with_check(
        series=harmonized_df["domesticviolenceworkervisit"],
        mapping={
            0: "0 times",
            1: "1-2 times",
            2: "3-4 times",
            3: "5-6 times",
            4: "7-11 times",
            5: "12 times or more",
        },
    )

    # alcohol and drug worker visit
    harmonized_df["alcohol_drug_worker_visit"] = map_with_check(
        series=harmonized_df["alcoholanddrugworkervisit"],
        mapping={
            0: "0 times",
            1: "1-2 times",
            2: "3-4 times",
            3: "5-6 times",
            4: "7-11 times",
            5: "12 times or more",
        },
    )

    harmonized_df["has_health_insurance"] = map_with_check(
        series=harmonized_df["insured"],
        mapping=yes_no_map,
    )

    harmonized_df["job_unemployment_since"] = harmonized_df["job_unemploy"].astype("string")

    harmonized_df["health_card_type"] = map_with_check(
        series=harmonized_df["card"],
        mapping={
            0: "Health Care Card (Centrelink)",
            1: "Pensioner Concession Card (Centrelink)",
            2: "Commonwealth Seniors Health Card",
            3: "Department of Veterans",
            4: pd.NA,
        },
    )

    harmonized_df["ability_to_manage_on_income"] = map_with_check(
        series=harmonized_df["income_t"],
        mapping={
            1: "Easily",
            2: "Not too bad",
            3: "Difficult some of the time",
            4: "Difficult all of the time",
            5: "Impossible",
        },
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "education_level",
            "employment_status",
            "student_status",
            "live_alone",
            "live_with_spouse",
            "live_with_defacto",
            "live_with_child",
            "live_with_stepchildren",
            "live_with_parent",
            "live_with_flatmate",
            "live_with_other",
            "self_rated_health_status",
            "internet_use",
            "has_disability",
            "disability_name",
            "activity_if_unemployed",
            "domestic_violence_worker_visit",
            "alcohol_drug_worker_visit",
            "has_health_insurance",
            "job_unemployment_since",
            "health_card_type",
            "ability_to_manage_on_income",
            "follow_up_months",
        ]
    ]
