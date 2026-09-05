const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

// UI regression fixtures; backend authorization is covered in test_dashboard_access.py.
(async () => {
  const browser = await chromium.launch();
  const artifacts = path.resolve('test-results/dashboard-access');
  fs.mkdirSync(artifacts, { recursive: true });
  const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
  try {
    for (const scenario of ['platform-admin', 'workspace-member', 'no-workspace']) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      const requests = [];
      const sockets = [];
      const exceptions = [];
      page.on('pageerror', error => exceptions.push(error.message));
      const workspace = { id: '11111111-1111-4111-8111-111111111111', name: 'Test Studio', role: 'OWNER' };
      const user = {
        id: 'test-user', email: 'dashboard@example.test', full_name: 'Dashboard Tester', is_active: true,
        is_staff: scenario === 'platform-admin', is_superuser: scenario === 'platform-admin',
        workspaces: scenario === 'workspace-member' ? [workspace] : [],
      };
      await page.addInitScript(() => {
        localStorage.setItem('authToken', 'dashboard-regression-token');
        localStorage.setItem('organizationId', 'stale-workspace');
      });
      await page.routeWebSocket(/\/ws\//, socket => {
        sockets.push(socket.url());
        socket.onMessage(message => {
          if (JSON.parse(message).type === 'ping') socket.send(JSON.stringify({ type: 'PONG' }));
        });
      });
      await page.route('**/api/v1/**', async route => {
        const url = new URL(route.request().url());
        requests.push({ path: url.pathname, org: route.request().headers()['x-organization-id'] });
        let json = {};
        if (url.pathname.endsWith('/auth/me/')) json = user;
        else if (url.pathname.endsWith('/admin/kpis/')) json = { total_users: 42 };
        else if (url.pathname.endsWith('/admin/analytics/')) json = { user_growth: [], revenue_growth: [], subscription_distribution: [], lead_analytics: { total_leads: 0, channel_breakdown: {} } };
        else if (url.pathname.endsWith('/admin/system/')) json = { recent_activity: [] };
        else if (url.pathname.endsWith('/analytics/dashboard/')) json = { leads: { total_leads: 0 }, bookings: {}, date_range: {}, leads_timeseries: [] };
        else if (url.pathname.includes('/subscriptions/')) json = { plan: { name: 'Free', lead_limit: 100 }, usage: { total_leads_count: 0 } };
        else if (url.pathname.endsWith('/organizations/current/')) json = workspace;
        else json = { results: [], count: 0 };
        await route.fulfill({ status: 200, json });
      });
      await page.goto(`${base}/app`);
      if (scenario === 'platform-admin') {
        await expect(page).toHaveURL(`${base}/admin`);
        await expect(page.getByRole('heading', { name: 'Super Admin Overview' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Back to App Workspace' })).toHaveCount(0);
        expect(requests.some(request => request.path === '/api/v1/analytics/dashboard/')).toBe(false);
        expect(sockets).toEqual([]);
        expect(await page.evaluate(() => localStorage.getItem('organizationId'))).toBe(null);
      } else if (scenario === 'workspace-member') {
        await expect(page.getByRole('heading', { name: /Good (morning|afternoon|evening)/ })).toBeVisible();
        await expect.poll(() => requests.some(request => request.path === '/api/v1/analytics/dashboard/')).toBe(true);
        expect(requests.find(request => request.path === '/api/v1/analytics/dashboard/').org).toBe(workspace.id);
        expect(await page.evaluate(() => localStorage.getItem('organizationId'))).toBe(workspace.id);
        await expect.poll(() => sockets.length).toBeGreaterThan(0);
        expect(sockets.every(url => new URL(url).searchParams.get('organization_id') === workspace.id)).toBe(true);
        await expect(page.getByText('Failed to load dashboard', { exact: true })).toHaveCount(0);
      } else {
        await expect(page.getByRole('heading', { name: 'Workspace access required' })).toBeVisible();
        expect(requests.map(request => request.path).every(path => path === '/api/v1/auth/me/')).toBe(true);
        expect(sockets).toEqual([]);
      }
      expect(exceptions).toEqual([]);
      await page.screenshot({ path: path.join(artifacts, `${scenario}.png`), fullPage: true });
      await page.close();
    }
    console.log('PASS: admin routing; workspace dashboard + WebSocket; stale workspace selection repaired; no-workspace access state; no unauthorized dashboard requests or socket loops.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
