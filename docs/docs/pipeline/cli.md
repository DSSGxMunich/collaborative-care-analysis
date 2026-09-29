# Command-line reference

All pipeline commands are subcommands of `collaborative_care_analysis/dataset.py`:

```bash
uv run collaborative_care_analysis/dataset.py --help
uv run collaborative_care_analysis/dataset.py <command> --help
```

## Dataset IDs

Wherever a command takes a `DATASET_ID`, you can give any of these forms. They
all match the loader `ds_04_Bekelman_2018.py`:

| Form             | Example                |
|------------------|------------------------|
| Number           | `04` or `4`            |
| Name             | `Bekelman_2018`        |
| Full file stem   | `ds_04_Bekelman_2018`  |

An ID that matches no loader raises an error.

## `run`

Run the whole pipeline: export → harmonize → merge → POOL2 backfill → enrich.

```bash
uv run collaborative_care_analysis/dataset.py run                 # all studies, clean regeneration
uv run collaborative_care_analysis/dataset.py run 4               # regenerate one study only
uv run collaborative_care_analysis/dataset.py run Katon_2001
uv run collaborative_care_analysis/dataset.py run -x 04 -x 17     # all studies except 04 and 17
uv run collaborative_care_analysis/dataset.py run --exclude 04 --exclude 17
```

| Argument / option     | Description                                                                                |
|-----------------------|--------------------------------------------------------------------------------------------|
| `DATASET_ID`          | Optional. Only this study is re-exported and re-harmonized. The merge still uses every other study's existing harmonized files. |
| `-x`, `--exclude ID`  | Repeatable. Clean regeneration that skips the given studies. Cannot be combined with `DATASET_ID`. |

After an exclusion run completes, a bold red warning lists the excluded IDs.
Raw data are never modified.

## `export`

Load each selected study with its loader and write the result to
`data/interim/exported_datasets/ds_<NN>_<Name>.csv`.

```bash
uv run collaborative_care_analysis/dataset.py export
uv run collaborative_care_analysis/dataset.py export 04
uv run collaborative_care_analysis/dataset.py export Bekelman_2018
```

Takes the same `DATASET_ID` / `--exclude` options as `run`.

## `harmonize`

Load each selected study, add `STUDY_ID`, and apply every matching
harmonization function. Each result is written to
`data/interim/harmonized_datasets/ds_<NN>_<Name>_<cluster>.csv`.

```bash
uv run collaborative_care_analysis/dataset.py harmonize
uv run collaborative_care_analysis/dataset.py harmonize 17
uv run collaborative_care_analysis/dataset.py harmonize Katon_2001
```

Takes the same `DATASET_ID` / `--exclude` options as `run`. See
[Harmonization](harmonization.md) for how scripts and functions are discovered.

## `merge`

Join each study's clusters and stack all studies into
`data/interim/merged_dataset/merged_dataset.csv`.

```bash
uv run collaborative_care_analysis/dataset.py merge
```

Takes no arguments. It always merges every harmonized file present. See
[Merge](merge-and-enrich.md#merge).

## `enrich`

Backfill missing `age` / `sex` from POOL2, then join the study-level
extra-info sheet. Reads the merged dataset and writes
`data/interim/enriched_dataset/enriched_dataset.csv`.

```bash
uv run collaborative_care_analysis/dataset.py enrich
```

Requires `merge` to have run first.

## Other entry points

| Command                                                                          | Purpose                                                   |
|----------------------------------------------------------------------------------|-----------------------------------------------------------|
| `uv run python -m collaborative_care_analysis.codebook <NN>`                     | Generate an Excel codebook from SPSS/Stata metadata ([Metadata tools](../tools.md)) |
| `uv run python -m collaborative_care_analysis.agent.inspect_metadata <NN or path>` | Print a file's schema in the terminal ([Metadata tools](../tools.md)) |
| `uv run python -m collaborative_care_analysis.data_analysis.dataset_creation`    | Build the analysis datasets ([Analysis dataset](../analysis/analysis-dataset.md)) |
| `Rscript collaborative_care_analysis/data_analysis/risk_score_model.R fit`       | Fit the Step 1 risk model ([Risk score model](../analysis/risk-score-model.md)) |
