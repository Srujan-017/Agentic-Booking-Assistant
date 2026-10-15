import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../hooks/useChat";
import { BookingCard } from "./BookingCard";
import { CitationChips } from "./CitationChips";
import { NodeBadge } from "./NodeBadge";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] sm:max-w-[70%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-600 text-white rounded-br-sm"
            : "bg-white text-slate-800 ring-1 ring-slate-200 rounded-bl-sm"
        }`}
      >
        <div
          className={`prose prose-sm max-w-none [&_p]:my-0 [&_ul]:my-1 [&_ol]:my-1 ${
            isUser ? "prose-invert" : ""
          }`}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
        {!isUser && message.citations && <CitationChips citations={message.citations} />}
        {!isUser && message.booking && <BookingCard booking={message.booking} />}
        {!isUser && message.nodePath && (
          <div className="mt-1.5">
            <NodeBadge path={message.nodePath} />
          </div>
        )}
      </div>
    </div>
  );
}
