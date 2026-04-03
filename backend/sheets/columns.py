"""
Column mappings for Google Sheets
"""

from typing import Any, Dict, List, Sequence, Tuple

# Canonical header order (matches the research spreadsheet layout). Used when creating
# new tabs and when inserting columns missing from older sheets.
CANONICAL_COLUMN_ORDER: Tuple[str, ...] = (
    'Primary ID',
    'Transmitter ID',
    'Freq',
    'ID',
    'ID2 (random sequence)',
    'Pit?',
    'Plastron Picture in Archive?',
    'Carapace Picture in Archive?',
    'Adopted?',
    'iButton?',
    'DNA Extracted?',
    'Date 1st found',
    'Species',
    'Name',
    'Sex',
    'iButton Last set',
    'Last Assay Date',
    'Dates refound',
    'Specific Location',
    'General Location',
    'Location',
    'Health Status',
    'Notes',
    'Transmitter put on by',
    'Transmitter On Date',
    'Transmitter Type',
    'Transmitter lifespan',
    'Radio Replace Date',
    'OLD Frequencies',
    'Mass (g)',
    'Flesh Flies?',
    'Curved carapace length (mm)',
    'Straight carapace length (mm)',
    'Carapace width (mm)',
    'Curved plastron length (mm)',
    'Straight plastron length (mm)',
    'Plastron width (mm)',
    'Dome height (mm)',
)

# Keys on turtle payloads that are not sheet columns
TURTLE_METADATA_KEYS = frozenset({'sheet_name', 'row_index'})

# Column mapping: Google Sheets column headers to internal field names.
# Put canonical headers first; legacy aliases below map old headers for reads.
COLUMN_MAPPING: Dict[str, str] = {
    'Primary ID': 'primary_id',
    'Transmitter ID': 'transmitter_id',
    'Freq': 'freq',
    'ID': 'id',
    'ID2 (random sequence)': 'id2',
    'Pit?': 'pit',
    'Plastron Picture in Archive?': 'plastron_picture_in_archive',
    'Carapace Picture in Archive?': 'carapace_picture_in_archive',
    'Adopted?': 'adopted',
    'iButton?': 'ibutton',
    'DNA Extracted?': 'dna_extracted',
    'Date 1st found': 'date_1st_found',
    'Species': 'species',
    'Name': 'name',
    'Sex': 'sex',
    'iButton Last set': 'ibutton_last_set',
    'Last Assay Date': 'last_assay_date',
    'Dates refound': 'dates_refound',
    'Specific Location': 'specific_location',
    'General Location': 'general_location',
    'Location': 'location',
    'Health Status': 'health_status',
    'Notes': 'notes',
    'Transmitter put on by': 'transmitter_put_on_by',
    'Transmitter On Date': 'transmitter_on_date',
    'Transmitter Type': 'transmitter_type',
    'Transmitter lifespan': 'transmitter_lifespan',
    'Radio Replace Date': 'radio_replace_date',
    'OLD Frequencies': 'old_frequencies',
    'Mass (g)': 'mass_g',
    'Flesh Flies?': 'flesh_flies',
    'Curved carapace length (mm)': 'curved_carapace_length_mm',
    'Straight carapace length (mm)': 'straight_carapace_length_mm',
    'Carapace width (mm)': 'carapace_width_mm',
    'Curved plastron length (mm)': 'curved_plastron_length_mm',
    'Straight plastron length (mm)': 'straight_plastron_length_mm',
    'Plastron width (mm)': 'plastron_width_mm',
    'Dome height (mm)': 'dome_height_mm',
    # Legacy headers (older spreadsheets)
    'Pic in 2024 Archive?': 'pic_in_2024_archive',
    'Transmitter type': 'transmitter_type',
}


def _build_field_to_column(column_mapping: Dict[str, str]) -> Dict[str, str]:
    """One preferred sheet header per internal field (first canonical header wins)."""
    out: Dict[str, str] = {}
    for header, field in column_mapping.items():
        if field not in out:
            out[field] = header
    # Explicit write targets when multiple headers share a field or we rename columns
    out['transmitter_type'] = 'Transmitter Type'
    out['plastron_picture_in_archive'] = 'Plastron Picture in Archive?'
    out['carapace_picture_in_archive'] = 'Carapace Picture in Archive?'
    out['pic_in_2024_archive'] = 'Plastron Picture in Archive?'
    return out


# Reverse mapping: internal field names to Google Sheets column headers (for inserts / writes)
FIELD_TO_COLUMN: Dict[str, str] = _build_field_to_column(COLUMN_MAPPING)

_CANONICAL_INDEX = {h: i for i, h in enumerate(CANONICAL_COLUMN_ORDER)}


def compute_insert_index_for_missing_column(
    headers_ordered: Sequence[str],
    missing_header: str,
    canonical_order: Sequence[str] = CANONICAL_COLUMN_ORDER,
) -> int:
    """
    0-based index where a new column with ``missing_header`` should be inserted
    so it stays consistent with canonical_order relative to existing headers.
    """
    normalized = [((h or '').strip()) for h in headers_ordered]
    header_set = set(normalized)
    try:
        pos = canonical_order.index(missing_header)
    except ValueError:
        return len(normalized)

    anchor_before_idx = -1
    for j in range(pos - 1, -1, -1):
        h = canonical_order[j]
        if h in header_set:
            anchor_before_idx = normalized.index(h)
            break

    anchor_after_idx = None
    for j in range(pos + 1, len(canonical_order)):
        h = canonical_order[j]
        if h in header_set:
            anchor_after_idx = normalized.index(h)
            break

    if anchor_before_idx >= 0:
        return anchor_before_idx + 1
    if anchor_after_idx is not None:
        return anchor_after_idx
    return len(normalized)


def collect_missing_headers_for_turtle_data(
    turtle_data: Dict[str, Any],
    existing_headers: Dict[str, int],
    field_to_column: Dict[str, str] = FIELD_TO_COLUMN,
    metadata_keys: frozenset = TURTLE_METADATA_KEYS,
) -> List[str]:
    """
    Sheet headers that are required to persist non-empty turtle_data fields but are
    absent from existing_headers (exact header text).
    """
    present = set(existing_headers.keys())
    targets: List[str] = []
    seen = set()

    def _has_value(v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, str):
            return bool(v.strip())
        return True

    for key, value in turtle_data.items():
        if key in metadata_keys:
            continue
        if key not in field_to_column:
            continue
        if not _has_value(value):
            continue
        header = field_to_column[key]
        if header in present or header in seen:
            continue
        targets.append(header)
        seen.add(header)

    targets.sort(key=lambda h: _CANONICAL_INDEX.get(h, 10_000))
    return targets
