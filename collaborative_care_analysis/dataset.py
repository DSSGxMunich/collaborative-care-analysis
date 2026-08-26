from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path
from typing import TypeVar

from loguru import logger
import pandas as pd
from rich.console import Console
from rich.table import Table
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
    return dataset_id in (numeric_id, descriptive_id, script_path.stem)


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


def _load_dataset(loader, script_path: Path) -> pd.DataFrame:
    """Call a loader's load() and validate that it produced a follow-up column.

    Loaders are expected to normalize their time axis into COLNAME_FOLLOW_UP;
    without it, a dataset would only fail much later and confusingly, when
    merge() joins on CLUSTER_JOIN_KEYS.
    """
    df = loader.load()
    if COLNAME_FOLLOW_UP not in df.columns:
        raise ValueError(
            f"Loader {script_path.stem} did not produce a '{COLNAME_FOLLOW_UP}' column."
        )
    return df


def _find_baseline_only_columns(df: pd.DataFrame) -> list[str]:
    """Return columns set only at each multi-visit patient's baseline row.

    A loader is expected to broadcast a time-invariant value (e.g. sex, a
    treatment arm) to every one of a patient's follow-up rows, the way
    ds_03_Aragones_2019.load() does. If a column is only ever populated on
    the row with that patient's minimum follow_up_months, and left null on
    every other row for the same patient, later stages that expect it to be
    present at every visit will silently see it as missing.
    """
    if COLNAME_PATIENT_ID not in df.columns or COLNAME_FOLLOW_UP not in df.columns:
        return []

    baseline_month = df.groupby(COLNAME_PATIENT_ID)[COLNAME_FOLLOW_UP].transform("min")
    is_baseline_row = df[COLNAME_FOLLOW_UP] == baseline_month
    has_multiple_visits = (
        df.groupby(COLNAME_PATIENT_ID)[COLNAME_FOLLOW_UP].transform("nunique") > 1
    )

    flagged = []
    for col in df.columns:
        if col in (COLNAME_PATIENT_ID, COLNAME_FOLLOW_UP):
            continue
        notna = df[col].notna()
        set_at_baseline = (notna & has_multiple_visits & is_baseline_row).any()
        set_at_follow_up = (notna & has_multiple_visits & ~is_baseline_row).any()
        if set_at_baseline and not set_at_follow_up:
            flagged.append(col)
    return flagged


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
        _load_dataset(loader, script_path).to_csv(output_path, index=False)
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
        raw_df = _load_dataset(loader, script_path)
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


@dataclass
class _StageResult:
    """Outcome of one attempted pipeline stage, for the 'report' command."""

    dataset: str
    stage: str
    status: str  # "ok", "warning", or "error"
    detail: str = ""


_T = TypeVar("_T")


def _run_stage(
    results: list[_StageResult], dataset: str, stage: str, func: Callable[[], _T]
) -> _T | None:
    """Run func, recording its outcome in results instead of letting it abort the report.

    Returns func's return value, or None if it raised.
    """
    try:
        value = func()
    except Exception as exc:  # noqa: BLE001 -- must survive any loader/harmonization bug
        detail = f"{type(exc).__name__}: {exc}"
        results.append(_StageResult(dataset, stage, "error", detail))
        logger.error(f"[{dataset}] {stage} failed: {detail}")
        return None
    results.append(_StageResult(dataset, stage, "ok"))
    return value


def _run_check(
    results: list[_StageResult], dataset: str, stage: str, func: Callable[[], str | None]
) -> None:
    """Run a non-raising heuristic check. func returns a warning message, or None if clean.

    Unlike _run_stage, an exception here means the check itself is broken, not
    that the dataset has a problem -- it's still recorded as an error so it's
    visible, but the check's own finding is a "warning", never blocks the rest
    of the pipeline, and isn't counted alongside real stage failures.
    """
    try:
        warning = func()
    except Exception as exc:  # noqa: BLE001 -- must survive a broken check
        detail = f"{type(exc).__name__}: {exc}"
        results.append(_StageResult(dataset, stage, "error", detail))
        logger.error(f"[{dataset}] {stage} failed: {detail}")
        return
    if warning:
        results.append(_StageResult(dataset, stage, "warning", warning))
        logger.warning(f"[{dataset}] {stage}: {warning}")
        return
    results.append(_StageResult(dataset, stage, "ok"))


def _print_report(results: list[_StageResult]) -> None:
    """Print a per-dataset overview table, then tables of warnings and failures."""
    console = Console()

    overview = Table(title="Pipeline report: dataset overview")
    overview.add_column("Dataset")
    overview.add_column("OK", justify="right")
    overview.add_column("Warned", justify="right")
    overview.add_column("Failed", justify="right")
    overview.add_column("Status")

    for dataset in sorted({r.dataset for r in results}):
        dataset_results = [r for r in results if r.dataset == dataset]
        n_ok = sum(1 for r in dataset_results if r.status == "ok")
        n_warn = sum(1 for r in dataset_results if r.status == "warning")
        n_error = sum(1 for r in dataset_results if r.status == "error")
        if n_error:
            status = "[bold red]FAILED[/bold red]"
        elif n_warn:
            status = "[yellow]WARNED[/yellow]"
        else:
            status = "[green]OK[/green]"
        overview.add_row(dataset, str(n_ok), str(n_warn), str(n_error), status)

    console.print(overview)

    warnings = [r for r in results if r.status == "warning"]
    if warnings:
        warning_table = Table(title="Warnings")
        warning_table.add_column("Dataset")
        warning_table.add_column("Stage")
        warning_table.add_column("Message")
        for r in warnings:
            warning_table.add_row(r.dataset, r.stage, r.detail)
        console.print(warning_table)

    failures = [r for r in results if r.status == "error"]
    if not failures:
        logger.success("No pipeline failures.")
        return

    detail_table = Table(title="Failures")
    detail_table.add_column("Dataset")
    detail_table.add_column("Stage")
    detail_table.add_column("Error type")
    detail_table.add_column("Message")
    for r in failures:
        error_type, _, message = r.detail.partition(": ")
        detail_table.add_row(r.dataset, r.stage, error_type, message)
    console.print(detail_table)

    issue_counts = Counter(r.detail.partition(": ")[0] for r in failures)
    issue_table = Table(title="Issue types")
    issue_table.add_column("Error type")
    issue_table.add_column("Count", justify="right")
    for error_type, count in issue_counts.most_common():
        issue_table.add_row(error_type, str(count))
    console.print(issue_table)

    n_failed_datasets = len({r.dataset for r in failures})
    logger.error(f"{len(failures)} stage(s) failed across {n_failed_datasets} dataset(s).")


@app.command()
def report(
    dataset_id: str | None = typer.Argument(
        None,
        help="Dataset ID to check, such as '04' or 'Bekelman_2018'. Omit to check every dataset.",
    ),
):
    """Run the full pipeline for one or all datasets, but never let one failure stop the rest.

    Every export/harmonize/merge step is attempted and its outcome recorded,
    then a summary table of what succeeded and what errored -- and why -- is
    printed at the end. Use this to triage broken loaders or harmonization
    scripts across the whole dataset collection in one run.
    """
    INTERIM_DATASETS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    HARMONIZED_DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    if dataset_id is None:
        _clear_directory(INTERIM_DATASETS_EXPORT_DIR, "exported dataset")
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
    results: list[_StageResult] = []

    for script_path in loader_scripts:
        dataset = script_path.stem
        logger.info(f"=== Checking {dataset} ===")

        def _do_export(script_path=script_path, dataset=dataset):
            module_path = ".".join(
                (
                    "collaborative_care_analysis",
                    *script_path.relative_to(PACKAGE_DIR).with_suffix("").parts,
                )
            )
            loader = importlib.import_module(module_path)
            raw_df = _load_dataset(loader, script_path)
            raw_df.to_csv(INTERIM_DATASETS_EXPORT_DIR / f"{dataset}.csv", index=False)
            return raw_df

        raw_df = _run_stage(results, dataset, "export", _do_export)
        if raw_df is None:
            continue

        def _do_check_baseline_only(raw_df=raw_df) -> str | None:
            flagged = _find_baseline_only_columns(raw_df)
            if not flagged:
                return None
            total = sum(
                1 for c in raw_df.columns if c not in (COLNAME_PATIENT_ID, COLNAME_FOLLOW_UP)
            )
            return (
                f"{len(flagged)} of {total} column(s) look time-invariant but are only "
                "populated at each patient's baseline visit -- they may need to be "
                "forward-filled to every follow-up row."
            )

        _run_check(results, dataset, "check:baseline_only_columns", _do_check_baseline_only)

        def _do_add_identifier(raw_df=raw_df, script_path=script_path):
            return _add_identifier(raw_df, script_path)

        df = _run_stage(results, dataset, "add_identifier", _do_add_identifier)
        if df is None:
            continue

        for harm_dir in harmonization_dirs:
            harm_type = _get_harmonization_type(harm_dir)
            matching_scripts = _find_matching_harmonization_scripts(harm_dir, dataset)

            for harm_script in matching_scripts:

                def _import_harm_module(harm_script=harm_script):
                    harm_module_path = ".".join(
                        (
                            "collaborative_care_analysis",
                            *harm_script.relative_to(PACKAGE_DIR).with_suffix("").parts,
                        )
                    )
                    return importlib.import_module(harm_module_path)

                import_stage = f"harmonize:{harm_dir.name}/{harm_script.name}:import"
                harm_module = _run_stage(results, dataset, import_stage, _import_harm_module)
                if harm_module is None:
                    continue

                harm_funcs = _get_harmonization_functions(harm_module)
                for func in harm_funcs:

                    def _do_apply(
                        func=func,
                        harm_funcs=harm_funcs,
                        harm_type=harm_type,
                        dataset=dataset,
                        df=df,
                    ):
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
                        output_path = HARMONIZED_DATASETS_DIR / f"{dataset}_{postfix}.csv"

                        harmonized_df = func(df.copy())
                        if harmonized_df is None:
                            raise ValueError(f"{func.__name__} returned None.")
                        if COLNAME_STUDYID not in harmonized_df.columns:
                            raise ValueError(
                                f"{func.__name__} removed '{COLNAME_STUDYID}' column."
                            )
                        if len(harmonized_df) != len(df):
                            logger.warning(f"{func.__name__} dropped rows for {dataset}.")

                        harmonized_df.to_csv(output_path, index=False)
                        return output_path

                    func_stage = f"harmonize:{harm_dir.name}/{harm_script.name}:{func.__name__}"
                    _run_stage(results, dataset, func_stage, _do_apply)

    if not loader_scripts:
        _print_report(results)
        return

    _run_stage(results, "ALL", "merge", merge)
    _print_report(results)


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
