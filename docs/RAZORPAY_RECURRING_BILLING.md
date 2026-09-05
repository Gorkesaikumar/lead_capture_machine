# Razorpay automatic monthly billing

Paid plans and the Starter DM Automation add-on use Razorpay Subscriptions and hosted Standard Checkout. The customer explicitly authorizes the monthly price and maximum number of charges. Existing paid access is honoured by scheduling the first full payment at its expiry. A refundable mandate authentication payment alone does not unlock a plan.

## Configuration

Server environment only (never VITE_ variables):

```dotenv
RAZORPAY_API_KEY=your_key_id
RAZORPAY_SECRET_KEY=your_key_secret
RAZORPAY_WEBHOOK_SECRET=your_separate_random_webhook_secret
RAZORPAY_SUBSCRIPTION_CYCLES=120
```

The legacy names RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET remain supported; the names above take precedence. Only the public key ID reaches checkout. Plans are created in the configured Razorpay account using server catalogue prices. Existing mandates retain their agreed price when an administrator changes catalogue prices. The cycle count is finite; a new authorization is required after completion.

## Required Razorpay dashboard setup

1. Enable Subscriptions for the merchant account and configure the desired recurring payment methods.
2. In the matching **Test** dashboard, add a webhook pointing to `https://YOUR_BACKEND/api/v1/subscriptions/webhooks/razorpay/`. Local testing requires a public HTTPS tunnel to the backend; localhost is not reachable by Razorpay.
3. Copy the value of your server's RAZORPAY_WEBHOOK_SECRET into that webhook's secret field. It is separate from the API secret. Do not place either secret in frontend code.
4. Subscribe to subscription.authenticated, subscription.activated, subscription.charged, subscription.pending, subscription.halted, subscription.cancelled, subscription.completed, subscription.paused, subscription.resumed and subscription.updated; also payment.captured, payment.failed, payment.refunded, refund.processed and invoice.paid where available. Keep order.paid for legacy one-off checkouts.
5. Confirm a signed delivery returns HTTP 200 and the corresponding PaymentWebhookEvent is processed.

Official references: [subscription integration](https://razorpay.com/docs/payments/subscriptions/integration-guide/), [subscription testing](https://razorpay.com/docs/payments/subscriptions/test/), [webhook configuration](https://razorpay.com/docs/payments/dashboard/account-settings/webhooks/).

## Deployment

```shell
python manage.py migrate
python manage.py check_payments --probe --deploy
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Production Compose already defines worker and beat services. Run one beat scheduler, keep Redis available, and set CELERY_TASK_ALWAYS_EAGER=False. Recovery runs every five minutes. `python manage.py reconcile_payments` dispatches an immediate bounded recovery batch. Monitor unprocessed webhook events, their attempts/last_error, and RecurringAgreement.last_error; alert on growing backlogs or unresolved creating intents. Configuration checks do not prove that the dashboard webhook or workers are running.

## Payment and cancellation behavior

- Only workspace owners/admins may purchase, reconcile or cancel. Prices, currency, mandate ownership, invoice identity, signatures and captured payments are checked on the server.
- Raw webhook signatures are verified before a minimal durable event is stored. Duplicate and out-of-order events are reconciled against current Razorpay data. Each paid invoice has one ledger entry and one entitlement period.
- Closing the browser after paying is recoverable via webhooks, periodic reconciliation or **Check payment status**. If checkout creation times out, the same POST is not blindly retried. Recovery searches by the saved intent UUID. An unresolved intent blocks another mandate; an administrator must inspect the matching provider records before resolving it. Do not delete intents to force a retry.
- Authorization without a captured full invoice shows a pending message. Failed renewals do not extend access. Already paid access lasts until its recorded expiry. Future-dated invoices do not activate access early.
- **Stop renewal** cancels the provider mandate; local success is shown only after provider confirmation. Stopping base-plan renewal also stops add-on renewal. A cancelled mandate cannot be restarted; authorize a new one. Active mandates must be stopped before choosing another plan; immediate prorated plan changes are not implemented.
- Full refunds recorded by Razorpay update the ledger and revoke the matching paid period. Partial refunds retain access. Refunds are issued through the Razorpay dashboard, not this application.
- Legacy one-off checkout verification remains available for orders created before the recurring rollout.

## Switching to live

Replace both API credentials in the server environment, configure a separate **Live** webhook and secret, restart web/worker/beat, and rerun the checks. Test mandates, invoices and paid access are isolated by the configured key ID and cannot become live subscriptions. Customers must authorize new live mandates. Key-ID rotation also changes this isolation boundary: reconcile/migrate existing live agreements deliberately before rotating an account's keys; do not assume a key replacement preserves existing agreement visibility.

Complete a sandbox checkout, successful monthly charge, declined renewal, cancellation, duplicate delivery and refund exercise before enabling live purchases. Confirm live account activation, recurring method availability and your published billing/refund terms. INR and USD catalogue prices are supported; actual currency/method availability depends on the Razorpay account. International recurring subscriptions require supported cards.

## Verification performed in this workspace

- 54 backend/integration tests passed, including a real Chromium/Django Starter add-on flow with simulated Razorpay responses.
- Three browser scenarios passed: mandate authorization without premature paid access, dismissed checkout and declined payment, including status recovery.
- Frontend production build, Django system checks and migration consistency passed.
- The configured test credentials were accepted by Razorpay. An actual sandbox monthly plan and an unauthenticated test subscription were created; the subscription was then cancelled successfully. No customer payment was made.
- A separate webhook secret was generated in the ignored local .env. The running backend rejects unsigned requests with HTTP 403. Public Razorpay webhook delivery and a captured sandbox charge remain to be verified after dashboard/tunnel setup.
