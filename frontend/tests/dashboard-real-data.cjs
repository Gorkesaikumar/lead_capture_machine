const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

// Deliberately distinct test records; these never enter an application database.
const workspace = { id: '11111111-1111-4111-8111-111111111111', name: 'Test workspace', role: 'OWNER' };
function summary(total = 0) {
  return {
    leads: { total_leads: total, new_leads_today: total, converted_leads: 0, open_conversations: 0, lead_to_booking_conversion_rate: 0 },
    bookings: {}, date_range: {}, timezone: 'Asia/Kolkata', generated_at: new Date().toISOString(),
    channels: [
      { id: 'ig', name: 'Instagram Direct', type: 'instagram', status: 'TOKEN_EXPIRED', leadCount: 0 },
      { id: 'wa', name: 'WhatsApp Business', type: 'whatsapp', status: 'DISCONNECTED', leadCount: 0 },
      { id: 'web', name: 'Website Forms', type: 'website', status: 'ACTIVE', leadCount: total },
    ],
    recent_leads: total ? [{ id: 'recorded-lead', customer: { display_name: 'Saved Browser Customer', email: 'saved@example.test' }, source_channel: 'WEBSITE', summary: 'Saved inquiry text', created_at: new Date().toISOString() }] : [],
    activities: total ? [{ id: 'recorded-event', lead_id: 'recorded-lead', type: 'website', title: 'Lead Created', subtitle: 'Saved Browser Customer', created_at: new Date().toISOString() }] : [],
    leads_timeseries: [{ date: '2026-09-01', total, converted: 0, instagram: 0, whatsapp: 0, website: total, other: 0 }],
  };
}

(async () => {
  const browser = await chromium.launch();
  const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
  const artifacts = path.resolve('test-results/dashboard-real-data');
  fs.mkdirSync(artifacts, { recursive: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.clock.install();
    await page.addInitScript(() => localStorage.setItem('authToken', 'test-only-dashboard-token'));
    let socket, current = summary(), failure = false, requests = [];
    await page.routeWebSocket(/\/ws\//, ws => { socket = ws; ws.onMessage(() => {}); });
    await page.route('**/api/v1/**', async route => {
      const url = new URL(route.request().url());
      let json = { results: [], count: 0 };
      if (url.pathname.endsWith('/auth/me/')) json = { id: 'test-user', email: 'tester@example.test', full_name: 'Real Profile Name', is_active: true, is_staff: false, is_superuser: false, workspaces: [workspace] };
      if (url.pathname.endsWith('/analytics/dashboard/')) {
        requests.push(url.searchParams.get('preset'));
        if (failure) return route.fulfill({ status: 503, json: { detail: 'Database unavailable' } });
        json = current;
      }
      if (url.pathname.includes('/subscriptions/')) json = { plan: { name: 'Free', lead_limit: 10 }, usage: { total_leads_count: 0, usage_percentage: 0, leads_remaining: 10 } };
      await route.fulfill({ status: 200, json });
    });
    await page.goto(`${base}/app`);
    await expect(page.getByRole('heading', { name: /Real Profile Name/ })).toBeVisible();
    await expect(page.getByText('No leads in this period.', { exact: true })).toBeVisible();
    await expect(page.getByText('No recorded lead activity in this period.', { exact: true })).toBeVisible();
    await expect(page.getByText('token expired', { exact: true })).toBeVisible();
    await expect(page.getByText('disconnected', { exact: true })).toBeVisible();
    const kpi = title => page.getByText(title, { exact: true }).locator('..').getByRole('heading');
    await expect(kpi('Total Leads')).toHaveText('0');
    await expect(kpi('Open Conversations')).toHaveText('0');
    await expect(kpi('Conversion Rate')).toHaveText('0%');
    await expect(page.getByText(/Sarah Jenkins|Rohan Mehta|May 1 - May 31, 2025|7\.42%|24\.5%/)).toHaveCount(0);
    await page.screenshot({ path: path.join(artifacts, 'empty.png'), fullPage: true });

    current = summary(1);
    await expect.poll(() => !!socket).toBe(true);
    socket.send(JSON.stringify({ type: 'NEW_LEAD', payload: { customer_name: 'Saved Browser Customer' } }));
    await expect(kpi('Total Leads')).toHaveText('1');
    await expect(page.getByText('Saved inquiry text', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Lead Created', exact: true })).toHaveAttribute('href', '/app/leads/recorded-lead');
    await expect(kpi('Open Conversations')).toHaveText('0');
    await page.getByLabel('Dashboard date range').selectOption('7d');
    await expect.poll(() => requests.includes('7d')).toBe(true);
    const beforePoll = requests.length;
    current = summary(2);
    await page.clock.runFor(30_100);
    await expect.poll(() => requests.length).toBeGreaterThan(beforePoll);
    await expect(kpi('Total Leads')).toHaveText('2');
    await page.screenshot({ path: path.join(artifacts, 'records.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(artifacts, 'mobile.png'), fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

    // Test API Failure (503 Service Unavailable)
    failure = true;
    await page.getByLabel('Dashboard date range').selectOption('today');
    await page.clock.runFor(10_000);
    await expect(page.getByText('Failed to load dashboard', { exact: true })).toBeVisible();
    await expect(page.getByText('No leads in this period.', { exact: true })).toHaveCount(0);
    await expect(page.getByText('1,248', { exact: true })).toHaveCount(0);

    // Test recovery with production Django HTTP 200 response shape (without channels/recent_leads/activities)
    failure = false;
    current = {
      date_range: { preset: "this_month", start: "2026-09-01T00:00:00Z", end: "2026-09-30T23:59:59Z" },
      leads: {
        total_leads: 0, new_leads_today: 0, instagram_leads: 0, whatsapp_leads: 0, website_leads: 0,
        open_conversations: 0, qualified_leads: 0, booking_links_sent: 0, converted_leads: 0,
        lead_to_booking_conversion_rate: 0.0, status_new: 0, status_contacted: 0, status_qualified: 0, status_lost: 0,
      },
      bookings: {
        total_bookings: 0, bookings_today: 0, bookings_tomorrow: 0, upcoming_bookings: 0, completed_bookings: 0,
        cancelled_bookings: 0, confirmed_bookings: 0, pending_bookings: 0, no_show_bookings: 0,
      },
      lead_source_breakdown: [], popular_services: [], timeseries: [], leads_timeseries: [],
    };
    await page.getByRole('button', { name: 'Try Again' }).click();
    await page.clock.runFor(5_000);
    await expect(page.getByText('Failed to load dashboard', { exact: true })).toHaveCount(0);
    await expect(kpi('Total Leads')).toHaveText('0');
    await expect(kpi('Open Conversations')).toHaveText('0');
    await expect(kpi('Conversion Rate')).toHaveText('0%');

    // Test malformed response payload (causes retryable error)
    current = null;
    await page.getByLabel('Dashboard date range').selectOption('30d');
    await page.clock.runFor(5_000);
    await expect(page.getByText('Failed to load dashboard', { exact: true })).toBeVisible();

    expect(errors).toEqual([]);
    console.log('PASS: database zeros, production response contract, saved names/activity, channel errors, date selection, WebSocket refresh, 30-second polling, mobile layout, malformed payload, and honest API failure.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
