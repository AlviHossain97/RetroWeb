import { useRef, useEffect } from "react";
import { MessageCircle } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { MODEL_ICONS, QUICK_ACTIONS } from "./constants";
import type { Message, ConvState } from "./constants";
import { RetroPiece } from "@/components/RetroPiece";

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
          <div className="flex flex-col items-center justify-center pt-20 gap-5 text-center">
            <div className="retro-piece-frame">
              {modelInfo ? (
                <img src={modelInfo.icon} alt="" className="w-10 h-10 object-contain" />
              ) : (
                <MessageCircle size={28} style={{ color: "var(--accent-secondary)" }} />
              )}
            </div>
            <div>
              <span className="retro-kicker mb-4">
                <RetroPiece size="sm" />
                AI Copilot
              </span>
              <h2 className="retro-heading text-[1.8rem] mb-2">
                <span className="retro-title-gradient">PiStation AI</span>
              </h2>
              <p className="retro-subtitle">Ask anything about your retro gaming world and I’ll surface stats, systems, and strategy.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => onQuickAction(action.prompt)}
                  className="retro-quick-action"
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
              <div className="flex items-center gap-3 text-sm animate-[fadeSlideIn_0.2s_ease-out]">
                <span style={{ color: "var(--danger)" }}>{lastError}</span>
                <button
                  onClick={onRetry}
                  className="retro-button retro-button--danger px-4 py-2 min-h-0 text-[0.56rem]"
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
