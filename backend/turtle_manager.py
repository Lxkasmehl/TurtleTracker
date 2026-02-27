import os
import shutil
import time
import cv2 as cv
import json
import sys

# --- PATH HACK ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- IMPORT THE BRAIN ---
try:
    from turtles.image_processing import brain
except ImportError:
    try:
        from image_processing import brain
    except ImportError:
        print("❌ CRITICAL: Could not import 'brain'. Check file structure.")
        sys.exit(1)

# --- CONFIGURATION ---
BASE_DATA_DIR = 'data'
LOCATION_NAME_MAP = {}  # Add mappings if needed


class TurtleManager:
    def __init__(self, base_data_dir='data'):
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), base_data_dir)
        self.review_queue_dir = os.path.join(self.base_dir, 'Review_Queue')

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.review_queue_dir, exist_ok=True)
        self._ensure_special_directories()

        # --- Indexing ---
        self.db_index = []
        print("🐢 TurtleManager: Indexing Database...")
        self.refresh_database_index()
        print(f"✅ Indexed {len(self.db_index)} known turtles.")

    def set_device(self, mode):
        """Passes device toggle down to the deep learning brain."""
        brain.set_device(mode)

    def save_benchmark(self, device_mode, total_time):
        """Saves sequential benchmark files for runtime analysis."""
        bench_dir = os.path.join(self.base_dir, 'benchmarks')
        os.makedirs(bench_dir, exist_ok=True)
        prefix = device_mode.upper()

        idx = 1
        while os.path.exists(os.path.join(bench_dir, f"{prefix}_{idx}.txt")):
            idx += 1

        filepath = os.path.join(bench_dir, f"{prefix}_{idx}.txt")
        with open(filepath, "w") as f:
            f.write(f"TurtleVision Benchmark Log\n")
            f.write(f"Device Used: {prefix}\n")
            f.write(f"Total Batch Runtime: {total_time:.4f} seconds\n")
        print(f"⏱️ Benchmark saved to {filepath}")

    def _ensure_special_directories(self):
        for special_folder in ["Community_Uploads", "Incidental_Finds"]:
            path = os.path.join(self.base_dir, special_folder)
            os.makedirs(path, exist_ok=True)

    def refresh_database_index(self):
        """Scans for .pt files to build the search index and pushes to VRAM."""
        self.db_index = []
        for root, dirs, files in os.walk(self.base_dir):
            if "ref_data" in root:
                for file in files:
                    if file.endswith(".pt"):
                        path_parts = root.split(os.sep)
                        if len(path_parts) >= 3:
                            turtle_id = path_parts[-2]
                            rel_path = os.path.relpath(root, self.base_dir)
                            loc_parts = rel_path.split(os.sep)[:-2]
                            location_name = "/".join(loc_parts)
                            self.db_index.append((os.path.join(root, file), turtle_id, location_name))

        # --- NEW: Push the indexed files directly into the Brain's VRAM ---
        if hasattr(brain, 'load_database_to_vram'):
            print("⚡ Pushing database to Memory Cache...")
            brain.load_database_to_vram(self.db_index)

    def get_all_locations(self):
        locations = ["Incidental_Finds", "Community_Uploads"]
        if os.path.exists(self.base_dir):
            for state in sorted(os.listdir(self.base_dir)):
                state_path = os.path.join(self.base_dir, state)
                if not os.path.isdir(state_path) or state.startswith('.'): continue
                if state in ["Review_Queue", "Community_Uploads", "Incidental_Finds", "benchmarks"]: continue
                for loc in sorted(os.listdir(state_path)):
                    if os.path.isdir(os.path.join(state_path, loc)) and not loc.startswith('.'):
                        locations.append(f"{state}/{loc}")
        return locations

    # --- RESTORED ORIGINAL INGEST LOGIC ---
    def ingest_flash_drive(self, drive_root_path):
        ingest_start_time = time.time()
        print(f"🐢 Starting Flat Ingest from: {drive_root_path}")

        count_new = 0
        count_skipped = 0

        # Iterate directly over the locations in the selected folder
        for location_name in os.listdir(drive_root_path):
            location_source_path = os.path.join(drive_root_path, location_name)

            # Skip files, hidden folders, or system folders
            if not os.path.isdir(location_source_path) or location_name.startswith(
                    '.') or location_name == "System Volume Information":
                continue

            official_name = LOCATION_NAME_MAP.get(location_name, location_name)
            # Create the location directly inside the base data directory
            location_dest_path = os.path.join(self.base_dir, official_name)
            os.makedirs(location_dest_path, exist_ok=True)

            for filename in os.listdir(location_source_path):
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')): continue
                turtle_id = filename[:4].strip().rstrip('_')
                source_path = os.path.join(location_source_path, filename)

                status = self._process_single_turtle(source_path, location_dest_path, turtle_id)
                if status == "created":
                    count_new += 1
                elif status == "skipped":
                    count_skipped += 1

        self.refresh_database_index()
        print(f"\n🎉 Ingest Complete. New: {count_new}, Skipped: {count_skipped}")

    def _process_single_turtle(self, source_path, location_dir, turtle_id):
        """Creates folders and generates .pt tensor file."""
        turtle_dir = os.path.join(location_dir, turtle_id)
        ref_dir = os.path.join(turtle_dir, 'ref_data')
        loose_dir = os.path.join(turtle_dir, 'loose_images')

        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(loose_dir, exist_ok=True)

        ext = os.path.splitext(source_path)[1]
        dest_image_path = os.path.join(ref_dir, f"{turtle_id}{ext}")
        dest_pt_path = os.path.join(ref_dir, f"{turtle_id}.pt")

        if os.path.exists(dest_pt_path):
            return "skipped"

        shutil.copy2(source_path, dest_image_path)
        success = brain.process_and_save(dest_image_path, dest_pt_path)

        if success:
            print(f"   ✅ Processed New: {turtle_id}")
            return "created"
        else:
            return "error"

    # --- FAST VRAM SEARCH LOGIC ---
    def search_for_matches(self, query_image_path, location_filter="All Locations"):
        filename = os.path.basename(query_image_path)
        t_start = time.time()

        print(f"🔍 Deep Searching {filename} (VRAM Cached Mode)...")

        # CALL THE NEW VRAM MATCHER (Bypasses disk entirely)
        results = brain.match_query_robust_vram(query_image_path, location_filter)

        t_elapsed = time.time() - t_start

        if results:
            print(f"✅ Found {len(results)} matches in {t_elapsed:.2f}s")
        else:
            print(f"⚠️ No matches found in {t_elapsed:.2f}s")

        return results[:5], t_elapsed

    # --- RESTORED ORIGINAL QUEUE & UPGRADE LOGIC ---

    # ARCHITECT NOTE: Restored review packet creation logic and candidate generation for app.py
    def create_review_packet(self, image_path, user_info=None):
        """Creates a pending packet in the Review Queue and generates candidate match images."""
        req_id = f"req_{int(time.time())}"
        packet_dir = os.path.join(self.review_queue_dir, req_id)
        os.makedirs(packet_dir, exist_ok=True)

        # 1. Copy the raw uploaded image into the packet
        shutil.copy2(image_path, packet_dir)

        # 2. Run the AI Search to find candidates
        print(f"🔍 Generating candidates for Review Packet: {req_id}...")
        results, _ = self.search_for_matches(image_path)

        # 3. Create candidate directory and populate it based on app.py expectations
        candidates_dir = os.path.join(packet_dir, 'candidate_matches')
        os.makedirs(candidates_dir, exist_ok=True)

        for rank, match in enumerate(results, start=1):
            turtle_id = match.get('site_id', 'Unknown')
            score = int(match.get('score', 0))
            pt_path = match.get('file_path', '')

            # Resolve the original reference image from the .pt file
            ref_img_path = None
            if pt_path and pt_path.endswith('.pt'):
                base_path = pt_path[:-3]
                for ext in ['.jpg', '.jpeg', '.png']:
                    if os.path.exists(base_path + ext):
                        ref_img_path = base_path + ext
                        break

            if ref_img_path:
                # App.py expects this exact naming convention: Rank1_IDT101_Score85.jpg
                ext = os.path.splitext(ref_img_path)[1]
                cand_filename = f"Rank{rank}_ID{turtle_id}_Score{score}{ext}"
                shutil.copy2(ref_img_path, os.path.join(candidates_dir, cand_filename))

        # 4. Dump metadata for the frontend
        meta = user_info if user_info else {}
        with open(os.path.join(packet_dir, 'metadata.json'), 'w') as f:
            json.dump(meta, f)

        print(f"📦 Review Packet {req_id} created with {len(results)} candidates.")
        return req_id

    def get_review_queue(self):
        queue_items = []
        if os.path.exists(self.review_queue_dir):
            for req_id in os.listdir(self.review_queue_dir):
                req_path = os.path.join(self.review_queue_dir, req_id)
                if os.path.isdir(req_path):
                    queue_items.append({'request_id': req_id, 'path': req_path, 'status': 'pending'})
        return queue_items

    def approve_review_packet(self, request_id, match_turtle_id=None, replace_reference=False, new_location=None,
                              new_turtle_id=None, uploaded_image_path=None):
        """
        Processes approval.
        If match_turtle_id + replace_reference=True: Swaps old master for new image.
        """
        query_image = None
        packet_dir = os.path.join(self.review_queue_dir, request_id)

        if os.path.exists(packet_dir):
            for f in os.listdir(packet_dir):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')) and f != 'metadata.json':
                    query_image = os.path.join(packet_dir, f)
                    break
        elif uploaded_image_path and os.path.exists(uploaded_image_path):
            query_image = uploaded_image_path

        if not query_image: return False, "Image not found"

        if match_turtle_id:
            target_dir = None
            for path, tid, _ in self.db_index:
                if tid == match_turtle_id:
                    target_dir = os.path.dirname(os.path.dirname(path))
                    break

            if not target_dir: return False, f"Could not find folder for {match_turtle_id}"

            ref_dir = os.path.join(target_dir, 'ref_data')
            loose_dir = os.path.join(target_dir, 'loose_images')
            os.makedirs(loose_dir, exist_ok=True)

            if replace_reference:
                print(f"✨ UPGRADING REFERENCE for {match_turtle_id}...")
                old_pt_path = os.path.join(ref_dir, f"{match_turtle_id}.pt")
                old_img_path = None
                for ext in ['.jpg', '.jpeg', '.png']:
                    possible = os.path.join(ref_dir, f"{match_turtle_id}{ext}")
                    if os.path.exists(possible):
                        old_img_path = possible
                        break

                if old_img_path:
                    archive_name = f"Archived_Master_{int(time.time())}{os.path.splitext(old_img_path)[1]}"
                    shutil.move(old_img_path, os.path.join(loose_dir, archive_name))
                    print(f"   📦 Archived old master to {archive_name}")

                if os.path.exists(old_pt_path):
                    os.remove(old_pt_path)

                new_ext = os.path.splitext(query_image)[1]
                new_master_path = os.path.join(ref_dir, f"{match_turtle_id}{new_ext}")
                new_pt_path = os.path.join(ref_dir, f"{match_turtle_id}.pt")

                shutil.copy2(query_image, new_master_path)
                brain.process_and_save(new_master_path, new_pt_path)

                obs_name = f"Obs_{int(time.time())}_{os.path.basename(query_image)}"
                shutil.copy2(query_image, os.path.join(loose_dir, obs_name))

                self.refresh_database_index()
                print(f"   ✅ {match_turtle_id} upgraded successfully.")

            else:
                print(f"📸 Adding observation to {match_turtle_id}...")
                obs_name = f"Obs_{int(time.time())}_{os.path.basename(query_image)}"
                shutil.copy2(query_image, os.path.join(loose_dir, obs_name))

        elif new_location and new_turtle_id:
            pass

        if os.path.exists(packet_dir):
            shutil.rmtree(packet_dir)

        return True, "Processed"

    def process_manual_upload(self, image_path, location_selection):
        pass


if __name__ == "__main__":
    m = TurtleManager()
    print("Manager Loaded.")