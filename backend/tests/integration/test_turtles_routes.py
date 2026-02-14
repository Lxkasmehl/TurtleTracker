"""
Integration tests: GET /api/turtles/images and DELETE /api/turtles/images/additional.
"""

import json
import os
import pytest


def _make_dummy_image(path, size=100):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\xff\xd8\xff" + b"\x00" * (size - 3))
    return path


@pytest.fixture
def turtle_with_images(fake_manager, tmp_path):
    """Create a turtle folder with ref_data, additional_images (manifest), loose_images."""
    turtle_id = "T42"
    location = "Kansas/Topeka"
    turtle_dir = os.path.join(fake_manager.base_dir, "Kansas", "Topeka", turtle_id)
    os.makedirs(turtle_dir, exist_ok=True)
    ref_dir = os.path.join(turtle_dir, "ref_data")
    os.makedirs(ref_dir, exist_ok=True)
    _make_dummy_image(os.path.join(ref_dir, "ref.jpg"))
    additional_dir = os.path.join(turtle_dir, "additional_images")
    os.makedirs(additional_dir, exist_ok=True)
    extra_name = "microhabitat_123_extra.jpg"
    _make_dummy_image(os.path.join(additional_dir, extra_name))
    with open(os.path.join(additional_dir, "manifest.json"), "w") as f:
        json.dump([
            {"filename": extra_name, "type": "microhabitat", "timestamp": "2025-01-01T12:00:00Z"},
        ], f)
    loose_dir = os.path.join(turtle_dir, "loose_images")
    os.makedirs(loose_dir, exist_ok=True)
    _make_dummy_image(os.path.join(loose_dir, "obs1.jpg"))
    return {"turtle_id": turtle_id, "location": location, "path": turtle_dir, "additional_filename": extra_name}


def test_get_turtle_images_no_turtle_id(client):
    """GET /api/turtles/images without turtle_id returns 400."""
    r = client.get("/api/turtles/images")
    assert r.status_code == 400


def test_get_turtle_images_not_found(client):
    """GET /api/turtles/images for unknown turtle_id returns 200 with empty primary/additional/loose."""
    r = client.get("/api/turtles/images?turtle_id=NonExistent99")
    assert r.status_code == 200
    data = r.get_json()
    assert data["primary"] is None
    assert data["additional"] == []
    assert data["loose"] == []


def test_get_turtle_images_success(client, turtle_with_images):
    """GET /api/turtles/images returns primary, additional, loose for existing turtle."""
    r = client.get(f"/api/turtles/images?turtle_id={turtle_with_images['turtle_id']}&sheet_name=Kansas/Topeka")
    assert r.status_code == 200
    data = r.get_json()
    assert data["primary"] is not None
    assert "ref_data" in data["primary"] and "ref.jpg" in data["primary"]
    assert len(data["additional"]) == 1
    assert data["additional"][0]["type"] == "microhabitat"
    assert len(data["loose"]) == 1


def test_delete_turtle_additional_no_turtle_id(client):
    """DELETE /api/turtles/images/additional without turtle_id returns 400."""
    r = client.delete("/api/turtles/images/additional?filename=any.jpg")
    assert r.status_code == 400


def test_delete_turtle_additional_no_filename(client, turtle_with_images):
    """DELETE /api/turtles/images/additional without filename returns 400."""
    r = client.delete(f"/api/turtles/images/additional?turtle_id={turtle_with_images['turtle_id']}")
    assert r.status_code == 400


def test_delete_turtle_additional_success(client, turtle_with_images):
    """DELETE /api/turtles/images/additional removes the image and updates manifest."""
    tid = turtle_with_images["turtle_id"]
    fn = turtle_with_images["additional_filename"]
    r = client.delete(f"/api/turtles/images/additional?turtle_id={tid}&filename={fn}&sheet_name=Kansas/Topeka")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    # GET images again: additional should be empty
    r2 = client.get(f"/api/turtles/images?turtle_id={tid}&sheet_name=Kansas/Topeka")
    assert r2.status_code == 200
    assert len(r2.get_json()["additional"]) == 0
