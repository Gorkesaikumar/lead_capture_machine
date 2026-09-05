const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch();
  const base = process.env.V4_PRIVACY_URL || 'http://localhost:5173';
  const built = process.env.V4_PRIVACY_STATIC === '1';
  const artifacts = path.resolve('test-results/privacy-policy');
  fs.mkdirSync(artifacts, { recursive: true });
  try {
    for (const scenario of ['desktop', 'mobile', 'expired-session', ...(built ? ['no-javascript'] : [])]) {
      const context = await browser.newContext({ viewport: scenario === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 }, javaScriptEnabled: scenario !== 'no-javascript' });
      const page = await context.newPage();
      const errors = [], privateRequests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      page.on('request', request => { if (/^\/(api|ws)\//.test(new URL(request.url()).pathname)) privateRequests.push(request.url()); });
      page.on('websocket', socket => { if (new URL(socket.url()).pathname.startsWith('/ws/')) privateRequests.push(socket.url()); });
      await page.route('https://fonts.googleapis.com/**', route => route.fulfill({ body: '', contentType: 'text/css' }));
      if (scenario === 'expired-session') {
        await page.addInitScript(() => { localStorage.setItem('authToken', 'expired-test-token'); localStorage.setItem('organizationId', 'old-workspace'); });
        await page.route('**/api/v1/**', route => route.fulfill({ status: 401, json: { detail: 'Expired' } }));
      }
      const response = await page.goto(`${base}/privacy-policy`);
      expect(response.status()).toBe(200);
      await expect(page).toHaveURL(`${base}/privacy-policy`);
      await expect(page).toHaveTitle('Privacy Policy | Nextora Lead Capture Machine');
      await expect(page.getByRole('heading', { name: 'Privacy Policy', exact: true })).toBeVisible();
      await expect(page.locator('article section')).toHaveCount(17);
      await expect(page.getByText('instagram_business_basic', { exact: false }).last()).toBeVisible();
      expect(await page.locator('article').innerText()).toContain('instagram_business_manage_messages');
      expect(await page.locator('article').innerText()).toContain('does not request or store your Instagram password');
      await expect(page.locator('#contact a')).toHaveAttribute('href', 'mailto:support@nextoracreations.co.in');
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', 'https://studio.nextoracreations.co.in/privacy-policy');
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(page.locator('img')).toHaveJSProperty('complete', true);
      expect(await page.locator('img').evaluate(img => img.naturalWidth)).toBeGreaterThan(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const broken = await page.locator('a[href^="#"]').evaluateAll(links => links.map(a => a.getAttribute('href')).filter(href => href === '#' || !document.getElementById(href.slice(1))));
      expect(broken).toEqual([]);
      const unknownLinks = await page.locator('a').evaluateAll(links => links.map(a => a.getAttribute('href')).filter(href => !href.startsWith('#') && !href.startsWith('mailto:') && href !== '/'));
      expect(unknownLinks).toEqual([]);
      await page.getByRole('navigation', { name: 'Table of contents' }).getByRole('link', { name: /Contact$/ }).click();
      await expect(page.locator('#contact')).toBeInViewport();
      const refresh = await page.reload();
      expect(refresh.status()).toBe(200);
      await expect(page.getByRole('heading', { name: 'Privacy Policy', exact: true })).toBeVisible();
      expect(privateRequests).toEqual([]);
      expect(errors).toEqual([]);
      await page.goto(`${base}/privacy-policy`);
      await page.screenshot({ path: path.join(artifacts, `${built ? 'nginx' : 'vite'}-${scenario}.png`) });
      await page.locator('#contact').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(artifacts, `${built ? 'nginx' : 'vite'}-${scenario}-contact.png`) });
      if (scenario === 'desktop') {
        await page.getByRole('link', { name: /Back to home/ }).click();
        await expect(page).toHaveURL(`${base}/`);
        await expect(page).toHaveTitle('Nextora Lead Capture Machine | Capture Leads From Instagram, WhatsApp & Website');
        await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
        await page.getByRole('link', { name: 'Privacy Policy', exact: true }).click();
        await expect(page).toHaveURL(`${base}/privacy-policy`);
        await expect(page.getByRole('heading', { name: 'Privacy Policy', exact: true })).toBeVisible();
      }
      await context.close();
    }
    if (built) {
      const response = await fetch(`${base}/privacy-policy`);
      const html = await response.text();
      expect(html).toContain('<h1');
      expect(html).toContain('instagram_business_manage_messages');
      expect(html).toContain('support@nextoracreations.co.in');
      expect(html).not.toMatch(/rzp_(test|live)_[A-Za-z0-9]+|EAAG[A-Za-z0-9]{20,}|TODO/);
      expect(html).toContain('og:title');
      expect((await fetch(`${base}/privacy-policy/`)).status).toBe(200);
    }
    console.log(`PASS ${built ? 'built Nginx' : 'Vite'}: direct public access, desktop/mobile, refresh, stale token isolation, content, metadata, navigation, no auth calls or console errors${built ? ', complete HTML without JavaScript' : ''}.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
