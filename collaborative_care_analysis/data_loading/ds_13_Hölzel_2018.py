import re

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

TIMEPOINT_TO_MONTHS = {"B1": 0, "B2": 6, "B3": 12}

VISIT_PREFIX = re.compile(rf"^GI_(?:{'|'.join(TIMEPOINT_TO_MONTHS)})_")

TIME_INDEPENDENT_COLS = [
    "ID",
    "v_zentrum",
    "Cluster",
    "RG",
    "PIN",
    "GI_B1_Alter",
    "GI_B1_Geschlecht",
    "GI_B1_Bildung",
    "GI_B1_Anstellung",
    "GI_B1_Erwerbsumfang",
    "GI_B1_Geld_aureichend",
]

COLUMN_NAME_FIXES = {
    # Med8_Groesse is misspelled at every timepoint.
    **{f"GI_{tp}_FIMA_med8_Groesse": f"GI_{tp}_FIMA_Med8_Groesse" for tp in TIMEPOINT_TO_MONTHS},
    # The stored PHQ-9 totals arrive without a visit prefix.
    **{f"PHQ_{months}_Monate": f"GI_{tp}_PHQ_Summe" for tp, months in TIMEPOINT_TO_MONTHS.items()},
}


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Stack the three visits, stripping the ``GI_B{t}_`` prefix from each stub."""
    time_varying = [c for c in df.columns if c not in TIME_INDEPENDENT_COLS]

    # a column with no visit prefix matches no frame below and would vanish
    if orphans := [c for c in time_varying if not VISIT_PREFIX.match(c)]:
        raise ValueError(f"columns belong to neither the patient nor a visit: {sorted(orphans)}")

    frames = []
    for timepoint, months in TIMEPOINT_TO_MONTHS.items():
        prefix = f"GI_{timepoint}_"
        visit_cols = [c for c in time_varying if c.startswith(prefix)]

        visit = df[TIME_INDEPENDENT_COLS + visit_cols].copy()
        stubs = [c.removeprefix("GI_B1_") for c in TIME_INDEPENDENT_COLS] + [
            c.removeprefix(prefix) for c in visit_cols
        ]
        # e.g. GI_B1_Alter (time-independent) and GI_B2_Alter both stack to Alter
        if len(set(stubs)) != len(stubs):
            raise ValueError(f"{prefix}: stub names collide after stripping the prefix")
        visit.columns = stubs
        visit.insert(len(TIME_INDEPENDENT_COLS), "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True)
        .rename(columns={"ID": "patient_id"}, errors="raise")
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("duplicate ('patient_id', 'follow_up_months') rows")

    first_columns = ["patient_id", "follow_up_months", "RG"]
    return long[first_columns + [c for c in long.columns if c not in first_columns]]


def load(
    file_path=RAW_DATASETS_DIR
    / "13_Hölzel_2018"
    / "Daten"
    / "20231120_German_IMPACT_f__r_IPD_MA.sav",
) -> pd.DataFrame:
    """Read the export and return it in long format."""
    df = pd.read_spss(path=file_path, convert_categoricals=False)

    # blank-out before dtype inference, so whitespaces are not inferred as a value
    df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True).convert_dtypes()

    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMN_NAME_FIXES, errors="raise")
    df = df.dropna(how="all", axis="index")
    df = df.dropna(how="all", axis="columns")

    return to_long(df)
