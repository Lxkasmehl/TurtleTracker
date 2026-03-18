import pytest

import general_locations_catalog as glc


@pytest.fixture()
def isolated_catalog(tmp_path, monkeypatch):
    catalog_file = tmp_path / 'general_locations.json'
    monkeypatch.setattr(glc, '_CATALOG_FILE', str(catalog_file))
    return catalog_file


def test_default_catalog_includes_seed_values(isolated_catalog):
    catalog = glc.get_general_location_catalog()

    assert catalog['states']['Kansas'] == [
        'Karlyle Woods',
        'Lawrence',
        'North Topeka',
        'Valencia',
    ]
    assert catalog['sheet_defaults']['Nebraska CPBS']['general_location'] == 'CPBS'
    assert isolated_catalog.exists()


def test_add_general_location_is_case_insensitive(isolated_catalog):
    glc.add_general_location('Kansas', 'Wichita')
    glc.add_general_location('kansas', 'wichita')

    catalog = glc.get_general_location_catalog()
    assert 'Wichita' in catalog['states']['Kansas']
    assert catalog['states']['Kansas'].count('Wichita') == 1


def test_resolve_general_location_from_sheet_and_value(isolated_catalog):
    glc.add_general_location('Kansas', 'Wichita')

    assert glc.get_general_location_options_for_sheet('Nebraska CPBS')['locations'] == ['CPBS']
    assert glc.get_general_location_options_for_sheet('Kansas')['locations'] == [
        'Karlyle Woods',
        'Lawrence',
        'North Topeka',
        'Valencia',
        'Wichita',
    ]
    assert glc.resolve_general_location_from_sheet_and_value('Nebraska CPBS', 'Anything') == 'CPBS'
    assert glc.resolve_general_location_from_sheet_and_value('Kansas', 'wichita') == 'Wichita'

    with pytest.raises(ValueError):
        glc.resolve_general_location_from_sheet_and_value('Kansas', 'Not A Real Location')
