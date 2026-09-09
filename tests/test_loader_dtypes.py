from pathlib import Path

import pandas as pd
import pytest
from tests.helpers import import_loader, loader_scripts


@pytest.mark.parametrize("script_path", loader_scripts(), ids=lambda p: p.stem)
def test_loader_output_uses_nullable_dtypes(script_path: Path) -> None:
    """Every loader's output must use pandas' nullable dtypes (Int64,
    Float64, boolean, string) rather than plain numpy dtypes.

    Numpy int64/bool cannot represent missing values -- pandas silently
    upcasts a numpy int column with NaN to float64, which is how integer
    codes quietly become '1.0' or how missingness gets masked as 0. Nullable
    dtypes make missingness explicit and force every downstream step to
    handle it deliberately, instead of only surfacing once a CSV round-trip
    already lost the distinction.
    """
    loader = import_loader(script_path)
    df = loader.load()

    non_nullable = []
    for col in df.columns:
        dtype = df[col].dtype
        is_nullable_ext = pd.api.types.is_extension_array_dtype(dtype)
        is_plain_object = dtype == object  # free-text/string columns are fine as object
        if not (is_nullable_ext or is_plain_object):
            non_nullable.append((col, str(dtype)))

    assert not non_nullable, (
        f"{script_path.stem}: column(s) with a non-nullable dtype leaving the "
        f"loader (use e.g. 'Int64'/'Float64'/'boolean' instead of numpy "
        f"int64/float64/bool): {non_nullable}"
    )


@pytest.mark.parametrize("script_path", loader_scripts(), ids=lambda p: p.stem)
def test_loader_columns_have_single_inferred_type(script_path: Path) -> None:
    """No column should mix incompatible Python value types (e.g. some rows
    numeric, some rows string) within the same column.

    This is distinct from the nullable-dtype check: an ``object`` column of
    strings is fine, but an ``object`` column mixing ``"3"`` and ``3`` and
    ``True`` is a sign of inconsistent recoding.
    """
    loader = import_loader(script_path)
    df = loader.load()

    mixed_cols = []
    for col in df.columns:
        inferred = pd.api.types.infer_dtype(df[col], skipna=True)
        if inferred in ("mixed", "mixed-integer"):
            mixed_cols.append(col)

    assert not mixed_cols, (
        f"{script_path.stem}: column(s) with mixed value types: {mixed_cols}. "
        f"Inspect with df['<col>'].apply(type).value_counts()."
    )
