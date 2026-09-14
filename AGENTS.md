# AGENTS.md

## Data access & privacy rules

This repo contains sensitive datasets. Never inspect or log raw row-level data:
no printing, logging, `head()`, `sample()`, `display()`, or notebook cell output
of individual records, and never include actual values in commit messages, PR
descriptions, or error messages.

**Allowed:** schema/metadata (column names, types, row/column counts) and
aggregates (counts, means, quantiles, null-rates, distributions). Processing
the data (transforms, joins, training) is fine as long as values are never
printed or logged.

**Not allowed:** `SELECT *` on unreviewed tables, writing raw data or samples
to files/fixtures/debug output, or pasting data into prompts or external tools.

If you need to debug something that seems to require real values, try:
synthetic/masked data instead, reducing the problem to a shape/type/null check,
or asking a human to check out-of-band. If none of that works, stop and ask a
human rather than inspecting raw values yourself.

## Inspecting file metadata

For a quick terminal look at an SPSS/Stata/SAS/CSV/Excel file's schema (variable
names, labels, value labels, row/column counts) without generating a workbook —
and, for the stats formats, without ever reading a row of participant data — use:

```bash
# by numeric dataset ID (shows every .sav/.dta file for that study)
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16

# by explicit path, with value-label dictionaries
uv run python -m collaborative_care_analysis.agent.inspect_metadata \
  "data/raw/Individual Datasets/16_Katon_1999/katon1999.sav" --values

# a CSV/Excel export by explicit path (label column shows the pandas dtype)
uv run python -m collaborative_care_analysis.agent.inspect_metadata some_export.csv

# only variables whose name or label matches a regex
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --grep scl
```

CSV and Excel files carry no embedded metadata, so the file is read in full to
recover its schema; still only column names, dtypes and aggregates are printed,
never a row.

Add `--stats` to also read the data and print per-column aggregates — non-null
count, distinct count and, for numeric columns, min/max/mean:

```bash
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --stats --grep scl
```

This is the quickest way to check that a scale actually lies on the range its
label claims before writing a loader for it. It stays within the rules above:
min/max/mean are printed for numeric columns only (where they are the 0% and
100% quantiles of a scale), and non-numeric columns such as free text, dates and
identifiers get counts only — never the values themselves.
