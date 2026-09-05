const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

// Run against the local Vite + Django servers: node tests/login-errors.cjs
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, colorScheme: 'dark' });
  const artifacts = path.resolve('test-results/login-errors');
  fs.mkdirSync(artifacts, { recursive: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const endpoint = '**/api/v1/auth/login/';
  const submit = () => page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const alert = page.getByRole('alert');
  const checkContrast = async locator => {
    const contrast = await locator.evaluate(element => {
      const style = getComputedStyle(element);
      const luminance = color => {
        const [r, g, b] = color.match(/[\d.]+/g).slice(0, 3).map(value => {
          const channel = Number(value) / 255;
          return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => b - a);
      return (values[0] + 0.05) / (values[1] + 0.05);
    });
    expect(contrast).toBeGreaterThanOrEqual(4.5);
  };
  try {
    await page.goto(process.env.V4_LOGIN_URL || 'http://localhost:5173/login');
    await page.getByLabel('Email', { exact: true }).fill('login-check@example.invalid');
    await page.getByLabel('Password', { exact: true }).fill('dummy-password-only');
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/auth/login/'));
    await submit();
    const response = await responsePromise;
    expect(response.status()).toBe(401);
    expect((await response.json()).code).toBe('invalid_credentials');
    await expect(alert).toHaveText('Invalid email or password.');
    await checkContrast(alert);
    await page.screenshot({ path: path.join(artifacts, 'invalid-credentials.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(alert).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: path.join(artifacts, 'invalid-credentials-mobile.png') });

    for (const [status, body, message] of [
      [502, '', 'Sign-in service is temporarily unavailable. Please try again shortly.'],
      [500, { message: 'Internal error' }, 'Sign-in service is temporarily unavailable. Please try again shortly.'],
      [429, { message: 'Too many requests. Please wait 60 seconds before retrying.' }, 'Too many requests. Please wait 60 seconds before retrying.'],
      [401, { message: 'Authentication is required. Please log in.' }, 'Invalid email or password.'],
      [200, {}, 'Unable to complete sign in. Please try again.'],
    ]) {
      await page.route(endpoint, route => route.fulfill({ status, contentType: 'application/json', body: typeof body === 'string' ? body : JSON.stringify(body) }));
      await submit();
      await expect(alert).toHaveText(message);
      await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeEnabled();
      await page.unroute(endpoint);
    }
    await page.route(endpoint, route => route.abort('connectionfailed'));
    await submit();
    await expect(alert).toHaveText('Unable to connect. Please check your internet connection and try again.');
    await page.unroute(endpoint);

    // Exercise the shared toaster under both OS themes to catch mixed foreground/background colors.
    const toasterSource = await (await page.request.get(new URL('/src/components/ui/sonner.tsx', page.url()).href)).text();
    const sonnerModule = toasterSource.match(/from "([^"]*\/sonner\.js[^\"]*)"/)[1];
    for (const colorScheme of ['dark', 'light']) {
      await page.emulateMedia({ colorScheme });
      await page.evaluate(async ({ moduleUrl, colorScheme }) => {
        const { toast } = await import(moduleUrl);
        toast.error('Visible error notification', { id: `contrast-check-${colorScheme}`, duration: Infinity });
      }, { moduleUrl: sonnerModule, colorScheme });
      const toast = page.locator('[data-sonner-toast][data-type="error"]');
      await expect(toast).toBeVisible();
      await checkContrast(toast);
      await expect.poll(() => toast.evaluate(element => element.getBoundingClientRect().bottom <= innerHeight)).toBe(true);
      await page.screenshot({ path: path.join(artifacts, `toast-${colorScheme}.png`) });
      await toast.getByRole('button', { name: 'Close toast' }).click();
      await expect(toast).toHaveCount(0);
    }
    expect(errors).toEqual([]);
    console.log('PASS: live invalid credentials; 401/429/500/502/network/malformed success; retry; mobile layout; alert + toast contrast in dark/light OS themes.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
