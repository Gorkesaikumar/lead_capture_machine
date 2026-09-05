# Instagram DM destination resolution fix

Branch: `feature/lead-capture-machine`. Changes were made and tested locally. No commit, push, deployment, production replay or production configuration change was performed.

## Root cause and evidence

Previously both parser paths calculated `normalized.destination_id` as `recipient.id` or, if missing, `entry.id`. Only the chosen ID survived normalization. The pipeline then required an exact JSON-string match on `IntegrationConfig.metadata.destination_id`. A connection stored under `account_id`, an older numeric JSON ID, or an Instagram envelope account ID different from the recipient representation could therefore produce the reported zero-match ValueError despite a normalized message being present. The same error correctly protected against ambiguous matches.

The connection code already distinguishes the OAuth token exchange's `user_id` from the Professional account returned by authenticated `/me`. It stores the latter as `destination_id` and `account_id`, but previously discarded `/me.id` when `/me.user_id` was present. Treating every OAuth subject as a webhook account alias would undo that distinction.

A second issue was the unconditional `capture_message_lead()` fallback after no trigger matched. That created Instagram leads from unrelated DMs, contrary to the requested keyword behavior.

The exact failing production payload and stored ID mapping were not available locally. Local read-only inspection found only a synthetic connection and no corresponding real DM. The tests reproduce the failure condition with clearly labelled synthetic fixtures using realistic, distinct account/customer IDs; they are not proof of a successful live delivery for `sai_kumar_drlg`.

## Exact mapping

| Input | Interpretation and handling |
| --- | --- |
| `entry[].messaging[].recipient.id` | Primary inbound Professional account destination. |
| `entry[].changes[field=messages].value.recipient.id` | Same destination role for the changes envelope. |
| `entry.id`, when `object=instagram` | Additional account-scoped envelope identity; retained even when recipient exists, and used when recipient is absent. |
| `sender.id` in either format | External customer IGSID, stored as the customer identity and used for replies. Never supplied to the workspace lookup. |
| Generic `value.id`, `value.account_id`, `value.metadata.*` | Not accepted as account-routing proof in these message formats. |
| `entry.id` when `object=page` | Not assumed to be an Instagram account; an explicit recognized recipient is required for message routing. |

Account identifiers must be positive numeric strings or integers, up to 32 digits. Empty, boolean, malformed and structured values do not become aliases. Explicit malformed recipients fail instead of silently falling back.

The resolver matches the union of valid recipient/envelope IDs against `metadata.destination_id`, `metadata.account_id`, and `metadata.profile_id` for `auth_architecture=instagram_login`. `profile_id` is newly saved from the same authenticated `/me` response as the canonical account, never copied from a webhook. Numeric JSON values are compared as text. Standalone `oauth_user_id` is excluded; if it equals an independently verified account/profile ID, that verified field already provides the match.

Only active Instagram configurations in active, non-deleted organizations qualify. Exactly one configuration must match across all supplied identities. Zero matches and cross-workspace/alias conflicts raise the existing error before customer, conversation, message or lead writes. OAuth connection creation checks alias collisions before saving or subscribing the account. Matching both aliases on the same row does not count twice.

Meta's [official Instagram collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-1ff01566-3509-48bd-a0f4-8571a91ccfdf) describes inbound message recipients as the app user's Instagram account and customer messaging in terms of Instagram-scoped IDs. The new verified-profile alias is an architectural inference from the app's authenticated `/me` response, not a claim that every OAuth identifier is interchangeable across Meta login architectures. No undocumented generic metadata fallback was added.

## Persistence, triggers and diagnostics

The existing path remains: signed webhook receiver → durable RawWebhookEvent → Celery → parser → unique workspace resolution → Customer/Conversation upsert → Message persistence → LeadDetectionService → lead/automation handling.

New Instagram messages still invoke `LeadDetectionService.process_inbound_message()`. Existing lowercase/punctuation normalization and word-boundary CONTAINS matching are unchanged. All four requested “baby shoot” examples match. Unrelated text and partial words do not create an Instagram lead. Existing active leads still receive follow-up activity. WhatsApp retains its phone-number routing and capture-all fallback.

Raw payload hashes and provider MID deduplication remain in place. Duplicate messages skip lead and automation evaluation. Existing row locks and transaction boundaries are preserved. Echo suppression now also applies to the changes envelope.

Structured stages `instagram_message_normalized` and `instagram_destination_resolved` contain the raw-event ID, destination ID, sender ID, candidate envelope IDs and resolution count. They do not contain DM text, access tokens, OAuth codes, secrets or full payloads.

## Files changed for this request

- `apps/integrations/meta/instagram/identity.py` — validated account IDs and alias lookup.
- `apps/integrations/meta/base.py` — normalized envelope account aliases.
- `apps/integrations/meta/instagram/parser.py` — retain recipient/envelope identities; suppress changes echoes.
- `apps/integrations/pipeline.py` — tenant-safe resolution, safe stages and trigger-gated Instagram leads.
- `apps/integrations/connection_service.py` — persist authenticated profile ID and reject alias ownership conflicts.
- `apps/integrations/tests/test_instagram_destination.py` — new routing, receiver/Celery, keyword, deduplication, logging and WhatsApp regressions.
- `apps/integrations/tests/test_instagram_login.py` — verified profile identity and alias collision assertions.
- `apps/integrations/tests/test_instagram_inbound.py` and `test_instagram_outbound.py` — replace nonnumeric business-account placeholders with realistic numeric fixture IDs.
- `tests/test_messaging_platform.py` — explicitly configure the Instagram keyword trigger for the existing full lead/automation flow.
- This report.

## Remaining production verification

Compare only the failing event's recipient/envelope IDs with the connection's stored account IDs. If neither is a known account ID and the only match is a differing OAuth subject, processing deliberately continues to fail closed. Verify the same account via authenticated `/me` before adding an alias or reconnecting. Historical connections do not automatically acquire the new `profile_id`. No production records were changed or replayed as part of this work.

## Test results

Final combined run: **366 passed in 39.65 seconds**. This comprises 238 integration tests, one lead concurrency test, and 127 broader Instagram/WhatsApp, trigger, message idempotency and tenant-isolation tests. Added 43 destination/DM cases and two OAuth alias-collision cases, plus an assertion that the authenticated profile ID is persisted.

Requested `pytest apps/integrations -v` and `pytest apps/leads -v` were run through the project's `.venv/Scripts/python.exe -m pytest`, with `--reuse-db` and short tracebacks. The final combined run included all their tests and the broader regression modules. No outbound live Meta calls or real DMs were used.

`python manage.py check`: passed with no issues. `git diff --check`: passed (exit 0). No database schema migration is required.
