import importlib
import inspect
from pathlib import Path

from loguru import logger
import pandas as pd
import typer

from collaborative_care_analysis.config import (
    COLNAME_STUDYID,
    HARMONIZED_DATASETS_DIR,
    INTERIM_DATASETS_EXPORT_DIR,
    MERGED_DATASET_DIR,
)

app = typer.Typer()
PACKAGE_DIR = Path(__file__).parent
DATA_LOADING_DIR = PACKAGE_DIR / "data_loading"

# Columns every harmonized cluster must expose, used as the join key.
COLNAME_PATIENT_ID = "patient_id"
COLNAME_FOLLOW_UP = "follow_up_months"
CLUSTER_JOIN_KEYS = [COLNAME_STUDYID, COLNAME_PATIENT_ID, COLNAME_FOLLOW_UP]


def _matches_dataset_id(script_path: Path, dataset_id: str) -> bool:
    """Return whether an ID matches a loader's numeric or descriptive identifier."""
    if script_path.stem == dataset_id:
        return True
    name_parts = script_path.stem.split("_")
    if len(name_parts) < 3 or name_parts[0] != "ds":
        return False

    numeric_id = name_parts[1]
    descriptive_id = "_".join(name_parts[2:])
    if dataset_id in (numeric_id, descriptive_id, script_path.stem):
        return True

    # Allow an unpadded numeric ID (e.g. "4") to match a zero-padded loader ID (e.g. "04").
    return dataset_id.isdigit() and numeric_id.isdigit() and int(dataset_id) == int(numeric_id)


def _get_study_id(script_path: Path) -> str:
    """Extract study ID from script path stem (e.g. '17_Katon_2001' from 'ds_17_Katon_2001')."""
    name_parts = script_path.stem.split("_")
    if len(name_parts) >= 3 and name_parts[0] == "ds":
        return "_".join(name_parts[1:])
    return script_path.stem


def _get_harmonization_dirs(package_dir: Path | None = None) -> list[Path]:
    """Find all directories named 'harmonization_*' in the package."""
    base_dir = package_dir if package_dir is not None else PACKAGE_DIR
    return sorted(
        d for d in base_dir.glob("harmonization_*") if d.is_dir() and d.name.isidentifier()
    )


def _get_harmonization_type(harm_dir: Path) -> str:
    """Extract harmonization type from directory name (e.g. 'harmonization_example' -> 'example')."""
    dir_name = harm_dir.name
    if dir_name.startswith("harmonization_"):
        return dir_name[len("harmonization_") :]
    return dir_name


def _find_matching_harmonization_scripts(harm_dir: Path, dataset_stem: str) -> list[Path]:
    """Find all harmonization scripts in harm_dir that match the dataset identifier."""
    return [
        s
        for s in sorted(harm_dir.rglob("*.py"))
        if s.name != "__init__.py"
        and (
            s.stem == dataset_stem
            or _matches_dataset_id(s, dataset_stem)
            or _matches_dataset_id(Path(f"{dataset_stem}.py"), s.stem)
        )
    ]


def _get_harmonization_functions(module) -> list:
    """Return all harmonization functions defined in the given module."""
    funcs = [
        obj
        for name, obj in module.__dict__.items()
        if inspect.isfunction(obj)
        and obj.__module__ == module.__name__
        and name.startswith("harmoniz")
    ]
    if not funcs:
        funcs = [
            obj
            for name, obj in module.__dict__.items()
            if inspect.isfunction(obj)
            and obj.__module__ == module.__name__
            and not name.startswith("_")
        ]
    return funcs


def _add_identifier(df: pd.DataFrame, script_path: Path) -> pd.DataFrame:
    """Add study identifier to the dataset."""
    df_copy = df.copy()
    study_id = _get_study_id(script_path)
    if COLNAME_STUDYID in df_copy.columns:
        logger.warning(f"Dataset {script_path.stem} already has a '{COLNAME_STUDYID}' column.")
    df_copy.insert(0, COLNAME_STUDYID, study_id)
    return df_copy


def _clear_directory(directory: Path, description: str) -> None:
    """Delete all CSVs in a directory before a full regeneration run.

    Only called when no dataset_id was given: a targeted run must not destroy
    output for the datasets it is not regenerating.
    """
    existing = sorted(directory.glob("*.csv"))
    if not existing:
        return
    for path in existing:
        path.unlink()
    logger.info(f"Cleared {len(existing)} existing {description} file(s) from {directory}.")


@app.callback()
def main():
    """Empty callback to require command names."""


@app.command()
def export(
    dataset_id: str | None = typer.Argument(
        None,
        help="Dataset ID to export, such as '04' or 'Bekelman_2018'.",
    ),
):
    """Load every dataset and save each result to the interim data directory."""
    INTERIM_DATASETS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # A full run regenerates everything, so files left over from renamed or
    # deleted loaders would otherwise linger.
    if dataset_id is None:
        _clear_directory(INTERIM_DATASETS_EXPORT_DIR, "exported dataset")

    loader_scripts = [
        script_path
        for script_path in sorted(DATA_LOADING_DIR.rglob("*.py"))
        if script_path.name != "__init__.py"
        and (dataset_id is None or _matches_dataset_id(script_path, dataset_id))
    ]
    if dataset_id is not None and not loader_scripts:
        raise typer.BadParameter(
            f"No data-loading script matches '{dataset_id}'.",
            param_hint="dataset_id",
        )

    for script_path in loader_scripts:
        module_path = ".".join(
            (
                "collaborative_care_analysis",
                *script_path.relative_to(PACKAGE_DIR).with_suffix("").parts,
            )
        )
        loader = importlib.import_module(module_path)
        output_path = INTERIM_DATASETS_EXPORT_DIR / f"{script_path.stem}.csv"

        logger.info(f"Loading dataset with {script_path.name}.")
        loader.load().to_csv(output_path, index=False)
        logger.success(f"Saved processed dataset to {output_path}.")


@app.command()
def harmonize(
    dataset_id: str | None = typer.Argument(
        None,
        help="Dataset ID to harmonize, such as '17' or 'Katon_2001'.",
    ),
):
    """Load datasets, apply harmonization scripts to original data, and save results to interim."""
    HARMONIZED_DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    # A full run regenerates everything. This is also what removes orphaned
    # cluster files whose harmonization_* directory was renamed or deleted --
    # those are what make merge emit "no matching harmonization type".
    if dataset_id is None:
        _clear_directory(HARMONIZED_DATASETS_DIR, "harmonized cluster")

    loader_scripts = [
        script_path
        for script_path in sorted(DATA_LOADING_DIR.rglob("*.py"))
        if script_path.name != "__init__.py"
        and (dataset_id is None or _matches_dataset_id(script_path, dataset_id))
    ]
    if dataset_id is not None and not loader_scripts:
        raise typer.BadParameter(
            f"No data-loading script matches '{dataset_id}'.",
            param_hint="dataset_id",
        )

    harmonization_dirs = _get_harmonization_dirs()
    if not harmonization_dirs:
        logger.warning("No harmonization_* directories found.")

    for script_path in loader_scripts:
        module_path = ".".join(
            (
                "collaborative_care_analysis",
                *script_path.relative_to(PACKAGE_DIR).with_suffix("").parts,
            )
        )
        loader = importlib.import_module(module_path)

        logger.info(f"Loading dataset with {script_path.name}.")
        raw_df = loader.load()
        df = _add_identifier(raw_df, script_path)

        applied_count = 0
        for harm_dir in harmonization_dirs:
            harm_type = _get_harmonization_type(harm_dir)
            matching_scripts = _find_matching_harmonization_scripts(harm_dir, script_path.stem)

            for harm_script in matching_scripts:
                harm_module_path = ".".join(
                    (
                        "collaborative_care_analysis",
                        *harm_script.relative_to(PACKAGE_DIR).with_suffix("").parts,
                    )
                )
                harm_module = importlib.import_module(harm_module_path)
                harm_funcs = _get_harmonization_functions(harm_module)

                for func in harm_funcs:
                    if len(harm_funcs) == 1:
                        postfix = harm_type
                    else:
                        func_suffix = (
                            func.__name__.removeprefix("harmonize_")
                            .removeprefix("harmonize")
                            .strip("_")
                        )
                        postfix = (
                            f"{harm_type}-{func_suffix}"
                            if func_suffix and func_suffix != harm_type
                            else (func_suffix or harm_type)
                        )

                    output_path = HARMONIZED_DATASETS_DIR / f"{script_path.stem}_{postfix}.csv"
                    logger.info(
                        f"Applying {func.__name__} from {harm_dir.name}/{harm_script.name} to {script_path.stem}."
                    )

                    # Run harmonization script
                    harmonized_df = func(df.copy())

                    # Check output from harmonization script
                    if harmonized_df is None:
                        raise ValueError(
                            f"Harmonization function {func.__name__} returned None for {script_path.stem}."
                        )
                    # Check whether study identifier is still there
                    if COLNAME_STUDYID not in harmonized_df.columns:
                        raise ValueError(
                            f"Harmonization function {func.__name__} removed '{COLNAME_STUDYID}' column for {script_path.stem}."
                        )
                    # Check whether any rows have been dropped
                    if len(harmonized_df) != len(df):
                        logger.warning(
                            f"Harmonization function {func.__name__} dropped rows for {script_path.stem}."
                        )

                    # Export data
                    harmonized_df.to_csv(output_path, index=False)
                    logger.success(f"Saved harmonized dataset to {output_path}.")

                    # Count successful harmonization
                    applied_count += 1

        if applied_count == 0:
            logger.info(f"No harmonization scripts applied to {script_path.stem}.")


def _split_harmonized_stem(stem: str, harm_types: list[str]) -> tuple[str, str] | None:
    """Split '<dataset_stem>_<harm_type>[-<func_suffix>]' into (dataset_stem, harm_type).

    harm_types must be sorted longest-first so that a type which contains
    another as a substring is matched before the shorter one.
    """
    for harm_type in harm_types:
        marker = f"_{harm_type}"
        idx = stem.find(marker)
        if idx != -1:
            return stem[:idx], harm_type
    return None


def _load_cluster(path: Path) -> pd.DataFrame:
    """Read one harmonized cluster file and validate it can be joined."""
    df = pd.read_csv(path)

    missing = [key for key in CLUSTER_JOIN_KEYS if key not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing join key(s): {missing}.")

    # A non-unique key would turn the inner join into a cartesian product.
    if df.duplicated(subset=CLUSTER_JOIN_KEYS).any():
        n_dupes = df.duplicated(subset=CLUSTER_JOIN_KEYS).sum()
        raise ValueError(f"{path.name} has {n_dupes} duplicate rows on the join key.")

    return df


def _merge_harmonized() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Join each dataset's harmonized clusters, then stack all datasets.

    Returns the merged frame and a mapping of cluster name -> every column
    contributed to that cluster across all studies.
    """
    # Longest-first: a type that contains another as a substring must be tried
    # before the shorter one, or find() would split on the wrong marker.
    harm_types = sorted(
        (_get_harmonization_type(d) for d in _get_harmonization_dirs()),
        key=len,
        reverse=True,
    )

    cluster_files = sorted(HARMONIZED_DATASETS_DIR.glob("*.csv"))
    if not cluster_files:
        raise FileNotFoundError(
            f"No harmonized files in {HARMONIZED_DATASETS_DIR}. Run 'harmonize' first."
        )

    # dataset_stem -> cluster -> file
    by_dataset: dict[str, dict[str, Path]] = {}
    for path in cluster_files:
        parsed = _split_harmonized_stem(path.stem, harm_types)
        if parsed is None:
            logger.warning(
                f"Skipping {path.name}: no matching harmonization type. "
                f"Re-run 'harmonize' without a dataset_id to clear stale files."
            )
            continue
        dataset_stem, cluster = parsed
        by_dataset.setdefault(dataset_stem, {})[cluster] = path

    cluster_columns: dict[str, set[str]] = {}
    reconstructed: list[pd.DataFrame] = []

    for dataset_stem, clusters in sorted(by_dataset.items()):
        merged = None

        for cluster, path in sorted(clusters.items()):
            df = _load_cluster(path)
            new_cols = [c for c in df.columns if c not in CLUSTER_JOIN_KEYS]
            cluster_columns.setdefault(cluster, set()).update(new_cols)

            if merged is None:
                merged = df
                continue

            # Only the join keys may be shared between clusters. Anything else
            # means two harmonization scripts claim the same output name, which
            # pandas would silently resolve into col_x / col_y.
            overlap = (set(merged.columns) & set(df.columns)) - set(CLUSTER_JOIN_KEYS)
            if overlap:
                raise ValueError(
                    f"{dataset_stem}: column(s) {sorted(overlap)} appear in cluster "
                    f"'{cluster}' and in an earlier cluster. Clusters may only share "
                    f"{CLUSTER_JOIN_KEYS}."
                )

            before = len(merged)
            merged = merged.merge(df, on=CLUSTER_JOIN_KEYS, how="inner")
            if len(merged) < before:
                logger.warning("=" * 88)
                logger.warning(
                    f"ROW LOSS: joining cluster '{cluster}' into {dataset_stem} dropped "
                    f"{before - len(merged)} of {before} row(s)."
                )
                logger.warning(
                    "The clusters do not cover the same patient-visits. This is almost "
                    "always a harmonization bug, not intended filtering."
                )
                logger.warning("=" * 88)

        if merged is None:
            logger.warning(f"No usable clusters for {dataset_stem}, skipping.")
            continue

        logger.info(
            f"Reconstructed {dataset_stem}: {merged.shape[0]} rows, "
            f"{merged.shape[1]} columns from {len(clusters)} cluster(s)."
        )
        reconstructed.append(merged)

    if not reconstructed:
        raise ValueError("No datasets could be reconstructed from the harmonized files.")

    cluster_columns_sorted = {c: sorted(cols) for c, cols in sorted(cluster_columns.items())}

    # Stack studies. pandas takes the union of columns and fills gaps with NaN,
    # so a study missing a cluster simply has those columns empty.
    merged_df = pd.concat(reconstructed, ignore_index=True, sort=False)

    ordered = CLUSTER_JOIN_KEYS + [col for cols in cluster_columns_sorted.values() for col in cols]
    merged_df = merged_df.reindex(columns=ordered)

    return merged_df, cluster_columns_sorted


@app.command()
def merge():
    """Join each study's harmonized clusters, then stack all studies into one frame."""
    MERGED_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    _clear_directory(MERGED_DATASET_DIR, "merged dataset")
    merged_df, cluster_columns = _merge_harmonized()

    for cluster, cols in cluster_columns.items():
        logger.info(f"Cluster '{cluster}': {len(cols)} column(s).")

    output_path = MERGED_DATASET_DIR / "merged_dataset.csv"
    merged_df.to_csv(output_path, index=False)
    logger.success(
        f"Saved merged dataset ({merged_df.shape[0]} rows, "
        f"{merged_df.shape[1]} columns) to {output_path}."
    )

    return merged_df, cluster_columns


@app.command()
def run():
    """Run the full pipeline: export, then harmonize, then merge.

    Each stage clears its own output directory first, so this is a clean
    regeneration from the raw data.
    """
    logger.info("=== Stage 1/3: export ===")
    export(dataset_id=None)

    logger.info("=== Stage 2/3: harmonize ===")
    harmonize(dataset_id=None)

    logger.info("=== Stage 3/3: merge ===")
    merged_df, cluster_columns = merge()

    logger.success("Full pipeline complete.")
    return merged_df, cluster_columns


if __name__ == "__main__":
    app()
