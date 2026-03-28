import { useRef, useCallback } from "react";
import { Paperclip, ArrowUp, Mic, X, Square } from "lucide-react";
import type { ConvState, VoiceState } from "./constants";

interface ChatInputProps {
  input: string;
  setInput: (v: string) => void;
  pendingImages: string[];
  pendingFiles: { name: string; content: string }[];
  removePendingImage: (idx: number) => void;
  removePendingFile: (idx: number) => void;
  hasContent: boolean;
  convState: ConvState;
  voiceState: VoiceState;
  kokoroOnline: boolean;
  onSend: () => void;
  onCancelStream: () => void;
  onToggleListening: () => void;
  onAddImages: (files: FileList) => void;
  onAddFiles: (files: FileList) => void;
}

export function ChatInput({
  input, setInput,
  pendingImages, pendingFiles,
  removePendingImage, removePendingFile,
  hasContent, convState, voiceState, kokoroOnline,
  onSend, onCancelStream, onToggleListening,
  onAddImages, onAddFiles,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const streaming = convState === "streaming";
  const listening = voiceState === "listening" || voiceState === "processing" || voiceState === "speaking";

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-grow
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [setInput]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  }, [onSend]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = e.target.files;
    const imageFiles: File[] = [];
    const otherFiles: File[] = [];
    Array.from(files).forEach(f => {
      if (f.type.startsWith("image/")) imageFiles.push(f);
      else otherFiles.push(f);
    });
    if (imageFiles.length > 0) {
      const dt = new DataTransfer();
      imageFiles.forEach(f => dt.items.add(f));
      onAddImages(dt.files);
    }
    if (otherFiles.length > 0) {
      const dt = new DataTransfer();
      otherFiles.forEach(f => dt.items.add(f));
      onAddFiles(dt.files);
    }
    e.target.value = "";
  }, [onAddImages, onAddFiles]);

  return (
    <div className="shrink-0 pb-4 pt-2 px-4" style={{ background: "var(--bg-primary)" }}>
      <div className="max-w-3xl mx-auto">
        {/* Pending attachments */}
        {(pendingImages.length > 0 || pendingFiles.length > 0) && (
          <div className="flex flex-wrap gap-2 mb-2">
            {pendingImages.map((img, i) => (
              <div key={`img-${i}`} className="relative">
                <img
                  src={`data:image/png;base64,${img}`}
                  alt="pending"
                  className="w-16 h-16 rounded-lg object-cover"
                  style={{ border: "1px solid var(--border-soft)" }}
                />
                <button
                  onClick={() => removePendingImage(i)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full flex items-center justify-center"
                  style={{ background: "var(--danger)", color: "#fff" }}
                >
                  <X size={10} />
                </button>
              </div>
            ))}
            {pendingFiles.map((f, i) => (
              <div
                key={`file-${i}`}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs"
                style={{ background: "var(--surface-2)", color: "var(--text-secondary)" }}
              >
                {f.name.length > 20 ? f.name.slice(0, 17) + "..." : f.name}
                <button onClick={() => removePendingFile(i)} style={{ color: "var(--danger)" }}>
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input row */}
        <div
          className="flex items-end gap-2 rounded-2xl px-3 py-2"
          style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)" }}
        >
          {/* Attachment button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-xl shrink-0 transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title="Attach files"
          >
            <Paperclip size={18} />
          </button>
          <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileChange} />

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Message PiStation AI..."
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={streaming}
            className="flex-1 bg-transparent resize-none outline-none text-sm py-1.5 placeholder:opacity-50"
            style={{
              color: "var(--text-primary)",
              maxHeight: "160px",
            }}
          />

          {/* Send / Stop / Mic button */}
          {streaming ? (
            <button
              onClick={onCancelStream}
              className="p-2 rounded-xl shrink-0 transition-colors hover:opacity-80"
              style={{ background: "var(--surface-3)", color: "var(--text-primary)" }}
              title="Stop generating"
            >
              <Square size={16} />
            </button>
          ) : hasContent ? (
            <button
              onClick={onSend}
              className="p-2 rounded-xl shrink-0 transition-colors hover:opacity-90"
              style={{ background: "var(--accent-primary)", color: "#fff" }}
              title="Send message"
            >
              <ArrowUp size={16} />
            </button>
          ) : kokoroOnline ? (
            <button
              onClick={onToggleListening}
              className={`p-2 rounded-xl shrink-0 transition-colors hover:opacity-80 ${listening ? "animate-pulse" : ""}`}
              style={{
                background: listening ? "var(--danger)" : "var(--surface-3)",
                color: listening ? "#fff" : "var(--text-muted)",
              }}
              title={listening ? "Stop listening" : "Start voice"}
            >
              <Mic size={16} />
            </button>
          ) : (
            <button
              onClick={onSend}
              className="p-2 rounded-xl shrink-0 opacity-40"
              style={{ background: "var(--surface-3)", color: "var(--text-muted)" }}
              disabled
            >
              <ArrowUp size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
