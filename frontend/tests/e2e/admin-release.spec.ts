import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsCommunity, navClick, openMobileMenu } from './fixtures';

test.describe('Admin Release (Digital Flags)', () => {
  test('Admin sees Release in nav', async ({ page }) => {
    await loginAsAdmin(page);
    await openMobileMenu(page);
    await expect(page.getByRole('button', { name: 'Release' })).toBeVisible();
  });

  test('Community does not see Release', async ({ page }) => {
    await loginAsCommunity(page);
    await openMobileMenu(page);
    await expect(page.getByRole('button', { name: 'Release' })).not.toBeVisible();
  });

  test('Release page shows title and empty state when no flags', async ({ page }) => {
    await loginAsAdmin(page);
    await navClick(page, 'Release');
    await expect(page).toHaveURL('/admin/release');
    await expect(
      page.getByRole('heading', { name: /Release – Digital Flags/i }),
    ).toBeVisible();
    await expect(
      page.getByText('No turtles with flag data yet', { exact: false }),
    ).toBeVisible({ timeout: 5000 });
  });

  test('Community cannot access release page', async ({ page }) => {
    await loginAsCommunity(page);
    await page.goto('/admin/release');
    await expect(page).toHaveURL('/');
  });
});
