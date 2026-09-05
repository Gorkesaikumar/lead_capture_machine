const { chromium, expect } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
  try {
    for (const [routeName, failed] of [['revenue', false], ['system', false], ['revenue', true], ['system', true], ['users', true], ['subscriptions', true], ['audit-logs', true]]) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => localStorage.setItem('authToken', 'admin-data-test-token'));
      await page.route('**/api/v1/**', async route => {
        const url = new URL(route.request().url());
        if (url.pathname.endsWith('/auth/me/')) return route.fulfill({ json: { id: 'test-admin', email: 'admin@example.test', full_name: 'Test Admin', is_active: true, is_staff: true, is_superuser: true, workspaces: [] } });
        if (failed) return route.fulfill({ status: 503, json: { detail: 'Test service unavailable' } });
        const totals = { INR: '399.00', USD: '5.00' };
        await route.fulfill({ json: routeName === 'revenue' ? {
          summary: { by_currency: { total: totals, today: totals, month: totals, starter: {}, creator: {}, enterprise: {} } },
          ledger: [{ id: 'saved-payment', transaction_id: 'recorded-payment', organization_name: 'Saved workspace', plan_name: 'Starter', amount: '399.00', currency: 'INR', payment_provider: 'Recorded gateway', status: 'success', created_at: new Date().toISOString() }],
        } : { total_users: 3, active_users: 2, suspended_users: 1, total_workspaces: 2, total_leads_captured: 0, recent_activity: [] } });
      });
      await page.goto(`${base}/admin/${routeName}`);
      if (failed) {
        await expect(page.getByText(/Unable to load/)).toBeVisible({ timeout: 15_000 });
        await expect(page.getByText(/No payments recorded|PostgreSQL & Redis Healthy/)).toHaveCount(0);
      } else if (routeName === 'revenue') {
        await expect(page.getByText('INR 399.00 / USD 5.00', { exact: true })).toHaveCount(3);
        await expect(page.getByRole('cell', { name: 'INR 399.00', exact: true })).toBeVisible();
        await expect(page.getByText('$399.00', { exact: true })).toHaveCount(0);
      } else {
        await expect(page.getByText('Not monitored', { exact: true })).toBeVisible();
        await expect(page.getByText('Operational', { exact: true })).toHaveCount(0);
      }
      expect(errors).toEqual([]);
      await page.close();
    }
    console.log('PASS: separate INR/USD revenue, correct ledger currency, honest infrastructure status, and error states across admin data screens.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
