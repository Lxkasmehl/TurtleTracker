import { test, expect } from '@playwright/test';
import {
  loginAsAdmin,
  loginAsStaff,
  loginAsCommunity,
  navClick,
  openMobileMenu,
} from './fixtures';

test.describe('Staff role and User Management', () => {
  test('Staff sees Turtle Records and Release in nav but not User Management', async ({
    page,
  }) => {
    await loginAsStaff(page);
    await openMobileMenu(page);
    await expect(page.getByRole('button', { name: 'Turtle Records' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Release' })).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'User Management' }),
    ).not.toBeVisible();
  });

  test('Staff can access Turtle Records and Release pages', async ({ page }) => {
    await loginAsStaff(page);
    await navClick(page, 'Turtle Records');
    await expect(page).toHaveURL(/\/admin\/turtle-records/);
    await navClick(page, 'Release');
    await expect(page).toHaveURL('/admin/release');
  });

  test('Staff is redirected from User Management to home', async ({ page }) => {
    await loginAsStaff(page);
    await page.goto('/admin/users');
    await expect(page).toHaveURL('/');
  });

  test('Admin sees User Management in nav and can open it', async ({ page }) => {
    await loginAsAdmin(page);
    await openMobileMenu(page);
    await expect(
      page.getByRole('button', { name: 'User Management' }),
    ).toBeVisible();
    await navClick(page, 'User Management');
    await expect(page).toHaveURL('/admin/users');
    await expect(
      page.getByRole('heading', { name: 'User Management' }),
    ).toBeVisible();
  });

  test('Admin can change a user role via User Management', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/users');
    await expect(page).toHaveURL('/admin/users');
    await expect(
      page.getByRole('heading', { name: /All users by role/i }),
    ).toBeVisible();
    const communityEmail =
      process.env.E2E_COMMUNITY_EMAIL ?? 'community@test.com';
    const row = page.locator('table tbody tr').filter({ hasText: communityEmail });
    await expect(row).toBeVisible({ timeout: 10000 });

    // Mantine Select: open dropdown (input or combobox in that row), then pick Staff
    const roleTrigger = row.getByRole('combobox').or(row.locator('input')).first();
    await roleTrigger.click();
    await page.getByRole('option', { name: 'Staff' }).click();

    await expect(
      page.getByText('Role updated', { exact: false }),
    ).toBeVisible({ timeout: 5000 });
    // User moved to Staff section: row with community email still visible (now under Staff)
    await expect(row).toBeVisible();
  });
});
