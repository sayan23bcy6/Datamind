import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../api/client";

export interface SSEEvent {
  id: string;
  type: string;
  data: any;
}

export interface UseInvestigationEventsResult {
  events: SSEEvent[];
  currentState: string | null;
  status: "connected" | "connecting" | "error" | "closed";
  error: string | null;
  retry: () => void;
}

export function useInvestigationEvents(investigationId: string | undefined): UseInvestigationEventsResult {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [currentState, setCurrentState] = useState<string | null>(null);
  const [status, setStatus] = useState<"connected" | "connecting" | "error" | "closed">("connecting");
  const [error, setError] = useState<string | null>(null);

  const lastEventIdRef = useRef<string | null>(null);
  const backoffRef = useRef<number>(1000); // start at 1000ms (1s)
  const failureCountRef = useRef<number>(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUnmountedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!investigationId) {
      setStatus("closed");
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setStatus("connecting");
    setError(null);

    if (typeof EventSource === "undefined") {
      setStatus("closed");
      return;
    }

    const url = api.getEventsUrl(investigationId);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      if (isUnmountedRef.current) return;
      setStatus("connected");
      setError(null);
      backoffRef.current = 1000; // Reset backoff on successful connection
      failureCountRef.current = 0;
    };

    const handleIncomingEvent = (type: string, ev: MessageEvent) => {
      if (isUnmountedRef.current) return;
      if (ev.lastEventId) {
        lastEventIdRef.current = ev.lastEventId;
      }
      try {
        const parsed = JSON.parse(ev.data);
        const sseEv: SSEEvent = {
          id: ev.lastEventId || String(Date.now()),
          type,
          data: parsed,
        };
        setEvents((prev) => [...prev, sseEv]);

        if (type === "state_changed" && parsed.to) {
          setCurrentState(parsed.to);
        } else if (type === "completed") {
          setCurrentState("COMPLETED");
          setStatus("closed");
          es.close();
        } else if (type === "failed") {
          setCurrentState("FAILED");
          setStatus("closed");
          es.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.addEventListener("state_changed", (e) => handleIncomingEvent("state_changed", e as MessageEvent));
    es.addEventListener("agent_message", (e) => handleIncomingEvent("agent_message", e as MessageEvent));
    es.addEventListener("tool_call", (e) => handleIncomingEvent("tool_call", e as MessageEvent));
    es.addEventListener("review_required", (e) => handleIncomingEvent("review_required", e as MessageEvent));
    es.addEventListener("completed", (e) => handleIncomingEvent("completed", e as MessageEvent));
    es.addEventListener("failed", (e) => handleIncomingEvent("failed", e as MessageEvent));

    es.onerror = () => {
      if (isUnmountedRef.current) return;
      es.close();
      eventSourceRef.current = null;

      failureCountRef.current += 1;
      if (failureCountRef.current >= 5) {
        setStatus("error");
        setError("Connection to event stream failed repeatedly. Please click Retry to reconnect.");
        return;
      }

      setStatus("connecting");
      const currentDelay = backoffRef.current;
      backoffRef.current = Math.min(15000, currentDelay * 2); // Exponential backoff capped at 15s

      reconnectTimerRef.current = setTimeout(() => {
        if (!isUnmountedRef.current) {
          connect();
        }
      }, currentDelay);
    };
  }, [investigationId]);

  const retry = useCallback(() => {
    failureCountRef.current = 0;
    backoffRef.current = 1000;
    connect();
  }, [connect]);

  useEffect(() => {
    isUnmountedRef.current = false;
    setEvents([]);
    setCurrentState(null);
    connect();

    return () => {
      isUnmountedRef.current = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [connect]);

  return { events, currentState, status, error, retry };
}
