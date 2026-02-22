
# --- PATH HACK: Allow importing from the 'turtles' package ---
import os
import shutil
import time
import cv2 as cv
import json
import sys

# --- PATH SETUP ---
# This ensures we can find the 'turtles' package regardless of where we run this script
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- IMPORT THE BRAIN ---
try:
    # Try importing as a package (Standard Django way)
    from turtles import image_processing
except ImportError:
    # Fallback: Try local import if files are flat
    import image_processing
# --- CONFIGURATION ---
BASE_DATA_DIR = 'data'

LOCATION_NAME_MAP = {
    #"CBPS": "WT",
    #"North Topeka": "NT",
}


class TurtleManager:
    def __init__(self, base_data_dir='data'):
        # backend/data/
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), base_data_dir)
        self.review_queue_dir = os.path.join(self.base_dir, 'Review_Queue')

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.review_queue_dir, exist_ok=True)

        self._ensure_special_directories()

        print("🐢 TurtleManager: Loading Search Index & Vocabulary...")
        image_processing.load_or_generate_persistent_data(self.base_dir)
        print("✅ Resources Ready.")

    def _ensure_special_directories(self):
        """Creates the folder roots for Community and Incidental finds."""
        for special_folder in ["Community_Uploads", "Incidental_Finds"]:
            path = os.path.join(self.base_dir, special_folder)
            os.makedirs(path, exist_ok=True)

    def get_official_location_name(self, folder_name):
        """Translates acronyms (CBPS) to official names (Central Biological Preserve)."""
        return LOCATION_NAME_MAP.get(folder_name, folder_name)

    def get_all_locations(self):
        """
        Scans the data folder to build a list of locations for the GUI Dropdown.
        Returns: ["Nebraska/Topeka", "Kansas/Karlyle Woods", "Incidental_Finds", ...]
        """
        locations = ["Incidental_Finds", "Community_Uploads"]

        if os.path.exists(self.base_dir):
            # Loop through States
            for state in sorted(os.listdir(self.base_dir)):
                state_path = os.path.join(self.base_dir, state)
                if not os.path.isdir(state_path) or state.startswith('.'): continue
                if state in ["Review_Queue", "Community_Uploads", "Incidental_Finds"]: continue

                # Loop through Locations
                for loc in sorted(os.listdir(state_path)):
                    if os.path.isdir(os.path.join(state_path, loc)) and not loc.startswith('.'):
                        locations.append(f"{state}/{loc}")

        return locations

    def process_manual_upload(self, image_path, location_selection):
        """
        Handles the GUI Manual Upload.
        Parses 'State/Location' string and calls the processor.
        """
        # 1. Determine Destination Folder
        if "/" in location_selection:
            state, loc = location_selection.split("/", 1)
            location_dir = os.path.join(self.base_dir, state, loc)
        else:
            # Handle roots like "Incidental_Finds"
            location_dir = os.path.join(self.base_dir, location_selection)

        if not os.path.exists(location_dir):
            os.makedirs(location_dir, exist_ok=True)

        # 2. Extract ID (First 4 chars)
        filename = os.path.basename(image_path)
        turtle_id = filename[:4].strip().rstrip('_')

        # 3. Run the standard processor
        print(f"Manual Upload: Processing {turtle_id} into {location_dir}...")
        return self._process_single_turtle(image_path, location_dir, turtle_id)


    def get_review_queue(self):
        """
        RECOVERS STATE ON RESTART.
        Scans the 'Review_Queue' folder and returns the list of pending requests.
        """
        queue_items = []

        # If the server restarted, this loop finds all the folders we haven't finished yet
        if os.path.exists(self.review_queue_dir):
            for req_id in os.listdir(self.review_queue_dir):
                req_path = os.path.join(self.review_queue_dir, req_id)

                if os.path.isdir(req_path):
                    # Basic info to send to frontend
                    queue_items.append({
                        'request_id': req_id,
                        'path': req_path,
                        'status': 'pending'  # If it's in this folder, it is pending
                    })

        return queue_items



    def create_new_location(self, state_name, location_name):
        """
        Future Use: Allows Admin to generate a new research site folder from the GUI.
        """
        official_name = self.get_official_location_name(location_name)
        path = os.path.join(self.base_dir, state_name, official_name)

        if not os.path.exists(path):
            os.makedirs(path)
            print(f"✅ Created new location: {state_name}/{official_name}")
            return path
        else:
            print(f"⚠️ Location already exists: {state_name}/{official_name}")
            return path

    def ingest_flash_drive(self, drive_root_path):
        """
        Scans drive, extracts 'Letter+3Digit' ID, creates folders, and skips duplicates.
        """
        ingest_start_time = time.time()

        print(f"🐢 Starting Ingest from: {drive_root_path}")
        if not os.path.exists(drive_root_path):
            print("❌ Error: Drive path does not exist.")
            return

        count_new = 0
        count_skipped = 0

        for state_name in os.listdir(drive_root_path):

            if state_name == "System Volume Information" or state_name.startswith('.'):
                continue

            state_source_path = os.path.join(drive_root_path, state_name)
            if not os.path.isdir(state_source_path): continue

            state_dest_path = os.path.join(self.base_dir, state_name)
            os.makedirs(state_dest_path, exist_ok=True)

            for location_name in os.listdir(state_source_path):
                location_source_path = os.path.join(state_source_path, location_name)
                if not os.path.isdir(location_source_path) or location_name.startswith('.'): continue

                official_name = self.get_official_location_name(location_name)
                location_dest_path = os.path.join(state_dest_path, official_name)
                os.makedirs(location_dest_path, exist_ok=True)

                for filename in os.listdir(location_source_path):
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')): continue

                    # --- CHANGE 1: Extract only the first 4 chars (Letter + 3 Numbers) ---
                    # Example: "T101_date.jpg" -> "T101"
                    turtle_id = filename[:4].strip().rstrip('_')

                    source_path = os.path.join(location_source_path, filename)

                    # Call helper (which handles the duplicate skipping logic)
                    status = self._process_single_turtle(source_path, location_dest_path, turtle_id)

                    if status == "created":
                        count_new += 1
                    elif status == "skipped":
                        count_skipped += 1
        # --- TIMER END ---
        total_time = time.time() - ingest_start_time
        print(f"\n🎉 Ingest Complete. New: {count_new}, Skipped (Existing/Duplicates): {count_skipped}")
        print(f"⏱️ Total Ingest Time: {total_time:.2f}s")

    def _process_single_turtle(self, source_path, location_dir, turtle_id):
        """
        Checks if NPZ exists (Duplicate/Resume check).
        If new, renames image to 'TurtleID.jpg' and generates 'TurtleID.npz'.
        """
        # backend/data/State/Location/T101/
        turtle_dir = os.path.join(location_dir, turtle_id)
        ref_dir = os.path.join(turtle_dir, 'ref_data')
        loose_dir = os.path.join(turtle_dir, 'loose_images')

        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(loose_dir, exist_ok=True)

        # --- CHANGE 2: Rename files to match the ID exactly ---
        # Get original extension (e.g. .jpg)
        ext = os.path.splitext(source_path)[1]

        # Save as T101.jpg
        dest_image_path = os.path.join(ref_dir, f"{turtle_id}{ext}")
        # Save as T101.npz
        dest_npz_path = os.path.join(ref_dir, f"{turtle_id}.npz")

        # --- THE "SKIP DUPLICATE" CHECK ---
        # If T101.npz exists, we assume this ID is already processed for this location.
        # This handles both restarting the server AND multiple images for T101 in the source folder.
        if os.path.exists(dest_npz_path):
            return "skipped"

        # If we get here, it is the FIRST time seeing this ID in this location.
        shutil.copy2(source_path, dest_image_path)
        success, _ = image_processing.process_image_through_SIFT(dest_image_path, dest_npz_path)

        if success:
            print(f"   ✅ Processed New: {turtle_id}")
            return "created"
        else:
            print(f"   ⚠️ SIFT Failed: {turtle_id}")
            return "error"



    def handle_community_upload(self, image_path, finder_name="Anonymous"):
        """
        Saves an image to 'backend/data/Community_Uploads/FinderName/'.
        """
        dest_folder = os.path.join(self.base_dir, "Community_Uploads", finder_name)
        os.makedirs(dest_folder, exist_ok=True)

        filename = os.path.basename(image_path)
        saved_path = os.path.join(dest_folder, filename)
        shutil.copy2(image_path, saved_path)
        print(f"Saved community find by {finder_name}")

        # --- NEW: Automatically Create a Review Packet for this upload ---
        # This puts it into the Admin's "Inbox" (Queue) immediately
        self.create_review_packet(saved_path, user_info={"finder": finder_name})

    def create_review_packet(self, query_image_path, user_info=None):
        """
        Creates a folder in 'Review_Queue' containing the query image
        and copies of the Top 5 candidate matches found by AI.
        """
        # 1. Create Unique Request Folder
        request_id = f"Req_{int(time.time())}_{os.path.basename(query_image_path)}"
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        candidates_dir = os.path.join(packet_dir, 'candidate_matches')

        os.makedirs(packet_dir, exist_ok=True)
        os.makedirs(candidates_dir, exist_ok=True)

        # 2. Save the Query Image
        filename = os.path.basename(query_image_path)
        query_save_path = os.path.join(packet_dir, filename)
        shutil.copy2(query_image_path, query_save_path)

        # 3. Save Metadata (includes optional flag/collected_to_lab/digital_flag from upload)
        if user_info:
            with open(os.path.join(packet_dir, 'metadata.json'), 'w') as f:
                json.dump(user_info, f)

        # Create additional_images dir for optional microhabitat/condition photos
        additional_dir = os.path.join(packet_dir, 'additional_images')
        os.makedirs(additional_dir, exist_ok=True)
        with open(os.path.join(additional_dir, 'manifest.json'), 'w') as f:
            json.dump([], f)

        print(f"🐢 Analysis: Running Smart Search for {filename}...")

        # 4. Run AI Search
        # Note: smart_search must return 'file_path' or 'filename' we can resolve
        results = image_processing.smart_search(query_save_path, k_results=5)

        # 5. Populate the Candidate Folder
        if results:
            for i, match in enumerate(results):
                match_id = match.get('site_id', 'Unknown')
                score = int(match.get('distance', 0) * 100)

                # Logic to find the original file to copy
                # Ideally, smart_search should return 'file_path' in the dict.
                # If not, we might need to look it up.
                # For now, we assume 'file_path' exists or we construct it from filename if possible.
                original_path = match.get('file_path')

                if original_path and os.path.exists(original_path):
                    # We copy the .npz's corresponding .jpg if possible,
                    # otherwise we just copy what we have.
                    # Assumption: .npz and .jpg are in the same folder with same basename
                    base_path = os.path.splitext(original_path)[0]  # Remove .npz
                    possible_exts = ['.jpg', '.jpeg', '.png']
                    found_img = None
                    for ext in possible_exts:
                        if os.path.exists(base_path + ext):
                            found_img = base_path + ext
                            break

                    if found_img:
                        new_name = f"Rank{i + 1}_ID{match_id}_Score{score}.jpg"
                        shutil.copy2(found_img, os.path.join(candidates_dir, new_name))

        print(f"✅ Review Packet Created: {request_id}")
        return request_id

    def add_additional_images_to_packet(self, request_id, files_with_types):
        """
        Add extra images (e.g. microhabitat, condition) to an existing review packet.
        files_with_types: list of dicts with keys: path (str), type (str, e.g. 'microhabitat' or 'condition'), timestamp (optional ISO str).
        """
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.isdir(packet_dir):
            return False, "Request not found"
        additional_dir = os.path.join(packet_dir, 'additional_images')
        os.makedirs(additional_dir, exist_ok=True)
        manifest_path = os.path.join(additional_dir, 'manifest.json')
        manifest = []
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        for item in files_with_types:
            src = item.get('path')
            typ = (item.get('type') or 'other').lower()
            if typ not in ('microhabitat', 'condition', 'other'):
                typ = 'other'
            ts = item.get('timestamp') or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            if not src or not os.path.isfile(src):
                continue
            ext = os.path.splitext(src)[1] or '.jpg'
            safe_name = f"{typ}_{int(time.time())}_{os.path.basename(src)}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in '._-')
            dest = os.path.join(additional_dir, safe_name)
            shutil.copy2(src, dest)
            manifest.append({"filename": safe_name, "type": typ, "timestamp": ts})
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)
        return True, "OK"

    def remove_additional_image_from_packet(self, request_id, filename):
        """
        Remove one image from a packet's additional_images by filename.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.isdir(packet_dir):
            return False, "Request not found"
        additional_dir = os.path.join(packet_dir, 'additional_images')
        manifest_path = os.path.join(additional_dir, 'manifest.json')
        if not os.path.isfile(manifest_path):
            return False, "No additional images"
        # Security: filename must not contain path separators
        if not filename or os.path.basename(filename) != filename:
            return False, "Invalid filename"
        file_path = os.path.join(additional_dir, filename)
        if not os.path.isfile(file_path):
            return False, "Image not found"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        new_manifest = [e for e in manifest if e.get('filename') != filename]
        if len(new_manifest) == len(manifest):
            return False, "Image not in manifest"
        try:
            os.remove(file_path)
        except OSError as e:
            return False, str(e)
        with open(manifest_path, 'w') as f:
            json.dump(new_manifest, f)
        return True, None

    def remove_additional_image_from_turtle(self, turtle_id, filename, sheet_name=None):
        """
        Remove one image from a turtle's additional_images folder by filename.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        turtle_dir = self._get_turtle_folder(turtle_id, sheet_name)
        if not turtle_dir or not os.path.isdir(turtle_dir):
            return False, "Turtle folder not found"
        additional_dir = os.path.join(turtle_dir, 'additional_images')
        if not os.path.isdir(additional_dir):
            return False, "No additional images folder"
        # Security: filename must not contain path separators
        if not filename or os.path.basename(filename) != filename:
            return False, "Invalid filename"
        file_path = os.path.join(additional_dir, filename)
        if not os.path.isfile(file_path):
            return False, "Image not found"
        manifest_path = os.path.join(additional_dir, 'manifest.json')
        if not os.path.isfile(manifest_path):
            try:
                os.remove(file_path)
                return True, None
            except OSError as e:
                return False, str(e)
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        new_manifest = [e for e in manifest if e.get('filename') != filename]
        if len(new_manifest) == len(manifest):
            return False, "Image not in manifest"
        try:
            os.remove(file_path)
        except OSError as e:
            return False, str(e)
        with open(manifest_path, 'w') as f:
            json.dump(new_manifest, f)
        return True, None

    # --- NEW: SEARCH & OBSERVATION LOGIC ---

    def search_for_matches(self, query_image_path, sheet_name=None):
        """
        Smart Search with "Auto-Mirror" fallback.
        1. Search Normal.
        2. If scores are low, flip image horizontal and search again.
        3. Return the best set of results.

        sheet_name: If set, only compare against turtles from this location (Google Sheet tab name).
                    None or empty = search across all locations.
        """
        total_search_start = time.time()
        location_filter = (sheet_name or '').strip() or None

        MATCH_CONFIDENCE_THRESHOLD = 15

        filename = os.path.basename(query_image_path)
        scope = f" (Location: {location_filter})" if location_filter else " (all locations)"
        print(f"🔍 Analyzing {filename} (Normal Orientation){scope}...")

        # 1. First Pass (Normal)
        # Use existing smart_search; optionally restrict to one location
        candidates_normal = image_processing.smart_search(
            query_image_path, location_filter=location_filter, k_results=20
        )
        # If location filter was used and we got no candidates, the filter may not match
        # our index (index uses folder names, UI may send sheet tab names). Fall back to all.
        if location_filter and not candidates_normal:
            candidates_normal = image_processing.smart_search(
                query_image_path, location_filter=None, k_results=20
            )
        results_normal = []

        # Rerank with RANSAC
        if candidates_normal:
            results_normal = image_processing.rerank_results_with_spatial_verification(query_image_path, candidates_normal)

        # Get best score
        best_score_normal = 0
        if results_normal:
            best_score_normal = results_normal[0].get('spatial_score', 0)

        # 2. Check Threshold
        if best_score_normal >= MATCH_CONFIDENCE_THRESHOLD:
            print(f"✅ Good match found ({best_score_normal} matches). Returning results.")
            print(f"⏱️ Total Search & Verify Logic: {time.time() - total_search_start:.4f}s")
            return results_normal[:5]

        # 3. Second Pass (Mirrored)
        print(f"⚠️ Low confidence ({best_score_normal} < {MATCH_CONFIDENCE_THRESHOLD}). Attempting Mirror Search...")

        # Generate Mirrored Image
        img = cv.imread(query_image_path)
        if img is None: return results_normal[:5]

        img_mirrored = cv.flip(img, 1)  # 1 = Horizontal Flip

        # Save temp file
        mirror_path = os.path.join(self.review_queue_dir, f"TEMP_MIRROR_{filename}")
        cv.imwrite(mirror_path, img_mirrored)

        try:
            candidates_mirror = image_processing.smart_search(
                mirror_path, location_filter=location_filter, k_results=20
            )
            if location_filter and not candidates_mirror:
                candidates_mirror = image_processing.smart_search(
                    mirror_path, location_filter=None, k_results=20
                )
            results_mirror = []
            if candidates_mirror:
                results_mirror = image_processing.rerank_results_with_spatial_verification(mirror_path, candidates_mirror)

            best_score_mirror = 0
            if results_mirror:
                best_score_mirror = results_mirror[0].get('spatial_score', 0)

            print(f"   Normal Best: {best_score_normal} | Mirrored Best: {best_score_mirror}")

            # 4. Compare and Return Winner
            if best_score_mirror > best_score_normal:
                print("🪞 Mirrored orientation yielded better results! Switching view.")
                print(f"⏱️ Total Search & Verify Logic: {time.time() - total_search_start:.4f}s")
                # Mark as mirrored for UI
                for res in results_mirror:
                    res['is_mirrored'] = True
                return results_mirror[:5]
            else:
                print("   Normal orientation was better.")
                print(f"⏱️ Total Search & Verify Logic: {time.time() - total_search_start:.4f}s")
                return results_normal[:5]

        finally:
            # Cleanup temp file
            if os.path.exists(mirror_path):
                os.remove(mirror_path)

    def add_observation_to_turtle(self, source_image_path, turtle_id, location_hint=None):
        """
        Called when you click "Match!" on the GUI.
        Moves the uploaded image to that Turtle's 'loose_images' folder,
        processes it, and then DELETES the temporary NPZ file.
        """
        # 1. Find the turtle's home folder (Logic remains the same)
        target_dir = None
        if location_hint and location_hint != "Unknown":
            possible_path = os.path.join(self.base_dir, location_hint, turtle_id)
            if os.path.exists(possible_path):
                target_dir = possible_path

        if not target_dir:
            print(f"Scanning for home of {turtle_id}...")
            for root, dirs, files in os.walk(self.base_dir):
                if os.path.basename(root) == turtle_id:
                    target_dir = root
                    break

        if not target_dir: return False, f"Could not find folder for {turtle_id}"

        # 2. Setup Paths
        loose_dir = os.path.join(target_dir, 'loose_images')
        os.makedirs(loose_dir, exist_ok=True)

        filename = os.path.basename(source_image_path)
        save_name = f"Obs_{int(time.time())}_{filename}"
        dest_path = os.path.join(loose_dir, save_name)

        npz_name = os.path.splitext(save_name)[0] + ".npz"
        npz_path = os.path.join(loose_dir, npz_name)  # Path to temporary NPZ

        try:
            # Copy the original image
            shutil.copy2(source_image_path, dest_path)
            print(f"📸 Image copied to {dest_path}")

            # 3. Process SIFT (Necessary for temporary validation, but not persistent storage)
            success, _ = image_processing.process_image_through_SIFT(dest_path, npz_path)

            if success:
                print(f"✅ Observation processed and added to {turtle_id}")
            else:
                print(f"⚠️ Warning: Image saved but SIFT processing failed for {os.path.basename(dest_path)}")

            # --- CRITICAL FIX: DELETE THE NPZ ---
            if os.path.exists(npz_path):
                os.remove(npz_path)
                print(f"🗑️ Deleted temporary NPZ file: {os.path.basename(npz_path)}")
            # -----------------------------------

            return True, dest_path
        except Exception as e:
            return False, str(e)

    def _get_turtle_folder(self, turtle_id, location_hint=None):
        """Resolve turtle folder path by turtle_id and optional location_hint."""
        if location_hint and location_hint != "Unknown":
            possible_path = os.path.join(self.base_dir, location_hint, turtle_id)
            if os.path.exists(possible_path):
                return possible_path
        for root, dirs, files in os.walk(self.base_dir):
            if os.path.basename(root) == turtle_id:
                return root
        return None

    def approve_review_packet(self, request_id, match_turtle_id=None, new_location=None, new_turtle_id=None, uploaded_image_path=None, find_metadata=None):
        """
        Called when Admin approves a packet.
        - If match_turtle_id is set: Adds image to that existing turtle's 'loose_images'.
        - If new_location and new_turtle_id are set: Creates a NEW turtle folder there.
        - find_metadata: optional dict with microhabitat_uploaded, other_angles_uploaded,
          collected_to_lab, physical_flag, digital_flag_lat, digital_flag_lon, digital_flag_source.
        - Copies packet's additional_images into turtle folder and writes find_metadata.json.
        
        Args:
            request_id: The request ID (can be from review queue or admin upload)
            match_turtle_id: Existing turtle ID to add observation to
            new_location: Location for new turtle (format: "State/Location")
            new_turtle_id: ID for new turtle (e.g., "T101")
            uploaded_image_path: Direct path to uploaded image (for admin uploads not in queue)
            find_metadata: Optional dict for flag/microhabitat confirmation and digital flag coords
        """
        # Try to find image in review queue first
        query_image = None
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        
        if os.path.exists(packet_dir):
            # Find the uploaded image inside the packet (ignoring subfolders)
            for f in os.listdir(packet_dir):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')) and f != 'metadata.json':
                    query_image = os.path.join(packet_dir, f)
                    break
        elif uploaded_image_path and os.path.exists(uploaded_image_path):
            # Admin upload: use the direct path provided
            query_image = uploaded_image_path
        else:
            return False, "Request not found and no image path provided"

        if not query_image or not os.path.exists(query_image):
            return False, "Error: No image found."

        # Logic: existing match vs new turtle
        if match_turtle_id:
            # Add to existing turtle's loose_images folder
            print(f"📸 Adding observation to existing Turtle {match_turtle_id}...")
            success, message = self.add_observation_to_turtle(query_image, match_turtle_id)
            if not success:
                return False, f"Failed to add to existing turtle: {message}"
            print(f"✅ Observation added to {match_turtle_id}")

        elif new_location and new_turtle_id:
            # Create new turtle. new_location can be "State" or "State/Location" for two-level paths.
            print(f"🐢 Creating new turtle {new_turtle_id} at {new_location}...")
            parts = [p.strip() for p in new_location.split("/") if p.strip()]
            sheet_name = parts[0] if parts else new_location
            if len(parts) >= 2:
                # Two-level: data/<sheet>/<location>/<turtle_id>/
                location_dir = os.path.join(self.base_dir, parts[0], parts[1])
            else:
                # Single-level (backward compatible): data/<sheet>/<turtle_id>/
                location_dir = os.path.join(self.base_dir, sheet_name)
            os.makedirs(location_dir, exist_ok=True)
            
            # Process the new turtle (this will create the turtle folder and process the image)
            status = self._process_single_turtle(query_image, location_dir, new_turtle_id)
            
            if status == "created":
                print(f"✅ New turtle {new_turtle_id} created successfully at {new_location}")
                # Rebuild search index so the new turtle is findable on the next upload
                print("♻️  Rebuilding search index to include new turtle...")
                image_processing.rebuild_index_and_reload(self.base_dir)
                print("✅ Search index updated.")
            elif status == "skipped":
                return False, f"Turtle {new_turtle_id} already exists at {new_location}"
            else:
                return False, f"Failed to process image for new turtle {new_turtle_id}"
        else:
            return False, "Either match_turtle_id or both new_location and new_turtle_id must be provided"

        # Resolve turtle folder and persist find_metadata + additional_images
        target_turtle_id = match_turtle_id if match_turtle_id else new_turtle_id
        location_hint = (new_location or "").split("/")[0].strip() if new_location else None
        target_dir = self._get_turtle_folder(target_turtle_id, location_hint)
        if target_dir:
            # Write find_metadata.json (flag, microhabitat, collected_to_lab, digital flag)
            if find_metadata is not None and isinstance(find_metadata, dict):
                meta_path = os.path.join(target_dir, 'find_metadata.json')
                with open(meta_path, 'w') as f:
                    json.dump(find_metadata, f)
            # Copy additional_images from packet to turtle's additional_images folder
            packet_dir = os.path.join(self.review_queue_dir, request_id)
            if os.path.isdir(packet_dir):
                src_additional = os.path.join(packet_dir, 'additional_images')
                if os.path.isdir(src_additional):
                    dest_additional = os.path.join(target_dir, 'additional_images')
                    os.makedirs(dest_additional, exist_ok=True)
                    manifest_path = os.path.join(src_additional, 'manifest.json')
                    if os.path.isfile(manifest_path):
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        for entry in manifest:
                            fn = entry.get('filename')
                            if fn and os.path.isfile(os.path.join(src_additional, fn)):
                                shutil.copy2(
                                    os.path.join(src_additional, fn),
                                    os.path.join(dest_additional, fn)
                                )
                        dest_manifest = os.path.join(dest_additional, 'manifest.json')
                        with open(dest_manifest, 'w') as f:
                            json.dump(manifest, f)

        # Clean up the review packet (only if it exists in review queue)
        if os.path.exists(packet_dir):
            try:
                shutil.rmtree(packet_dir)
                print(f"🗑️ Queue Item {request_id} deleted (Processed).")
            except Exception as e:
                print(f"⚠️ Error deleting packet: {e}")
                # Still return success since the main operation completed
                return True, f"Processed successfully (cleanup warning: {str(e)})"
        else:
            # Admin upload: clean up temp file if it's in temp directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            if query_image.startswith(temp_dir):
                try:
                    os.remove(query_image)
                    print(f"🗑️ Temp file deleted: {os.path.basename(query_image)}")
                except Exception as e:
                    print(f"⚠️ Error deleting temp file: {e}")
        
        return True, "Processed successfully"

    def _add_turtle_flag_if_present(self, results, turtle_path, turtle_id, location_label):
        """If turtle_path has find_metadata.json, append to results (skip if already released)."""
        meta_path = os.path.join(turtle_path, 'find_metadata.json')
        if not os.path.isfile(meta_path):
            return
        try:
            with open(meta_path, 'r') as f:
                find_metadata = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        # Exclude turtles already marked as released back to nature
        if find_metadata.get('released_at'):
            return
        results.append({
            'turtle_id': turtle_id,
            'location': location_label,
            'path': turtle_path,
            'find_metadata': find_metadata,
        })

    def clear_release_flag(self, turtle_id, location_hint=None):
        """
        Mark turtle as released back to nature: clear digital flag and set released_at.
        Updates find_metadata.json so the turtle no longer appears on the release list.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        turtle_dir = self._get_turtle_folder(turtle_id, location_hint)
        if not turtle_dir or not os.path.isdir(turtle_dir):
            return False, "Turtle folder not found"
        meta_path = os.path.join(turtle_dir, 'find_metadata.json')
        if not os.path.isfile(meta_path):
            return False, "No find metadata"
        try:
            with open(meta_path, 'r') as f:
                find_metadata = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return False, str(e)
        # Remove digital flag so it is no longer used for release
        for key in ('digital_flag_lat', 'digital_flag_lon', 'digital_flag_source'):
            find_metadata.pop(key, None)
        # Mark as released (ISO timestamp)
        find_metadata['released_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        try:
            with open(meta_path, 'w') as f:
                json.dump(find_metadata, f)
        except OSError as e:
            return False, str(e)
        return True, None

    def get_turtles_with_flags(self):
        """
        Scan data dir for turtles that have find_metadata.json (e.g. with digital_flag or collected_to_lab).
        Handles both structures: data/State/TurtleID and data/State/Location/TurtleID.
        Returns list of dicts: turtle_id, location (State or State/Location), path, find_metadata.
        """
        results = []
        for state in sorted(os.listdir(self.base_dir)):
            state_path = os.path.join(self.base_dir, state)
            if not os.path.isdir(state_path) or state.startswith('.'):
                continue
            if state in ["Review_Queue", "Community_Uploads", "Incidental_Finds"]:
                continue
            for name in sorted(os.listdir(state_path)):
                sub_path = os.path.join(state_path, name)
                if not os.path.isdir(sub_path) or name.startswith('.'):
                    continue
                # Case 1: state/name is a turtle folder (e.g. data/Kansas/T101)
                self._add_turtle_flag_if_present(results, sub_path, name, state)
                # Case 2: state/name is a location folder; look for turtle folders inside
                for turtle_id in sorted(os.listdir(sub_path)):
                    turtle_path = os.path.join(sub_path, turtle_id)
                    if not os.path.isdir(turtle_path) or turtle_id.startswith('.'):
                        continue
                    self._add_turtle_flag_if_present(results, turtle_path, turtle_id, f"{state}/{name}")
        return results

    def reject_review_packet(self, request_id):
        """
        Delete a review queue packet without processing (e.g. junk/spam).
        Removes the packet folder from Review_Queue. Admin only.
        """
        packet_dir = os.path.join(self.review_queue_dir, request_id)
        if not os.path.exists(packet_dir) or not os.path.isdir(packet_dir):
            return False, "Request not found"
        # Security: ensure we only delete inside review_queue_dir (no path traversal)
        real_packet = os.path.realpath(packet_dir)
        real_base = os.path.realpath(self.review_queue_dir)
        if not real_packet.startswith(real_base):
            return False, "Invalid request path"
        try:
            shutil.rmtree(packet_dir)
            print(f"🗑️ Queue Item {request_id} deleted (Rejected/Discarded).")
            return True, "Deleted"
        except Exception as e:
            return False, str(e)

# --- TEST BLOCK ---
if __name__ == "__main__":
    manager = TurtleManager()
    # 1. Test Queue Persistence
    print("\n--- Checking Queue Status ---")
    manager.get_review_queue()

    # 2. Test Ingest
    path = input("\n(Optional) Enter Flash Drive Path to test Ingest: ")
    if path:
        manager.ingest_flash_drive(path)