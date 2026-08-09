import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
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
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const listenersRef = useRef<Map<string, Set<(payload: any, event: RealtimeEvent) => void>>>(new Map());

  const getWsUrl = useCallback(() => {
    const token = localStorage.getItem("authToken");
    if (!token) return null;

    if (import.meta.env.VITE_WS_BASE_URL) {
      // Ensure there is no trailing slash on the base URL
      const baseUrl = import.meta.env.VITE_WS_BASE_URL.replace(/\/$/, "");
      return `${baseUrl}/admin/dashboard/?token=${encodeURIComponent(token)}`;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/ws/admin/dashboard/?token=${encodeURIComponent(token)}`;
  }, []);

  const dispatchEvent = useCallback((event: RealtimeEvent) => {
    setLastEvent(event);

    // Invoke registered listeners for this event type
    const listeners = listenersRef.current.get(event.type);
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(event.payload, event);
        } catch (err) {
          console.error(`Error in WebSocket listener for ${event.type}:`, err);
        }
      });
    }

    // Global listeners
    const wildcardListeners = listenersRef.current.get("*");
    if (wildcardListeners) {
      wildcardListeners.forEach((listener) => {
        try {
          listener(event.payload, event);
        } catch (err) {
          console.error(`Error in WebSocket wildcard listener:`, err);
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
        break;
      }

      case "NEW_LEAD": {
        const payload = event.payload || {};
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        toast.success("New Lead Detected!", {
          description: `${payload.customer_name || "Instagram User"} inquired about ${payload.service_name || "Photography Session"}.`,
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
        break;
      }

      case "BOOKING_CREATED": {
        const payload = event.payload || {};
        queryClient.invalidateQueries({ queryKey: ["bookings"] });
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        toast.success("Booking Confirmed!", {
          description: `Booking #${payload.reference_id || ""} confirmed for ${payload.customer_name || "Customer"}.`,
        });
        break;
      }

      case "BOOKING_UPDATED": {
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

  const connect = useCallback(() => {
    if (!user) {
      setStatus("DISCONNECTED");
      return;
    }

    const wsUrl = getWsUrl();
    if (!wsUrl) {
      setStatus("DISCONNECTED");
      return;
    }

    // Close existing socket if any
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      wsRef.current.close();
    }

    setStatus((prev) => (prev === "CONNECTED" ? "RECONNECTING" : "CONNECTING"));

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setStatus("CONNECTED");
        reconnectAttemptsRef.current = 0;

        // Start heartbeat ping every 30s
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 30000);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "PONG" || data.type === "CONNECTION_ESTABLISHED") {
            return;
          }
          if (data.type) {
            dispatchEvent({
              type: data.type,
              payload: data.payload || {},
              timestamp: data.timestamp || new Date().toISOString(),
            });
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err, event.data);
        }
      };

      socket.onerror = (err) => {
        console.warn("WebSocket connection error:", err);
      };

      socket.onclose = (event) => {
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        wsRef.current = null;

        // If user is still logged in and socket was not closed cleanly due to logout or auth rejection
        if (user && event.code !== 4001 && event.code !== 4003 && event.code !== 4403) {
          setStatus("RECONNECTING");
          const nextAttempt = reconnectAttemptsRef.current + 1;
          reconnectAttemptsRef.current = nextAttempt;
          console.log(`WebSocket reconnecting, attempt: ${nextAttempt} (close code: ${event.code})`);
          
          // Exponential backoff with jitter: 1s, 2s, 4s, 8s ... max 30s
          const delay = Math.min(1000 * Math.pow(1.5, nextAttempt) + Math.random() * 500, 30000);

          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus("DISCONNECTED");
        }
      };
    } catch (err) {
      console.error("Failed to create WebSocket instance:", err);
      setStatus("DISCONNECTED");
    }
  }, [user, getWsUrl, dispatchEvent]);

  useEffect(() => {
    if (user) {
      connect();
    } else {
      if (wsRef.current) {
        wsRef.current.close(1000, "User logged out");
        wsRef.current = null;
      }
      setStatus("DISCONNECTED");
    }

    return () => {
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close(1000, "Unmounted");
        wsRef.current = null;
      }
    };
  }, [user, connect]);

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
