"""
Integration tests: Review queue additional images (microhabitat/condition) and single packet GET.
"""

import json
import os
import pytest


def _make_dummy_image(path, size=100):
    """Write a minimal binary file that can be sent as image (e.g. JPEG)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\xff\xd8\xff" + b"\x00" * (size - 3))  # minimal JPEG-like
    return path


@pytest.fixture
def review_packet_dir(fake_manager, tmp_path):
    """Create one review packet with additional_images dir and manifest."""
    request_id = "test_req_001"
    packet_dir = os.path.join(fake_manager.review_queue_dir, request_id)
    os.makedirs(packet_dir, exist_ok=True)
    # Main image (so _format_packet_item finds something)
    _make_dummy_image(os.path.join(packet_dir, "query.jpg"))
    additional_dir = os.path.join(packet_dir, "additional_images")
    os.makedirs(additional_dir, exist_ok=True)
    with open(os.path.join(additional_dir, "manifest.json"), "w") as f:
        json.dump([], f)
    return request_id, packet_dir


def test_get_review_queue_empty(client):
    """GET /api/review-queue returns success and empty list when queue is empty."""
    r = client.get("/api/review-queue")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["items"] == []


def test_get_review_queue_with_packet(client, fake_manager, review_packet_dir):
    """GET /api/review-queue returns the packet with additional_images and structure."""
    request_id, _ = review_packet_dir
    r = client.get("/api/review-queue")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["request_id"] == request_id
    assert "uploaded_image" in item
    assert item.get("additional_images") == []
    assert item.get("candidates") == []
    assert item.get("status") == "pending"


def test_get_review_packet_not_found(client):
    """GET /api/review-queue/<id> returns 404 for unknown request_id."""
    r = client.get("/api/review-queue/nonexistent_id_123")
    assert r.status_code == 404
    data = r.get_json()
    assert "error" in data or "Request not found" in str(data)


def test_get_review_packet_success(client, review_packet_dir):
    """GET /api/review-queue/<id> returns single packet with same shape as queue item."""
    request_id, _ = review_packet_dir
    r = client.get(f"/api/review-queue/{request_id}")
    assert r.status_code == 200
    data = r.get_json()
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
    data = r.get_json()
    assert "error" in data


def test_add_additional_images_success(client, review_packet_dir, tmp_path):
    """POST additional-images with file_0 and type_0 adds image to packet."""
    from io import BytesIO
    request_id, packet_dir = review_packet_dir
    img_path = str(tmp_path / "micro.jpg")
    _make_dummy_image(img_path)
    with open(img_path, "rb") as f:
        file_data = f.read()
    r = client.post(
        f"/api/review-queue/{request_id}/additional-images",
        data={
            "file_0": (BytesIO(file_data), "micro.jpg"),
            "type_0": "microhabitat",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert "Added" in data.get("message", "")

    # GET packet and check additional_images
    r2 = client.get(f"/api/review-queue/{request_id}")
    assert r2.status_code == 200
    item = r2.get_json()["item"]
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
    from io import BytesIO
    request_id, packet_dir = review_packet_dir
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
    item = r2.get_json()["item"]
    assert len(item["additional_images"]) >= 1
    filename = item["additional_images"][0]["filename"]

    r3 = client.delete(
        f"/api/review-queue/{request_id}/additional-images",
        json={"filename": filename},
        content_type="application/json",
    )
    assert r3.status_code == 200
    r4 = client.get(f"/api/review-queue/{request_id}")
    assert len(r4.get_json()["item"]["additional_images"]) == 0
