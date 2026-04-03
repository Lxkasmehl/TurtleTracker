"""
Normalize sheet cell values for API consistency (Yes/No, biology ID display).
"""

from __future__ import annotations

from typing import Any, Dict

# Internal field names that use Yes/No in the UI and should accept Y/N from Sheets
YES_NO_INTERNAL_FIELDS = frozenset(
    {
        'pit',
        'adopted',
        'ibutton',
        'dna_extracted',
        'plastron_picture_in_archive',
        'carapace_picture_in_archive',
        'pic_in_2024_archive',
        'flesh_flies',
    }
)


def normalize_yes_no_from_sheet(value: Any) -> str:
    if value is None:
        return ''
    v = str(value).strip()
    if not v:
        return ''
    vl = v.lower()
    if vl in ('y', 'yes', '1', 'true'):
        return 'Yes'
    if vl in ('n', 'no', '0', 'false'):
        return 'No'
    return v


def normalize_yes_no_to_sheet(value: Any) -> str:
    """Write canonical Yes/No when the value is an obvious boolean-ish token."""
    if value is None:
        return ''
    v = str(value).strip()
    if not v:
        return ''
    vl = v.lower()
    if vl in ('y', 'yes', '1', 'true'):
        return 'Yes'
    if vl in ('n', 'no', '0', 'false'):
        return 'No'
    return v


def normalize_turtle_row_after_read(data: Dict[str, Any]) -> None:
    """Mutate turtle payload from Sheets: canonical biology ID and Yes/No answers."""
    from sheets import migration

    if data.get('id'):
        data['id'] = migration.normalize_biology_id_display(str(data['id']))
    for key in YES_NO_INTERNAL_FIELDS:
        if key in data and data[key]:
            data[key] = normalize_yes_no_from_sheet(data[key])


def format_field_value_for_sheet(field_name: str, value: Any) -> str:
    """String to store in a sheet cell for a mapped field."""
    from sheets import migration

    if value is None:
        return ''
    s = str(value).strip()
    if not s:
        return ''
    if field_name == 'id':
        return migration.normalize_biology_id_display(s)
    if field_name in YES_NO_INTERNAL_FIELDS:
        return normalize_yes_no_to_sheet(s)
    return str(value)
