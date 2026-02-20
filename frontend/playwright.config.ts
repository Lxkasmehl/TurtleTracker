import { defineConfig, devices } from '@playwright/test';

/** When set (e.g. in CI with Docker), frontend is already running at this URL; no dev server is started. */
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Skip instructions modal by pre-setting localStorage */
    storageState: {
      cookies: [],
      origins: [
        {
          origin: baseURL,
          localStorage: [
            {
              name: 'hasSeenInstructions',
              value: 'true',
            },
          ],
        },
      ],
    },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* Run your local dev server before starting the tests (skipped when PLAYWRIGHT_BASE_URL is set, e.g. Docker CI) */
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : [
    // Start auth backend first (with test user seeding)
    {
      command:
        process.platform === 'win32'
          ? 'cd ..\\auth-backend && npm run test:dev'
          : 'cd ../auth-backend && npm run test:dev',
      url: 'http://localhost:3001/api/health',
      reuseExistingServer: true, // Reuse existing server in CI (started by workflow) and locally
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...process.env,
        // Test user credentials
        E2E_ADMIN_EMAIL: process.env.E2E_ADMIN_EMAIL || 'admin@test.com',
        E2E_ADMIN_PASSWORD: process.env.E2E_ADMIN_PASSWORD || 'testpassword123',
        E2E_COMMUNITY_EMAIL: process.env.E2E_COMMUNITY_EMAIL || 'community@test.com',
        E2E_COMMUNITY_PASSWORD: process.env.E2E_COMMUNITY_PASSWORD || 'testpassword123',
        // Auth backend configuration (with defaults for testing)
        PORT: process.env.AUTH_PORT || '3001',
        NODE_ENV: process.env.NODE_ENV || 'test',
        JWT_SECRET: process.env.JWT_SECRET || 'test-jwt-secret-key-for-e2e-tests-only',
        SESSION_SECRET:
          process.env.SESSION_SECRET || 'test-session-secret-key-for-e2e-tests-only',
        FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:5173',
      },
    },
    // Start Flask backend (turtle API server)
    {
      command:
        process.platform === 'win32'
          ? 'cd ..\\backend && python app.py'
          : 'cd ../backend && python3 app.py',
      // Use 127.0.0.1 instead of localhost for more reliable connection
      // Try health endpoint first, fallback to root if needed
      url: 'http://127.0.0.1:5000/api/health',
      reuseExistingServer: true, // Reuse existing server in CI (started by workflow) and locally
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
      // Health check settings - Playwright will poll this URL until it gets 200
      // Make sure the endpoint responds quickly
      env: {
        ...process.env,
        // JWT_SECRET must match auth-backend for token verification
        JWT_SECRET: process.env.JWT_SECRET || 'test-jwt-secret-key-for-e2e-tests-only',
        PORT: process.env.BACKEND_PORT || '5000',
        // Disable Flask debug mode for tests to avoid reload issues
        FLASK_DEBUG: 'false',
        // Force Python to output immediately (unbuffered)
        PYTHONUNBUFFERED: '1',
      },
    },
    // Start frontend dev server last (after backends are ready)
    // Vite should start quickly, but we need to ensure it's fully ready
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true, // Reuse existing server in CI and locally
      timeout: 180 * 1000, // Increased timeout for Vite startup
      stdout: 'pipe',
      stderr: 'pipe',
      // Vite typically starts quickly, but may need more time on first run
      // The URL check ensures Vite is serving the app before tests start
    },
  ],
});
