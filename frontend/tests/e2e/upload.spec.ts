import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  grantLocationPermission,
  getTestImageBuffer,
  clickUploadPhotoButton,
} from './fixtures';

test.describe('Photo Upload', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await grantLocationPermission(page);
  });

  test('Admin: selecting file and starting upload leads to match page', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'e2e-turtle.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });

    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);

    await expect(page).toHaveURL(/\/admin\/turtle-match\/[^/]+/, { timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Turtle Match Review/ })).toBeVisible({
      timeout: 15_000,
    });
  });

  test('Upload shows progress (uploading or location)', async ({ page }) => {
    test.setTimeout(60_000);
    await loginAsAdmin(page);

    const fileInput = page.locator('input[type="file"]:not([capture])').first();
    await fileInput.setInputFiles({
      name: 'e2e-progress.png',
      mimeType: 'image/png',
      buffer: getTestImageBuffer(),
    });

    await page.waitForSelector('button:has-text("Upload Photo")', { timeout: 5000 });
    await clickUploadPhotoButton(page);

    // Either progress text appears or we navigate quickly to match page (fast CI/webkit)
    const progressOrLocation = page.getByText(/Getting location|Uploading/i);
    const matchUrl = /\/admin\/turtle-match\/[^/]+/;
    await Promise.race([
      progressOrLocation.waitFor({ state: 'visible', timeout: 8000 }),
      page.waitForURL(matchUrl, { timeout: 8000 }),
    ]);

    await expect(page).toHaveURL(matchUrl, { timeout: 30_000 });
  });
});
