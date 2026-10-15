import { useEffect, useRef } from "react";
import type { ChatMessage, ChatStatus } from "../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { NodeBadge } from "./NodeBadge";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: ChatMessage[];
  streamingMessages: ChatMessage[];
  nodePath: string[];
  status: ChatStatus;
  error: string | null;
  restoring: boolean;
  onRetry: () => void;
}

export function ChatWindow({
  messages,
  streamingMessages,
  nodePath,
  status,
  error,
  restoring,
  onRetry,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, streamingMessages, status]);

  const waitingForFirstToken = status === "thinking" && streamingMessages.length === 0;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {restoring && (
          <p className="text-center text-xs text-slate-400">Restoring conversation…</p>
        )}

        {!restoring && messages.length === 0 && streamingMessages.length === 0 && (
          <div className="mt-10 text-center text-sm text-slate-400">
            Ask a question about the employee handbook, or say "I'd like to book a
            Performance Review" to get started.
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {streamingMessages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {status === "thinking" && nodePath.length > 0 && (
          <div className="pl-1">
            <NodeBadge path={nodePath} live />
          </div>
        )}

        {waitingForFirstToken && <TypingIndicator />}

        {status === "error" && error && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
            <span>{error}</span>
            <button
              type="button"
              onClick={onRetry}
              className="shrink-0 rounded-lg bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-500"
            >
              Retry
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
