import type { BookingOut, ChatResponse, CitationOut, HealthOut, SlotOut, ThreadStateOut } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }

  if (!res.ok) {
    let detail = res.statusText || `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // body wasn't JSON; fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

export function sendMessage(threadId: string | null, message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId, message }),
  });
}

export function getThread(threadId: string): Promise<ThreadStateOut> {
  return request<ThreadStateOut>(`/api/threads/${encodeURIComponent(threadId)}`);
}

export function getSlots(): Promise<SlotOut[]> {
  return request<SlotOut[]>("/api/slots");
}

export function getHealth(): Promise<HealthOut> {
  return request<HealthOut>("/api/health");
}

export interface StreamHandlers {
  onNode?: (node: string) => void;
  onToken?: (node: string, text: string) => void;
  /** Authoritative final text for a node's message, sent once that node
   * completes. Some messages (e.g. a hardcoded booking confirmation) never
   * produce token events at all, so this is the only way to receive them. */
  onMessage?: (node: string, text: string) => void;
  onCitations?: (citations: CitationOut[]) => void;
  onBooking?: (booking: BookingOut) => void;
  onDone?: (threadId: string) => void;
  onError?: (detail: string) => void;
}

function dispatchSseEvent(raw: string, handlers: StreamHandlers) {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  const data = dataLines.join("\n");
  if (!data) return;

  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return; // malformed event; skip rather than crash the stream
  }

  switch (eventName) {
    case "node":
      handlers.onNode?.((parsed as { node: string }).node);
      break;
    case "token": {
      const p = parsed as { node: string; text: string };
      handlers.onToken?.(p.node, p.text);
      break;
    }
    case "message": {
      const p = parsed as { node: string; text: string };
      handlers.onMessage?.(p.node, p.text);
      break;
    }
    case "citations":
      handlers.onCitations?.(parsed as CitationOut[]);
      break;
    case "booking":
      handlers.onBooking?.(parsed as BookingOut);
      break;
    case "done":
      handlers.onDone?.((parsed as { thread_id: string }).thread_id);
      break;
    case "error":
      handlers.onError?.((parsed as { detail: string }).detail);
      break;
  }
}

/**
 * Streams a chat turn over SSE (POST, so the native EventSource API can't be
 * used — it only supports GET). Resolves once the stream ends naturally
 * (a "done" or "error" event was received, or the connection closed).
 */
export async function streamMessage(
  threadId: string | null,
  message: string,
  handlers: StreamHandlers
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, message }),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `Streaming request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // SSE line endings can arrive as \r\n (what this server sends) or \n;
    // normalize once so both the blank-line event separator and per-line
    // parsing below don't have to special-case \r.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      dispatchSseEvent(rawEvent, handlers);
    }
  }
}
