"""
Integration tests: GET /api/turtles/images and DELETE /api/turtles/images/additional.
Run against backend in Docker; fixture data includes Kansas/Topeka/T42 with ref_data, additional, loose.
"""

import pytest

# From fixture data: backend/tests/fixture-data/Kansas/Topeka/T42
TURTLE_WITH_IMAGES = {
    "turtle_id": "T42",
    "location": "Kansas/Topeka",
    "additional_filename": "microhabitat_123_extra.jpg",
}


@pytest.fixture
def turtle_with_images():
    """Turtle folder with ref_data, additional_images, loose_images. From fixture data."""
    return TURTLE_WITH_IMAGES


def test_get_turtle_images_no_turtle_id(client):
    """GET /api/turtles/images without turtle_id returns 400."""
    r = client.get("/api/turtles/images")
    assert r.status_code == 400


def test_get_turtle_images_not_found(client):
    """GET /api/turtles/images for unknown turtle_id returns 200 with empty primary/additional/loose."""
    r = client.get("/api/turtles/images?turtle_id=NonExistent99")
    assert r.status_code == 200
    data = r.json()
    assert data["primary"] is None
    assert data["additional"] == []
    assert data["loose"] == []


def test_get_turtle_images_success(client, turtle_with_images):
    """GET /api/turtles/images returns primary, additional, loose for existing turtle."""
    tid = turtle_with_images["turtle_id"]
    loc = turtle_with_images["location"]
    r = client.get(f"/api/turtles/images?turtle_id={tid}&sheet_name={loc}")
    assert r.status_code == 200
    data = r.json()
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
    r = client.delete(
        f"/api/turtles/images/additional?turtle_id={turtle_with_images['turtle_id']}"
    )
    assert r.status_code == 400


def test_delete_turtle_additional_success(client, turtle_with_images):
    """DELETE /api/turtles/images/additional removes the image and updates manifest."""
    tid = turtle_with_images["turtle_id"]
    fn = turtle_with_images["additional_filename"]
    loc = turtle_with_images["location"]
    r = client.delete(
        f"/api/turtles/images/additional?turtle_id={tid}&filename={fn}&sheet_name={loc}"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    r2 = client.get(f"/api/turtles/images?turtle_id={tid}&sheet_name={loc}")
    assert r2.status_code == 200
    assert len(r2.json()["additional"]) == 0
