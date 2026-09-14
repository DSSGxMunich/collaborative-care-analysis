"""Source-code and schema hygiene for the cluster-harmonization package.

These need no study data. They enforce the conventions the package claims to
follow, so a future edit that quietly reintroduces a bare assert or a column
name that differs from another only by case fails here rather than in a
result table.
"""

import ast
import pathlib
import re

import pandas as pd
import pytest

from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.registry import (
    IMPLEMENTED_CLUSTERS,
    REQUIRED_ATTRIBUTES,
    cluster_modules,
    source_pairs,
)

PACKAGE = pathlib.Path("collaborative_care_analysis/harmonization_column_clusters")
SOURCES = sorted(PACKAGE.glob("*.py"))


def _module_ids(paths):
    return [path.name for path in paths]


# --- source hygiene ----------------------------------------------------------


@pytest.mark.parametrize("path", SOURCES, ids=_module_ids(SOURCES))
def test_module_contains_no_bare_assert(path) -> None:
    """An assert vanishes under `python -O`, taking its guarantee with it.

    Data problems warn and drop to missing; code and schema problems raise.
    Neither is an assert.
    """
    tree = ast.parse(path.read_text())
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert asserts == [], f"{path.name} has assert(s) at line(s) {asserts}"


@pytest.mark.parametrize("path", SOURCES, ids=_module_ids(SOURCES))
def test_module_contains_no_unfinished_work_marker(path) -> None:
    markers = [
        index + 1
        for index, line in enumerate(path.read_text().split("\n"))
        if re.search(r"#\s*(TODO|FIXME|XXX|HACK)\b", line)
    ]
    assert markers == [], f"{path.name} has a marker at line(s) {markers}"


@pytest.mark.parametrize("path", SOURCES, ids=_module_ids(SOURCES))
def test_module_has_a_docstring(path) -> None:
    """Each module has to say what it harmonizes and on what evidence."""
    assert ast.get_docstring(ast.parse(path.read_text())), path.name


# Functions whose whole purpose is to print a table for a human to read.
# loguru would prefix every line with a timestamp and level, which is exactly
# what you do not want in a column-by-column report.
INTERACTIVE_REPORTERS = ("preview_",)


@pytest.mark.parametrize("path", SOURCES, ids=_module_ids(SOURCES))
def test_module_never_prints_outside_an_interactive_report(path) -> None:
    """Anything the build emits goes through loguru; print would bypass the log.

    The exception is a function named ``preview_*``, which exists to put a
    readable table in front of a person and is never called by the build.
    """
    tree = ast.parse(path.read_text())
    exempt = {
        node
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        and function.name.startswith(INTERACTIVE_REPORTERS)
        for node in ast.walk(function)
    }
    prints = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
        and node not in exempt
    ]
    assert prints == [], f"{path.name} prints outside a preview at line(s) {prints}"


# --- registry contract -------------------------------------------------------


def test_every_listed_cluster_imports_and_satisfies_the_contract() -> None:
    modules = cluster_modules()
    assert len(modules) == len(IMPLEMENTED_CLUSTERS)
    for module in modules:
        for attribute in REQUIRED_ATTRIBUTES:
            assert hasattr(module, attribute), f"{module.__name__}.{attribute}"


def test_implemented_clusters_are_listed_alphabetically() -> None:
    """The list is append-only and sorted so two cluster branches merge cleanly."""
    assert IMPLEMENTED_CLUSTERS == sorted(IMPLEMENTED_CLUSTERS)


def test_cluster_key_matches_the_module_name() -> None:
    for module in cluster_modules():
        assert module.__name__.endswith(f".{module.CLUSTER_KEY}")


def test_harmonized_column_names_are_snake_case() -> None:
    for module in cluster_modules():
        for column in module.HARMONIZED_COLS:
            assert re.fullmatch(r"[a-z][a-z0-9_]*", column), column


def test_consumption_declares_the_four_buckets() -> None:
    for module in cluster_modules():
        for bucket in ("sources", "superseded", "review", "conditional_on"):
            assert bucket in module.CONSUMPTION, f"{module.CLUSTER_KEY}/{bucket}"


def test_no_study_is_declared_twice_for_the_same_column() -> None:
    """A duplicated (study, column) pair means one of them is dead code."""
    for module in cluster_modules():
        pairs = list(source_pairs(module.CONSUMPTION))
        assert len(pairs) == len(set(pairs)), module.CLUSTER_KEY


# --- column-name confusion ---------------------------------------------------


def test_sentinel_bands_exclude_the_byte_range() -> None:
    """Stata's byte band is 101-127, where blood pressures and weights live."""
    assert all(threshold > 127 for threshold in checks.STATA_SENTINELS.values())


def test_millisecond_and_second_epochs_exceed_the_magnitude_floor() -> None:
    """A date read as a number must trip the guard, in seconds or milliseconds."""
    seconds, milliseconds = 1.554e9, 1.554e12
    assert seconds > checks.IMPLAUSIBLE_MAGNITUDE
    assert milliseconds > checks.IMPLAUSIBLE_MAGNITUDE


def test_millisecond_timestamp_is_reported(captured_logs) -> None:
    checks.check_magnitude(pd.Series([1.554e12]), "c", "s", "event_time_ms")
    assert "too large for a clinical measurement" in "".join(captured_logs)
