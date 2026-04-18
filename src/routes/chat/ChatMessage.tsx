import { useState } from "react";
import { Copy, Check, Download } from "lucide-react";
import { RenderCleanMessage } from "./RenderCleanMessage";
import type { Message } from "./constants";

interface ChatMessageProps {
  msg: Message;
  isLast: boolean;
  streaming: boolean;
  selectedModel: string;
}

export function ChatMessage({ msg, isLast, streaming }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = msg.role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex animate-[fadeSlideIn_0.2s_ease-out] ${isUser ? "justify-end" : "justify-start"}`}
      style={{ maxWidth: "100%" }}
    >
      <div className={`group flex flex-col ${isUser ? "items-end max-w-[85%] md:max-w-[65%]" : "items-start w-full"} min-w-0`}>
        <div
          className={
            isUser
              ? "retro-chat-bubble retro-chat-bubble--user rounded-br-sm px-4 py-3 text-sm break-words"
              : "text-sm break-words w-full"
          }
          style={{ color: "var(--text-primary)" }}
        >
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

          {/* Generated image */}
          {msg.generatedImage && (
            <div className="mb-2 space-y-2">
              <div className="rounded-xl overflow-hidden" style={{ border: "2px solid var(--border-soft)" }}>
                <img
                  src={`data:${msg.generatedImage.mimeType};base64,${msg.generatedImage.base64}`}
                  alt={msg.generatedImage.title || "Generated art"}
                  className="w-full object-contain"
                  style={{ maxHeight: "400px", background: "#0a0a0a" }}
                />
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {msg.generatedImage.title && (
                  <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                    {msg.generatedImage.title}
                  </span>
                )}
                {msg.generatedImage.stylePreset && (
                  <span className="retro-chip retro-chip--success text-[9px]">
                    {msg.generatedImage.stylePreset}
                  </span>
                )}
                <button
                  onClick={() => {
                    const gi = msg.generatedImage!;
                    const ext = gi.mimeType.includes("png") ? "png" : "jpg";
                    const link = document.createElement("a");
                    link.href = `data:${gi.mimeType};base64,${gi.base64}`;
                    link.download = `${gi.title || "pistation-art"}.${ext}`;
                    link.click();
                  }}
                  className="retro-button retro-button--ghost retro-icon-button min-h-0 text-[0.5rem]"
                  aria-label="Download image"
                >
                  <Download size={12} />
                </button>
              </div>
            </div>
          )}

          {msg.content ? (
            <RenderCleanMessage content={msg.content} isUser={isUser} />
          ) : (
            streaming && isLast && !msg.generatedImage && (
              <span className="animate-pulse" style={{ color: "var(--text-muted)" }}>|</span>
            )
          )}
        </div>

        {!isUser && msg.content && (
          <button
            onClick={handleCopy}
            className="retro-button retro-button--ghost mt-2 px-3 py-1.5 min-h-0 text-[0.5rem] opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
            aria-label="Copy message"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        )}

        {!isUser && msg.grounded && (
          <div className="mt-1.5 flex flex-col items-start gap-1">
            <span
              className="retro-chip retro-chip--success"
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
                <div className="flex flex-col gap-1.5 mt-1.5 pl-3 pb-1" style={{ borderLeft: "2px solid var(--border-soft)" }}>
                  {msg.sources.map((src) => (
                    <a
                      key={src.id}
                      href={/^https?:\/\//.test(src.url) ? src.url : "#"}
                      target="_blank"
                      rel="noreferrer"
                      className="retro-list-item p-2 block hover:opacity-80"
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
