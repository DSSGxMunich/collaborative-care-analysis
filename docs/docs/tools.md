# Metadata tools

Two tools let you understand a raw file **without looking at participant rows**.
Use them before you write a loader or a harmonizer.

## `inspect_metadata`: quick terminal look

`collaborative_care_analysis/agent/inspect_metadata.py`

For SPSS / Stata / SAS files, it prints variable names, variable labels, value
labels and row/column counts **from the file metadata only**. No data row is
read.

```bash
# every .sav/.dta file of dataset 16
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16

# one file, with value-label dictionaries
uv run python -m collaborative_care_analysis.agent.inspect_metadata \
  "data/raw/Individual Datasets/16_Katon_1999/katon1999.sav" --values

# only variables whose name or label matches a regex (case-insensitive)
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --grep scl

# per-column aggregates
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --stats --grep scl

# CSV / Excel (explicit path only)
uv run python -m collaborative_care_analysis.agent.inspect_metadata some_export.csv --stats
```

| Argument         | Description                                                                                  |
|------------------|----------------------------------------------------------------------------------------------|
| `target`         | A file path (`.sav`, `.dta`, `.sas7bdat`, `.csv`, `.xlsx`) or a numeric dataset ID           |
| `--values`       | Also print the value-label dictionary of each labelled variable                              |
| `--grep REGEX`   | Only show variables whose name or label matches                                              |
| `--stats`        | Read the data and print aggregates: non-null count, distinct count and, for **numeric columns only**, min / max / mean |

### Why `--stats` stays within the privacy rules

- min / max / mean are shown **only for numeric columns**, where they are the
  0 % / 100 % quantiles of a scale.
- Free-text, date and ID columns get **counts only**. Their values are never
  printed.

`--stats` is the quickest way to find a scale that is off its documented
range, for example a "GAD-7 total" that reaches 26 or a 0–3 item with a 9 in it.

CSV and Excel files have no embedded metadata, so they are always read in full
to recover their schema. The label column then shows the pandas dtype, and
there are no value labels. Only names, dtypes and aggregates are printed.

## `codebook`: Excel codebook

`collaborative_care_analysis/codebook.py`

This generates a codebook workbook for a study that did not come with one. It
uses the metadata embedded in its SPSS / Stata files and reads them with
`metadataonly=True`.

```bash
uv run python -m collaborative_care_analysis.codebook 13
```

- Finds `data/raw/Individual Datasets/<NN>_*/` (exactly one folder must match).
- Collects every `.sav` / `.dta` file under it. If the same file exists in
  both formats, the SPSS version wins.
- Writes one `<file>_metadata.xlsx` per file to
  `data/interim/generated_codebooks/<NN>_<Name>/`.
- The **Codebook** sheet joins the variable labels with the value labels: one
  row per coded value, and variables without value labels keep empty value
  fields. The header row is frozen and has filters.
