# Data privacy rules

The repository works with **confidential, participant-level clinical trial
data**. The rules below come from `AGENTS.md`. They apply to everyone who works
on the project, including AI coding assistants.

## Never inspect or log raw rows

Do not print, log or display individual records. That means no `head()`,
`sample()`, `display()`, `print(df)`, or notebook cell output that shows rows.
Never put actual data values into:

- commit messages, PR descriptions or issue comments,
- error messages or log lines,
- files, test fixtures or debug output,
- prompts or any external tool or service.

## What is allowed

| Allowed                                                        | Not allowed                                         |
|----------------------------------------------------------------|-----------------------------------------------------|
| Schema and metadata: column names, dtypes, row/column counts   | `SELECT *` or full dumps of unreviewed tables       |
| Aggregates: counts, means, quantiles, null rates, distributions | Writing raw data or samples to files or fixtures   |
| Unique values per column                                       | Pasting data into prompts or external tools         |
| Processing: transforms, joins, model training (without printing values) | Printing individual records                  |

## How the code follows these rules

- **Git ignores all data.** `.gitignore` excludes every data format (`*.csv`,
  `*.sav`, `*.dta`, `*.xlsx`, `*.parquet`, `*.rds`, …) and everything under
  `data/`. The only exception is the small annotation CSVs in
  `data/raw/annotations/`.
- **Notebook outputs are stripped** before commit with `nbstripout` (see
  [Development](development.md)).
- **Pipeline errors report counts, not values.** For example, the merge reports
  "*N* duplicate rows", and `map_with_check` reports the unmapped *codes*, never
  patient rows.
- **The fitted risk model does not store its training data.** The R script
  saves coefficients and scaling constants only, not the `clmm` object.
- **Metadata tools** (`inspect_metadata`, `codebook`) read variable names,
  labels and value labels without reading participant rows. See
  [Metadata tools](tools.md).

## When you need to debug with real values

Try these first:

1. Use synthetic or masked data that reproduces the shape of the problem.
2. Reduce the problem to a shape, type or null-count check.
3. Use `inspect_metadata --stats` to see ranges and distinct counts.
4. Ask a team member with data access to check out-of-band.

If none of these works, **stop and ask a human** rather than printing values.
