# Changelog

All notable changes to TurtleTracker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Location selection (sheet + location)**: Two-level location hierarchy for new turtles and community uploads. Users select a spreadsheet/sheet (e.g. Kansas, Nebraska) and then a location folder (e.g. Wichita, Lawrence). Backend paths are now `data/<sheet>/<location>/<turtle_id>/` instead of `data/<sheet>/<turtle_id>/`. New locations can be added under an existing sheet without creating a new Google Sheet tab. API `GET /api/locations` returns backend location paths (State/Location) for dropdowns. Resolves #96.
- **Post-confirmation automation**: After the turtle team confirms an upload (match or new turtle), the backend now (1) relabels photos/records with the confirmed turtle ID (e.g. copies images into the turtle folder with timestamped filenames) and (2) syncs confirmed data to a **community-facing Google Spreadsheet** (separate from the research spreadsheet). Set `GOOGLE_SHEETS_COMMUNITY_SPREADSHEET_ID` in backend `.env`; community spreadsheet is required for community-upload confirmations. Resolves #73.
- **Email verification**: New users (email/password registration) must verify their email via a link sent on signup. Auth backend supports `email_verified` / `email_verified_at` on users, an `email_verifications` table for tokens, and endpoints `POST /auth/verify-email` and `POST /auth/resend-verification`. Google OAuth users are treated as verified. Admin-only routes (promote-to-admin, users list) require a verified email via `requireEmailVerified` middleware.
- **Password policy**: Registration and change-password enforce a password policy via `validatePassword`. New endpoint `POST /auth/change-password` (authenticated) to update password with the same policy.
- **Email service**: Verification emails via `sendVerificationEmail`; shared helpers `wrapEmailHtml` and `sendMailSafe`; admin promotion and invitation emails refactored to use them. No-reply sender configurable via `SMTP_FROM`.
- **Docker**: Configurable frontend host port via `FRONTEND_PORT` in `.env` (default 80). When port 80 is in use, set `FRONTEND_PORT=8080` and `FRONTEND_URL=http://localhost:8080` so auth redirects work correctly. See `.env.docker.example` and comments in `docker-compose.yml`.
- Backend folder structure driven by admin and community sheet names (on startup and after full reset): `data/<admin sheet>`, `data/Community_Uploads/<community sheet>`.
- Review queue: badges in list and detail view indicating "Admin upload" vs "Community upload" (by `request_id`).
- Sheet/Location dropdown source: `sheetSource` (admin | community) so community uploads use community spreadsheet tabs and admin use admin sheet/State.
- API: `GET /api/sheets/community-sheets`; `POST /api/sheets/sheets` and `POST /api/sheets/turtle` accept `target_spreadsheet: 'community'` to create/list in community spreadsheet.
- Option "+ Create New Sheet" for community turtles; new community sheet creates tab and `data/Community_Uploads/<name>` folder.

### Changed

- **Auth backend**: Database migration adds `email_verified` and `email_verified_at` to existing users (treated as verified). SQLite-style wrapper supports `email_verifications` table and DELETE on verification tokens. JWT and `/auth/me` include `email_verified`. Admin and auth middleware use Express `Request` with `AuthRequest` cast where needed.
- **Test setup**: `seed-test-users` and `test-setup` scripts set test users to email-verified so E2E login flows land on the app as expected.
- **Intake survey**: "Health Status" field with free-text input and an optional "?" tooltip guiding community members on what to look for when assessing turtle health (e.g. mucous discharge, eye coloration, shell damage, dehydration, flesh flies, mites). Data is stored in Google Sheets when the "Health Status" column is present.
- **Docker**: Configurable frontend host port via `FRONTEND_PORT` in `.env` (default 80). When port 80 is in use, set `FRONTEND_PORT=8080` and `FRONTEND_URL=http://localhost:8080` so auth redirects work correctly. See `.env.docker.example` and comments in `docker-compose.yml`.
- **Turtle forms**: ID field is always read-only (create and edit). Description clarifies read-only behavior and that IDs may not be unique across sheets. E2E tests cover ID read-only and descriptions in create (match dialog) and edit (Sheets Browser) flows.
- Admin turtle backend path: always `data/State/Location/PrimaryID`; Location = General Location (sheet field). General Location is required when creating admin turtles.
- Review queue new turtle: admin uploads send `new_location` as `Sheet/general_location`; community uploads use single sheet name and are stored in community spreadsheet and `Community_Uploads/<sheet>`.
- `get_all_locations()` now includes state-level folder names so sheet-based state folders appear in dropdowns even with no Location subfolders.

### Fixed

- **Google Sheets**: Single RLock for all Sheets API use and reinit to avoid concurrent SSL/connection errors (e.g. DECRYPTION_FAILED_OR_BAD_RECORD_MAC, record layer failure) and process segfaults (exit 139). Route that reads sheet values for validation now holds the same lock.
- **Create New Turtle E2E (ID auto-generate)**: Test no longer fails on WebKit/Firefox when the ID field stays empty. The form now requests the biology ID when sex is selected, using the selected sheet or the first available sheet so the ID appears even when sheet selection state hasn’t updated yet. E2E test waits for the generate-id response and mocks `/api/locations` for the backend-locations flow.
- **E2E**: Stabilize flaky tests: scope sex dropdown option to listbox and wait before click (fixes WebKit failure in admin-turtle-id-auto-generate); increase timeout for "From this upload" on turtle match page (Chromium/Mobile Chrome); wait for review queue content before branching and add timeouts for "No pending reviews" (Mobile Safari).

### Removed
- Incidental_Finds: removed from backend (reset, turtle_manager, README), frontend (HomePage, useTurtleSheetsDataForm), and locations API docstring.

---

## [0.1.0] - 2026-02-27

First release of TurtleTracker: a community-driven web platform for turtle population monitoring using image-based identification.

### Added

- **Authentication**: User registration, login, and Google OAuth via auth backend (Node.js/Express). JWT-based sessions and role-based access (admin vs community).
- **Photo upload and matching**: Admins and community users can upload turtle photos; system returns top matches. Community uploads go to a review queue for admin approval.
- **Admin features**: Review queue for community uploads with suggested matches; admin can confirm match or create new turtle. Photo upload with immediate top-5 match selection.
- **Turtle records / data**: Turtle data management with optional Google Sheets integration (service account); auto-generated biology IDs and configurable fields.
- **Frontend**: React (TypeScript) app with Mantine UI, Tailwind, Leaflet maps; configured for auth and turtle API backends.
- **Backend**: Flask API (Python) for photo processing and matching; auth backend for user and session management.
- **Deployment**: Docker Compose setup for running frontend, auth-backend, and backend together; persistent volumes for DB, uploads, and review state.
- **Testing**: Playwright E2E tests (Docker-based) and backend integration tests (pytest); CI workflows for main/develop.
- **Documentation**: README with quick start (Docker and local), functionality overview, and versioning guide in `docs/VERSION_AND_RELEASES.md`.
- Version control and release process: `CHANGELOG.md`, version in `frontend/package.json`, and guide in `docs/VERSION_AND_RELEASES.md`.

[Unreleased]: https://github.com/Lxkasmehl/TurtleProject/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Lxkasmehl/TurtleProject/releases/tag/v0.1.0
