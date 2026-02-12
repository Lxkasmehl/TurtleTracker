"""
Migration functions for Google Sheets
"""

import time
import threading
import random
from typing import Dict, Optional
from googleapiclient.errors import HttpError
from .helpers import escape_sheet_name, column_index_to_letter
from .sheet_management import ensure_primary_id_column


def generate_primary_id(service, spreadsheet_id: str, list_sheets_func=None, find_row_by_primary_id_func=None,
                       state: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Generate a new unique primary ID for a turtle.
    Checks all sheets to ensure uniqueness across the entire spreadsheet.
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: Google Sheets spreadsheet ID
        list_sheets_func: Function to list all sheets
        find_row_by_primary_id_func: Function to find row by primary ID
        state: State name (optional, not used for ID generation)
        location: Optional specific location (optional, not used for ID generation)
        
    Returns:
        New unique primary ID
    """
    # Get all available sheets to check for uniqueness
    # Use a timeout to avoid blocking for too long (IDs are unique by timestamp anyway)
    # If list_sheets fails or times out, use empty list (we'll still generate unique IDs)
    all_sheets = []
    try:
        # Use threading to add a timeout to list_sheets()
        sheets_result = [None]
        exception_result = [None]
        
        def call_list_sheets():
            try:
                sheets_result[0] = list_sheets_func()
            except Exception as e:
                exception_result[0] = e
        
        thread = threading.Thread(target=call_list_sheets)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)  # 5 second timeout
        
        if thread.is_alive():
            # Timeout occurred - list_sheets is taking too long
            print(f"Warning: list_sheets() timed out after 5 seconds for ID uniqueness check - continuing without check")
            all_sheets = []  # Continue with empty list - IDs are still unique based on timestamp
        elif exception_result[0]:
            # Exception occurred
            print(f"Warning: Could not list sheets for ID uniqueness check: {exception_result[0]}")
            all_sheets = []  # Continue with empty list
        else:
            # Success
            all_sheets = sheets_result[0] if isinstance(sheets_result[0], list) else []
    except Exception as e:
        print(f"Warning: Could not list sheets for ID uniqueness check: {e}")
        all_sheets = []  # Continue with empty list - IDs are still unique based on timestamp
    
    max_attempts = 100
    
    for attempt in range(max_attempts):
        # Generate a unique ID based on timestamp and random number
        timestamp = int(time.time() * 1000)  # Use milliseconds for better uniqueness
        random_part = random.randint(10000, 99999)  # Larger random range
        candidate_id = f"T{timestamp}{random_part}"
        
        # Check if this ID already exists in any sheet
        id_exists = False
        for sheet in all_sheets:
            try:
                row_idx = find_row_by_primary_id_func(sheet, candidate_id, 'Primary ID')
                if row_idx:
                    id_exists = True
                    break
            except:
                # If sheet doesn't have Primary ID column yet, that's okay
                pass
        
        if not id_exists:
            return candidate_id
    
    # Fallback: if we couldn't generate a unique ID after max_attempts, use a more complex one
    timestamp = int(time.time() * 1000000)  # Microseconds
    random_part = random.randint(100000, 999999)
    return f"T{timestamp}{random_part}"


def needs_migration(service, spreadsheet_id: str, list_sheets_func=None, ensure_primary_id_column_func=None) -> bool:
    """
    Check if migration is needed (i.e., there are turtles with ID but no Primary ID).
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: Google Sheets spreadsheet ID
        list_sheets_func: Function to list all sheets
        ensure_primary_id_column_func: Function to ensure Primary ID column exists
        
    Returns:
        True if migration is needed, False otherwise
    """
    try:
        all_sheets = list_sheets_func()
        if not all_sheets:
            return False  # No sheets available, nothing to migrate
        
        # Note: "Inital" is a typo in the actual sheet name
        backup_sheet_names = ['Backup (Initial State)', 'Backup (Inital State)', 'Backup']
        sheets_to_check = [s for s in all_sheets if s not in backup_sheet_names]
        
        for sheet_name in sheets_to_check:
            try:
                # Ensure Primary ID column exists
                ensure_primary_id_column_func(sheet_name)
                
                # Get all rows from the sheet
                escaped_sheet = escape_sheet_name(sheet_name)
                range_name = f"{escaped_sheet}!A:Z"
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                if len(values) < 2:
                    continue  # No data rows
                
                # Get headers
                headers = values[0]
                column_indices = {}
                for idx, header in enumerate(headers):
                    if header and header.strip():
                        column_indices[header.strip()] = idx
                
                # Find Primary ID and ID column indices
                primary_id_col_idx = column_indices.get('Primary ID')
                id_col_idx = column_indices.get('ID')
                
                if primary_id_col_idx is None or id_col_idx is None:
                    continue
                
                # Check if any row has ID but no Primary ID
                for row_data in values[1:]:
                    if not row_data or len(row_data) == 0:
                        continue
                    
                    has_id = id_col_idx < len(row_data) and row_data[id_col_idx] and str(row_data[id_col_idx]).strip()
                    has_primary_id = primary_id_col_idx < len(row_data) and row_data[primary_id_col_idx] and str(row_data[primary_id_col_idx]).strip()
                    
                    if has_id and not has_primary_id:
                        return True  # Migration needed
                        
            except Exception as e:
                print(f"Warning: Error checking migration status for sheet '{sheet_name}': {e}")
                continue
        
        return False  # No migration needed
        
    except Exception as e:
        print(f"Error checking if migration is needed: {e}")
        import traceback
        traceback.print_exc()
        return False  # Assume no migration needed on error


def migrate_ids_to_primary_ids(service, spreadsheet_id: str, list_sheets_func=None,
                               ensure_primary_id_column_func=None, generate_primary_id_func=None) -> Dict[str, int]:
    """
    Migrate all turtles from using "ID" column to "Primary ID" column.
    Generates new unique Primary IDs for all turtles that don't have one.
    Uses batch updates to avoid rate limiting.
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: Google Sheets spreadsheet ID
        list_sheets_func: Function to list all sheets
        ensure_primary_id_column_func: Function to ensure Primary ID column exists
        generate_primary_id_func: Function to generate a new primary ID
        
    Returns:
        Dictionary with sheet names as keys and number of migrated turtles as values
    """
    migration_stats = {}
    
    try:
        all_sheets = list_sheets_func()
        
        # Exclude backup sheets explicitly (note: "Inital" is a typo in the actual sheet name)
        backup_sheet_names = ['Backup (Initial State)', 'Backup (Inital State)', 'Backup']
        sheets_to_migrate = [s for s in all_sheets if s not in backup_sheet_names]
        
        print(f"🔄 Starting migration for {len(sheets_to_migrate)} sheets (excluding backup sheets)")
        
        for sheet_name in sheets_to_migrate:
            try:
                # Ensure Primary ID column exists
                ensure_primary_id_column_func(sheet_name)
                
                # Get all rows from the sheet
                escaped_sheet = escape_sheet_name(sheet_name)
                range_name = f"{escaped_sheet}!A:Z"
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                if len(values) < 2:
                    continue  # No data rows
                
                # Get headers
                headers = values[0]
                column_indices = {}
                for idx, header in enumerate(headers):
                    if header and header.strip():
                        column_indices[header.strip()] = idx
                
                # Find Primary ID and ID column indices
                primary_id_col_idx = column_indices.get('Primary ID')
                id_col_idx = column_indices.get('ID')
                
                if primary_id_col_idx is None:
                    print(f"Warning: 'Primary ID' column not found in sheet '{sheet_name}'")
                    continue
                
                if id_col_idx is None:
                    print(f"Info: 'ID' column not found in sheet '{sheet_name}', skipping migration")
                    continue
                
                # Collect rows that need migration (have ID but no Primary ID, OR have Primary ID but it's empty)
                rows_to_update = []
                for row_idx, row_data in enumerate(values[1:], start=2):
                    if not row_data or len(row_data) == 0:
                        continue
                    
                    # Check if row has ID but no Primary ID (or Primary ID is empty)
                    has_id = id_col_idx < len(row_data) and row_data[id_col_idx] and str(row_data[id_col_idx]).strip()
                    has_primary_id = primary_id_col_idx < len(row_data) and row_data[primary_id_col_idx] and str(row_data[primary_id_col_idx]).strip()
                    
                    # Migrate if: has ID but no Primary ID, OR Primary ID exists but is empty
                    if has_id and not has_primary_id:
                        # Generate new unique Primary ID
                        new_primary_id = generate_primary_id_func()
                        
                        # Store the row index and new Primary ID for batch update
                        rows_to_update.append((row_idx, new_primary_id))
                        print(f"  Row {row_idx}: Will migrate ID '{row_data[id_col_idx]}' -> Primary ID '{new_primary_id}'")
                
                if not rows_to_update:
                    migration_stats[sheet_name] = 0
                    continue
                
                # Batch update using batchUpdate (more efficient than individual updates)
                # Use batchUpdate with valueInputOption for multiple ranges
                data = []
                for row_idx, new_primary_id in rows_to_update:
                    # Update only the Primary ID cell for this row
                    range_name = f"{escaped_sheet}!{column_index_to_letter(primary_id_col_idx)}{row_idx}"
                    data.append({
                        'range': range_name,
                        'values': [[str(new_primary_id)]]
                    })
                
                # Split into batches of 50 to avoid too large requests
                batch_size = 50
                migrated_count = 0
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i+batch_size]
                    body = {
                        'valueInputOption': 'RAW',
                        'data': batch
                    }
                    
                    try:
                        service.spreadsheets().values().batchUpdate(
                            spreadsheetId=spreadsheet_id,
                            body=body
                        ).execute()
                        migrated_count += len(batch)
                        
                        # Small delay to avoid rate limiting
                        if i + batch_size < len(data):
                            time.sleep(1)  # Wait 1 second between batches
                            
                    except HttpError as e:
                        if e.resp.status == 429:
                            print(f"Rate limit hit for sheet '{sheet_name}', waiting 60 seconds...")
                            time.sleep(60)  # Wait 60 seconds if rate limited
                            # Retry this batch
                            try:
                                service.spreadsheets().values().batchUpdate(
                                    spreadsheetId=spreadsheet_id,
                                    body=body
                                ).execute()
                                migrated_count += len(batch)
                            except Exception as retry_error:
                                print(f"Error retrying batch update for sheet '{sheet_name}': {retry_error}")
                        else:
                            print(f"Error updating batch for sheet '{sheet_name}': {e}")
                
                migration_stats[sheet_name] = migrated_count
                print(f"✅ Migrated {migrated_count} turtles in sheet '{sheet_name}' with new unique Primary IDs")
                
            except Exception as e:
                print(f"Error migrating IDs in sheet '{sheet_name}': {e}")
                migration_stats[sheet_name] = 0
                continue
        
        return migration_stats
        
    except Exception as e:
        print(f"Error in migrate_ids_to_primary_ids: {e}")
        return migration_stats
