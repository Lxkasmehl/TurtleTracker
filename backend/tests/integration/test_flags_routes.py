"""
Integration tests: Flags (turtles with find_metadata) and release flag clear.
"""

import json
import os
import pytest


@pytest.fixture
def turtle_with_flag(fake_manager, tmp_path):
    """Create a turtle folder with find_metadata.json (no released_at)."""
    # Structure: base_dir / State / Location / turtle_id / find_metadata.json
    state, loc, turtle_id = "Kansas", "Topeka", "T101"
    turtle_dir = os.path.join(fake_manager.base_dir, state, loc, turtle_id)
    os.makedirs(turtle_dir, exist_ok=True)
    meta = {
        "collected_to_lab": "yes",
        "physical_flag": "yes",
        "digital_flag_lat": 39.0,
        "digital_flag_lon": -95.7,
        "digital_flag_source": "gps",
    }
    with open(os.path.join(turtle_dir, "find_metadata.json"), "w") as f:
        json.dump(meta, f)
    return {"turtle_id": turtle_id, "location": f"{state}/{loc}", "path": turtle_dir}


def test_get_flags_empty(client):
    """GET /api/flags returns success and empty list when no turtles have flags."""
    r = client.get("/api/flags")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["items"] == []


def test_get_flags_with_turtle(client, turtle_with_flag):
    """GET /api/flags returns turtles that have find_metadata and no released_at."""
    r = client.get("/api/flags")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["turtle_id"] == turtle_with_flag["turtle_id"]
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
    data = r.get_json()
    assert data["success"] is True

    # Turtle should no longer appear in flags list (released_at set)
    r2 = client.get("/api/flags")
    assert r2.status_code == 200
    assert len(r2.get_json()["items"]) == 0


def test_clear_release_flag_no_metadata(client, fake_manager):
    """POST /api/flags/release for turtle without find_metadata returns 400."""
    turtle_dir = os.path.join(fake_manager.base_dir, "State", "Loc", "T999")
    os.makedirs(turtle_dir, exist_ok=True)
    # No find_metadata.json
    r = client.post(
        "/api/flags/release",
        json={"turtle_id": "T999", "location": "State/Loc"},
        content_type="application/json",
    )
    assert r.status_code == 400
