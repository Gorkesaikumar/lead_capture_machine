# Nextora Meta connections — implementation and setup

Status as of 5 September 2026: software implemented and tested with external HTTP/SDK test doubles. **Real Instagram and WhatsApp onboarding, incoming messages, and outbound replies have not been verified.** This does not meet the live end-to-end acceptance criterion yet.

## What was found before changes

The project already had a shared Customer/Lead/Conversation/Message pipeline, organization permissions, encrypted IntegrationConfig credentials, signed webhooks, Celery ingestion, database message deduplication, messaging-window checks, an outbound outbox, delivery receipts, lead capture, and paid DM automation. These components were retained.

The gaps were user/workspace binding for OAuth state, WhatsApp's manual business-ID discovery flow, incomplete verification before connection status, missing periodic account checks, missing disconnect confirmation, raw callback error codes, and obsolete Channels navigation links.

## Implemented

- Instagram API with Instagram Login: professional-account authorization, cryptographic single-use state stored as a hash, initiating-user/workspace binding, callback membership revalidation, backend-only code exchange, permission checks, long-lived token exchange, account identity validation, webhook subscription, and encrypted storage.
- WhatsApp Embedded Signup: backend-provided public app/config IDs, official Facebook SDK popup, code response, strict postMessage origin checks, backend validation of the granted WABA and selected phone, registration for phones that are not connected, and WABA subscription. A business portfolio ID or permanent token is not requested from customers.
- Active Meta destinations have a database uniqueness constraint across workspaces. PostgreSQL locks prevent competing onboarding/subscription operations. A different account in the same workspace requires disconnect first.
- Connection status comes from the server. A success URL alone cannot display a successful connection. Verification and provider acceptance are separate from actual delivered/read receipts.
- Periodic account/token/subscription checks every six hours, manual check, Instagram token refresh near expiry, explicit expired/permission/error states, and stale verification detection after 24 hours.
- Disconnect invalidates local credentials and stops subsequent ingestion/sends while preserving CRM history. Remote unsubscribe is attempted; other active numbers sharing a WABA retain their subscription. Already in-flight provider requests cannot be recalled.
- Location and shared-contact WhatsApp messages now have useful text plus retained structured metadata. Existing text, image, document, audio, video, interactive, and unsupported-message handling remains.
- Message-driven New Lead and New Conversation automation triggers added. Existing keyword, incoming-message, and first-interaction triggers retained. Outbound messages do not trigger automation; duplicate inbound deliveries do not rerun it.
- OAuth query parameters are redacted from configured application/development HTTP logs. Nginx already logs paths without query strings.

## Files created

Paths are relative to `D:\v4-studio`.

- `apps/integrations/connection_service.py`
- `apps/integrations/connection_views.py`
- `apps/integrations/health_service.py`
- `apps/integrations/tests/test_connections.py`
- `apps/integrations/migrations/0004_secure_meta_onboarding.py`
- `apps/automations/migrations/0003_message_lifecycle_triggers.py`
- `frontend/src/features/channels/metaSignup.ts`
- `docs/META_CONNECTIONS.md`

## Files modified

- `apps/integrations/models.py`, `views.py`, `urls.py`, `tasks.py`, `pipeline.py`, `oauth_service.py`
- `apps/integrations/meta/whatsapp/oauth.py`, `parser.py`
- `apps/integrations/tests/test_oauth.py`
- `apps/conversations/outbound.py`
- `apps/automations/models.py`, `services.py`, `views.py`
- `apps/core/logging.py`
- `config/settings/base.py`, `config/urls.py`
- `frontend/src/features/channels/ChannelsDashboard.tsx`
- `frontend/src/api/integrations.queries.ts`
- `frontend/src/features/inbox/components/InboxConversationList.tsx`
- `frontend/src/features/automations/AutomationsPage.tsx`
- `tests/test_platform_security.py`, `tests/test_messaging_platform.py`
- `.env.example`, `.env.production.example`

Existing unrelated working-tree edits were retained.

## Database migrations

`integrations.0004_secure_meta_onboarding` creates OAuthAttempt, adds connected_by, and enforces one active workspace per provider/destination. It does not rewrite stored credentials or mark old integrations connected. A deployment with duplicate active destinations must resolve ownership before applying the constraint.

`automations.0003_message_lifecycle_triggers` adds the message-driven lifecycle trigger choices.

Both migrations are applied to the local development database. Django reports no pending model changes.

## API endpoints

All paths below are relative to the configured public API origin.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/integrations/status/` | Workspace-specific Instagram, WhatsApp, and website status; no credentials |
| GET | `/api/v1/integrations/instagram/connect/` | Admin/owner-only authorization URL |
| GET | `/api/v1/integrations/instagram/callback/` | Alias for the Instagram callback |
| POST | `/api/v1/integrations/instagram/disconnect/` | Invalidate credentials and unsubscribe |
| GET | `/api/v1/integrations/whatsapp/connect/` | Admin/owner-only Embedded Signup config and state |
| POST | `/api/v1/integrations/whatsapp/complete/` | Authenticated code, state, WABA, and phone completion |
| POST | `/api/v1/integrations/whatsapp/callback/` | Completion alias; GET does not onboard |
| POST | `/api/v1/integrations/whatsapp/disconnect/` | Invalidate credentials and unsubscribe where appropriate |
| POST | `/api/v1/integrations/{instagram or whatsapp}/verify/` | Check provider access and subscription |
| GET/POST | `/api/v1/webhooks/instagram/` | Instagram verification/ingestion alias |
| GET/POST | `/api/v1/webhooks/whatsapp/` | WhatsApp verification/ingestion alias |
| GET/POST | `/api/v1/webhooks/meta/` | Combined webhook alias |

Existing `/api/v1/integrations/health/`, `/api/v1/integrations/oauth/...`, and `/api/v1/webhooks/meta/{instagram or whatsapp}/` routes remain available. The old WhatsApp GET callback no longer accepts a manual portfolio flow.

Outbound replies retain `POST /api/v1/conversations/{id}/send/`, tenant/window checks, approved WhatsApp templates outside the service window, and provider-confirmed external message IDs.

## Environment variables

| Variable | Use |
| --- | --- |
| `META_APP_ID` | Facebook/Meta application ID for WhatsApp |
| `META_APP_SECRET` | Backend-only Meta secret for WhatsApp and its signatures |
| `META_INSTAGRAM_APP_ID` | Instagram product's app ID; falls back to META_APP_ID only for compatible existing setups |
| `META_INSTAGRAM_APP_SECRET` | Instagram product secret; falls back to META_APP_SECRET |
| `META_VERIFY_TOKEN` | Shared private webhook verification token |
| `META_GRAPH_API_VERSION` | Explicit supported version configured for the Meta app; existing project fallback is v25.0, not a claim that this is the latest version |
| `META_REDIRECT_BASE_URL` | Public HTTPS API origin, without trailing slash |
| `META_INSTAGRAM_REDIRECT_URI` | Optional exact override for the Instagram callback |
| `META_WHATSAPP_CONFIG_ID` | Facebook Login for Business configuration for WhatsApp Embedded Signup |
| `FRONTEND_URL` | Public frontend origin for OAuth completion |
| `VITE_API_BASE_URL` | Public API base or `/api/v1` for same-origin proxy |
| `SECRET_KEY` | Existing backend key used by credential encryption; preserve securely during deployments |

The existing META_WHATSAPP_REDIRECT_URI is retained for compatibility. Embedded Signup SDK code exchange does not use the legacy redirect-based portfolio flow. Global INSTAGRAM_ACCESS_TOKEN / WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID are not the primary SaaS onboarding mechanism.

Never put app secrets, access tokens, registration PINs, or SECRET_KEY in VITE variables. Configure secrets directly in the backend deployment environment. Do not print tokens in shell output.

## Meta Developer Dashboard setup

1. Configure the Meta business app and Instagram API with Instagram Login product. Use the Instagram product credentials, which may differ from the Facebook application ID/secret.
2. Enable the permissions required by the chosen architecture: Instagram `instagram_business_basic` and `instagram_business_manage_messages`. Facebook Page discovery and its permissions are not used by this implementation. Meta's [Instagram Login API collection](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login) documents this permission family.
3. Register the exact Instagram OAuth redirect URI and configure deauthorization/data-deletion callbacks, a privacy policy, and the data deletion information required for your app.
4. Add eligible Instagram professional accounts/testers and enable access to messages in the account settings as required by Meta.
5. Create a Facebook Login for Business configuration with the **WhatsApp Embedded Signup** variation, WhatsApp accounts as assets, and `whatsapp_business_management` plus `whatsapp_business_messaging`. Select the supported system-user/code flow in the configuration. Set its ID as META_WHATSAPP_CONFIG_ID.
6. Configure the public frontend domain and allowed JavaScript SDK domains in Meta. Allow `https://connect.facebook.net` for the SDK and the Meta login popup in browser/CSP settings.
7. This implementation uses standard Cloud API onboarding with a phone. Coexistence/business-app onboarding and WABA-only completion events are explicitly rejected rather than marked connected. Credit-line allocation/reseller billing is not implemented; customer WhatsApp billing must be configured in Meta.
8. Configure Instagram webhooks for `messages` and `messaging_seen`; configure WhatsApp `messages`. Use the same backend META_VERIFY_TOKEN in Meta's verification setup. App-level webhook setup must exist before per-account subscription can work.
9. Finish the Tech Provider/business requirements, business verification and permission review requested in your Meta dashboard before onboarding unrelated customer accounts. Request only the permissions used by this implementation. Meta's older [Embedded Signup collection](https://www.postman.com/meta/whatsapp-business-platform/documentation/du6gzjv/embedded-signup?entity=request-13382743-afd10045-c2ea-4860-ac73-55423cd06558) also covers partner/credit-line workflows with business_management; those broader workflows are not implemented here.

The Meta developer implementation pages returned HTTP 429 to research requests during this task. Accessible Meta-owned Postman documentation was used to cross-check account scopes, WABA discovery, registration, and subscriptions. The current dashboard configuration and a live developer-account flow still need verification before production launch.

## Exact callback/webhook URL templates

Replace `https://api.example.com` and `https://app.example.com` with the actual domains. No public domain was supplied during this task.

- Instagram OAuth redirect registered by default: `https://api.example.com/api/v1/integrations/oauth/instagram/callback/`
- Instagram deauthorization: `https://api.example.com/api/v1/integrations/oauth/instagram/deauthorize/`
- Instagram data deletion: `https://api.example.com/api/v1/integrations/oauth/instagram/data-deletion/`
- Instagram webhook: `https://api.example.com/api/v1/webhooks/meta/instagram/`
- WhatsApp webhook: `https://api.example.com/api/v1/webhooks/meta/whatsapp/`
- WhatsApp SDK completion: authenticated POST to `https://api.example.com/api/v1/integrations/whatsapp/complete/`; not a browser OAuth redirect URL.
- Frontend return: `https://app.example.com/app/settings/channels`

Configure the exact redirect selected by the backend; aliases are not interchangeable during authorization code exchange. Webhooks need public HTTPS access, even when the app is running locally behind a development tunnel.

## Local testing procedure

1. Set the variables above in backend configuration. Run `python manage.py migrate`. Restart Django, Celery worker, Celery Beat and Vite when environment settings change.
2. Verify PostgreSQL and Redis are available. Run `python manage.py check`.
3. Automated regression command: `python -m pytest apps/integrations/tests tests/test_messaging_platform.py tests/test_platform_security.py tests/test_instagram_integration.py tests/test_whatsapp_integration.py tests/test_integrations.py apps/conversations/tests/test_idempotency.py -q`.
4. Frontend: `npm run build` in `frontend`.
5. For real tests, expose the configured API via HTTPS, register the callbacks, open Nextora as an organization owner/admin, and use an eligible Meta developer/test account to finish authorization.
6. Send a real DM from a separate Instagram account. Confirm one Customer, one Lead, one Conversation and one inbound Message. Reply from the Nextora inbox and confirm receipt on Instagram. Check the external message ID and delivery state.
7. Repeat for WhatsApp after onboarding its WABA/phone. Test an approved template outside the service window; free-form sending should be blocked then.
8. Enable a permitted paid-plan automation, send a matching incoming message, verify one execution and one reply. Re-deliver a signed event and confirm no duplicates. Test New Lead and New Conversation triggers only on their first applicable event.
9. Test a second workspace. Verify its status/inbox remains isolated. Disconnect, confirm history remains, and verify subsequent queued sends fail instead of using invalidated credentials.

## Production test and approval procedure

Deploy migrations and restart workers/Beat. Configure TLS, public origins, Meta domains, webhook callbacks, privacy/deletion endpoints, a stable encryption key and secret storage. Confirm app review, advanced access, business/Tech Provider verification and WhatsApp account/number status in the dashboard. Use an eligible real customer workspace to repeat the exact inbound-to-reply checks above. Verify webhook signature rejection, callback replay rejection and revoked-token health detection before launch. Record real provider message IDs and receipts in your private acceptance log; do not publish credentials or customer content.

Instagram access for unrelated customer accounts and WhatsApp Embedded Signup release require the appropriate Meta review/access configuration. Development-role eligibility is not evidence of production approval. The actual approval state was not inspected, so **BLOCKED BY META APPROVAL is not established**.

## Test results and remaining blockers

- Initial full messaging/integration regression: 196 tests passed.
- Browser checks passed with test-only API/SDK doubles: backend-driven status, no false success from a callback query, actionable errors, Embedded Signup completion, rejected foreign postMessage origins, disconnect confirmation/cancel, and mobile fit.
- Production frontend build passed, with the existing large-chunk advisory.
- Django checks and migration-drift check passed. Both new migrations applied locally.
- Final focused verification after lifecycle, permission-health, locking, and logging changes: 76 tests passed. These overlap with the initial regression; they are not 76 additional unique tests.

**Live-test blockers:** no META_WHATSAPP_CONFIG_ID, no configured public callback base, and no completed developer-account authorization/inbound/reply test. Instagram product credentials and Meta approval status still need dashboard verification. Existing META_APP_ID and META_APP_SECRET are present locally, but their presence alone does not establish validity or product suitability. No production credential values were printed or changed.

**Implemented:** application code and setup path. **Tested:** automated/backend/browser checks. **Not yet tested:** real Meta onboarding and message round trips. **Meta approval:** unverified; may limit production users.

Meta source references for the implementation: [debug-token WABA grants](https://www.postman.com/meta/whatsapp-business-platform/request/i1mz7w8/debug-token), [phone registration and two-step verification](https://www.postman.com/meta/whatsapp-business-platform/request/mk4p87j/register-phone-number), and [WABA subscriptions](https://www.postman.com/meta/whatsapp-business-platform/documentation/du6gzjv/embedded-signup?entity=request-13382743-062af851-7627-4f28-bd3b-4cbfcb0ff837).
