> Payment update: automatic monthly renewal is now implemented. See [Razorpay recurring billing](RAZORPAY_RECURRING_BILLING.md) for the current flow, environment names, webhook events and deployment instructions. The one-off checkout details below describe the retained legacy path.

# Starter DM Automation: pricing, rules and activation

Prepared 5 September 2026. This update implements the requested **₹399 extra per month**, not a change to Starter's base price.

## Pricing in the application

| Plan | Base price in INR/month | DM Automation | App run allowance |
|---|---:|---|---|
| Free | ₹0 | Drafts and previews only | No live runs |
| Starter | ₹400 | Optional ₹399/month add-on | 1,000 runs per paid add-on month |
| Creator | ₹1,500 | Included, as before | No additional app run cap |
| Enterprise | ₹8,000 | Included, as before | No additional app run cap |

**Starter with the add-on is ₹799/month.** Meta and other messaging-provider charges are separate. The add-on is charged in INR, including when the base-plan price selector displays USD. No currency conversion is implied.

The 1,000-run Starter allowance is the application's commercial limit. It is not a Meta allowance, a promise of 1,000 delivered messages, or a conversion of an API rate limit into a monthly quota. Creator/Enterprise's existing uncapped app access does not override Meta restrictions.

One run means one matching automation rule started for one incoming message. Multiple actions inside that rule consume one run; two matching rules consume two runs. Started runs still count if an action subsequently fails. Drafts, previews, repeated webhook delivery, disabled/nonmatching rules and runs blocked by the quota consume none. At the cap, new runs are recorded as blocked; no overage payment is triggered. Deleting a rule or its history does not erase usage. Worker concurrency is serialized by workspace when reserving a run.

The add-on lasts one calendar month from verified payment, with month-end dates clamped as needed. Its period is separate from the base subscription. An active Starter subscription is required throughout. Renewal is manual checkout, not an automatic debit mandate. The next paid add-on period receives a fresh allowance. Renewing the base plan alone does not reset add-on usage.

## What Meta's rules mean for this price

The official material reviewed does not specify a universal number of DM automation runs allowed per month. Permissions, account-specific messaging limits, recipient eligibility, quality enforcement and reply windows govern delivery. Do not multiply a throughput limit by the seconds in a month and advertise that as guaranteed capacity.

Instagram automated replies require an incoming customer interaction and the standard 24-hour messaging window. Human Agent access cannot extend automated replies. These restrictions remain enforced; buying the add-on does not change them. See [Meta's official Instagram documentation](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df).

WhatsApp prices eligible delivered messages by category and recipient market, with volume tiers where applicable. Its current pricing page describes service replies inside the 24-hour customer-service window as free and utility replies in that window as free. Outside the window, the application requires an approved template. Rates and exemptions can change; the app links to the current source and does not fabricate a fixed INR rate or Meta invoice. See [WhatsApp's official pricing page](https://business.whatsapp.com/products/platform-pricing).

The ₹399 charge pays for the application's automation engine and allowance. It is not a resale of a Meta monthly bundle. Automated rules currently send free-form replies/booking links in response to inbound messages; manual WhatsApp template sending remains available subject to Meta's validation. Business-initiated marketing campaigns, bulk sends and Human Agent workarounds were not added.

Some developers.facebook.com limit/rate-card pages were unavailable or rate-limited during research. Exact account throughput/recipient ceilings and current per-category INR tariffs were therefore not hardcoded. Confirm the connected account's current limits in Meta before live acceptance.

## Payment implementation and setup

The previous upgrade flow could grant paid access without verifying a payment. It has been replaced for both base plans and the automation add-on:

1. Only an active workspace owner/admin can create or verify an order.
2. The server sets the SKU, amount and currency. Starter remains ₹400; the add-on is ₹399 (39,900 paise). Unpaid orders are reused on retries.
3. Razorpay Standard Checkout collects payment. The frontend cannot activate access just by submitting a plan name.
4. The server verifies the checkout HMAC and fetches the payment, requiring captured status and exact order, amount, currency and payment ID.
5. A signed payment webhook can complete the same grant if the browser closes. Repeated callbacks do not extend access twice. The ledger identifies base-plan and add-on payments separately.

Implementation follows [Razorpay's Standard Checkout guide](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/), [Orders API](https://razorpay.com/docs/api/orders/create/) and [webhook validation guide](https://razorpay.com/docs/webhooks/validate-test/).

Configure backend-only `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET`. Enable captured payments in the provider account and subscribe to `payment.captured`/`order.paid` at:

`https://<api-host>/api/v1/subscriptions/webhooks/razorpay/`

The public key is returned to Checkout; secret keys stay on the server. No real payment was made in this task. The local configuration had no Razorpay keys, so purchase buttons deliberately explain that payment configuration is required. No real workspace was upgraded or granted a complimentary add-on.

The new schema is in `subscriptions/0004_plan_automation_run_limit_and_more` and `automations/0002_automationusage`. The local database reports both applied. Apply migrations and restart web/worker processes in other deployments. The standard plan catalog is synchronized by the existing seeding service, including Starter's add-on description and limit.

Operational boundaries: real gateway credentials, capture settings, webhook connectivity and live payment acceptance still need verification. Automatic recurring mandates, proration, automated refunds/chargebacks and tax invoicing are not implemented. If provider order creation is unconfirmed, the pending ledger intent blocks automatic duplicate order creation; reconcile it with Razorpay before retrying or marking it failed. Never manually label an unpaid record successful to bypass verification.

## Verification

Automated checks cover Starter eligibility, expiry, inactive/pending subscriptions, one run per rule/message, quota rollover, duplicate events, concurrent workers, retained usage after deletion, server-authoritative prices, duplicate checkout, forged signatures, wrong amounts/currencies/orders, captured-payment requirements, workspace permissions and callback idempotency.

Chromium tests use the real Django test server/database with simulated external payment/Meta responses. The Starter flow verifies ₹799 total pricing, a 39,900-paise checkout, paid add-on activation, the 1,000-run meter and creation of an enabled rule. Browser simulations are not proof of a real charge or Meta delivery.

Final validation: **377 tests passed**, including five Chromium workflows. The production frontend build, Django checks, migration-consistency check and Git whitespace check passed. The full run reported one database teardown warning; test-thread connection cleanup was corrected, and all three affected concurrency cases then passed without warnings. The existing frontend bundle-size advisory remains. The local Vite server on port 5173 was checked and serves the updated add-on pricing UI.
