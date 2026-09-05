const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', dialog => dialog.accept());
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    const response = await route.fetch({ url: process.env.V4_BACKEND_URL + url.pathname + url.search });
    await route.fulfill({ response });
  });
  await page.addInitScript(({ token, org, signature }) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('organizationId', org);
    // External checkout is simulated only in this test; real DRF verifies mocked capture.
    window.Razorpay = class {
      constructor(options) { this.options = options; }
      on() {}
      open() {
        window.testCheckoutSubscription = this.options.subscription_id;
        this.options.handler({ razorpay_subscription_id: this.options.subscription_id, razorpay_payment_id: 'pay_browser', razorpay_signature: signature });
      }
    };
  }, { token: process.env.V4_TEST_TOKEN, org: process.env.V4_TEST_ORG, signature: process.env.V4_PAYMENT_SIGNATURE });
  try {
    await page.goto('http://127.0.0.1:5178/app/automations');
    await expect(page.getByRole('status').filter({ hasText: 'Starter supports DM Automation' })).toBeVisible();
    await page.getByRole('link', { name: 'View plans', exact: true }).click();
    const addon = page.getByRole('region', { name: 'DM Automation add-on' });
    await expect(addon.getByText('₹799/month', { exact: true })).toBeVisible();
    await addon.getByRole('button', { name: 'Activate DM Automation — ₹399' }).click();
    await expect(addon.getByText('Add-on active until', { exact: false })).toBeVisible();
    expect(await page.evaluate(() => window.testCheckoutSubscription)).toBe('sub_browser');
    await addon.scrollIntoViewIfNeeded();
    const artifacts = path.resolve('test-results/automation-addon');
    fs.mkdirSync(artifacts, { recursive: true });
    await page.screenshot({ path: path.join(artifacts, 'starter-addon.png'), fullPage: true, animations: 'disabled' });
    await page.goto('http://127.0.0.1:5178/app/automations');
    await expect(page.getByRole('status').filter({ hasText: '0 / 1,000 automation runs used' })).toBeVisible();
    await page.getByRole('button', { name: 'Create automation', exact: true }).click();
    await page.getByLabel('Name', { exact: true }).fill('Starter auto reply');
    await page.getByLabel('Trigger type').selectOption('INCOMING');
    await page.getByLabel('Reply text').fill('Thanks for contacting us.');
    await page.getByLabel('Enable after saving').check();
    await page.getByRole('button', { name: 'Save automation', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Enabled', exact: true })).toBeVisible();
    expect(errors).toEqual([]);
    console.log('PASS: Starter extra ₹399, captured payment activates add-on, 1,000-run meter, enable automation.');
  } finally { await page.unrouteAll({ behavior: 'ignoreErrors' }); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
