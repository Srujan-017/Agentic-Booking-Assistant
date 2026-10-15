import { useEffect, useRef, useState } from "react";
import { ApiError, getSlots, getThread, sendMessage, streamMessage } from "../api/client";
import type { BookingOut, CitationOut, Role, SlotOut } from "../api/types";

const THREAD_STORAGE_KEY = "agentic-booking:thread_id";

export type ChatStatus = "idle" | "thinking" | "error";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  citations?: CitationOut[];
  booking?: BookingOut;
  nodePath?: string[];
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export function useChat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingMessages, setStreamingMessages] = useState<ChatMessage[]>([]);
  const [nodePath, setNodePath] = useState<string[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [booking, setBooking] = useState<BookingOut | null>(null);
  const [slots, setSlots] = useState<SlotOut[]>([]);
  const [restoring, setRestoring] = useState(true);
  const lastMessageRef = useRef<string | null>(null);

  async function refreshSlots() {
    try {
      setSlots(await getSlots());
    } catch {
      // non-fatal: the slots panel just stays empty/stale
    }
  }

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(THREAD_STORAGE_KEY);
    } catch {
      // private browsing / blocked storage: fine, just start fresh
    }

    void refreshSlots();

    if (!stored) {
      setRestoring(false);
      return;
    }

    getThread(stored)
      .then((state) => {
        setThreadId(state.thread_id);
        setMessages(
          state.messages.map((m) => ({ id: newId(), role: m.role, content: m.content }))
        );
        setBooking(state.booking);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          try {
            localStorage.removeItem(THREAD_STORAGE_KEY);
          } catch {
            /* ignore */
          }
        }
      })
      .finally(() => setRestoring(false));
  }, []);

  function applyThreadId(newThreadId: string) {
    setThreadId((prev) => {
      if (newThreadId === prev) return prev;
      try {
        localStorage.setItem(THREAD_STORAGE_KEY, newThreadId);
      } catch {
        /* ignore */
      }
      return newThreadId;
    });
  }

  /** Non-streaming path: also the fallback when the SSE stream fails partway. */
  async function performNonStreamingSend(trimmed: string, wasAlreadyConfirmed: boolean) {
    const res = await sendMessage(threadId, trimmed);
    applyThreadId(res.thread_id);

    setMessages((prev) => [
      ...prev,
      ...res.new_messages.map((m, i) => ({
        id: newId(),
        role: m.role,
        content: m.content,
        // Citations belong to the FAQ answer, which is always the first new
        // message this turn (even when a second, booking-continuation
        // message follows it after an interleaved FAQ detour).
        citations: i === 0 ? res.citations : undefined,
        // Only show the confirmation card on the message that just
        // confirmed the booking, not on every later unrelated reply.
        booking:
          i === res.new_messages.length - 1 &&
          !wasAlreadyConfirmed &&
          res.booking.status === "confirmed"
            ? res.booking
            : undefined,
      })),
    ]);
    setBooking(res.booking);
    setStatus("idle");
    if (res.booking.status === "confirmed") void refreshSlots();
  }

  /** Streaming path. Returns normally on success, throws to trigger the
   * non-streaming fallback on any failure (network error, or the server
   * reporting a mid-stream failure via an "error" SSE event). */
  async function performStreamingSend(trimmed: string, wasAlreadyConfirmed: boolean) {
    let live: ChatMessage[] = [];
    let currentNode: string | null = null;
    const pathSeen: string[] = [];
    let serverReportedError: string | null = null;

    await streamMessage(threadId, trimmed, {
      onNode: (node) => {
        pathSeen.push(node);
        setNodePath([...pathSeen]);
      },
      onToken: (node, text) => {
        if (node !== currentNode || live.length === 0) {
          currentNode = node;
          live = [...live, { id: newId(), role: "assistant", content: text }];
        } else {
          const last = live[live.length - 1];
          live = [...live.slice(0, -1), { ...last, content: last.content + text }];
        }
        setStreamingMessages(live);
      },
      onMessage: (node, text) => {
        if (currentNode === node && live.length > 0) {
          // Replace the token-streamed bubble's content with the
          // authoritative final text from the server (source of truth).
          const lastIdx = live.length - 1;
          live = [...live.slice(0, lastIdx), { ...live[lastIdx], content: text }];
        } else {
          // No token-streamed bubble exists for this node — e.g. a reply
          // with no LLM call behind it at all, like booking's hardcoded
          // confirmation line. Create the bubble now or it's lost entirely.
          currentNode = node;
          live = [...live, { id: newId(), role: "assistant", content: text }];
        }
        setStreamingMessages(live);
      },
      onCitations: (citations) => {
        if (live.length === 0) return;
        live = [{ ...live[0], citations }, ...live.slice(1)];
        setStreamingMessages(live);
      },
      onBooking: (newBooking) => {
        setBooking(newBooking);
        if (live.length > 0 && !wasAlreadyConfirmed && newBooking.status === "confirmed") {
          const lastIdx = live.length - 1;
          live = [...live.slice(0, lastIdx), { ...live[lastIdx], booking: newBooking }];
          setStreamingMessages(live);
        }
        if (newBooking.status === "confirmed") void refreshSlots();
      },
      onDone: (newThreadId) => {
        applyThreadId(newThreadId);
        if (live.length > 0) {
          const lastIdx = live.length - 1;
          live = [...live.slice(0, lastIdx), { ...live[lastIdx], nodePath: pathSeen }];
        }
        setMessages((prev) => [...prev, ...live]);
        setStreamingMessages([]);
        setStatus("idle");
      },
      onError: (detail) => {
        serverReportedError = detail;
      },
    });

    if (serverReportedError) {
      setStreamingMessages([]);
      throw new Error(serverReportedError);
    }
  }

  async function performSend(text: string, echoUser: boolean) {
    const trimmed = text.trim();
    if (!trimmed || status === "thinking") return;

    lastMessageRef.current = trimmed;
    setError(null);
    if (echoUser) {
      setMessages((prev) => [...prev, { id: newId(), role: "user", content: trimmed }]);
    }
    setStatus("thinking");
    setNodePath([]);
    setStreamingMessages([]);

    // Only the turn that actually confirms a booking should show the
    // confirmation card; otherwise it would silently reappear on every
    // later, unrelated reply for as long as booking.status stays
    // "confirmed" in state.
    const wasAlreadyConfirmed = booking?.status === "confirmed";

    try {
      await performStreamingSend(trimmed, wasAlreadyConfirmed);
    } catch {
      // Streaming failed (connection dropped, or the server hit an error
      // mid-stream) — fall back to a plain request for this turn.
      setStreamingMessages([]);
      try {
        await performNonStreamingSend(trimmed, wasAlreadyConfirmed);
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    }
  }

  function send(text: string) {
    return performSend(text, true);
  }

  function retry() {
    if (lastMessageRef.current) return performSend(lastMessageRef.current, false);
  }

  function newChat() {
    try {
      localStorage.removeItem(THREAD_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setThreadId(null);
    setMessages([]);
    setStreamingMessages([]);
    setNodePath([]);
    setBooking(null);
    setStatus("idle");
    setError(null);
  }

  return {
    threadId,
    messages,
    streamingMessages,
    nodePath,
    status,
    error,
    booking,
    slots,
    restoring,
    send,
    retry,
    newChat,
  };
}
