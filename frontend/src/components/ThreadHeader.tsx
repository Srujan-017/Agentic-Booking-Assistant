import { useState } from "react";
import type { ConnectionState } from "../hooks/useHealth";

interface Props {
  threadId: string | null;
  connection: ConnectionState;
  onNewChat: () => void;
  onToggleSlots: () => void;
}

const DOT_STYLES: Record<ConnectionState, string> = {
  online: "bg-emerald-500",
  offline: "bg-red-500",
  checking: "bg-amber-400",
};

const LABELS: Record<ConnectionState, string> = {
  online: "Connected",
  offline: "Backend unreachable",
  checking: "Checking connection…",
};

export function ThreadHeader({ threadId, connection, onNewChat, onToggleSlots }: Props) {
  const [copied, setCopied] = useState(false);

  async function copyThreadId() {
    if (!threadId) return;
    try {
      await navigator.clipboard.writeText(threadId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard permission denied; silently ignore
    }
  }

  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white font-semibold">
          AB
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-slate-800">
            Agentic Booking &amp; Policy Assistant
          </h1>
          <button
            type="button"
            onClick={copyThreadId}
            disabled={!threadId}
            className="truncate text-xs text-slate-400 hover:text-slate-600 disabled:cursor-default"
            title={threadId ?? undefined}
          >
            {threadId ? (copied ? "Copied!" : `Thread ${threadId.slice(0, 8)}…`) : "New conversation"}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
          <span className={`h-2 w-2 rounded-full ${DOT_STYLES[connection]}`} aria-hidden />
          {LABELS[connection]}
        </span>
        <span
          className={`sm:hidden h-2 w-2 rounded-full ${DOT_STYLES[connection]}`}
          title={LABELS[connection]}
        />
        <button
          type="button"
          onClick={onToggleSlots}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 lg:hidden"
        >
          Slots
        </button>
        <button
          type="button"
          onClick={onNewChat}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
        >
          New chat
        </button>
      </div>
    </header>
  );
}
