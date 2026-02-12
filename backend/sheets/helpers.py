"""
Helper functions for Google Sheets operations
"""

from typing import Optional, Dict
from googleapiclient.errors import HttpError


def escape_sheet_name(sheet_name: str) -> str:
    """
    Escape sheet name for use in A1 notation.
    Sheet names with special characters or spaces need to be wrapped in single quotes.
    
    Args:
        sheet_name: Raw sheet name
        
    Returns:
        Escaped sheet name for use in range notation
    """
    # If sheet name contains special characters, spaces, or starts with a number, wrap in quotes
    if any(char in sheet_name for char in [' ', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '+', '=']):
        return f"'{sheet_name}'"
    return sheet_name


def get_sheet_name_for_region(sheet_name: Optional[str] = None, state: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Determine which sheet (tab) to use.
    If sheet_name is provided, use it directly. Otherwise, try to determine from state/location.
    Rejects backup sheets.
    
    Args:
        sheet_name: Direct sheet name (e.g., "Location A", "Location B")
        state: State name (e.g., "Kansas") - not used for sheet selection
        location: Optional specific location - not used for sheet selection
        
    Returns:
        Sheet name (tab name) in the spreadsheet
        
    Raises:
        ValueError: If sheet_name is empty or is a backup sheet
    """
    # If sheet_name is provided and not empty, use it directly
    if sheet_name and sheet_name.strip():
        sheet_name = sheet_name.strip()
        
        # Reject backup sheets (note: "Inital" is a typo in the actual sheet name)
        backup_sheet_names = ['Backup (Initial State)', 'Backup (Inital State)', 'Backup']
        if sheet_name in backup_sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' is a backup sheet and cannot be modified or accessed")
        
        return sheet_name
    
    # Fallback should NOT use state, as state might be general_location (e.g., "CPBS")
    # This is a critical error - sheet_name must always be provided
    print(f"ERROR: sheet_name is empty or None! state='{state}', location='{location}'")
    raise ValueError("Sheet name must be provided and cannot be empty")


def find_column_index(service, spreadsheet_id: str, sheet_name: str, column_header: str) -> Optional[int]:
    """
    Find the column index for a given header in a sheet.
    Searches row 1 (header row) for the column header.
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: Google Sheets spreadsheet ID
        sheet_name: Name of the sheet (tab)
        column_header: Header text to find
        
    Returns:
        Column index (0-based) or None if not found
    """
    try:
        # Get the first row (headers)
        escaped_sheet = escape_sheet_name(sheet_name)
        range_name = f"{escaped_sheet}!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None
        
        headers = values[0]
        try:
            return headers.index(column_header)
        except ValueError:
            return None
    except HttpError as e:
        print(f"Error finding column index: {e}")
        return None


def get_all_column_indices(service, spreadsheet_id: str, sheet_name: str, list_sheets_func) -> Dict[str, int]:
    """
    Get all column indices for a sheet by reading the header row.
    Skips backup sheets.
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: Google Sheets spreadsheet ID
        sheet_name: Name of the sheet (tab)
        list_sheets_func: Function to list available sheets
        
    Returns:
        Dictionary mapping column headers to indices (0-based)
    """
    # Skip backup sheets - they should not be accessed
    backup_sheet_names = ['Backup (Initial State)', 'Backup (Inital State)', 'Backup']
    if sheet_name in backup_sheet_names:
        print(f"Info: Skipping backup sheet '{sheet_name}'")
        return {}
    
    try:
        # First, verify the sheet exists
        available_sheets = list_sheets_func()
        if sheet_name not in available_sheets:
            print(f"Warning: Sheet '{sheet_name}' not found. Available sheets: {available_sheets}")
            return {}
        
        # Get the first row (headers)
        escaped_sheet = escape_sheet_name(sheet_name)
        range_name = f"{escaped_sheet}!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return {}
        
        headers = values[0]
        column_indices = {}
        for idx, header in enumerate(headers):
            if header and header.strip():
                column_indices[header.strip()] = idx
        
        return column_indices
    except HttpError as e:
        print(f"Error getting column indices for sheet '{sheet_name}': {e}")
        # Try to list available sheets for debugging
        try:
            available_sheets = list_sheets_func()
            print(f"Available sheets: {available_sheets}")
        except:
            pass
        return {}


def column_index_to_letter(col_idx: int) -> str:
    """
    Convert a 0-based column index to Google Sheets column letter (A, B, C, ..., Z, AA, AB, ...)
    
    Args:
        col_idx: 0-based column index
        
    Returns:
        Column letter(s) (e.g., 'A', 'B', 'AA')
    """
    result = ''
    col_idx += 1  # Convert to 1-based
    while col_idx > 0:
        col_idx -= 1
        result = chr(65 + (col_idx % 26)) + result
        col_idx //= 26
    return result


def is_backup_sheet(sheet_name: str) -> bool:
    """
    Check if a sheet name is a backup sheet.
    
    Args:
        sheet_name: Name of the sheet to check
        
    Returns:
        True if it's a backup sheet, False otherwise
    """
    backup_sheet_names = ['Backup (Initial State)', 'Backup (Inital State)', 'Backup']
    return sheet_name in backup_sheet_names
