# V4 Studio messaging operations

Prepared 5 September 2026. This guide describes the implemented application. It does not certify Meta approval, production deployment, or delivery to a real recipient.

## Runtime and data flow

React/Vite → DRF token authentication → active organization membership → service layer → PostgreSQL. The organization header is optional only when the server can select an active membership; an explicitly invalid or foreign `X-Organization-ID` fails closed.

Inbound flow: Meta signature verification → durable `RawWebhookEvent` → Celery → configured destination account → organization-scoped contact identity → conversation/message → lead capture → automation → committed outbox → channel adapter → Meta. WebSocket events publish only after commit and only to the relevant organization/entity. The UI also polls as a fallback.

Outbound flow: `POST /api/v1/conversations/{id}/send/` → validate channel, membership, identity, configuration and reply window → persist `QUEUED` → return HTTP 202 → worker claims `SENDING` → provider call → `SENT` only with provider success and an external message ID. Delivery/read callbacks advance status monotonically. Early receipts are retained and reconciled after the send response.

`SENT` means provider acceptance, not delivery. `DELIVERED` and `READ` require supported callbacks. A queue acknowledgment is not a provider acknowledgment.

## Configuration

| Variable | Purpose |
|---|---|
| `DJANGO_SETTINGS_MODULE=config.settings.production` | Production security settings; set on web, worker and beat |
| `SECRET_KEY` | Django signing and existing Fernet credential encryption; preserve it across deployments |
| `ALLOWED_HOSTS` | Exact frontend and API hostnames |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | PostgreSQL connection |
| `REDIS_URL` | Cache and Channels Redis |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Task broker/results |
| `FRONTEND_URL` | Public HTTPS application base URL used for links |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Explicit application origins; public form submissions have a separate path-scoped CORS exception |
| `META_APP_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN` | Meta app and signed webhook verification |
| `META_GRAPH_API_VERSION` | Explicit supported version selected for the app; required in production |
| `META_WHATSAPP_CONFIG_ID` | WhatsApp Embedded Signup configuration ID; no redirect URI is required |
| `META_REDIRECT_BASE_URL`, `META_INSTAGRAM_REDIRECT_URI` | Production origin and canonical Instagram callback; see META_PRODUCTION_SETUP.md |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Password reset, verification and invitations via SMTP |
| `VITE_API_BASE_URL` | Optional frontend build variable; default `/api/v1` uses the same hostname |

Normal tenant sends do **not** use global `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_PAGE_ACCESS_TOKEN` or `WHATSAPP_ACCESS_TOKEN`. Those names remain for legacy adapter compatibility. Each active workspace has an encrypted `IntegrationConfig` with an access token and a `metadata.destination_id`: an Instagram professional-account ID or a WhatsApp phone-number ID. A phone number is not the phone-number ID.

Never pass access tokens as command-line arguments or frontend build variables. An administrator may inject `META_CHANNEL_ACCESS_TOKEN` into the process environment from a secret manager, then run:

```sh
python manage.py configure_meta_channel --organization <workspace-uuid> --channel INSTAGRAM --destination <instagram-account-id>
python manage.py configure_meta_channel --organization <workspace-uuid> --channel WHATSAPP --destination <phone-number-id>
```

Run the appropriate command separately with that channel's token. It saves credentials as `CONFIGURED_UNVERIFIED`; it does not subscribe webhooks or prove permissions. The command rejects a destination already actively assigned to another workspace. Delete the temporary token environment variable afterward.

The existing encryption implementation derives its key from `SECRET_KEY`. Changing that key invalidates saved credentials and outstanding signed links. Coordinate credential re-encryption or reconnection before rotation; never silently replace it.

## Deployment sequence

1. Review the existing uncommitted repository changes alongside this implementation. No branch reset, commit, production migration, or deployment was performed by this task.
2. Back up PostgreSQL and the current deployment configuration. Rehearse restore and migration on a staging copy. Stop writers/workers during the schema and ownership transition.
3. Review `.env.production.example`. Supply secrets externally. Replace the example domains and the existing concrete hostnames/certificate paths in `nginx/nginx.conf` with the intended deployment. Provision TLS certificates before starting HTTPS Nginx; its configuration expects existing certificate files.
4. Build with the committed lockfile. Docker build contexts exclude `.env*`, `.venv`, Git, node_modules and test artifacts. The production Compose file explicitly selects production Django settings on all application processes.
5. Run the following on staging, then on the deployment during maintenance:

```sh
docker compose --env-file .env.production -f docker-compose.production.yml build
docker compose --env-file .env.production -f docker-compose.production.yml up -d db redis
docker compose --env-file .env.production -f docker-compose.production.yml run --rm web python manage.py migrate
docker compose --env-file .env.production -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput
docker compose --env-file .env.production -f docker-compose.production.yml run --rm web python manage.py check --deploy
docker compose --env-file .env.production -f docker-compose.production.yml run --rm web python manage.py check_messaging_platform
```

6. Resolve any unowned legacy records before opening the studio. Identity/conversation ownership is backfilled from the customer; booking ownership is backfilled before the new tenant booking exclusion constraint. Scheduling rows without ownership remain quarantined. Do not infer their owner just because one studio is currently active. After reviewing actual record IDs, use `adopt_legacy_records` first without `--apply`, then with it:

```sh
python manage.py adopt_legacy_records --organization <workspace-uuid> --model scheduling.WeeklyAvailability --ids <reviewed-row-uuid>
```

The tool accepts only explicitly selected unowned records and rejects conflicting related ownership. Assign parents before children. Schedule and customer ownership must be reviewed by someone who knows the legacy data. Rerun diagnostics afterward.

7. Start web, frontend, worker, exactly one beat scheduler, and Nginx. Use ASGI for WebSockets. Production Compose already uses an ASGI worker. Verify `/health/ready/`, login, tenant selection, leads, availability, and `/ws/admin/dashboard/`. The frontend hostname now proxies `/api/` and `/ws/`; the API hostname remains supported.
8. Complete the separate Meta acceptance checklist. Verify worker/beat health and queue recovery before opening real traffic. Keep a rollback plan that restores the matching database snapshot and application version together; do not reverse tenant constraints against live writes.

## Monitoring and failure recovery

`python manage.py check_messaging_platform` is read-only and prints channel states, unowned-record counts and queue totals, never tokens or message bodies.

Beat runs recovery every minute. Committed `QUEUED` messages survive broker outages. A worker abandoned in `SENDING` for ten minutes becomes `FAILED/delivery_unconfirmed`; the system does not automatically resend an ambiguous POST. Inspect the actual channel before manually resending. Keep the same request ID when retrying the same HTTP submission after an uncertain client response; changing its content with the same ID returns a validation error.

Webhook processing uses bounded Celery retries and recovers recent pending/failed records. Automatic recovery covers the previous day. Older failures remain available in Django admin for explicit investigation and task replay after fixing their configuration. Replaying an already processed event is idempotent. Keep raw webhook retention bounded through the organization's operational retention policy; avoid exposing message bodies in diagnostics or exports.

Watch for: increasing queue age, repeated webhook failures, multiple workspace mappings for a destination, expired tokens, permission errors, unconfirmed sends, and missing delivery callbacks. Credentials alone never turn the integrations badge into `CONNECTED`; that status records an accepted send and is not a guarantee of continuing delivery.

Data-deletion callbacks verify a signed request, disconnect credentials, persist a random confirmation code and return a real status endpoint. A recoverable worker removes the locally stored Instagram conversation/identity/lead/notification data in scope. Independent WhatsApp records and booking records are retained. Backup expiry and any independently collected business records require the operator's retention process. Reconnection is blocked while the matching deletion is pending.

## Application boundaries

- One Instagram destination and one WhatsApp destination per workspace. Automatic contact merging across unrelated channels is intentionally absent.
- Inbox history starts with stored events; there is no historical account-wide import.
- Website forms create inbox inquiries; website email/chat replies have no configured transport and are disabled with an explanation.
- Manual composers support text and approved WhatsApp templates. The API also supports media URLs and stores incoming media metadata. Media upload, expiring-media download/proxying, and a template approval/catalog editor are not provided.
- Automations react to incoming messages only. No comment-growth campaigns, mass messaging, scheduled marketing follow-ups, or automated Human Agent exemption.
- UI notification preference switches that lack a delivery backend remain disabled. Billing-provider operation and subscription payment collection were not certified by this messaging task.
- Windows tests use mocked external calls. Linux container startup, real Redis recovery under process crashes, production load, SMTP delivery, certificate issuance and real Meta delivery still need deployment acceptance.

## Repeatable tests

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm ci
npx playwright install chromium
npm run build
npm run dev -- --host 127.0.0.1 --port 5178 --strictPort
```

With Vite running, from the project root in another terminal:

```powershell
$env:V4_BROWSER_TESTS='1'
.venv\Scripts\python.exe -m pytest -q
```

The browser test launches Chromium against Vite and the Django test database. Browser API requests reach the real test server; outbound Meta dispatch alone is mocked. Test caches are reset per test so rate-limit histories do not leak between unrelated tests. Never run test fixtures against production data.
