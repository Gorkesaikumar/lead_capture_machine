# V4 Studio implementation report

5 September 2026 · Existing project: `D:\v4-studio`

**The core application-side lead capture, unified inbox, messaging and DM automation workflows are implemented and verified by automated tests. External Meta integration is not verified as approved or operational. No real Meta send acknowledgment or delivery callback was obtained.**

The existing Django/React project was extended, preserving its architecture and visual design. The repository already contained substantial uncommitted work; this task did not reset it, commit it, run production migrations or deploy it. Review the combined working tree before release.

## 1. Existing features discovered

The backend uses Django, Django REST Framework, PostgreSQL, Redis, Celery and Channels. The frontend uses React, TypeScript, Vite and query caching. Existing Django apps covered accounts, organizations, customers, leads, conversations, integrations, bookings, scheduling, services, notifications, analytics, audit, subscriptions and administration.

Existing capabilities included token authentication, workspace membership, CRM lead lifecycle, keyword lead triggers, website forms, conversation storage, partial Meta adapters/OAuth, booking links, availability, plan limits, dashboards and Docker/Nginx deployment configuration. Existing screens use Nextora branding; that branding was preserved.

| Area | Audit finding | Verified application outcome |
|---|---|---|
| Accounts and teams | Implemented with recovery, invitation and isolation gaps | Validation, recovery, invitation acceptance and tenant access repaired |
| Leads and website forms | Existing capture and lifecycle with duplication/assignment gaps | Stable identity capture, atomic manual creation and website inbox storage |
| Conversations and sending | Partial integration with inconsistent send paths/statuses | Shared outbound service, durable queue and truthful provider states |
| Meta webhooks | Existing handlers needing routing and replay safeguards | Signed, durable, idempotent and workspace-scoped processing |
| Automations | Lead keywords existed; full DM workflow builder missing | New rules, ordered actions, preview and execution history |
| Bookings and scheduling | Existing business logic with ownership/overlap problems | Tenant-aware availability, booking constraints and regression coverage |
| UI and dashboards | Existing screens with stale routes and placeholder interactions | Repaired navigation/data, functional inbox/builder, explicit disabled states |
| External services | Code/configuration existed | Meta, SMTP and payment-provider operation remain externally unverified |

## 2. Problems discovered

The main risks were inconsistent tenant resolution after authentication; globally scoped identities and auxiliary records; assignment using membership IDs instead of user IDs; duplicate capture paths; and direct lead status changes bypassing lifecycle/audit services.

Messaging had divergent legacy dispatch paths, inadequate distinction between queueing and provider acceptance, unsafe retry potential after uncertain sends, incomplete delivery callback reconciliation and weak failure visibility. Webhooks needed exact destination-to-workspace routing, durable replay handling and stronger isolation. Global realtime broadcasts and token revocation behavior needed correction.

Other issues included missing account recovery/verification behavior, invitation delivery assumptions, wrong team API routes, fake account/notification details, ignored navigation tabs, incomplete deployment environment examples, WSGI development startup despite WebSockets and tenant-unaware booking overlap constraints.

## 3. Problems fixed

- Resolve an active organization membership after DRF authentication. Explicit foreign or invalid organization headers fail closed. Scope leads, contacts, messages, automation, bookings, scheduling, notifications and audit access; restrict assignment to active workspace members.
- Add transactional registration/manual lead creation, password validation and token revocation, signed password recovery, email verification/resend and real invitation acceptance. Missing SMTP returns an actionable failure instead of claiming delivery.
- Deduplicate inbound leads using workspace/channel/external identity, enforce plan limits, route lead lifecycle changes through the existing service and bound regex execution time.
- Consolidate manual replies, legacy sends, automation replies and booking links through shared outbound rules. Persist queued sends before dispatch; require a successful provider result with an external ID before marking a send accepted.
- Validate webhook signatures over original bytes, retain raw events, route exact destination accounts, ignore echoes, preserve idempotency and recover pending processing. Handle early and out-of-order status callbacks without downgrading delivery state.
- Restrict realtime events to the workspace/entity and recheck membership, active account and token validity before delivery. Retain polling fallback.
- Correct booking ownership and exclusion constraints, frontend staff identifiers, team endpoints, lead links, analytics booking-link counts, navigation and account/unread displays.
- Harden production settings selection, ASGI startup, Docker secret exclusions, same-host API/WebSocket proxying and logging that previously risked including query-string credentials.

## 4. New features implemented

The unified inbox supports channel/search/unread filters, pagination, chronological message history with older-message loading, unread updates, conversation state, assignment, lead context and direct replies. Text replies and approved WhatsApp template submissions use real backend validation. Website inquiries enter the inbox; their composer explains that an outbound website transport is unavailable.

The outbound state machine is `QUEUED → SENDING → SENT → DELIVERED → READ`, with visible `FAILED` outcomes. Provider rejection, invalid/expired tokens, permission errors, rate limits, reply-window restrictions and ambiguous network outcomes are distinguishable. Client request IDs prevent duplicate submissions. Recovery drains committed queued messages; uncertain POSTs are not automatically repeated.

New DM automation includes workspace-owned rules/actions/executions, a management UI, dry-run preview and retained history. New administration commands diagnose messaging configuration, configure encrypted per-workspace channel credentials and adopt explicitly reviewed unowned legacy records. Signed Instagram deletion requests now have durable processing and a real confirmation/status endpoint.

## 5. Database migrations added

Twelve migration files were added or supplied to align existing model drift:

| App / migration | Purpose |
|---|---|
| `accounts/0004_user_email_verified_at` | Verification timestamp |
| `audit/0002_auditevent_organization` | Audit workspace ownership |
| `automations/0001_initial` | Automation, action and execution models |
| `bookings/0004_remove_booking_exclude_overlapping_active_bookings_and_more` | Booking ownership, backfill and tenant-aware exclusion constraint |
| `conversations/0006_remove_message_unique_external_message_id_and_more` | Message identity/state/outbound schema changes |
| `conversations/0007_backfill_conversation_organization` | Ownership backfill |
| `conversations/0008_messagereceipt` | Durable callback reconciliation |
| `customers/0003_remove_customeridentity_unique_channel_external_user_id_and_more` | Workspace-scoped external identities |
| `customers/0004_backfill_identity_organization` | Identity ownership backfill |
| `integrations/0003_datadeletionrequest` | Recoverable deletion requests |
| `scheduling/0002_blockedperiod_organization_and_more` | Scheduling ownership |
| `subscriptions/0003_alter_plan_code` | Align pre-existing plan model choices |

These ran against test databases only. Unknown legacy ownership is quarantined, not guessed. Review affected rows and use the dry-run adoption command before releasing production traffic.

## 6. APIs added/modified

Paths below are relative to `/api/v1/` unless specified.

| API | Change |
|---|---|
| `automations/`, `automations/{id}/` | Authorized CRUD, enabled/channel filters and validated ordered actions |
| `automations/{id}/test/` | Side-effect-free sample evaluation |
| `automations/history/` | Scoped, paginated execution results |
| `conversations/` | Scoped channel/search/unread listing |
| `conversations/{id}/messages/`, `read/`, `status/`, `assign/` | History and conversation management |
| `conversations/{id}/send/` | Idempotent, validated outbound request; HTTP 202 means queued |
| `leads/` and existing lead actions | Atomic creation, assignment, lifecycle validation and shared dispatch |
| `forms/{public_id}/submit/` | Anonymous, throttled website capture with path-scoped CORS |
| `webhooks/meta/instagram/`, `webhooks/meta/whatsapp/` | Verified challenges, signed events and durable processing |
| `integrations/health/` and OAuth routes | Non-secret diagnostics, connection/error states and guarded configuration |
| `integrations/data-deletion/{code}/` | Public random-code deletion status |
| `auth/password/reset/`, `password/reset/confirm/`, `email/verify/`, `email/resend/` | Recovery and verification; existing `accounts/` aliases retained |
| `organizations/team/`, `organizations/invitations/` | Membership checks, delivery handling and invitation acceptance |
| Existing booking, scheduling, notification, audit and admin APIs | Ownership/authorization and regression repairs |

The existing integration outbound endpoint also uses the shared service. WebSocket endpoints retain compatibility while preferring token authentication through the subprotocol instead of URL query strings.

## 7. Frontend pages/components added/modified

Added the DM Automation page/builder with create, edit, delete, enable/disable, channel, priority, triggers, conditions, ordered actions, preview and history. Updated inbox APIs/components, channel diagnostics, lead creation/detail/assignment, account recovery/verification/invitation screens, authentication cache handling, security settings and navigation.

The sidebar exposes existing Customers, Bookings, Calendar, Services and Availability pages and separates DM Automations from lead keywords. Unsupported report/segment/support entries and notification preferences have explicit disabled explanations. Header identity, membership role and unread counts now come from API data.

Screenshots from the real-browser test are included as `automation-builder.png`, `instagram-inbox.png` and `mobile-inbox.png`. They contain synthetic test contacts. Their queued messages and local “Connecting” indicator are not evidence of live Meta delivery or a production WebSocket connection.

## 8. Instagram functionality status

**Application-side implemented and mock-tested; live channel unverified.** Signed incoming DMs can create a scoped identity, conversation, message and lead, update unread state, evaluate automation and queue a permitted reply. Manual replies use the Instagram-scoped recipient ID and professional-account endpoint. Provider acceptance stores the external ID; supported read events update state. Echoes and repeated events do not create automation loops.

Missing configuration/permissions, token errors and closed reply windows return meaningful states. OAuth, deauthorization and deletion handling are implemented, but successful authorization, app approval, actual send acceptance and real callbacks were not exercised with Meta.

## 9. WhatsApp functionality status

**Application-side implemented and mock-tested; live channel unverified.** Incoming Cloud API messages and statuses share the tenant-safe ingestion/inbox architecture. Free-form messages obey the 24-hour customer-service window; outside it, the composer/API can submit an approved template with language/components. Meta remains authoritative about actual template approval and acceptance.

The OAuth path discovers existing owned business assets; it is not full Embedded Signup or a phone-registration wizard. It requires exactly one WABA/phone result; multiple assets use explicit administrator configuration. Real phone registration, permissions, delivery receipts and template sending remain deployment acceptance tasks.

## 10. DM Automation functionality status

Implemented triggers: incoming message, exact keyword, contains keyword and first interaction. Conditions cover lead status, required tag, message type and unassigned state. Actions support reply, create/find lead, change status, add tag, assign member and send booking link. Rules run in priority order and actions in configured order; later evaluation sees earlier lead changes.

Rules default disabled and require the relevant plan capability to activate/execute. Disabled rules, outbound messages and echoes do not trigger replies. Execution identity prevents duplicate evaluation for the same rule/message. History preserves rule names/results after rule deletion; completed lead actions and outbound delivery status remain distinct. Preview sends nothing and changes no records.

The builder, permission checks, matching, ordered execution, failures and idempotency passed automated tests. Live automatic reply acceptance remains subject to the same Meta approval and messaging rules as manual replies. Scheduled marketing follow-ups and comment campaigns are not implemented.

## 11. Tests created

Added 59 cases: 39 in `tests/test_messaging_platform.py`, 17 in `tests/test_platform_security.py`, one opt-in Chromium workflow in `tests/test_browser_platform.py` plus `frontend/tests/browser-platform.cjs`, and two realtime isolation/revocation cases.

Coverage includes stable identity/duplicate capture, signed webhook rejection/replay/routing, conversations, automation triggers/conditions/actions/disabled rules/history, queued dispatch, template/window rules, provider failure, early receipts, workspace isolation, recovery/verification, invitations, deletion and atomic lead assignment. Existing tests were updated with explicit workspace/configuration/reply-window fixtures and future booking dates. Production authorization and throttling were not weakened to accommodate old fixtures.

The browser test uses Vite, Chromium and a real Django test server/database. It creates and previews a multi-action rule, edits/disables it, opens Instagram and WhatsApp inbox threads, submits replies/templates, follows the full lead link and verifies mobile layout. Browser submissions validate queueing; separate service tests use mocked Meta responses to verify dispatch and external ID/status handling.

## 12. Tests passed/failed

| Check | Result |
|---|---|
| Initial suite run | 285 cases: 163 passed, 100 failed, 22 errors |
| Final complete suite with browser enabled | **344 passed, 0 failed, 0 errors** in 68.75 seconds |
| Focused Chromium rerun after final navigation/header changes | **1 passed** in 11.16 seconds |
| Final TypeScript/Vite production build | Passed |
| Django system check under test settings | Passed, zero issues |
| Migration consistency dry run | Passed, no changes detected |
| Production Compose configuration validation | Passed |
| Git whitespace/diff check | Passed |

The build reports an existing bundle-size advisory: the largest output chunk is approximately 663 KB. The normal suite skips the opt-in browser case unless `V4_BROWSER_TESTS=1`; the reported 344-case run enabled it. Linux container startup, real Redis crash recovery, production load, SMTP delivery and external Meta operations were not certified by these tests.

## 13. Meta permissions/approvals still required

Instagram uses Instagram API with Instagram Login for professional accounts: `instagram_business_basic` and `instagram_business_manage_messages`, with `messages,messaging_seen` account subscriptions. Permission and endpoint names were checked against [Meta's official Instagram collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-894be833-d0b6-4877-859e-c61ae6474d64).

WhatsApp requires `whatsapp_business_messaging` and `whatsapp_business_management`; the existing-business discovery flow additionally requests `business_management`. Configure a registered number, WABA and app subscription to the WABA, including the `messages` webhook field. See [Meta's official Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).

Confirm App Review/access levels, business verification where required, app roles/test recipients, privacy/deletion URLs and asset ownership in the actual Meta dashboard. None is assumed approved. The code's `v25.0` compatibility default is not claimed to be latest; production requires an explicitly selected supported version and live validation. Exact callback URLs, reviewer evidence and a ten-step live acceptance checklist are in `META_APPROVAL_READINESS.md`.

## 14. Environment variables required

Supply production Django settings, `SECRET_KEY`, `ALLOWED_HOSTS`, PostgreSQL variables, Redis/Celery URLs, `FRONTEND_URL`, explicit CORS/CSRF origins, `META_APP_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_GRAPH_API_VERSION` and `META_WHATSAPP_REDIRECT_URI`. SMTP variables are needed for actual recovery/verification/invitation delivery. `VITE_API_BASE_URL` is optional when using the same-host `/api/v1` proxy.

Normal sends use encrypted per-workspace `IntegrationConfig` credentials and destination IDs, not frontend secrets or shared global channel tokens. `configure_meta_channel` reads a temporary `META_CHANNEL_ACCESS_TOKEN` environment value. Preserve `SECRET_KEY`: existing credential encryption derives from it, so rotation requires coordinated re-encryption or reconnection. The complete variable table and configuration commands are in `MESSAGING_OPERATIONS.md` and `.env.production.example`.

## 15. Production deployment steps

1. Review the combined working tree, back up the database/configuration and rehearse deployment plus restore on staging.
2. Supply production secrets, supported API version, real domains and TLS certificates; review Nginx's existing concrete hostnames/certificate paths.
3. Stop writes/workers for the schema transition. Build the images, start PostgreSQL/Redis, run migrations, collect static files, run Django deployment checks and `check_messaging_platform`.
4. Review quarantined ownership records. Use `adopt_legacy_records` with explicit model/IDs in dry-run mode before `--apply`; do not infer ownership from whichever user logs in.
5. Start ASGI web, frontend, worker, one beat scheduler and Nginx. Verify readiness, authentication, tenant selection, inbox, booking availability, WebSockets and recovery tasks.
6. Configure the intended Meta assets, complete the approval checklist and run real inbound/manual/automated reply tests for both channels. Record actual provider IDs and callbacks before declaring either channel operational.

Exact commands, monitoring, retry behavior and rollback considerations are in `MESSAGING_OPERATIONS.md`. Production migration and deployment remain unperformed.

## 16. Remaining limitations

- No verified live Meta approval, authorization, send acknowledgment, template acceptance or delivery/read callback. These are release blockers for claiming operational messaging.
- One Instagram destination and one WhatsApp destination per workspace; no historical inbox import or automatic cross-channel contact merging.
- Website capture is inbound-only. Manual media upload/download proxying and a template approval/catalog editor are absent; supported media metadata/API URL handling is present.
- Automation supports inbound message workflows, not scheduled marketing follow-ups, comment-growth campaigns, bulk messaging or automated Human Agent exemptions.
- WhatsApp connection covers existing owned assets, not complete Embedded Signup/registration. Multiple discovered assets require explicit administrator selection/configuration.
- Unknown legacy ownership requires operator review. Independent booking records and backups follow a separate retention process from Instagram deletion.
- Billing-provider payment collection, SMTP delivery, production containers/TLS, real Redis fault recovery and load behavior remain unverified. Some optional UI features are explicitly disabled because their backend is unavailable.
- Automated coverage is meaningful but not exhaustive proof of every possible UI action, external event or production failure. The frontend bundle-size advisory remains.

**Release decision:** application-side core functionality passes the recorded checks; production rollout and external Meta operational acceptance are still required.
