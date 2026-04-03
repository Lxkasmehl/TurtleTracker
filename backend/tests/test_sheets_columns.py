"""
Unit tests: sheets column mapping for optional mass and morphometrics.
Ensures COLUMN_MAPPING and FIELD_TO_COLUMN include the new fields so that
GET/POST/PUT turtle data can read/write them when the sheet has those columns.
"""

from sheets.columns import (
    CANONICAL_COLUMN_ORDER,
    COLUMN_MAPPING,
    FIELD_TO_COLUMN,
    collect_missing_headers_for_turtle_data,
    compute_insert_index_for_missing_column,
)

MORPHOMETRICS_HEADERS = {
    'Mass (g)': 'mass_g',
    'Curved carapace length (mm)': 'curved_carapace_length_mm',
    'Straight carapace length (mm)': 'straight_carapace_length_mm',
    'Carapace width (mm)': 'carapace_width_mm',
    'Curved plastron length (mm)': 'curved_plastron_length_mm',
    'Straight plastron length (mm)': 'straight_plastron_length_mm',
    'Plastron width (mm)': 'plastron_width_mm',
    'Dome height (mm)': 'dome_height_mm',
}


def test_column_mapping_includes_morphometrics():
    """COLUMN_MAPPING contains all optional mass and morphometrics headers."""
    for header, field_name in MORPHOMETRICS_HEADERS.items():
        assert header in COLUMN_MAPPING, f"Missing header {header!r}"
        assert COLUMN_MAPPING[header] == field_name


def test_field_to_column_includes_morphometrics():
    """FIELD_TO_COLUMN (reverse mapping) contains all morphometrics field names."""
    for header, field_name in MORPHOMETRICS_HEADERS.items():
        assert field_name in FIELD_TO_COLUMN, f"Missing field {field_name!r}"
        assert FIELD_TO_COLUMN[field_name] == header


def test_transmitter_type_write_header_prefers_canonical_casing():
    assert FIELD_TO_COLUMN['transmitter_type'] == 'Transmitter Type'


def test_compute_insert_index_inserts_specific_location_before_general():
    headers = [
        'Primary ID',
        'Transmitter ID',
        'ID',
        'Dates refound',
        'General Location',
        'Location',
    ]
    idx = compute_insert_index_for_missing_column(headers, 'Specific Location')
    assert headers[idx] == 'General Location'


def test_collect_missing_headers_skips_empty_values():
    existing = {'Primary ID': 0, 'Name': 1}
    td = {'primary_id': 'P1', 'name': '', 'species': 'Chrysemys'}
    miss = collect_missing_headers_for_turtle_data(td, existing)
    assert 'Species' in miss
    assert 'Name' not in miss


def test_canonical_order_covers_all_mapped_headers():
    """Every non-legacy COLUMN_MAPPING header appears in CANONICAL_COLUMN_ORDER."""
    legacy = {'Pic in 2024 Archive?', 'Transmitter type'}
    for header in COLUMN_MAPPING:
        if header in legacy:
            continue
        assert header in CANONICAL_COLUMN_ORDER, f"Missing from canonical order: {header!r}"
