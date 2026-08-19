import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "04_Bekelman_2018" / "CASAforIPD-MA (1).csv",
):
    df = pd.read_csv(
        filepath_or_buffer=file_path,
        # these columns have mixed types, pd suggests to specify a dtype
        dtype={251: "str", 253: "str", 300: "str"},
    )

    # Remove all rows and columns with all NA values.
    df.dropna(how="all", inplace=True)

    # Remove leading and trailing whitespaces from column names.
    df.columns = df.columns.str.strip()

    # Remove all columns that are not explained in the codebook.
    codebook_dict = pd.read_excel(
        io=RAW_DATASETS_DIR / "04_Bekelman_2018" / "Codebook_Bekelman et al. (2018).xlsx",
        sheet_name=None,  # loads all worksheets
    )

    for name in codebook_dict:
        codebook_dict[name].dropna(how="all", inplace=True)

    for name, worksheet in list(codebook_dict.items())[1:]:
        worksheet.columns = worksheet.columns.str.strip()
        worksheet["Variable"] = worksheet["Variable"].str.strip()

    column_source_dict = {}
    for col in df.columns:
        column_source_dict[col] = []
        for name, worksheet in list(codebook_dict.items())[1:]:
            if col in [val for val in worksheet["Variable"].values]:
                column_source_dict[col].append(f"{name}")

    empty_cols = [col for col in column_source_dict if not column_source_dict[col]]
    print(df[empty_cols].iloc[0:10])

    df.drop(labels=empty_cols, axis=1, inplace=True)

    # Remove caregiver rows:
    # any non-missing value in a cg_* column identifies a caregiver row.
    cg_cols = [col for col in df.columns if col.startswith("cg_")]
    is_caregiver = df[cg_cols].notna().any(axis=1)
    df = df.loc[~is_caregiver]

    # Keep rows with at least one relevant patient score available.
    patient_score_cols = [
        "phqtotal",
        "phqtotalv2",
        "gadtotal",
        "ticstot",
        "ticstotv2",
        "kccqos",
    ]

    has_patient_score = df[patient_score_cols].notna().any(axis=1)
    df = df.loc[has_patient_score]

    return df
