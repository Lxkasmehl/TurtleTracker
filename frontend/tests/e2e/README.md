# E2E tests (Playwright)

**What:** End-to-end tests in a real browser (login, upload, admin flows). Frontend, auth, and backend are tested together.

**Where:** All E2E tests live in `frontend/tests/e2e/`. They run with Playwright.

**Data:** In the recommended flow, all services run in Docker (volumes `backend-data`, `auth-data`) – real host data is not used.

- **Recommended (Docker):** `docker compose up -d --build`, seed test users, then `PLAYWRIGHT_BASE_URL=http://localhost npm test` from the frontend. Real backend data stays untouched.
- **Without Docker:** If `PLAYWRIGHT_BASE_URL` is not set, Playwright starts the auth and backend locally; the backend then uses local `backend/data` – suitable for local development only, not for isolated test runs.

CI always uses Docker (`.github/workflows/playwright-e2e-tests.yml`).
