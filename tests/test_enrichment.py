"""Tests for the study-level enrichment step."""

from collaborative_care_analysis.dataset import DATA_LOADING_DIR, _get_study_id
from collaborative_care_analysis.enrichment import (
    COLNAME_EXTRA_INFO_STUDYID,
    load_study_level_extra_infos,
)


def _loader_study_ids() -> set[str]:
    """STUDY_ID of every data-loading script (e.g. '16_Katon_1999')."""
    return {
        _get_study_id(path)
        for path in DATA_LOADING_DIR.rglob("*.py")
        if path.name != "__init__.py"
    }


def test_study_ids_match_between_extra_infos_and_datasets() -> None:
    """The extra-info sheet's study ids line up exactly with the datasets.

    ``enrich`` does an exact join, so any mismatch here has to be fixed by
    correcting the identifier at the source (the sheet or the loader), not
    with fuzzy matching.
    """
    extra_ids = set(load_study_level_extra_infos()[COLNAME_EXTRA_INFO_STUDYID])
    loader_ids = _loader_study_ids()

    missing_from_sheet = loader_ids - extra_ids
    unexpected_in_sheet = extra_ids - loader_ids

    assert not missing_from_sheet and not unexpected_in_sheet, (
        f"study id mismatch between the extra-info sheet and the datasets:\n"
        f"  missing from sheet: {sorted(missing_from_sheet)}\n"
        f"  unexpected in sheet: {sorted(unexpected_in_sheet)}"
    )
