import React, { createContext, useContext, useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuth } from "./AuthContext";

export type ConnectionStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "RECONNECTING";

export interface RealtimeEvent<T = any> {
  type: string;
  payload: T;
  timestamp: string;
}

interface RealtimeContextType {
  status: ConnectionStatus;
  lastEvent: RealtimeEvent | null;
  subscribe: (eventType: string, handler: (payload: any, event: RealtimeEvent) => void) => () => void;
  sendPing: () => void;
}

const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ConnectionStatus>("DISCONNECTED");
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const connectionCountRef = useRef(0);
  const resumeRef = useRef<(() => void) | null>(null);
  const listenersRef = useRef<Map<string, Set<(payload: any, event: RealtimeEvent) => void>>>(new Map());
  // Depend on session identity, not the profile object's reference.
  const userId = user?.id;
  const organizationId = user?.workspace?.id;
  // AuthContext publishes a new profile only after verifying the stored token.
  // Do not adopt a login's pending token on an unrelated loading-state render.
  const token = useMemo(() => user ? localStorage.getItem("authToken") : null, [user]);

  const dispatchEvent = useCallback((event: RealtimeEvent) => {
    setLastEvent(event);

    // Invoke registered listeners for this event type
    const listeners = listenersRef.current.get(event.type);
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(event.payload, event);
        } catch {
          console.error("[realtime] Event listener failed");
        }
      });
    }

    // Global listeners
    const wildcardListeners = listenersRef.current.get("*");
    if (wildcardListeners) {
      wildcardListeners.forEach((listener) => {
        try {
          listener(event.payload, event);
        } catch {
          console.error("[realtime] Wildcard listener failed");
        }
      });
    }

    // Core TanStack Query Cache invalidation handlers
    switch (event.type) {
      case "NEW_MESSAGE": {
        const payload = event.payload || {};
        if (payload.lead_id) {
          queryClient.invalidateQueries({ queryKey: ["leads", payload.lead_id, "conversation"] });
          queryClient.invalidateQueries({ queryKey: ["leads", "detail", payload.lead_id] });
        }
        if (payload.conversation_id) {
          queryClient.invalidateQueries({ queryKey: ["conversations", payload.conversation_id, "messages"] });
        }
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["subscriptions"] });

        // If inbound message, notify admin
        if (payload.direction === "INBOUND") {
          toast.info("New message received", {
            description: payload.text ? (payload.text.length > 60 ? payload.text.slice(0, 60) + "..." : payload.text) : "New media message",
          });
        }
        break;
      }

      case "MESSAGE_UPDATED": {
        const payload = event.payload || {};
        if (payload.conversation_id) {
          queryClient.invalidateQueries({ queryKey: ["conversations", payload.conversation_id, "messages"] });
        }
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
        break;
      }

      case "NEW_LEAD": {
        const payload = event.payload || {};
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
        toast.success("New Lead Detected!", {
          description: payload.customer_name ? `New inquiry from ${payload.customer_name}${payload.service_name ? ` about ${payload.service_name}` : ""}.` : "A new lead was captured in this workspace.",
        });
        break;
      }

      case "LEAD_UPDATED": {
        const payload = event.payload || {};
        if (payload.id) {
          queryClient.invalidateQueries({ queryKey: ["leads", payload.id, "conversation"] });
          queryClient.invalidateQueries({ queryKey: ["leads", "detail", payload.id] });
        }
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
        break;
      }

      case "BOOKING_CREATED": {
        const payload = event.payload || {};
        queryClient.invalidateQueries({ queryKey: ["bookings"] });
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
        toast.success("Booking Confirmed!", {
          description: `Booking #${payload.reference_id || ""} confirmed for ${payload.customer_name || "Customer"}.`,
        });
        break;
      }

      case "BOOKING_UPDATED": {
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        queryClient.invalidateQueries({ queryKey: ["bookings"] });
        break;
      }

      case "DASHBOARD_STATS_UPDATED": {
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
        break;
      }

      default:
        break;
    }
  }, [queryClient]);

  useEffect(() => {
    // All callbacks and timers belong to this session/organization generation.
    let disposed = false;
    let suspended = false;
    let terminal = false;
    let attempts = 0;
    let reconnectTimer: number | null = null;
    let heartbeatTimer: number | null = null;
    let stableTimer: number | null = null;
    let handshakeTimer: number | null = null;
    setLastEvent(null);
    setStatus("DISCONNECTED");

    const sessionMatches = () => userId != null && !!organizationId && !!token
      && localStorage.getItem("authToken") === token
      && localStorage.getItem("organizationId") === organizationId;
    const canConnect = () => !disposed && !suspended && !terminal
      && navigator.onLine && sessionMatches();
    // Never log URLs, protocols, tokens, organization IDs or message bodies.
    const diagnostic = (event: string, detail: Record<string, string | number> = {}) => {
      console.debug("[realtime]", event, { connection: connectionCountRef.current, attempt: attempts, ...detail });
    };
    const clearSocketTimers = () => {
      if (heartbeatTimer !== null) window.clearInterval(heartbeatTimer);
      if (stableTimer !== null) window.clearTimeout(stableTimer);
      if (handshakeTimer !== null) window.clearTimeout(handshakeTimer);
      heartbeatTimer = stableTimer = handshakeTimer = null;
    };
    const clearReconnect = () => {
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    };
    const detach = (socket: WebSocket) => {
      socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
    };
    const releaseSocket = (reason: string) => {
      clearSocketTimers();
      const socket = wsRef.current;
      wsRef.current = null;
      if (!socket) return;
      detach(socket);
      if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
        socket.close(1000, reason);
      }
      diagnostic("disconnect", { reason });
    };
    const stop = (reason: string) => {
      clearReconnect();
      releaseSocket(reason);
      if (!disposed) setStatus("DISCONNECTED");
    };
    const scheduleReconnect = () => {
      if (!canConnect()) {
        if (!disposed) setStatus("DISCONNECTED");
        return;
      }
      if (reconnectTimer !== null) return;
      // Cap the exponent too, so prolonged outages cannot overflow it.
      const delay = Math.min(1000 * 2 ** Math.min(attempts, 5), 30000);
      attempts += 1;
      setStatus("RECONNECTING");
      diagnostic("reconnect scheduled", { delayMs: delay });
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, delay);
    };
    const connect = () => {
      if (!canConnect()) {
        if (!disposed) setStatus("DISCONNECTED");
        return;
      }
      const existing = wsRef.current;
      if (existing && (existing.readyState === WebSocket.CONNECTING || existing.readyState === WebSocket.OPEN)) return;
      clearReconnect();
      setStatus(attempts > 0 ? "RECONNECTING" : "CONNECTING");
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const base = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, "")
        || `${protocol}//${window.location.host}/ws`;
      const wsUrl = `${base}/admin/dashboard/?organization_id=${encodeURIComponent(organizationId!)}`;
      connectionCountRef.current += 1;
      diagnostic("connect");
      let socket: WebSocket;
      try {
        socket = new WebSocket(wsUrl, ["v4", `token.${token}`]);
      } catch {
        diagnostic("creation failed");
        scheduleReconnect();
        return;
      }
      wsRef.current = socket;
      const isCurrent = () => !disposed && wsRef.current === socket;
      // Bound stalled handshakes; browser CONNECTING must not last indefinitely.
      handshakeTimer = window.setTimeout(() => {
        if (!isCurrent()) return;
        releaseSocket("Connection timeout");
        scheduleReconnect();
      }, 15000);
      socket.onopen = () => {
        if (!isCurrent()) return;
        if (!canConnect()) { stop("Session unavailable"); return; }
        if (handshakeTimer !== null) window.clearTimeout(handshakeTimer);
        handshakeTimer = null;
        setStatus("CONNECTED");
        diagnostic("connected");
        // A briefly OPEN socket must not reset backoff during a server outage.
        stableTimer = window.setTimeout(() => {
          stableTimer = null;
          if (isCurrent() && canConnect() && socket.readyState === WebSocket.OPEN) {
            attempts = 0;
            diagnostic("stable");
          }
        }, 30000);
        heartbeatTimer = window.setInterval(() => {
          if (!isCurrent()) return;
          if (!canConnect()) { stop("Session unavailable"); return; }
          if (socket.readyState === WebSocket.OPEN) {
            try { socket.send(JSON.stringify({ type: "ping" })); }
            catch { releaseSocket("Heartbeat send failed"); scheduleReconnect(); }
          }
        }, 30000);
      };
      socket.onmessage = (event) => {
        if (!isCurrent()) return;
        if (!canConnect()) { stop("Session unavailable"); return; }
        try {
          const data = JSON.parse(event.data);
          if (data?.type === "PONG" || data?.type === "CONNECTION_ESTABLISHED") return;
          if (typeof data?.type === "string") {
            dispatchEvent({ type: data.type, payload: data.payload || {}, timestamp: data.timestamp || new Date().toISOString() });
          }
        } catch {
          diagnostic("invalid message");
        }
      };
      // Browsers follow errors with close; only close schedules a retry.
      socket.onerror = () => { if (isCurrent()) diagnostic("transport error"); };
      socket.onclose = (event) => {
        if (!isCurrent()) return;
        clearSocketTimers();
        detach(socket);
        wsRef.current = null;
        diagnostic("disconnected", { code: event.code });
        terminal = [1000, 1008, 4001, 4003, 4401, 4403].includes(event.code);
        if (terminal) setStatus("DISCONNECTED");
        else scheduleReconnect();
      };
    };
    const onOffline = () => stop("Browser offline");
    const onOnline = () => {
      if (canConnect() && reconnectTimer === null) connect();
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === null || event.key === "authToken" || event.key === "organizationId") {
        if (!sessionMatches()) {
          // Another tab changed identity. Wait for AuthContext to authenticate it.
          suspended = true;
          stop("Session changed");
        }
      }
    };
    resumeRef.current = () => {
      suspended = false;
      onOnline();
    };
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    window.addEventListener("storage", onStorage);
    connect();
    return () => {
      disposed = true;
      resumeRef.current = null;
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("storage", onStorage);
      stop("Session cleanup");
    };
  }, [userId, organizationId, token, dispatchEvent]);

  // A verified profile refresh can restore temporarily cleared login storage.
  // Resume a stopped connection, retaining healthy sockets and pending backoff.
  useEffect(() => { resumeRef.current?.(); }, [user]);

  const subscribe = useCallback((eventType: string, handler: (payload: any, event: RealtimeEvent) => void) => {
    if (!listenersRef.current.has(eventType)) {
      listenersRef.current.set(eventType, new Set());
    }
    const set = listenersRef.current.get(eventType)!;
    set.add(handler);

    return () => {
      set.delete(handler);
      if (set.size === 0) {
        listenersRef.current.delete(eventType);
      }
    };
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ping" }));
    }
  }, []);

  return (
    <RealtimeContext.Provider value={{ status, lastEvent, subscribe, sendPing }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error("useRealtime must be used within a RealtimeProvider");
  }
  return context;
}

/**
 * Hook to listen to a specific real-time event.
 */
export function useRealtimeEvent<T = any>(
  eventType: string,
  handler: (payload: T, event: RealtimeEvent<T>) => void,
  deps: any[] = []
) {
  const { subscribe } = useRealtime();

  useEffect(() => {
    const unsubscribe = subscribe(eventType, handler);
    return () => unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subscribe, eventType, ...deps]);
}
