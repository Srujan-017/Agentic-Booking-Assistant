import { useState } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { Composer } from "./components/Composer";
import { SlotsPanel } from "./components/SlotsPanel";
import { ThreadHeader } from "./components/ThreadHeader";
import { useChat } from "./hooks/useChat";
import { useHealth } from "./hooks/useHealth";

function App() {
  const chat = useChat();
  const connection = useHealth();
  const [slotsOpen, setSlotsOpen] = useState(false);

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      <ThreadHeader
        threadId={chat.threadId}
        connection={connection}
        onNewChat={chat.newChat}
        onToggleSlots={() => setSlotsOpen((v) => !v)}
      />

      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <ChatWindow
            messages={chat.messages}
            streamingMessages={chat.streamingMessages}
            nodePath={chat.nodePath}
            status={chat.status}
            error={chat.error}
            restoring={chat.restoring}
            onRetry={chat.retry}
          />
          <Composer disabled={chat.status === "thinking"} onSend={chat.send} />
        </div>

        <SlotsPanel
          slots={chat.slots}
          booking={chat.booking}
          open={slotsOpen}
          onClose={() => setSlotsOpen(false)}
        />
      </div>
    </div>
  );
}

export default App;
