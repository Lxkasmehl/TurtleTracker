"""Regression: new-turtle disk paths must use sheet tab name, not General Location alone."""

from routes.review import normalize_new_turtle_location_for_disk


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
