# Turtle Project Backend

Flask API Server for the Turtle Identification System.

## Installation

1. Make sure Python 3.8+ is installed.

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the `backend` directory (copy from `env.template`):

```bash
# On Windows (PowerShell)
Copy-Item env.template .env

# On Linux/Mac
cp env.template .env
```

2. Update the `.env` file with your configuration:

```env
# Server Port (default: 5000)
PORT=5000

# Flask Debug Mode
FLASK_DEBUG=true

# JWT Secret - MUST match the JWT_SECRET in auth-backend/.env
JWT_SECRET=your-secret-key-change-in-production
```

**Important:** The `JWT_SECRET` must match the `JWT_SECRET` in `auth-backend/.env` so that the Flask backend can verify JWT tokens from the auth-backend.

## Starting the Server

1. Navigate to the backend directory:

```bash
cd backend
```

2. Start the Flask server:

```bash
python app.py
```

The server runs by default on `http://localhost:5000`.

## API Endpoints

### Health Check

- `GET /api/health` - Checks if the server is running

### Photo Upload

- `POST /api/upload` - Uploads a photo

  - **Admin**: Processes immediately and returns top 5 matches
  - **Community**: Saves to review queue with top 5 matches

  Form Data:

  - `file`: The image file
  - `role`: 'admin' or 'community'
  - `email`: User's email address

### Review Queue

- `GET /api/review-queue` - Returns all pending review items (Admin only)

### Approve Review

- `POST /api/review/<request_id>/approve` - Approves a review item (Admin only)

  Body:

  ```json
  {
    "match_turtle_id": "T101" // The selected turtle ID
  }
  ```

### Get Images

- `GET /api/images` - Returns an image from the file system
  - Query parameter: `path=<encoded_image_path>`

## Data Structure

The backend uses the following directory structure:

```
backend/
├── data/                    # Main data directory
│   ├── Review_Queue/        # Community uploads (waiting for review)
│   ├── Community_Uploads/   # Saved community uploads
│   └── [State]/[Location]/  # Official turtle data
│       └── [TurtleID]/
│           ├── ref_data/     # Reference images
│           └── loose_images/ # Additional observations
├── app.py                   # Flask API Server
├── turtle_manager.py        # Main logic for turtle management
├── image_processing.py      # SIFT/VLAD image processing
└── search_utils.py          # FAISS search functions
```

## Important Notes

- On first startup, the system will automatically generate FAISS indexes and vocabulary if they don't exist yet.
- Community uploads are saved in `data/Review_Queue/` and wait for admin review.
- Admin uploads are processed immediately and the top 5 matches are returned.

## Clearing Uploaded Data

To clear all uploaded data (Review Queue, Community Uploads, temporary files):

```bash
python clear_uploads.py
```

This will:

- Delete all items in the Review Queue
- Delete all Community Uploads
- Clear temporary uploaded files

**Note:** This does NOT delete:

- Official turtle data (State/Location folders)
- FAISS indexes and vocabulary
- Trained models

To clear only the Review Queue:

```bash
python clear_uploads.py --review-only
```

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change the port in your `.env` file:

```env
PORT=5001
```

Or set it as an environment variable before starting:

```bash
PORT=5001 python app.py
```

### Environment Configuration

The backend uses a separate `.env` file that is completely independent from `auth-backend/.env`. The only shared configuration is `JWT_SECRET`, which must match between both backends for authentication to work.

- `backend/.env` - Flask backend configuration (PORT, FLASK_DEBUG, JWT_SECRET)
- `auth-backend/.env` - Auth backend configuration (PORT, JWT_SECRET, etc.)

These are kept separate to avoid configuration conflicts.

### Missing Dependencies

Make sure all packages are installed:

```bash
pip install -r requirements.txt
```

### FAISS Installation Issues

If `faiss-cpu` cannot be installed, try:

```bash
pip install faiss-cpu --no-cache-dir
```

## Google Sheets API Integration

The backend supports integration with Google Sheets for turtle data management. This allows admins to sync turtle data directly to Google Sheets when approving matches or creating new turtles.

### Prerequisites

1. A Google Cloud Project
2. A Google Sheets spreadsheet with the turtle data
3. Service Account credentials

### Setup Instructions

#### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

#### Step 2: Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `turtle-sheets-service` (or any name you prefer)
   - Description: `Service account for Turtle Project Google Sheets integration`
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

#### Step 3: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create" - this will download a JSON file
6. Save this file securely (e.g., `backend/credentials/google-sheets-credentials.json`)

#### Step 4: Share Google Sheet with Service Account

1. Open your Google Sheets spreadsheet
2. Click the "Share" button
3. Add the service account email (found in the JSON file as `client_email`)
4. Give it "Editor" permissions
5. Click "Send"

#### Step 5: Get Spreadsheet ID

1. Open your Google Sheets spreadsheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Copy the `SPREADSHEET_ID` part

#### Step 6: Configure Environment Variables

Add the following variables to your `backend/.env` file:

```env
# Google Sheets API Configuration
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google-sheets-credentials.json
```

Replace `your-spreadsheet-id-here` with your actual spreadsheet ID and update the credentials path if you saved the JSON file in a different location.

#### Step 7: Install Dependencies

The Google Sheets API dependencies are already included in `requirements.txt`. If you haven't installed them yet:

```bash
pip install -r requirements.txt
```

This will install:
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`

#### Step 8: Verify Setup

1. Start the backend server:
   ```bash
   python app.py
   ```

2. Check the console output - you should see no errors related to Google Sheets
3. If there are errors, check:
   - The credentials file path is correct
   - The spreadsheet ID is correct
   - The service account has access to the spreadsheet
   - The Google Sheets API is enabled

### Google Sheets Structure

The Google Sheets spreadsheet should have:

1. **Multiple sheets (tabs)**: One sheet per region/state
   - Example: "Kansas", "Nebraska", etc.

2. **Header row (Row 1)**: Contains column headers:
   - Transmitter ID
   - ID (Primary ID - this is the key field)
   - ID2 (random sequence)
   - Pit?
   - Pic in 2024 Archive?
   - Adopted?
   - iButton?
   - DNA Extracted?
   - Date 1st found
   - Species
   - Name
   - Sex
   - iButton Last set
   - Dates refound
   - General Location
   - Location
   - Notes
   - Transmitter put on by
   - Transmitter On Date
   - Transmitter type
   - Transmitter lifespan
   - Radio Replace Date
   - OLD Frequencies

3. **Data rows**: Each row represents one turtle

### Important Notes

- **Column headers must match exactly** (case-sensitive)
- **The "ID" column is the primary key** - it should be unique across all sheets
- **Sheet names should match state names** (e.g., "Kansas", "Nebraska")
- The system automatically finds columns by header name, so column order can change
- New columns can be added - just make sure the header name matches the expected format

### Google Sheets API Endpoints

- `GET /api/sheets/turtle/<primary_id>` - Get turtle data from Google Sheets (Admin only)
- `POST /api/sheets/turtle` - Create new turtle data in Google Sheets (Admin only)
- `PUT /api/sheets/turtle/<primary_id>` - Update turtle data in Google Sheets (Admin only)
- `GET /api/sheets/sheets` - List all available sheets (Admin only)

### Troubleshooting Google Sheets

#### Error: "Google Sheets service not configured"
- Check that `GOOGLE_SHEETS_SPREADSHEET_ID` and `GOOGLE_SHEETS_CREDENTIALS_PATH` are set in `.env`
- Verify the credentials file exists at the specified path

#### Error: "Failed to authenticate with Google Sheets"
- Check that the credentials JSON file is valid
- Verify the service account email has access to the spreadsheet
- Make sure the Google Sheets API is enabled in your Google Cloud project

#### Error: "Turtle not found in Google Sheets"
- Verify the turtle's Primary ID exists in the spreadsheet
- Check that you're looking in the correct sheet (state/region)
- Ensure the "ID" column header is exactly "ID" (case-sensitive)

#### Error: "Failed to create/update turtle data"
- Check that the service account has "Editor" permissions on the spreadsheet
- Verify the sheet name matches the state name
- Check that all required columns exist in the header row
