# Nextora Meta production URLs

The code and local tests are ready for review. No commit, push, deployment, container restart, production environment edit, or application migration was performed for this update. Live Meta acceptance is still unverified.

## Diagnosis and behavior

Previously `callback_uri()` preferred the explicit redirect override, then the configured base, then the incoming request's host. Its HTTPS check still accepted loopback/tunnel hosts and arbitrary callback paths. A pre-fix local reproduction with `DEBUG=False` accepted HTTPS localhost, 127.0.0.1, a ngrok-free host, and the production callback missing its final slash. The example configuration left the Instagram callback/base blank and used a placeholder frontend origin.

These defects permit a URI different from the one registered with Meta. The reported `Invalid redirect_uri` is consistent with that mismatch, but the exact deployed value and Meta Dashboard entry were not inspected. A specific deployed before-URI cannot honestly be supplied. The earlier Nginx routing problem is reported fixed by the operator and was not changed here.

After this change, a production callback requires an explicit URI or base origin. It must use HTTPS, the canonical path, and its exact trailing slash. Loopback and ngrok hosts, userinfo, query/fragment additions, malformed ports, and noncanonical paths are rejected with `configuration_required`. URLs are validated without silently rewriting the override. The frontend return origin receives the same production host/scheme checks.

The URI selected at authorization is saved in `OAuthAttempt.redirect_uri` and reused unchanged for code exchange, even if settings change during the attempt. Existing single-use state, initiating membership validation, token encryption, account verification, subscription, webhook HMAC verification, idempotency, and Celery ingestion remain intact.

Before frontend route: `GET /api/v1/integrations/instagram/connect/`.

After frontend route: `GET /api/v1/integrations/oauth/instagram/login/`.

Both existing aliases remain compatible. Register only the canonical callback below with Meta. WhatsApp continues using the Facebook SDK Embedded Signup flow and authenticated POST `/api/v1/integrations/whatsapp/complete/`. It does not require `META_WHATSAPP_REDIRECT_URI`.

## Exact environment and Dashboard configuration

Set these nonsecret values in the deployed backend environment through the normal configuration process; this task did not edit the real environment file:

```dotenv
FRONTEND_URL=https://studio.nextoracreations.co.in
META_REDIRECT_BASE_URL=https://studio.nextoracreations.co.in
META_INSTAGRAM_REDIRECT_URI=https://studio.nextoracreations.co.in/api/v1/integrations/oauth/instagram/callback/
```

Required Meta configuration: `META_APP_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_GRAPH_API_VERSION`, and `META_WHATSAPP_CONFIG_ID`. Use the Instagram product's `META_INSTAGRAM_APP_ID` and `META_INSTAGRAM_APP_SECRET` where these differ from the main Meta application; the existing fallback is retained. App credentials and the registered callback must belong to the same app/product. All example credentials are placeholders. Preserve the existing `SECRET_KEY` used for encryption.

Keep `DJANGO_SETTINGS_MODULE=config.settings.production` and `DEBUG=False`. The production examples include the frontend/API hosts and trusted origins. The frontend API base remains relative `/api/v1`, resolving to `https://studio.nextoracreations.co.in/api/v1/`. No frontend secret or new Vite variable is needed.

| Meta Dashboard field | Exact value |
|---|---|
| Instagram OAuth Redirect URI | `https://studio.nextoracreations.co.in/api/v1/integrations/oauth/instagram/callback/` |
| Instagram Webhook Callback | `https://studio.nextoracreations.co.in/api/v1/webhooks/meta/instagram/` |
| Instagram Deauthorization Callback | `https://studio.nextoracreations.co.in/api/v1/integrations/oauth/instagram/deauthorize/` |
| Instagram Data Deletion Callback | `https://studio.nextoracreations.co.in/api/v1/integrations/oauth/instagram/data-deletion/` |
| WhatsApp Webhook Callback | `https://studio.nextoracreations.co.in/api/v1/webhooks/meta/whatsapp/` |
| Webhook verify token | `META_VERIFY_TOKEN` |
| Frontend/Embedded Signup website origin | `https://studio.nextoracreations.co.in` |

Instagram returns to `https://studio.nextoracreations.co.in/app/settings/channels`, with the existing success/error query parameters. The Channels page confirms server connection status before showing success.

WhatsApp's SDK flow is consistent with [Meta's official Embedded Signup guidance](https://www.postman.com/meta/whatsapp-business-platform/folder/b1a1oq8/step-1-embed-the-signup-flow). The official Instagram Business Login documentation returned HTTP 429 during research; no Dashboard acceptance or access-level approval was inferred from search results.

## Local development

Use `config.settings.local` (`DEBUG=True`). Set `FRONTEND_URL=http://localhost:5173`, `META_REDIRECT_BASE_URL=http://127.0.0.1:8002`, and clear the production `META_INSTAGRAM_REDIRECT_URI` override. The canonical callback path is appended to that base. With both callback settings empty, request-based discovery is permitted only in DEBUG mode.

For actual Meta development callbacks, configure an explicitly registered public HTTPS tunnel and DEBUG mode. Application support for local HTTP testing does not imply that Meta accepts localhost in its Dashboard. Production rejects these development hosts. Existing Vite development proxy/tunnel configuration is unchanged.

## Validation

- `python manage.py check`: no issues.
- Relevant integration/auth/security pytest suite: 263 passed, including 49 new production URL cases. All new external HTTP is mocked and guarded against accidental live requests.
- `node tests/meta-connections.cjs`: passed canonical Instagram endpoint, exact authorization redirect, rejection of profile URLs, and WhatsApp SDK/completion behavior with mocked API/SDK responses.
- `npm run build`: passed; existing large-chunk warning remains.
- `git diff --check`: required before review.

Backend command from the repository root:

```bash
python -m pytest apps/integrations/tests tests/test_instagram_integration.py tests/test_whatsapp_integration.py tests/test_integrations.py tests/test_auth_api.py tests/test_messaging_platform.py tests/test_platform_security.py -q --tb=short
```

The tests exercise callback replay rejection, invalid state, successful encrypted account storage, subscription, signed webhook ingestion, duplicates, and both provider verification paths. They use an isolated local test database, not the deployed database.

## Later EC2 deployment — commands only, not executed

These commands target the checked-in Docker Compose v2 production topology. Run from the confirmed EC2 application directory, after the approved release files are present. Do not use the general deployment script: this update needs no migration. Existing onboarding migrations must already be installed.

Risk: replacing web/frontend processes can briefly interrupt requests. The stricter checks deliberately stop onboarding when deployed URLs are invalid. Existing connected accounts/data are preserved. Retain the previous images and private configuration before updating the three public URL variables.

```bash
set -eu
docker compose version
umask 077
rollback_dir="$(mktemp -d /var/tmp/nextora-meta-rollback.XXXXXX)"
cp .env.production "$rollback_dir/env.production"
printf 'services:\n' > "$rollback_dir/images.yml"
for service in web frontend celery_worker celery_beat; do
  container_id="$(docker compose --env-file .env.production -f docker-compose.production.yml ps -q "$service")"
  test -n "$container_id"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
  printf '  %s:\n    image: "%s"\n' "$service" "$image_id" >> "$rollback_dir/images.yml"
done
printf 'Keep this private rollback directory: %s\n' "$rollback_dir"
```

The backup contains secrets; it is outside the repository with restricted permissions. Do not print/upload its contents or prune the saved images. Update only the approved public URL variables in the deployed configuration through your normal secure process, and register the exact Meta Dashboard values. Then:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml build web frontend celery_worker celery_beat
docker compose --env-file .env.production -f docker-compose.production.yml up -d --no-deps --wait web frontend celery_worker celery_beat
docker compose --env-file .env.production -f docker-compose.production.yml exec -T nginx nginx -t
docker compose --env-file .env.production -f docker-compose.production.yml exec -T nginx nginx -s reload
docker compose --env-file .env.production -f docker-compose.production.yml exec -T web python manage.py check
```

The proxy reload refreshes upstream addresses after service replacement; it does not change Nginx configuration. No database/container volume deletion, migration, secret rotation, git checkout, or automatic source update is included.

## Exact rollback procedure

Use the private `rollback_dir` printed above. Restore the previous environment and saved image references; do not rebuild or restore a database:

```bash
set -eu
test -f "$rollback_dir/env.production"
test -f "$rollback_dir/images.yml"
cp "$rollback_dir/env.production" .env.production
chmod 600 .env.production
docker compose --env-file .env.production -f docker-compose.production.yml -f "$rollback_dir/images.yml" up -d --no-deps --no-build --wait web frontend celery_worker celery_beat
docker compose --env-file .env.production -f docker-compose.production.yml exec -T nginx nginx -t
docker compose --env-file .env.production -f docker-compose.production.yml exec -T nginx nginx -s reload
```

If a new SSH session is used, first set `rollback_dir` to the exact previously recorded directory. Retain the corrected Meta callback registration if it was merely bringing the Dashboard into agreement with this canonical path; any intentional Dashboard rollback requires its own reviewed previous values.

## Remaining live acceptance

After approval/deployment, use a real eligible workspace to initiate Instagram login. Privately inspect only the decoded `redirect_uri` (do not share the complete authorization URL/state). Confirm Meta accepts it, callback reaches Django, account is stored, `subscribed_apps` succeeds, and Channels reports connected. Complete webhook verification using the configured verify token privately, then test incoming message delivery, duplicate handling and a reply. Repeat WhatsApp Embedded Signup and message checks. App permissions/review, product-specific credentials, TLS reachability, and live Meta acceptance are external requirements not proven by mocked tests.
