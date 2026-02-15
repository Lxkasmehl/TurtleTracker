"""
Fake TurtleManager for integration tests.

Allows fast pytest integration tests without the real TurtleManager: no SIFT/FAISS,
no loading the search index, only file operations in a temporary directory. Tests
run in isolation and never touch real backend/data.

If you later run integration tests against a dockerized app (real TurtleManager in
a container, API over HTTP), you can replace or supplement these with container-based
tests. The fake is then optional but can still be used for fast runs without
starting any container (local/CI).
"""

import os
import json
import shutil
import time
import tempfile
import uuid


class FakeTurtleManager:
    """Minimal TurtleManager implementation for API integration tests."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or tempfile.mkdtemp(prefix="turtle_test_")
        self.review_queue_dir = os.path.join(self.base_dir, "Review_Queue")
        os.makedirs(self.review_queue_dir, exist_ok=True)

    def get_review_queue(self):
        items = []
        if os.path.exists(self.review_queue_dir):
            for req_id in os.listdir(self.review_queue_dir):
                req_path = os.path.join(self.review_queue_dir, req_id)
                if os.path.isdir(req_path):
                    items.append({"request_id": req_id, "path": req_path, "status": "pending"})
        return items

    def add_additional_images_to_packet(self, request_id, files_with_types):
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.isdir(packet_dir):
            return False, "Request not found"
        additional_dir = os.path.join(packet_dir, "additional_images")
        os.makedirs(additional_dir, exist_ok=True)
        manifest_path = os.path.join(additional_dir, "manifest.json")
        manifest = []
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        for item in files_with_types:
            src = item.get("path")
            typ = (item.get("type") or "other").lower()
            if typ not in ("microhabitat", "condition", "other"):
                typ = "other"
            ts = item.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if not src or not os.path.isfile(src):
                continue
            ext = os.path.splitext(src)[1] or ".jpg"
            safe_name = f"{typ}_{int(time.time())}_{os.path.basename(src)}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
            dest = os.path.join(additional_dir, safe_name)
            shutil.copy2(src, dest)
            manifest.append({"filename": safe_name, "type": typ, "timestamp": ts})
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
        return True, "OK"

    def remove_additional_image_from_packet(self, request_id, filename):
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.isdir(packet_dir):
            return False, "Request not found"
        additional_dir = os.path.join(packet_dir, "additional_images")
        manifest_path = os.path.join(additional_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            return False, "No additional images"
        if not filename or os.path.basename(filename) != filename:
            return False, "Invalid filename"
        file_path = os.path.join(additional_dir, filename)
        if not os.path.isfile(file_path):
            return False, "Image not found"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        new_manifest = [e for e in manifest if e.get("filename") != filename]
        if len(new_manifest) == len(manifest):
            return False, "Image not in manifest"
        try:
            os.remove(file_path)
        except OSError as e:
            return False, str(e)
        with open(manifest_path, "w") as f:
            json.dump(new_manifest, f)
        return True, None

    def _get_turtle_folder(self, turtle_id, location_hint=None):
        if location_hint and location_hint != "Unknown":
            possible = os.path.join(self.base_dir, location_hint, turtle_id)
            if os.path.exists(possible):
                return possible
        for root, _dirs, _files in os.walk(self.base_dir):
            if os.path.basename(root) == turtle_id:
                return root
        return None

    def remove_additional_image_from_turtle(self, turtle_id, filename, sheet_name=None):
        turtle_dir = self._get_turtle_folder(turtle_id, sheet_name)
        if not turtle_dir or not os.path.isdir(turtle_dir):
            return False, "Turtle folder not found"
        additional_dir = os.path.join(turtle_dir, "additional_images")
        if not os.path.isdir(additional_dir):
            return False, "No additional images folder"
        if not filename or os.path.basename(filename) != filename:
            return False, "Invalid filename"
        file_path = os.path.join(additional_dir, filename)
        if not os.path.isfile(file_path):
            return False, "Image not found"
        manifest_path = os.path.join(additional_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            try:
                os.remove(file_path)
                return True, None
            except OSError as e:
                return False, str(e)
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        new_manifest = [e for e in manifest if e.get("filename") != filename]
        if len(new_manifest) == len(manifest):
            return False, "Image not in manifest"
        try:
            os.remove(file_path)
        except OSError as e:
            return False, str(e)
        with open(manifest_path, "w") as f:
            json.dump(new_manifest, f)
        return True, None

    def reject_review_packet(self, request_id):
        """Remove a review packet (e.g. reject/spam). Used by E2E and integration tests."""
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.exists(packet_dir) or not os.path.isdir(packet_dir):
            return False, "Request not found"
        real_packet = os.path.realpath(packet_dir)
        real_base = os.path.realpath(self.review_queue_dir)
        if not real_packet.startswith(real_base):
            return False, "Invalid request path"
        try:
            shutil.rmtree(packet_dir)
            return True, "Deleted"
        except Exception as e:
            return False, str(e)

    def approve_review_packet(
        self,
        request_id,
        match_turtle_id=None,
        new_location=None,
        new_turtle_id=None,
        uploaded_image_path=None,
        find_metadata=None,
    ):
        """Stub: remove packet from queue. No real turtle creation for E2E/fake."""
        return self.reject_review_packet(request_id)

    def create_review_packet(self, query_image_path, user_info=None):
        """Create a minimal review packet dir and return request_id. For E2E/fake."""
        request_id = f"Req_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        candidates_dir = os.path.join(packet_dir, "candidate_matches")
        os.makedirs(packet_dir, exist_ok=True)
        os.makedirs(candidates_dir, exist_ok=True)
        if query_image_path and os.path.isfile(query_image_path):
            dest = os.path.join(packet_dir, os.path.basename(query_image_path))
            shutil.copy2(query_image_path, dest)
        if user_info:
            with open(os.path.join(packet_dir, "metadata.json"), "w") as f:
                json.dump(user_info, f)
        additional_dir = os.path.join(packet_dir, "additional_images")
        os.makedirs(additional_dir, exist_ok=True)
        with open(os.path.join(additional_dir, "manifest.json"), "w") as f:
            json.dump([], f)
        return request_id

    def search_for_matches(self, query_image_path, sheet_name=None):
        """Stub: no real search. Returns empty list for E2E/fake."""
        return []

    def get_turtles_with_flags(self):
        results = []
        skip = {"Review_Queue", "Community_Uploads", "Incidental_Finds"}
        if not os.path.exists(self.base_dir):
            return results
        for state in sorted(os.listdir(self.base_dir)):
            state_path = os.path.join(self.base_dir, state)
            if not os.path.isdir(state_path) or state.startswith(".") or state in skip:
                continue
            for name in sorted(os.listdir(state_path)):
                sub_path = os.path.join(state_path, name)
                if not os.path.isdir(sub_path) or name.startswith("."):
                    continue
                self._add_flag_if_present(results, sub_path, name, state)
                for turtle_id in sorted(os.listdir(sub_path)):
                    turtle_path = os.path.join(sub_path, turtle_id)
                    if not os.path.isdir(turtle_path) or turtle_id.startswith("."):
                        continue
                    self._add_flag_if_present(results, turtle_path, turtle_id, f"{state}/{name}")
        return results

    def _add_flag_if_present(self, results, turtle_path, turtle_id, location_label):
        meta_path = os.path.join(turtle_path, "find_metadata.json")
        if not os.path.isfile(meta_path):
            return
        try:
            with open(meta_path, "r") as f:
                find_metadata = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        if find_metadata.get("released_at"):
            return
        results.append({
            "turtle_id": turtle_id,
            "location": location_label,
            "path": turtle_path,
            "find_metadata": find_metadata,
        })

    def clear_release_flag(self, turtle_id, location_hint=None):
        turtle_dir = self._get_turtle_folder(turtle_id, location_hint)
        if not turtle_dir or not os.path.isdir(turtle_dir):
            return False, "Turtle folder not found"
        meta_path = os.path.join(turtle_dir, "find_metadata.json")
        if not os.path.isfile(meta_path):
            return False, "No find metadata"
        try:
            with open(meta_path, "r") as f:
                find_metadata = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return False, str(e)
        for key in ("digital_flag_lat", "digital_flag_lon", "digital_flag_source"):
            find_metadata.pop(key, None)
        find_metadata["released_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with open(meta_path, "w") as f:
                json.dump(find_metadata, f)
        except OSError as e:
            return False, str(e)
        return True, None
