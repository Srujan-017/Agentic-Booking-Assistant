export type Role = "user" | "assistant";

export interface MessageOut {
  role: Role;
  content: string;
}

export interface CitationOut {
  page: number;
  source: string;
  snippet: string;
}

export type BookingStatus = "idle" | "collecting" | "confirmed";

export interface BookingOut {
  service_type: string | null;
  name: string | null;
  email: string | null;
  slot_id: number | null;
  slot_label: string | null;
  status: BookingStatus;
  reference_id: string | null;
}

export interface ChatResponse {
  thread_id: string;
  reply: string;
  new_messages: MessageOut[];
  active_node: string;
  citations: CitationOut[];
  booking: BookingOut;
}

export interface ThreadStateOut {
  thread_id: string;
  messages: MessageOut[];
  booking: BookingOut;
  citations: CitationOut[];
}

export interface SlotOut {
  id: number;
  label: string;
  start_iso: string;
}

export interface HealthOut {
  status: string;
  llm_key_configured: boolean;
  vector_store_doc_count: number;
}
