"""Regression: new-turtle disk paths must use sheet tab name, not General Location alone."""

from routes.review import (
    canonical_new_turtle_folder_id,
    normalize_new_turtle_location_for_disk,
)


def test_nebraska_cpbs_wrong_cpbs_prefix_uses_sheet_tab():
    loc, gl = normalize_new_turtle_location_for_disk(
        "CPBS/NW of Geo 2",
        {"sheet_name": "NebraskaCPBS", "general_location": ""},
        is_community_upload=False,
    )
    assert loc == "NebraskaCPBS/CPBS"
    assert gl == "CPBS"


def test_nebraska_cpbs_client_sent_sheet_and_gl():
    loc, gl = normalize_new_turtle_location_for_disk(
        "NebraskaCPBS/CPBS",
        {"sheet_name": "NebraskaCPBS", "general_location": "CPBS"},
        is_community_upload=False,
    )
    assert loc == "NebraskaCPBS/CPBS"
    assert gl == "CPBS"


def test_kansas_path_tail_from_new_location_when_sheet_matches():
    loc, gl = normalize_new_turtle_location_for_disk(
        "Kansas/Lawrence",
        {"sheet_name": "Kansas", "general_location": ""},
        is_community_upload=False,
    )
    assert loc == "Kansas/Lawrence"
    assert gl == "Lawrence"


def test_community_single_segment_returns_none_second():
    loc, gl = normalize_new_turtle_location_for_disk(
        "Kansas",
        {"sheet_name": "Kansas", "general_location": "Lawrence"},
        is_community_upload=True,
    )
    assert loc == "Kansas"
    assert gl is None


# --- Canonical <bio_id>_<primary_id> folder naming for new turtles ---


def test_canonical_folder_id_combines_bio_and_primary():
    assert canonical_new_turtle_folder_id("F298", "T1771234567", "T1771234567") == "F298_T1771234567"


def test_canonical_folder_id_ignores_fallback_when_both_known():
    # the frontend-sent id is discarded once both real ids are resolved
    assert canonical_new_turtle_folder_id("F298", "T1771234567", "whatever") == "F298_T1771234567"


def test_canonical_folder_id_partial_combine_when_primary_missing():
    # primary couldn't be resolved (e.g. Sheets down) -> legacy partial combine
    assert canonical_new_turtle_folder_id("F298", "", "T1771234567") == "F298_T1771234567"


def test_canonical_folder_id_no_double_prefix():
    # fallback already carries the bio_id prefix -> don't prepend it twice
    assert canonical_new_turtle_folder_id("F298", "", "F298_T1771234567") == "F298_T1771234567"


def test_canonical_folder_id_bare_fallback_when_no_bio_id():
    assert canonical_new_turtle_folder_id("", "", "T1771234567") == "T1771234567"
