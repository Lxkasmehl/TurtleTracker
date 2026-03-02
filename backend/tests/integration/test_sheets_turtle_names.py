"""
Integration tests: GET /api/sheets/turtle-names (list all turtle names across sheets).
Used by the frontend to prevent duplicate turtle names when creating/editing.
Run against backend in Docker; requires admin auth.
"""

import pytest


def test_get_turtle_names_requires_auth(backend_url, integration_env):
    """GET /api/sheets/turtle-names without Authorization returns 401."""
    if not integration_env:
        pytest.skip("Set BACKEND_URL and AUTH_URL to run integration tests")
    import requests

    r = requests.get(f"{backend_url}/api/sheets/turtle-names", timeout=10)
    assert r.status_code == 401
    data = r.json() if r.content else {}
    assert "error" in data


def test_get_turtle_names_success(client):
    """GET /api/sheets/turtle-names with admin auth returns 200 and { success, names }."""
    r = client.get("/api/sheets/turtle-names")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    assert data.get("success") is True
    assert "names" in data
    assert isinstance(data["names"], list)
    # When Sheets is configured, names may be populated; when not, backend returns names: []
    for entry in data["names"]:
        assert "name" in entry
        assert "primary_id" in entry


def test_get_turtle_names_structure(client):
    """Each entry in names has name and primary_id (string) for duplicate check across sheets."""
    r = client.get("/api/sheets/turtle-names")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    names = data.get("names", [])
    for entry in names:
        assert isinstance(entry.get("name"), str)
        assert isinstance(entry.get("primary_id"), str)
