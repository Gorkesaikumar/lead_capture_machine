const { chromium, expect } = require('@playwright/test');

// Local browser tests with synthetic API responses; never use real credentials.
(async () => {
  const browser = await chromium.launch();
  const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
  const page = await browser.newPage();
  const user = { id: 'test-admin', email: 'admin@example.test', is_active: true, is_staff: true, is_superuser: true, workspaces: [] };
  let loginResponse = { status: 405, contentType: 'text/html', body: '<h1>405 Not Allowed</h1>' };
  let meResponse = { status: 200, json: user };
  let loginRequest;
  let meAuthorization;
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === '/api/v1/auth/login/') {
      loginRequest = { method: request.method(), body: request.postDataJSON() };
      if (loginResponse.abort) return route.abort('connectionfailed');
      return route.fulfill(loginResponse);
    }
    if (path === '/api/v1/auth/me/') {
      meAuthorization = request.headers().authorization;
      return route.fulfill(meResponse);
    }
    return route.fulfill({ json: {} });
  });
  const submit = async () => {
    await page.locator('input[type=email]').fill('admin@example.test');
    await page.locator('input[type=password]').fill('SyntheticPassword9!');
    await page.getByRole('button', { name: 'Sign In to Admin Panel' }).click();
  };
  try {
    await page.goto(`${base}/admin/login`);
    await submit();
    await expect(page.getByText('Authentication endpoint is unavailable.', { exact: true })).toBeVisible();
    expect(loginRequest).toEqual({ method: 'POST', body: { email: 'admin@example.test', password: 'SyntheticPassword9!' } });
    console.log('PASS: HTML 405 is an endpoint error, with correct login URL and payload.');
    for (const [status, message] of [
      [400, 'Please check your email and password.'],
      [401, 'Invalid email or password.'],
      [403, 'You do not have administrator access.'],
      [404, 'Authentication endpoint is unavailable.'],
      [429, 'Too many sign-in attempts. Please wait a minute and try again.'],
      [500, 'Authentication service is temporarily unavailable.'],
      [502, 'Authentication service is temporarily unavailable.'],
    ]) {
      loginResponse = { status, json: { message: 'PRIVATE INTERNAL ERROR DETAILS' } };
      await submit();
      await expect(page.getByRole('alert').locator('span').last()).toHaveText(message);
      await expect(page.getByText('PRIVATE INTERNAL ERROR DETAILS')).toHaveCount(0);
    }
    loginResponse = { abort: true };
    await submit();
    await expect(page.getByRole('alert').locator('span').last()).toHaveText('Unable to connect to the server.');
    loginResponse = { status: 200, contentType: 'text/html', body: '<html>SPA fallback</html>' };
    await submit();
    await expect(page.getByRole('alert').locator('span').last()).toHaveText('Authentication service returned an invalid response.');
    loginResponse = { json: { status: 'success', data: { token: 'synthetic-test-token', user } } };
    meResponse = { status: 200, contentType: 'text/html', body: '<html>SPA fallback</html>' };
    await submit();
    await expect(page.getByRole('alert').locator('span').last()).toHaveText('Unable to verify your session. Please try again.');
    expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBeNull();
    meResponse = { status: 503, json: {} };
    await submit();
    await expect(page.getByRole('alert').locator('span').last()).toHaveText('Unable to verify your session. Please try again.');
    expect(new URL(page.url()).pathname).toBe('/admin/login');
    meResponse = { json: user };
    await submit();
    await expect(page).toHaveURL(`${base}/admin`);
    expect(meAuthorization).toBe('Token synthetic-test-token');
    expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBe('synthetic-test-token');
    await expect(page.getByText('Total Registered Users', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText('Total Registered Users', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Logout Admin' }).click();
    await expect(page).toHaveURL(`${base}/admin/login`);
    expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBeNull();
    await submit();
    await expect(page).toHaveURL(`${base}/admin`);
    meResponse = { json: { ...user, is_staff: false, is_superuser: false } };
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Access Denied' })).toBeVisible();
    await page.evaluate(() => localStorage.clear());
    await page.goto(`${base}/admin`);
    await expect(page).toHaveURL(`${base}/admin/login`);
    console.log('PASS: safe errors; invalid profile rejected; token storage/header; dashboard; session refresh; regular/anonymous access denied.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });

