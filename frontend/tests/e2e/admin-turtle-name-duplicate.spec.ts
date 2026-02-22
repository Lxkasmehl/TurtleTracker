import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  grantLocationPermission,
  getTestImageBuffer,
  clickUploadPhotoButton,
} from './fixtures';

/**
 * E2E tests: duplicate turtle name validation in the Create New Turtle form.
 * The WebApp must not allow a new turtle name that already exists in the Master
 * Google Spreadsheet (across any location sheet).
 */

const MOCK_EXISTING_NAMES = [
  { name: 'Master Oogway', primary_id: 'K001' },
  { name: "Leonardo", primary_id: 'T042' },
];

test.describe('Admin Create New Turtle – duplicate name validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await grantLocationPermission(page);
  });

  test('Duplicate turtle name shows error and blocks submit', async ({ page }) => {
    test.setTimeout(60_000);

    // Mock turtle-names so the form sees "Master Oogway" as already existing
    await page.route('**/api/sheets/turtle-names', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          names: MOCK_EXISTING_NAMES,
        }),
      });
    });

    // Mock list sheets so the Create New Turtle form has a sheet to select
    await page.route('**/api/sheets/sheets**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ sheets: ['Kansas'], success: true }),
        });
      } else {
        await route.continue();
      }
    });

    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'duplicate-name-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Turtle Match Review/ })).toBeVisible({
      timeout: 15_000,
    });

    const createBtn = page.getByRole('button', { name: 'Create New Turtle' });
    await expect(createBtn).toBeVisible({ timeout: 15_000 });
    // Wait for turtle-names request that fires when the form mounts (before we click)
    const turtleNamesResponse = page.waitForResponse(
      (resp) => resp.url().includes('turtle-names') && resp.status() === 200,
      { timeout: 15_000 },
    );
    await createBtn.click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Create New Turtle' })).toBeVisible();
    await turtleNamesResponse;

    // Select a sheet so name validation can run (form requires sheet for submit)
    const sheetSelect = dialog.getByRole('textbox', { name: 'Sheet / Location' });
    await sheetSelect.click();
    await page.getByRole('option', { name: 'Kansas' }).click();

    // Fill Name with an existing name (case-insensitive match)
    const nameInput = dialog.getByLabel('Name', { exact: true });
    await nameInput.fill('Master Oogway');
    await nameInput.blur();

    // Form validates on blur: duplicate name must show error
    await expect(dialog.getByText('This name is already used by another turtle')).toBeVisible({
      timeout: 5000,
    });

    // Submit should be blocked by validation and show notification
    await dialog.getByRole('button', { name: 'Create Turtle Data' }).click();
    await expect(page.getByText('Please fix the errors in the form')).toBeVisible({
      timeout: 5000,
    });
    await expect(dialog).toBeVisible();
  });

  test('Duplicate name (different casing) is still rejected', async ({ page }) => {
    test.setTimeout(60_000);

    await page.route('**/api/sheets/turtle-names', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          names: MOCK_EXISTING_NAMES,
        }),
      });
    });
    await page.route('**/api/sheets/sheets**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ sheets: ['Kansas'], success: true }),
        });
      } else {
        await route.continue();
      }
    });

    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'duplicate-casing-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });

    const turtleNamesResponse = page.waitForResponse(
      (resp) => resp.url().includes('turtle-names') && resp.status() === 200,
      { timeout: 15_000 },
    );
    await page.getByRole('button', { name: 'Create New Turtle' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await turtleNamesResponse;

    const sheetSelect = dialog.getByRole('textbox', { name: 'Sheet / Location' });
    await sheetSelect.click();
    await page.getByRole('option', { name: 'Kansas' }).click();

    // Different casing than stored "Leonardo" – should still be treated as duplicate
    const nameInput = dialog.getByLabel('Name', { exact: true });
    await nameInput.fill('leonardo');
    await nameInput.blur();

    await expect(dialog.getByText('This name is already used by another turtle')).toBeVisible({
      timeout: 5000,
    });
  });

  test('Unique name does not show duplicate error', async ({ page }) => {
    test.setTimeout(60_000);

    await page.route('**/api/sheets/turtle-names', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          names: MOCK_EXISTING_NAMES,
        }),
      });
    });
    await page.route('**/api/sheets/sheets**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ sheets: ['Kansas'], success: true }),
        });
      } else {
        await route.continue();
      }
    });

    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'unique-name-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });

    await page.getByRole('button', { name: 'Create New Turtle' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const sheetSelect = dialog.getByRole('textbox', { name: 'Sheet / Location' });
    await sheetSelect.click();
    await page.getByRole('option', { name: 'Kansas' }).click();

    const nameInput = dialog.getByLabel('Name', { exact: true });
    await nameInput.fill('E2E Unique Turtle Name 999');
    await nameInput.dispatchEvent('blur');

    // No duplicate error should appear
    await expect(dialog.getByText('This name is already used by another turtle')).not.toBeVisible();
  });
});
