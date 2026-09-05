# WebSocket reconnect audit

Reviewed September 6, 2026. Changes are local only; no commit, deployment, backend change or Redis infrastructure change was performed.

## Findings and root-cause boundary

The frontend had two concrete reconnect-amplification defects:

1. The connection callback and lifecycle effect depended on the entire `user` object. Replacing a profile with an equivalent authenticated user/workspace caused cleanup and a new socket. Ordinary renders with the same user reference were **not** an every-render reconnect loop.
2. `onopen` immediately reset the attempt counter. If the server accepted a connection and then failed shortly afterward, every retry returned to the shortest delay. The previous formula also used a 1.5 multiplier rather than the documented doubling sequence.

Additional lifecycle gaps: a connect call replaced an existing CONNECTING/OPEN socket rather than returning; offline state was not checked; cleanup did not detach all socket callbacks; open/message callbacks did not reject obsolete sockets; constructor failures stopped permanently; and there was no deadline for a stalled handshake. Existing cleanup did clear its tracked heartbeat/reconnect timers and the close callback already checked socket identity. This audit does not claim those existing timers were proven to leak in production.

The repository has one `RealtimeProvider` placement and one application WebSocket creation site. The `/ws/admin/dashboard/` path is the existing organization event stream, despite its name. The consumer joins the authenticated organization's group and handles the existing ping/PONG and realtime event protocol.

**The cause of the Redis read timeout is not established by this frontend audit.** The supplied Redis PONG, Django ping, low memory use and successful analytics REST responses establish basic availability for those operations, but do not establish that the Channels receive path is healthy. Repeated socket connections can be a consequence of a backend failure, and frontend retry behavior can amplify that churn. No production trace was collected in this task, so the frontend defects should not be presented as proof of the Redis timeout's cause. Likewise, the supplied CancelledError line alone does not establish why cancellation occurred.

## Implemented behavior

- Lifecycle ownership is keyed by authenticated user ID, verified token and workspace ID, rather than profile object reference. Each mounted application/tab maintains at most one CONNECTING or OPEN socket for its current session/workspace; separate browser tabs remain separate application instances.
- Tokens are captured when AuthContext publishes a verified profile. A verified profile refresh can resume a connection stopped during temporarily cleared login storage, without replacing a healthy socket or bypassing pending backoff.
- Retry delays: 1, 2, 4, 8, 16, 30 seconds, then capped at 30 seconds. The attempt counter resets only after 30 seconds continuously connected.
- A 15-second handshake deadline bounds CONNECTING failures. Constructor failures use the same retry scheduler.
- Logout, missing organization/token, storage identity changes, offline state and unmount prevent reconnection. Online events resume only an eligible session and cannot create duplicate sockets or bypass a pending retry.
- Cleanup detaches socket handlers, clears reconnect/heartbeat/stability/handshake timers, closes the current socket, and removes online/offline/storage listeners. Obsolete queued callbacks are ignored by generation and socket identity checks.
- Existing clean/auth/policy close handling remains terminal; observed codes 1000, 1008, 4001, 4003, 4401 and 4403 stop retries for that lifecycle.
- Existing subscriptions, wildcard handlers, cache invalidation, notifications and 30-second heartbeat remain. `lastEvent` clears at a session/workspace boundary.
- Console diagnostics record connection count, retry attempt, delay and close code. They omit tokens, subprotocols, URLs, organization/user identifiers and message contents. Enable Debug/Verbose console output to see `[realtime]` entries.

Example diagnostic:

```text
[realtime] reconnect scheduled { connection: 4, attempt: 3, delayMs: 4000 }
```

## Exact files changed

- `frontend/src/contexts/RealtimeContext.tsx`: lifecycle fixes and diagnostics; existing event mappings preserved.
- `frontend/tests/realtime-lifecycle.cjs`: Playwright regression suite with controlled WebSocket failures and virtual time.
- `frontend/tests/realtime-harness.html`: development test entry point, excluded from the production build inputs.
- `frontend/tests/realtime-harness.tsx`: fixture mounting the real AuthProvider and RealtimeProvider under React StrictMode.
- `docs/WEBSOCKET_RECONNECT_REVIEW.md`: this report.

Read-only backend review: `apps/core/consumers.py` and `config/settings/base.py`. Channels groups, capacity, expiry, Redis hosts and infrastructure were not changed.

## Validation

Run frontend commands from `frontend/` with its Vite development server running. `V4_FRONTEND_URL` can override the test server URL (default `http://localhost:5173`).

- `node tests/realtime-lifecycle.cjs`: passed. Covers equivalent-profile refreshes while CONNECTING and OPEN; ordinary renders; exact retry timing and cap; stable reset; constructor and handshake failures; repeated online events; offline during retries and active connections; organization replacement and stale callbacks; missing organization during retry; logout during retry and active connection; token rotation; delayed profile verification; storage-triggered logout; terminal rejection; unmount while retrying and open; StrictMode cleanup; heartbeats; single event delivery and query invalidation. Maximum observed active socket count was one. Diagnostics were checked for fixture identifiers/secrets.
- `node tests/dashboard-access.cjs`: passed using the existing browser WebSocket routing fixtures.
- `node tests/login-errors.cjs`: passed.
- `node tests/privacy-policy.cjs`: passed during the audit, including public route isolation from realtime.
- `npm run build`: passed after the final runtime changes, including TypeScript, Vite and privacy prerendering. The existing large-bundle warning remains.
- `npx oxlint src/contexts/RealtimeContext.tsx`: no errors; two Fast Refresh warnings for the pre-existing pattern of exporting hooks alongside the provider.
- `git -c core.safecrlf=false diff --check`: passed.

The lifecycle suite tests the real frontend providers with simulated transport failures, not the production Redis connection. After a separately authorized deployment, correlate browser `[realtime]` attempt/delay/close records with backend connection timestamps. If Redis timeouts persist with bounded frontend reconnects, inspect the complete Channels/Redis traceback and deployed dependency/timeout configuration before choosing a backend or infrastructure change.
