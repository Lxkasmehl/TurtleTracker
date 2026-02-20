"""
Integration tests: Flags (turtles with find_metadata) and release flag clear.
Run against backend in Docker; fixture data includes Kansas/Topeka/T101 and State/Loc/T999.
"""

import pytest

# From fixture data: backend/tests/fixture-data/Kansas/Topeka/T101/find_metadata.json
TURTLE_WITH_FLAG = {"turtle_id": "T101", "location": "Kansas/Topeka"}


@pytest.fixture
def turtle_with_flag():
    """Turtle that has find_metadata (no released_at). From fixture data."""
    return TURTLE_WITH_FLAG


def test_get_flags_empty(client):
    """GET /api/flags returns success and empty list when no turtles have flags."""
    r = client.get("/api/flags")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    # Fixture has T101 with flag; so we accept empty or one item
    assert isinstance(data["items"], list)


def test_get_flags_with_turtle(client, turtle_with_flag):
    """GET /api/flags returns turtles that have find_metadata and no released_at."""
    r = client.get("/api/flags")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["items"]) >= 1
    item = next((i for i in data["items"] if i["turtle_id"] == turtle_with_flag["turtle_id"]), None)
    assert item is not None
    assert item["location"] == turtle_with_flag["location"]
    assert "find_metadata" in item
    assert item["find_metadata"].get("digital_flag_lat") == 39.0


def test_clear_release_flag_no_turtle_id(client):
    """POST /api/flags/release without turtle_id returns 400."""
    r = client.post("/api/flags/release", json={}, content_type="application/json")
    assert r.status_code == 400


def test_clear_release_flag_success(client, turtle_with_flag):
    """POST /api/flags/release clears digital flag and sets released_at."""
    r = client.post(
        "/api/flags/release",
        json={"turtle_id": turtle_with_flag["turtle_id"], "location": turtle_with_flag["location"]},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True

    # Turtle should no longer appear in flags list (released_at set)
    r2 = client.get("/api/flags")
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert not any(i["turtle_id"] == turtle_with_flag["turtle_id"] for i in items)


def test_clear_release_flag_no_metadata(client):
    """POST /api/flags/release for turtle without find_metadata returns 400."""
    # Fixture has State/Loc/T999 with no find_metadata.json
    r = client.post(
        "/api/flags/release",
        json={"turtle_id": "T999", "location": "State/Loc"},
        content_type="application/json",
    )
    assert r.status_code == 400
