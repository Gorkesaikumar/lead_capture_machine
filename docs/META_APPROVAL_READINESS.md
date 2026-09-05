# Meta approval and live acceptance

Application implementation and external approval are separate. No real Meta send acknowledgment or delivery callback was verified during this task. All automated outbound acceptance responses were mocked.

## Products and permissions

The implemented Instagram path is **Instagram API with Instagram Login** for a professional account. Request `instagram_business_basic` and `instagram_business_manage_messages`. It sends through `graph.instagram.com/{version}/{account-id}/messages`, using the customer's Instagram-scoped ID from the inbound event. The recipient must have contacted the professional account. These names and this endpoint are documented in [Meta's official Instagram collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-894be833-d0b6-4877-859e-c61ae6474d64).

WhatsApp uses **WhatsApp Cloud API** with `whatsapp_business_messaging` and `whatsapp_business_management`. The business-asset discovery OAuth path also requests `business_management` because it queries a user-selected business portfolio's owned WABAs. Sending uses `graph.facebook.com/{version}/{phone-number-id}/messages`. Subscribe the app to its WABA through `/{waba-id}/subscribed_apps`; subscribing the callback URL alone is insufficient. See [Meta's official Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).

A registered business phone number, WABA and suitable token are needed. Test accounts and allowed test recipients must be configured in the actual app dashboard. For accounts outside app roles, obtain the access level and App Review approvals required by that dashboard. Complete business verification and provider onboarding where Meta requires them for the intended deployment. This task could not inspect the app's access levels, verification status, approved scopes or test roles, so none is assumed approved.

The WhatsApp login implemented here authorizes **existing owned business assets**. It asks for a business portfolio ID and fails if there is not exactly one WABA and phone to select. It is not a complete Embedded Signup or phone-registration wizard. For multiple assets, use the explicit administrator channel-configuration command with the verified phone-number ID and token. Registration and asset setup remain in Meta's dashboard.

## Webhooks and URLs

Replace `api.example.com` with the public HTTPS host. Register exact URLs, including trailing slashes.

| Purpose | URL/path |
|---|---|
| Instagram webhook | `https://api.example.com/api/v1/webhooks/meta/instagram/` |
| WhatsApp webhook | `https://api.example.com/api/v1/webhooks/meta/whatsapp/` |
| Instagram OAuth callback | `/api/v1/integrations/oauth/instagram/callback/` |
| WhatsApp OAuth callback | `/api/v1/integrations/oauth/whatsapp/callback/` |
| Instagram deauthorization | `/api/v1/integrations/oauth/instagram/deauthorize/` |
| Instagram data deletion | `/api/v1/integrations/oauth/instagram/data-deletion/` |
| Deletion status returned by callback | `/api/v1/integrations/data-deletion/{random-code}/` |

The Instagram connection requests `messages,messaging_seen` on the account subscription. WhatsApp uses the `messages` webhook field for incoming messages and message statuses. The application supports Instagram message/read events and WhatsApp incoming/status events. Confirm each subscription and available field against the app's selected API version in the Meta dashboard. Unsupported events are not interpreted as messages or automation triggers.

Set a strong, matching `META_VERIFY_TOKEN` in the backend and the webhook configuration. The callback answers the GET challenge only for the matching subscribe request. Every POST must carry a valid `X-Hub-Signature-256` calculated with the app secret over the original bytes. Reverse proxies must preserve the body and signature header.

## Messaging rules

The application enforces a conservative 24-hour free-form window from the latest incoming provider timestamp. Outside it, WhatsApp requires an approved template and Instagram waits for a new customer message. Template name, language and component parameters are submitted to Meta, which remains authoritative about approval and delivery. See [Meta's approved-template API reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/template/).

Human Agent access is a separate reviewed capability and disallows automated messages; V4 Studio does not use that tag to extend automation windows. See [Meta's Human Agent documentation in its official collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df).

No unofficial API, browser-session scraping or policy bypass is used.

## API version

The code's compatibility default is `v25.0`; it is **not presented as the latest version**. Production requires an explicit `META_GRAPH_API_VERSION`. The official version-release page could not be retrieved reliably during this audit. Select a currently supported version in the actual Meta app dashboard, review its changes, and run the live checks below before enabling traffic. Permission and endpoint names above were checked against Meta's official collections on 5 September 2026.

## App Review evidence to prepare

Provide the reviewer with an accessible staging URL, an app test account, exact login/connection steps and a screencast showing: incoming message → correct workspace inbox → lead capture → manual reply → stored external message ID. Show a second screencast for an enabled keyword automation and its execution history. Explain each requested permission by the screen/API action that needs it.

Provide real privacy-policy, terms and data-deletion information, a working deletion callback/status flow and current support details. Test deauthorization, denied authorization and expiry paths. Do not represent screenshots from mocked automated tests as proof of Meta delivery.

## Live acceptance checklist — not yet executed

1. Confirm app product configuration, access levels, permissions, business verification, professional account/WABA ownership, phone registration and test-user roles in Meta.
2. Configure exact redirect URLs, HTTPS, verify token and signed webhook subscriptions. Confirm the app is subscribed to the destination asset, not just a test callback.
3. Connect a test destination to a dedicated workspace. Check that diagnostics initially say `CONFIGURED_UNVERIFIED`.
4. Send a real Instagram DM from a permitted test user. Confirm one raw event, one stored message, one stable identity, a lead and an unread inbox item in that workspace. Resend the same webhook to confirm deduplication.
5. Reply through the inbox. Record the real Meta HTTP result and external message ID without exposing the token. Only then record send acceptance. Confirm supported read/delivery callbacks separately.
6. Repeat the inbound and manual reply checks for WhatsApp. Check `sent`, `delivered`, `read` and failed callbacks with their message IDs.
7. Enable a keyword automation in a plan that permits it. Send a new real incoming message; verify exactly one execution and one accepted automatic reply. Disable it and verify the next message receives no automation reply.
8. Use an old WhatsApp conversation outside the reply window: free-form must be blocked, while an approved matching template is attempted and its actual response retained. Verify the Instagram blocked-window message too.
9. Exercise revoked/expired tokens, missing permissions, broker interruption, worker restart, unavailable SMTP and a second workspace. Failed/unconfirmed sends must never show fake success or leak across workspaces.
10. Record dated evidence and remaining failures in the deployment release record. Only declare the channel operational after actual provider acceptance and the relevant callback checks succeed.
