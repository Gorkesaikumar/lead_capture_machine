const { chromium, expect } = require('@playwright/test');

// Entire API and Meta navigation/SDK are mocked. No provider/account changes.
(async () => {
  const browser = await chromium.launch();
  const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
  const callback = 'https://studio.nextoracreations.co.in/api/v1/integrations/oauth/instagram/callback/';
  const authorization = 'https://www.instagram.com/oauth/authorize?redirect_uri=' + encodeURIComponent(callback) + '&state=synthetic-state';
  const workspace = { id: '11111111-1111-4111-8111-111111111111', name: 'Synthetic workspace', role: 'OWNER' };
  const context = await browser.newContext();
  await context.addInitScript(() => {
    localStorage.setItem('authToken', 'synthetic-browser-token');
    window.FB = {
      init: config => { window.syntheticInit = config; },
      login: (callback, options) => {
        window.syntheticSignupOptions = options;
        callback({ authResponse: { code: 'synthetic-code' } });
        window.dispatchEvent(new MessageEvent('message', {
          origin: 'https://www.facebook.com', source: window,
          data: { type: 'WA_EMBEDDED_SIGNUP', event: 'FINISH', data: { waba_id: '123', phone_number_id: '456' } },
        }));
      },
    };
  });
  const requests = [];
  let completion;
  let authUrl = authorization;
  let connected = false;
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname === 'www.instagram.com') return route.fulfill({ contentType: 'text/html', body: 'Mock Meta authorization' });
    if (url.origin !== new URL(base).origin) return route.abort();
    if (!url.pathname.startsWith('/api/v1/')) return route.continue();
    requests.push(url.pathname);
    let json = { results: [], count: 0 };
    if (url.pathname.endsWith('/auth/me/')) json = { id: 'synthetic-user', email: 'owner@example.test', is_active: true, is_staff: false, is_superuser: false, workspaces: [workspace] };
    if (url.pathname.endsWith('/organizations/current/')) json = workspace;
    if (url.pathname.includes('/subscriptions/')) json = { plan: { name: 'Starter', lead_limit: 100 }, usage: { total_leads_count: 0 } };
    if (url.pathname.endsWith('/integrations/status/')) json = {
      instagram: { connection_status: 'DISCONNECTED', webhook_status: 'UNKNOWN' },
      whatsapp: { connection_status: connected ? 'CONNECTED' : 'DISCONNECTED', webhook_status: connected ? 'ACTIVE' : 'UNKNOWN' },
    };
    if (url.pathname.endsWith('/integrations/oauth/instagram/login/')) json = { url: authUrl };
    if (url.pathname.endsWith('/integrations/whatsapp/connect/')) json = { app_id: 'synthetic-app', config_id: 'synthetic-config', graph_version: 'v25.0', state: 'synthetic-state' };
    if (url.pathname.endsWith('/integrations/whatsapp/complete/')) {
      completion = request.postDataJSON(); connected = true; json = { status: 'connected', provider: 'whatsapp' };
    }
    return route.fulfill({ json });
  });
  const page = await context.newPage();
  await page.routeWebSocket(/\/ws\//, () => {});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base + '/app/settings/channels');
    await page.getByRole('button', { name: 'Connect Instagram', exact: true }).click();
    await expect(page).toHaveURL(authorization);
    expect(requests).toContain('/api/v1/integrations/oauth/instagram/login/');
    expect(requests).not.toContain('/api/v1/integrations/instagram/connect/');
    expect(new URL(page.url()).searchParams.get('redirect_uri')).toBe(callback);
    await page.goto(base + '/app/settings/channels');
    authUrl = 'https://www.instagram.com/synthetic-profile';
    await page.getByRole('button', { name: 'Connect Instagram', exact: true }).click();
    await expect(page.getByText('Invalid Meta authorization URL.', { exact: true })).toBeVisible();
    await expect(page).toHaveURL(base + '/app/settings/channels');
    await page.getByRole('button', { name: 'Connect WhatsApp', exact: true }).click();
    await page.getByRole('button', { name: 'Continue with Meta', exact: true }).click();
    await expect.poll(() => completion).toEqual({ code: 'synthetic-code', state: 'synthetic-state', waba_id: '123', phone_number_id: '456' });
    expect(await page.evaluate(() => window.syntheticSignupOptions.response_type)).toBe('code');
    expect(await page.evaluate(() => window.syntheticSignupOptions.config_id)).toBe('synthetic-config');
    expect(requests.some(path => path.includes('oauth/whatsapp/callback'))).toBe(false);
    await expect(page).toHaveURL(base + '/app/settings/channels');
    expect(errors).toEqual([]);
    console.log('PASS: canonical Instagram start + exact production callback; profile URL rejected; WhatsApp SDK Embedded Signup + authenticated completion preserved; no live Meta calls.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
