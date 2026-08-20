import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Columns needed for later merge operations.
    id_columns = ["STUDY_ID", "patient_id", "follow_up_months"]

    df.rename(columns={"ticstot": "tics_total"}, inplace=True, errors="raise")

    # Max points per item, per codebook.
    tics_max = {
        "tics01": 2,
        "tics02": 5,
        "tics03": 5,
        "tics04": 2,
        "tics05": 10,
        "tics06": 5,
        "tics07": 4,
        "tics08": 2,
        "tics09": 2,
        "tics10": 2,
        "tics11": 2,
    }
    tics_total_max = 41
    tics_cols = list(tics_max) + ["tics_total"]

    # tics items should be numeric
    non_numeric = [c for c in tics_cols if not pd.api.types.is_numeric_dtype(df[c])]
    assert not non_numeric, f"Non-numeric tics columns: {non_numeric}"

    # Each item score must fall within [0, max_points]
    for col, max_points in tics_max.items():
        out_of_range = df[col].dropna()
        bad = out_of_range[(out_of_range < 0) | (out_of_range > max_points)]
        assert bad.empty, f"{col} has values outside [0, {max_points}]: {bad.unique()}"

    total_out_of_range = df["tics_total"].dropna()
    bad_total = total_out_of_range[
        (total_out_of_range < 0) | (total_out_of_range > tics_total_max)
    ]
    assert bad_total.empty, (
        f"tics_total has values outside [0, {tics_total_max}]: {bad_total.unique()}"
    )

    return df[id_columns + tics_cols]
