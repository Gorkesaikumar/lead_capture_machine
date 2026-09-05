const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch();
  try {
    for (const scenario of ['authorized', 'dismissed', 'failed']) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
      const errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain('every month');
        await dialog.accept();
      });
      const workspace = { id: '11111111-1111-4111-8111-111111111111', name: 'Billing Test', role: 'OWNER' };
      const plans = [['free', 'Free', '0'], ['starter', 'Starter', '400'], ['creator', 'Creator', '1500']].map(([code, name, price]) => ({ id: code, code, name, price, price_inr: price, price_usd: '5', currency: 'INR', lead_limit: 100, features: [] }));
      const subscription = { id: 'sub-local', plan: plans[0], status: 'active', is_valid: true, current_period_start: new Date().toISOString(), current_period_end: null, cancel_at_period_end: false, billing_country: 'IN', billing_currency: 'INR', charged_amount: '0', usage: { total_leads_count: 0 }, billing: { test_mode: true, payment_available: true, cycles: 120, plan: null, dm_automation: null }, automation: { included: false, entitled: false, addon_available: false, payment_available: true, can_manage_billing: true, runs_used: 0 } };
      await page.addInitScript(({ scenario, org }) => {
        localStorage.setItem('authToken', 'recurring-browser-test');
        localStorage.setItem('organizationId', org);
        window.Razorpay = class {
          constructor(options) { this.options = options; window.checkoutOptions = options; }
          on(event, callback) { this.failed = callback; }
          open() {
            if (scenario === 'authorized') this.options.handler({ razorpay_subscription_id: this.options.subscription_id, razorpay_payment_id: 'pay_test', razorpay_signature: 'test' });
            else {
              if (scenario === 'failed') this.failed({ error: { description: 'Your test payment was declined.' } });
              this.options.modal.ondismiss();
            }
          }
        };
      }, { scenario, org: workspace.id });
      await page.routeWebSocket(/\/ws\//, () => {});
      await page.route('**/api/v1/**', async route => {
        const pathname = new URL(route.request().url()).pathname;
        let json = { results: [], count: 0 };
        if (pathname.endsWith('/auth/me/')) json = { id: 'user-test', email: 'billing@example.test', full_name: 'Billing Tester', is_active: true, workspaces: [workspace] };
        else if (pathname.endsWith('/organizations/current/')) json = workspace;
        else if (pathname.endsWith('/subscriptions/current/')) json = subscription;
        else if (pathname.endsWith('/subscriptions/plans/')) json = { plans, currency: 'INR', country: 'IN' };
        else if (pathname.endsWith('/recurring/checkout/')) {
          requests.push({ path: pathname, data: route.request().postDataJSON() });
          subscription.billing.plan = { id: 'agreement-test', subscription_id: 'sub_test', status: 'created', amount: '400', currency: 'INR', plan_code: 'starter', cancel_at_period_end: false, short_url: '' };
          json = { subscription_id: 'sub_test', key: 'rzp_test_public', amount: 40000, currency: 'INR', description: 'Starter monthly' };
        } else if (pathname.endsWith('/recurring/verify/')) {
          requests.push({ path: pathname, data: route.request().postDataJSON() });
          subscription.billing.plan.status = 'authenticated';
          json = { paid: false, message: 'Mandate confirmed. Access will activate after the first full payment is captured.' };
        } else if (pathname.endsWith('/recurring/sync/')) json = { message: 'Payment status updated.' };
        await route.fulfill({ json });
      });
      await page.goto((process.env.V4_FRONTEND_URL || 'http://localhost:5173') + '/app/subscription');
      await expect(page.getByRole('heading', { name: 'Subscription & Billing' })).toBeVisible();
      await page.getByRole('button', { name: 'Upgrade to Starter', exact: true }).click();
      expect(requests[0].data).toMatchObject({ plan_code: 'starter', accept_recurring: true });
      const status = page.getByRole('status').filter({ hasText: scenario === 'authorized' ? 'Mandate confirmed' : scenario === 'failed' ? 'declined' : 'Checkout closed' });
      await expect(status).toBeVisible();
      expect(await page.evaluate(() => window.checkoutOptions.subscription_id)).toBe('sub_test');
      expect(await page.evaluate(() => window.checkoutOptions.order_id)).toBeUndefined();
      expect(requests.filter(r => r.path.endsWith('/verify/')).length).toBe(scenario === 'authorized' ? 1 : 0);
      await expect(page.getByText('Payment verified. Paid access is active.', { exact: true })).toHaveCount(0);
      if (scenario === 'authorized') await expect(page.getByRole('button', { name: 'Upgrade to Starter', exact: true })).toBeDisabled();
      await page.getByRole('button', { name: 'Check payment status', exact: true }).click();
      await expect(page.getByRole('status').filter({ hasText: 'Payment status updated.' })).toBeVisible();
      expect(errors).toEqual([]);
      const artifacts = path.resolve('test-results/recurring-billing'); fs.mkdirSync(artifacts, { recursive: true });
      await page.screenshot({ path: path.join(artifacts, `${scenario}.png`), fullPage: true });
      await page.close();
    }
    console.log('PASS: monthly consent, subscription checkout, pending authorization, dismissal, declined payment, status recovery, no premature paid access.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
