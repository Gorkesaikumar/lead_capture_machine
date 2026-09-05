const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const scenario = process.env.V4_AUTOMATION_ACCESS_CASE;
  let failPlanLookup = scenario === 'unavailable';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    if (failPlanLookup && url.pathname.endsWith('/subscriptions/current/')) {
      return route.fulfill({ status: 503, json: { detail: 'Temporarily unavailable.' } });
    }
    const response = await route.fetch({ url: process.env.V4_BACKEND_URL + url.pathname + url.search });
    await route.fulfill({ response });
  });
  await page.addInitScript(({ token, org }) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('organizationId', org);
  }, { token: process.env.V4_TEST_TOKEN, org: process.env.V4_TEST_ORG });
  try {
    await page.goto('http://127.0.0.1:5178/app/automations');
    const reason = scenario === 'expired' ? 'Your subscription is not active.'
      : scenario === 'unavailable' ? 'Could not check automation access.'
      : 'Your Free plan does not include DM Automation.';
    await expect(page.getByRole('status').filter({ hasText: reason })).toBeVisible({ timeout: 20000 });
    await page.getByRole('button', { name: 'Create automation' }).click();
    await page.getByLabel('Name', { exact: true }).fill('Plan access draft');
    await page.getByLabel('Trigger type').selectOption('INCOMING');
    await page.getByLabel('Reply text').fill('   ');
    await expect(page.getByLabel('Enable after saving')).toBeDisabled();
    await expect(page.getByLabel('Enable after saving')).not.toBeChecked();
    await expect(page.getByRole('dialog').getByText(reason, { exact: false })).toBeVisible();
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    const alert = page.getByRole('dialog').getByRole('alert');
    await expect(alert).toHaveText('Reply requires 1–1000 characters.');
    await expect(alert).not.toContainText('correlation_id');
    await expect(page.getByLabel('Name', { exact: true })).toHaveValue('Plan access draft');
    await page.getByLabel('Reply text').fill('Thanks for contacting us.');
    const saved = page.waitForResponse(response => response.url().endsWith('/automations/') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    const response = await saved;
    expect(response.status()).toBe(201);
    expect((await response.json()).enabled).toBe(false);
    await expect(page.getByRole('heading', { name: 'Plan access draft' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Disabled', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Preview', exact: true }).click();
    await page.getByRole('button', { name: 'Test rule' }).click();
    await expect(page.getByText('Rule matches', { exact: true })).toBeVisible();
    await page.keyboard.press('Escape');
    if (scenario === 'unavailable') {
      await expect(page.getByRole('button', { name: 'Retry plan check' })).toBeVisible({ timeout: 20000 });
      failPlanLookup = false;
      await page.getByRole('button', { name: 'Retry plan check' }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Your Free plan' })).toBeVisible();
    }
    await page.getByRole('button', { name: 'Edit Plan access draft' }).click();
    await expect(page.getByLabel('Reply text')).toHaveValue('Thanks for contacting us.');
    const artifacts = path.resolve('test-results/automation-access');
    fs.mkdirSync(artifacts, { recursive: true });
    await page.screenshot({ path: path.join(artifacts, `${scenario}.png`), fullPage: true });
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await page.getByRole('link', { name: 'View plans', exact: true }).click();
    await expect(page).toHaveURL(/\/app\/settings\/subscription$/);
    await expect(page.getByRole("heading", { name: "Subscription & Billing", exact: true })).toBeVisible();
    expect(errors).toEqual([]);
    console.log(`PASS: ${scenario}: activation unavailable; draft create/edit/preview; readable validation; plan navigation.`);
  } finally {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
