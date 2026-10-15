import type { ChatResponse, HealthOut, SlotOut, ThreadStateOut } from "./types";

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
