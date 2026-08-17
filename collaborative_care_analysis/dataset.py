import importlib
import inspect
from pathlib import Path

from loguru import logger
import pandas as pd
import typer

from collaborative_care_analysis.config import (
    COLNAME_ROWID,
    COLNAME_STUDYID,
    HARMONIZED_DATASETS_DIR,
    INTERIM_DATASETS_EXPORT_DIR,
)

app = typer.Typer()
PACKAGE_DIR = Path(__file__).parent
DATA_LOADING_DIR = PACKAGE_DIR / "data_loading"


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
    return sorted([d for d in base_dir.glob("harmonization_*") if d.is_dir()])


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


def _add_identifiers(df: pd.DataFrame, script_path: Path) -> pd.DataFrame:
    """Add study/rowid columns to the dataset."""
    df_copy = df.copy()
    study_id = _get_study_id(script_path)
    row_ids = [f"{study_id}_R{i}" for i in range(len(df_copy))]
    if COLNAME_STUDYID in df_copy.columns:
        logger.warning(f"Dataset {script_path.stem} already has a '{COLNAME_STUDYID}' column.")
    if COLNAME_ROWID in df_copy.columns:
        logger.warning(f"Dataset {script_path.stem} already has a '{COLNAME_ROWID}' column.")
    df_copy.insert(0, COLNAME_ROWID, row_ids)
    df_copy.insert(0, COLNAME_STUDYID, study_id)
    return df_copy


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
        df = _add_identifiers(raw_df, script_path)

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
                            f"{harm_type}_{func_suffix}"
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
                    # Check whether study and rowid are still there
                    if COLNAME_STUDYID not in harmonized_df.columns:
                        raise ValueError(
                            f"Harmonization function {func.__name__} removed '{COLNAME_STUDYID}' column for {script_path.stem}."
                        )
                    if COLNAME_ROWID not in harmonized_df.columns:
                        raise ValueError(
                            f"Harmonization function {func.__name__} removed '{COLNAME_ROWID}' column for {script_path.stem}."
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


if __name__ == "__main__":
    app()
