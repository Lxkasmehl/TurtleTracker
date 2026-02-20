"""
Integration tests: Review queue additional images (microhabitat/condition) and single packet GET.
Run against backend in Docker: BACKEND_URL and AUTH_URL must be set; fixture data includes test_req_001.
"""

import json
import os
import pytest
from io import BytesIO


def _make_dummy_image(path, size=100):
    """Write a minimal binary file that can be sent as image (e.g. JPEG)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\xff\xd8\xff" + b"\x00" * (size - 3))
    return path


# Request ID from fixture data (backend/tests/fixture-data/Review_Queue/test_req_001)
REVIEW_PACKET_REQUEST_ID = "test_req_001"


@pytest.fixture
def review_packet_dir(tmp_path):
    """Return request_id and packet_dir path hint for tests. Data lives in Docker-mounted fixture."""
    return REVIEW_PACKET_REQUEST_ID, None


def test_get_review_queue_empty(client):
    """GET /api/review-queue returns success; items is a list (empty or fixture packet only)."""
    r = client.get("/api/review-queue")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert isinstance(data["items"], list)
    # Fixture may have test_req_001 or be empty
    if len(data["items"]) == 1:
        assert data["items"][0].get("request_id") == REVIEW_PACKET_REQUEST_ID


def test_get_review_queue_with_packet(client, review_packet_dir):
    """GET /api/review-queue returns the packet with additional_images and structure."""
    request_id, _ = review_packet_dir
    r = client.get("/api/review-queue")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["items"]) >= 1
    item = next((i for i in data["items"] if i["request_id"] == request_id), None)
    assert item is not None
    assert "uploaded_image" in item
    assert item.get("additional_images") == []
    assert item.get("candidates") == []
    assert item.get("status") == "pending"


def test_get_review_packet_not_found(client):
    """GET /api/review-queue/<id> returns 404 for unknown request_id."""
    r = client.get("/api/review-queue/nonexistent_id_123")
    assert r.status_code == 404
    data = r.json()
    assert "error" in data or "Request not found" in str(data)


def test_get_review_packet_success(client, review_packet_dir):
    """GET /api/review-queue/<id> returns single packet with same shape as queue item."""
    request_id, _ = review_packet_dir
    r = client.get(f"/api/review-queue/{request_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    item = data["item"]
    assert item["request_id"] == request_id
    assert "uploaded_image" in item
    assert "additional_images" in item
    assert "candidates" in item
    assert "metadata" in item


def test_add_additional_images_no_files(client, review_packet_dir):
    """POST additional-images with no valid files returns 400."""
    request_id, _ = review_packet_dir
    r = client.post(
        f"/api/review-queue/{request_id}/additional-images",
        data={},
    )
    assert r.status_code == 400
    data = r.json()
    assert "error" in data


def test_add_additional_images_success(client, review_packet_dir, tmp_path):
    """POST additional-images with file_0 and type_0 adds image to packet."""
    request_id, _ = review_packet_dir
    img_path = str(tmp_path / "micro.jpg")
    _make_dummy_image(img_path)
    with open(img_path, "rb") as f:
        file_data = f.read()
    r = client.post(
        f"/api/review-queue/{request_id}/additional-images",
        data={
            "file_0": ("micro.jpg", BytesIO(file_data)),
            "type_0": "microhabitat",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "Added" in data.get("message", "")

    r2 = client.get(f"/api/review-queue/{request_id}")
    assert r2.status_code == 200
    item = r2.json()["item"]
    assert len(item["additional_images"]) >= 1
    added = item["additional_images"][0]
    assert added.get("type") == "microhabitat"
    assert "filename" in added


def test_remove_additional_image_no_filename(client, review_packet_dir):
    """DELETE additional-images with no filename in body returns 400."""
    request_id, _ = review_packet_dir
    r = client.delete(
        f"/api/review-queue/{request_id}/additional-images",
        json={},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_remove_additional_image_success(client, review_packet_dir, tmp_path):
    """Add one image then DELETE by filename; packet then has no additional images."""
    request_id, _ = review_packet_dir
    img_path = str(tmp_path / "cond.jpg")
    _make_dummy_image(img_path)
    with open(img_path, "rb") as f:
        data = f.read()
    r = client.post(
        f"/api/review-queue/{request_id}/additional-images",
        data={
            "file_0": (BytesIO(data), "cond.jpg"),
            "type_0": "condition",
        },
    )
    assert r.status_code == 200
    r2 = client.get(f"/api/review-queue/{request_id}")
    item = r2.json()["item"]
    assert len(item["additional_images"]) >= 1
    filename = item["additional_images"][0]["filename"]

    r3 = client.delete(
        f"/api/review-queue/{request_id}/additional-images",
        json={"filename": filename},
        content_type="application/json",
    )
    assert r3.status_code == 200
    r4 = client.get(f"/api/review-queue/{request_id}")
    remaining = r4.json()["item"]["additional_images"]
    assert not any(a.get("filename") == filename for a in remaining)
