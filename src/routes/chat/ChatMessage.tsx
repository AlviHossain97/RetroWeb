import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { RenderCleanMessage } from "./RenderCleanMessage";
import { MODEL_ICONS } from "./constants";
import type { Message } from "./constants";

interface ChatMessageProps {
  msg: Message;
  isLast: boolean;
  streaming: boolean;
  selectedModel: string;
}

export function ChatMessage({ msg, isLast, streaming, selectedModel }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = msg.role === "user";
  const modelInfo = MODEL_ICONS[selectedModel];

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex gap-3 animate-[fadeSlideIn_0.2s_ease-out] ${isUser ? "flex-row-reverse" : ""}`}
      style={{ maxWidth: "100%" }}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-full shrink-0 overflow-hidden mt-1" style={{ background: "var(--surface-2)" }}>
          {modelInfo ? (
            <img src={modelInfo.icon} alt="" className="w-7 h-7 object-cover" />
          ) : (
            <div className="w-7 h-7 rounded-full" style={{ background: "var(--surface-3)" }} />
          )}
        </div>
      )}

      {/* Bubble */}
      <div className={`group flex flex-col ${isUser ? "items-end" : "items-start"} min-w-0 max-w-[85%] md:max-w-[65%]`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm break-words ${isUser ? "rounded-br-sm" : "rounded-bl-sm"}`}
          style={{
            background: isUser ? "var(--surface-3)" : "transparent",
            color: "var(--text-primary)",
            border: isUser ? "none" : undefined,
          }}
        >
          {/* Images */}
          {msg.images && msg.images.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {msg.images.map((img, j) => (
                <img
                  key={j}
                  src={`data:image/png;base64,${img}`}
                  alt="uploaded"
                  className="max-w-[280px] rounded-xl object-cover"
                  style={{ border: "1px solid var(--border-soft)" }}
                />
              ))}
            </div>
          )}

          {/* Content */}
          {msg.content ? (
            <RenderCleanMessage content={msg.content} isUser={isUser} />
          ) : (
            streaming && isLast && (
              <span className="animate-pulse" style={{ color: "var(--text-muted)" }}>|</span>
            )
          )}
        </div>

        {/* Copy button for assistant */}
        {!isUser && msg.content && (
          <button
            onClick={handleCopy}
            className="mt-1 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: "var(--text-muted)" }}
            title="Copy message"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        )}

        {/* Web sources */}
        {!isUser && msg.grounded && (
          <div className="mt-1.5 flex flex-col items-start gap-1">
            <span
              className="text-[10px] font-medium flex items-center gap-1 px-2 py-0.5 rounded-md"
              style={{ background: "rgba(34,197,94,0.1)", color: "var(--success)", border: "1px solid rgba(34,197,94,0.2)" }}
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Verified with web sources
            </span>
            {msg.sources && msg.sources.length > 0 && (
              <details className="text-[10px] group cursor-pointer w-full max-w-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
                <summary className="select-none hover:opacity-80 transition-colors list-none flex items-center gap-1">
                  <span className="group-open:rotate-90 transition-transform">&#x25b8;</span> Show {msg.sources.length} sources
                </summary>
                <div className="flex flex-col gap-1.5 mt-1.5 pl-2 pb-1" style={{ borderLeft: "1px solid var(--border-soft)" }}>
                  {msg.sources.map((src) => (
                    <a
                      key={src.id}
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded transition-colors block hover:opacity-80"
                      style={{ border: "1px solid transparent" }}
                    >
                      <div className="font-medium flex items-center gap-1 truncate" style={{ color: "var(--accent-cyan)" }}>
                        <span style={{ color: "var(--text-muted)" }}>[{src.id}]</span> {src.title}
                      </div>
                      {src.snippet && (
                        <div className="mt-0.5 truncate text-[9px]" style={{ color: "var(--text-muted)" }}>{src.snippet}</div>
                      )}
                    </a>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
