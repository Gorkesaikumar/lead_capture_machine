const { chromium, expect } = require('@playwright/test');

const base = process.env.V4_FRONTEND_URL || 'http://localhost:5173';
const orgA = '11111111-1111-4111-8111-111111111111';
const orgB = '22222222-2222-4222-8222-222222222222';
const token = 'realtime-regression-token';

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const errors = [];
    let workspaceId = orgA;
    let profileGate = null;
    page.on('pageerror', error => errors.push(error.message));
    await page.clock.install({ time: new Date('2026-09-06T00:00:00Z') });
    await page.clock.pauseAt(new Date('2026-09-06T00:00:00Z'));
    await page.addInitScript(({ token, orgA }) => {
      localStorage.setItem('authToken', token);
      localStorage.setItem('organizationId', orgA);
      window.sockets = [];
      window.diagnostics = [];
      window.maxActive = 0;
      window.online = true;
      Object.defineProperty(navigator, 'onLine', { get: () => window.online });
      window.network = online => {
        window.online = online;
        window.dispatchEvent(new Event(online ? 'online' : 'offline'));
      };
      const debug = console.debug.bind(console);
      console.debug = (...args) => { window.diagnostics.push(args); debug(...args); };
      window.lifecycleListeners = new Map(['online', 'offline', 'storage'].map(type => [type, new Set()]));
      const add = window.addEventListener.bind(window);
      const remove = window.removeEventListener.bind(window);
      window.addEventListener = (type, listener, ...args) => {
        window.lifecycleListeners.get(type)?.add(listener);
        return add(type, listener, ...args);
      };
      window.removeEventListener = (type, listener, ...args) => {
        window.lifecycleListeners.get(type)?.delete(listener);
        return remove(type, listener, ...args);
      };
      const NativeSocket = window.WebSocket;
      window.WebSocket = class {
        static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
        readyState = 0; sent = []; onopen = null; onclose = null; onmessage = null; onerror = null;
        constructor(url, protocols) {
          if (!url.includes('/admin/dashboard/')) return new NativeSocket(url, protocols);
          if (window.failConstruction) { window.failConstruction = false; throw new Error('fixture'); }
          this.url = url; this.protocols = protocols;
          window.sockets.push(this);
          window.maxActive = Math.max(window.maxActive, window.sockets.filter(s => s.readyState < 2).length);
        }
        open() { this.readyState = 1; this.onopen?.({}); }
        close(code = 1000) { this.readyState = 3; this.onclose?.({ code }); }
        fail(code = 1006) { this.onerror?.({}); this.close(code); }
        message(data) { this.onmessage?.({ data: JSON.stringify(data) }); }
        send(data) { if (this.readyState !== 1) throw new Error('closed socket send'); this.sent.push(JSON.parse(data)); }
      };
    }, { token, orgA });
    await page.route('**/api/v1/**', async route => {
      const isProfile = route.request().url().includes('/auth/me/');
      if (isProfile && profileGate) await profileGate;
      await route.fulfill({ status: 200, json: isProfile ? {
        id: 'realtime-user', email: 'realtime@example.test', is_active: true, is_staff: false, is_superuser: false,
        workspaces: workspaceId ? [{ id: workspaceId, name: 'Regression workspace', role: 'OWNER' }] : [],
      } : {},
      });
    });
    await page.goto(`${base}/tests/realtime-harness.html`);
    const count = () => page.evaluate(() => window.sockets.length);
    const active = () => page.evaluate(() => window.sockets.filter(socket => socket.readyState < 2).length);
    const open = () => page.evaluate(() => window.sockets.at(-1).open());
    const fail = code => page.evaluate(code => window.sockets.at(-1).fail(code), code);
    const status = value => expect(page.getByTestId('status')).toHaveText(value);
    const refreshUser = () => page.evaluate(token => window.controls.auth.login(token), token);
    const retryAfter = async delay => {
      const previous = await count();
      await page.clock.runFor(delay - 1);
      expect(await count()).toBe(previous);
      await page.clock.runFor(1);
      expect(await count()).toBe(previous + 1);
      expect(await active()).toBe(1);
    };
    await status('CONNECTING');
    const mountedListeners = await page.evaluate(() => [...window.lifecycleListeners.values()].map(listeners => listeners.size));
    expect(await count()).toBe(1);
    await page.evaluate(() => { window.controls.rerender(); window.network(true); window.network(true); });
    await refreshUser(); // New profile object, same authenticated identity.
    expect(await count()).toBe(1);
    await open();
    await status('CONNECTED');
    await refreshUser();
    expect(await count()).toBe(1);
    await page.evaluate(() => {
      const socket = window.sockets.at(-1);
      socket.message({ type: 'PONG' });
      socket.message({ type: 'CONNECTION_ESTABLISHED' });
      socket.message({ type: 'NEW_MESSAGE', payload: { lead_id: 'lead-fixture', conversation_id: 'conversation-fixture' } });
      window.realtime.sendPing();
    });
    expect(await page.evaluate(() => window.received.map(event => event.type))).toEqual(['NEW_MESSAGE']);
    expect(await page.evaluate(() => window.invalidations)).toEqual(expect.arrayContaining([
      ['leads', 'lead-fixture', 'conversation'], ['conversations', 'conversation-fixture', 'messages'], ['analytics'],
    ]));
    expect(await page.evaluate(() => window.sockets.at(-1).sent)).toEqual([{ type: 'ping' }]);

    // Short-lived OPEN sockets must retain exponentially increasing delays.
    for (const delay of [1000, 2000, 4000, 8000, 16000, 30000, 30000]) {
      await fail();
      await status('RECONNECTING');
      await page.evaluate(() => { window.network(true); window.controls.rerender(); });
      await retryAfter(delay);
      await open();
    }
    await page.clock.runFor(30000);
    expect(await page.evaluate(() => window.sockets.at(-1).sent)).toEqual([{ type: 'ping' }]);
    await fail();
    await retryAfter(1000); // Stable connection reset.

    // Stalled handshake closes before a replacement is created.
    await page.clock.runFor(15000);
    expect(await active()).toBe(0);
    await retryAfter(2000);
    await open();
    await fail();
    await page.evaluate(() => window.network(false));
    const offlineCount = await count();
    await page.clock.runFor(120000);
    expect(await count()).toBe(offlineCount);
    await status('DISCONNECTED');
    await page.evaluate(() => { window.network(true); window.network(true); });
    expect(await count()).toBe(offlineCount + 1);
    await open();
    // Offline while open detaches callbacks and heartbeat, then one online open.
    await page.evaluate(() => window.network(false));
    expect(await active()).toBe(0);
    await page.clock.runFor(60000);
    await page.evaluate(() => window.network(true));
    await open();

    // Organization change releases the old socket; queued old callbacks are inert.
    await page.evaluate(() => {
      const old = window.sockets.at(-1);
      window.oldSocket = old;
      window.staleCallbacks = [old.onopen, old.onclose, old.onmessage];
    });
    workspaceId = orgB;
    await refreshUser();
    await expect(page.getByTestId('identity')).toHaveText(orgB);
    await expect.poll(active).toBe(1);
    expect(await page.evaluate(() => window.oldSocket.readyState)).toBe(3);
    expect(await page.evaluate(() => [window.oldSocket.onopen, window.oldSocket.onclose, window.oldSocket.onmessage, window.oldSocket.onerror])).toEqual([null, null, null, null]);
    expect(new URL(await page.evaluate(() => window.sockets.at(-1).url)).searchParams.get('organization_id')).toBe(orgB);
    await page.evaluate(() => {
      window.staleCallbacks[0]({}); window.staleCallbacks[1]({ code: 1006 });
      window.staleCallbacks[2]({ data: JSON.stringify({ type: 'NEW_LEAD' }) });
    });
    expect(await page.evaluate(() => window.received.length)).toBe(1);
    await status('CONNECTING');
    await open();
    await page.evaluate(() => window.sockets.at(-1).message({ type: 'LEAD_UPDATED', payload: { id: 'new-workspace-lead' } }));
    expect(await page.evaluate(() => window.received.at(-1).type)).toBe('LEAD_UPDATED');

    // Unmount while reconnect is pending: no timer, heartbeat or event listener survives.
    await fail();
    await page.evaluate(() => window.controls.setMounted(false));
    await expect(page.getByTestId('status')).toHaveCount(0);
    const unmountedCount = await count();
    await page.clock.runFor(120000);
    await page.evaluate(() => { window.network(false); window.network(true); });
    expect(await count()).toBe(unmountedCount);
    // QueryClient retains its own online/offline listeners outside this provider.
    expect(await page.evaluate(() => [...window.lifecycleListeners.values()].map(listeners => listeners.size))).toEqual(mountedListeners.map(count => count - 1));
    await page.evaluate(() => window.controls.setMounted(true));
    await status('CONNECTING');
    expect(await active()).toBe(1); // StrictMode setup/cleanup/setup never overlaps.
    await open();
    await page.evaluate(() => window.sockets.at(-1).message({ type: 'BOOKING_UPDATED' }));
    expect(await page.evaluate(() => window.received.filter(event => event.type === 'BOOKING_UPDATED').length)).toBe(1);

    // Authorization rejection remains terminal, even through online events.
    await fail(4403);
    await status('DISCONNECTED');
    const rejectedCount = await count();
    await page.evaluate(() => { window.network(false); window.network(true); });
    await page.clock.runFor(120000);
    expect(await count()).toBe(rejectedCount);

    workspaceId = null;
    await refreshUser();
    await expect(page.getByTestId('identity')).toHaveText('none');
    await page.evaluate(() => window.network(true));
    expect(await count()).toBe(rejectedCount);
    workspaceId = orgA;
    await refreshUser();
    await status('CONNECTING');
    await open();
    await fail();
    workspaceId = null;
    await refreshUser();
    await expect(page.getByTestId('identity')).toHaveText('none');
    const missingOrgCount = await count();
    await page.clock.runFor(120000);
    await page.evaluate(() => window.network(true));
    expect(await count()).toBe(missingOrgCount);
    workspaceId = orgA;
    await refreshUser();
    await status('CONNECTING');
    await open();
    await fail();
    await page.evaluate(() => window.controls.auth.logout());
    await status('DISCONNECTED');
    const logoutCount = await count();
    await page.clock.runFor(120000);
    await page.evaluate(() => window.network(true));
    expect(await count()).toBe(logoutCount);

    // Login while offline is dormant; constructor failure then uses backoff.
    await page.evaluate(() => window.network(false));
    await refreshUser();
    expect(await count()).toBe(logoutCount);
    await page.evaluate(() => { window.failConstruction = true; window.network(true); });
    await status('RECONNECTING');
    await retryAfter(1000);
    await open();
    // A new token for the same user/workspace is a new session generation.
    const beforeRotation = await count();
    await page.evaluate(() => window.controls.auth.login('rotated-regression-token'));
    await status('CONNECTING');
    expect(await count()).toBe(beforeRotation + 1);
    expect(await active()).toBe(1);
    await open();
    // An event during a same-session profile refresh sees temporarily empty
    // organization storage. Resume after verification instead of staying stuck.
    let releaseProfile;
    profileGate = new Promise(resolve => { releaseProfile = resolve; });
    await page.evaluate(() => { window.pendingRefresh = window.controls.auth.login('rotated-regression-token'); });
    await expect.poll(() => page.evaluate(() => localStorage.getItem('organizationId'))).toBe(null);
    await page.evaluate(() => window.sockets.at(-1).message({ type: 'DASHBOARD_STATS_UPDATED' }));
    await status('DISCONNECTED');
    releaseProfile();
    profileGate = null;
    await page.evaluate(() => window.pendingRefresh);
    await status('CONNECTING');
    expect(await active()).toBe(1);
    await open();
    const beforeUnmount = await page.evaluate(() => window.sockets.at(-1).sent.length);
    await page.evaluate(() => { window.openUnmountSocket = window.sockets.at(-1); window.controls.setMounted(false); });
    await expect(page.getByTestId('status')).toHaveCount(0);
    await page.clock.runFor(120000);
    expect(await active()).toBe(0);
    expect(await page.evaluate(() => window.openUnmountSocket.sent.length)).toBe(beforeUnmount);
    expect(await page.evaluate(() => [window.openUnmountSocket.onopen, window.openUnmountSocket.onclose, window.openUnmountSocket.onmessage, window.openUnmountSocket.onerror])).toEqual([null, null, null, null]);
    await page.evaluate(() => window.controls.setMounted(true));
    await status('CONNECTING');
    await open();
    await page.evaluate(() => window.controls.auth.logout());
    await status('DISCONNECTED');
    expect(await active()).toBe(0);
    await refreshUser();
    await status('CONNECTING');
    await open();
    await page.evaluate(() => {
      localStorage.removeItem('authToken');
      window.dispatchEvent(new StorageEvent('storage', { key: 'authToken' }));
    });
    await status('DISCONNECTED');
    expect(await active()).toBe(0);
    const storageCount = await count();
    await page.clock.runFor(120000);
    await page.evaluate(() => window.network(true));
    expect(await count()).toBe(storageCount);
    expect(await page.evaluate(() => window.maxActive)).toBe(1);
    const diagnostics = await page.evaluate(() => JSON.stringify(window.diagnostics));
    for (const secret of [token, 'rotated-regression-token', orgA, orgB, 'lead-fixture', 'conversation-fixture', 'example.test']) expect(diagnostics).not.toContain(secret);
    expect(errors).toEqual([]);
    console.log('PASS realtime: one active socket; stable session renders; bounded exponential backoff; stable reset; handshake timeout; offline/online; organization/logout/storage cleanup; unmount + StrictMode; terminal rejection; heartbeat; event delivery/cache invalidation; secret-free diagnostics.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
