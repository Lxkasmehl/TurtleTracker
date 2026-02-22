import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsCommunity, navClick, openMobileMenu } from './fixtures';

test.describe('Admin Turtle Records (Review Queue)', () => {
  test('Admin sees Turtle Records in nav', async ({ page }) => {
    await loginAsAdmin(page);
    await openMobileMenu(page);
    await expect(page.getByRole('button', { name: 'Turtle Records' })).toBeVisible();
  });

  test('Community does not see Turtle Records', async ({ page }) => {
    await loginAsCommunity(page);
    await openMobileMenu(page);
    await expect(page.getByRole('button', { name: 'Turtle Records' })).not.toBeVisible();
  });

  test('Turtle Records opens Review Queue', async ({ page }) => {
    await loginAsAdmin(page);
    await navClick(page, 'Turtle Records');
    await expect(page).toHaveURL('/admin/turtle-records');
    await expect(page.getByRole('tab', { name: /Review Queue/ })).toBeVisible();
  });

  test('Empty queue: "No pending reviews" or Pending badge visible', async ({ page }) => {
    await page.route('**/api/review-queue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, items: [] }),
      });
    });

    await loginAsAdmin(page);
    await navClick(page, 'Turtle Records');

    const emptyOrBadge = page
      .getByText('No pending reviews')
      .or(page.locator('text=/\\d+ Pending/i'));
    await expect(emptyOrBadge).toBeVisible({ timeout: 5000 });
  });

  test('Review button opens modal when entries exist', async ({ page }) => {
    await loginAsAdmin(page);
    await navClick(page, 'Turtle Records');
    await expect(page.getByRole('tab', { name: /Review Queue/ })).toBeVisible();

    const tabPanel = page.getByRole('tabpanel', { name: /Review Queue/ });
    const hasItems = await tabPanel.getByText(/\d+ matches/).count() > 0;
    if (hasItems) {
      await tabPanel.getByText(/\d+ matches/).first().click();
      await expect(page.getByRole('button', { name: /Back to list/ })).toBeVisible();
      await expect(page.getByText('Uploaded Photo')).toBeVisible();
    } else {
      await expect(page.getByText('No pending reviews')).toBeVisible();
    }
  });
});
