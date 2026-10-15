import { useEffect, useRef, useState } from "react";
import { ApiError, getSlots, getThread, sendMessage } from "../api/client";
import type { BookingOut, CitationOut, Role, SlotOut } from "../api/types";

const THREAD_STORAGE_KEY = "agentic-booking:thread_id";

export type ChatStatus = "idle" | "thinking" | "error";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  citations?: CitationOut[];
  booking?: BookingOut;
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export function useChat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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

  async function performSend(text: string, echoUser: boolean) {
    const trimmed = text.trim();
    if (!trimmed || status === "thinking") return;

    lastMessageRef.current = trimmed;
    setError(null);
    if (echoUser) {
      setMessages((prev) => [...prev, { id: newId(), role: "user", content: trimmed }]);
    }
    setStatus("thinking");

    // Only the turn that actually confirms a booking should show the
    // confirmation card; otherwise it would silently reappear on every
    // later, unrelated reply for as long as booking.status stays
    // "confirmed" in state.
    const wasAlreadyConfirmed = booking?.status === "confirmed";

    try {
      const res = await sendMessage(threadId, trimmed);

      if (res.thread_id !== threadId) {
        setThreadId(res.thread_id);
        try {
          localStorage.setItem(THREAD_STORAGE_KEY, res.thread_id);
        } catch {
          /* ignore */
        }
      }

      setMessages((prev) => [
        ...prev,
        ...res.new_messages.map((m, i) => ({
          id: newId(),
          role: m.role,
          content: m.content,
          // Citations belong to the FAQ answer, which is always the first
          // new message this turn (even when a second, booking-continuation
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
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong.");
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
    setBooking(null);
    setStatus("idle");
    setError(null);
  }

  return {
    threadId,
    messages,
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
