import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  loginAsCommunity,
  grantLocationPermission,
  getTestImageBuffer,
  clickUploadPhotoButton,
} from './fixtures';

test.describe('Admin Turtle Match', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await grantLocationPermission(page);
  });

  test('After upload: match page shows header and Back button', async ({ page }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'match-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);

    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Turtle Match Review/ })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole('button', { name: 'Back' })).toBeVisible();
  });

  test('Back button navigates to home', async ({ page }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'back-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });

    await expect(page.getByRole('heading', { name: /Turtle Match Review/ })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole('button', { name: 'Back' }).click();
    await expect(page).toHaveURL('/');
  });

  test('Create New Turtle opens modal with form', async ({ page }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'new-turtle-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });

    const createBtn = page.getByRole('button', { name: 'Create New Turtle' });
    await expect(createBtn).toBeVisible({ timeout: 15_000 });
    await createBtn.click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Create New Turtle' })).toBeVisible();
    await expect(page.getByRole('dialog').getByRole('textbox', { name: 'Sheet / Location' })).toBeVisible();
  });

  test('Match page shows Additional photos (microhabitat / condition) section and add buttons', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'microhabitat-e2e.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });
    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);
    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Turtle Match Review/ })).toBeVisible({
      timeout: 15_000,
    });

    // When there are 0 matches, the section lives in the Create New Turtle modal; when there are matches, it's in the right column after selecting one. Open the modal so the section is visible regardless of match count.
    await page.getByRole('button', { name: 'Create New Turtle' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await expect(
      dialog.getByText('Additional photos (microhabitat / condition)', { exact: false }),
    ).toBeVisible();
    // Add controls are <Button component="label"> (render as <label>), so target by visible text
    await expect(dialog.getByText('Microhabitat', { exact: true })).toBeVisible();
    await expect(dialog.getByText('Condition', { exact: true })).toBeVisible();
  });

  test('Community cannot access match page', async ({ page }) => {
    await loginAsCommunity(page);
    await page.goto('/admin/turtle-match/any-id');
    await expect(page).toHaveURL('/');
  });
});
