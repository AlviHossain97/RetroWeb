import { useRef, useEffect } from "react";
import { MessageCircle } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { MODEL_ICONS, QUICK_ACTIONS } from "./constants";
import type { Message, ConvState } from "./constants";

interface ChatMessagesProps {
  messages: Message[];
  convState: ConvState;
  lastError: string | null;
  selectedModel: string;
  onQuickAction: (prompt: string) => void;
  onRetry: () => void;
}

export function ChatMessages({ messages, convState, lastError, selectedModel, onQuickAction, onRetry }: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isNearBottom = useRef(true);

  // Track if user is near bottom
  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    isNearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  };

  // Auto-scroll only when near bottom
  useEffect(() => {
    if (isNearBottom.current) {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  const modelInfo = MODEL_ICONS[selectedModel];
  const streaming = convState === "streaming";

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto"
      role="log"
      aria-live="polite"
    >
      <div className="max-w-3xl mx-auto px-4 py-6">
        {messages.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center pt-24 gap-5">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center overflow-hidden"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)" }}
            >
              {modelInfo ? (
                <img src={modelInfo.icon} alt="" className="w-10 h-10 object-contain" />
              ) : (
                <MessageCircle size={28} style={{ color: "var(--accent-primary)" }} />
              )}
            </div>
            <div className="text-center">
              <h2 className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>PiStation AI</h2>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>Ask me anything about your retro gaming world</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => onQuickAction(action.prompt)}
                  className="px-3 py-2 rounded-xl text-sm transition-all hover:scale-[1.02]"
                  style={{ background: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border-soft)" }}
                >
                  {action.icon} {action.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message list */
          <div className="flex flex-col gap-4">
            {messages.map((msg, i) => (
              <ChatMessage
                key={`msg-${i}-${msg.role}-${msg.content.slice(0, 8)}`}
                msg={msg}
                isLast={i === messages.length - 1}
                streaming={streaming}
                selectedModel={selectedModel}
              />
            ))}
            {/* Inline error with retry */}
            {convState === "error" && lastError && (
              <div className="flex items-center gap-2 text-sm animate-[fadeSlideIn_0.2s_ease-out]">
                <span style={{ color: "var(--danger)" }}>{lastError}</span>
                <button
                  onClick={onRetry}
                  className="px-3 py-1 rounded-lg text-xs font-medium transition-colors hover:opacity-80"
                  style={{ background: "var(--surface-2)", color: "var(--text-secondary)" }}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
