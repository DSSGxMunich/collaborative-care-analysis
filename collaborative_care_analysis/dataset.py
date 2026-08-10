import importlib
from pathlib import Path

from loguru import logger
import typer

from collaborative_care_analysis.config import INTERIM_DATASETS_EXPORT_DIR

app = typer.Typer()
DATA_LOADING_DIR = Path(__file__).parent / "data_loading"


def _matches_dataset_id(script_path: Path, dataset_id: str) -> bool:
    """Return whether an ID matches a loader's numeric or descriptive identifier."""
    name_parts = script_path.stem.split("_")
    if len(name_parts) < 3 or name_parts[0] != "ds":
        return script_path.stem == dataset_id

    numeric_id = name_parts[1]
    descriptive_id = "_".join(name_parts[2:])
    return dataset_id in (numeric_id, descriptive_id)


@app.callback()
def main():
    """Empty callback to require command names."""
    pass


@app.command()
def export(
    dataset_id: str | None = typer.Argument(
        None,
        help="Dataset ID to export, such as '04' or 'Bekelman_2018'.",
    ),
):
    """Load every dataset and save each result to the processed-data directory."""
    INTERIM_DATASETS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Loader filenames follow ds_<numeric-id>_<descriptive-id>.py.
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
        # Import each loader by its package path so its own imports resolve normally.
        module_path = ".".join(
            (
                "collaborative_care_analysis",
                *script_path.relative_to(DATA_LOADING_DIR.parent).with_suffix("").parts,
            )
        )
        loader = importlib.import_module(module_path)
        output_path = INTERIM_DATASETS_EXPORT_DIR / f"{script_path.stem}.csv"

        logger.info(f"Loading dataset with {script_path.name}.")
        loader.load().to_csv(output_path, index=False)
        logger.success(f"Saved processed dataset to {output_path}.")


if __name__ == "__main__":
    app()
