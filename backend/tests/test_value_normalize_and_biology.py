"""Biology ID canonical form and Yes/No normalization."""

import pytest

from sheets import migration
from sheets.value_normalize import (
    format_field_value_for_sheet,
    normalize_turtle_row_after_read,
    normalize_yes_no_from_sheet,
    normalize_yes_no_to_sheet,
)


@pytest.mark.parametrize(
    'raw,expected',
    [
        ('F1', 'F001'),
        ('f001', 'F001'),
        ('F026', 'F026'),
        ('M12', 'M012'),
        ('Null.1', 'U001'),
        ('null 5', 'U005'),
        ('F.26', 'F026'),
        ('J.3', 'J003'),
    ],
)
def test_normalize_biology_id_display(raw, expected):
    assert migration.normalize_biology_id_display(raw) == expected


def test_normalize_biology_id_unknown_passthrough():
    assert migration.normalize_biology_id_display('Turtle42') == 'Turtle42'


def test_yes_no_round_trip():
    assert normalize_yes_no_from_sheet('Y') == 'Yes'
    assert normalize_yes_no_from_sheet('n') == 'No'
    assert normalize_yes_no_to_sheet('Y') == 'Yes'
    assert normalize_yes_no_to_sheet('No') == 'No'
    assert normalize_yes_no_from_sheet('Maybe') == 'Maybe'


def test_format_field_value_for_sheet_id_and_pit():
    assert format_field_value_for_sheet('id', 'f2') == 'F002'
    assert format_field_value_for_sheet('pit', 'y') == 'Yes'


def test_normalize_turtle_row_after_read_mutates():
    row = {'id': 'm5', 'pit': 'N', 'species': 'X'}
    normalize_turtle_row_after_read(row)
    assert row['id'] == 'M005'
    assert row['pit'] == 'No'
    assert row['species'] == 'X'
