import { useRef, useCallback } from "react";
import { Paperclip, ArrowUp, Mic, X, Square } from "lucide-react";
import type { ConvState, VoiceState } from "./constants";
import type { ActivationMode } from "./useChatVoice";

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
  voiceModeActive: boolean;
  kokoroOnline: boolean;
  activationMode: ActivationMode;
  onSend: () => void;
  onCancelStream: () => void;
  onStartVoiceMode: () => void;
  onStopVoiceMode: () => void;
  onStartRecording: (source: "keyboard" | "pointer") => void;
  onStopRecording: (source: "keyboard" | "pointer") => void;
  onAddImages: (files: FileList) => void;
  onAddFiles: (files: FileList) => void;
}

export function ChatInput({
  input, setInput,
  pendingImages, pendingFiles,
  removePendingImage, removePendingFile,
  hasContent, convState, voiceState, voiceModeActive, kokoroOnline,
  activationMode,
  onSend, onCancelStream,
  onStartVoiceMode, onStopVoiceMode,
  onStartRecording, onStopRecording,
  onAddImages, onAddFiles,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const streaming = convState === "streaming";
  const listening = voiceModeActive && (voiceState === "listening" || voiceState === "processing" || voiceState === "speaking");
  const passiveReplySpeaking = !voiceModeActive && voiceState === "speaking";
  const isPTT = activationMode === "push_to_talk";

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
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

  // Mic button click for continuous modes, pointer events for PTT
  const handleMicClick = useCallback(() => {
    if (isPTT) return; // PTT uses pointer events, not click
    if (listening) {
      onStopVoiceMode();
    } else {
      onStartVoiceMode();
    }
  }, [isPTT, listening, onStartVoiceMode, onStopVoiceMode]);

  const handleMicPointerDown = useCallback((e: React.PointerEvent) => {
    if (!isPTT) return;
    e.preventDefault();
    onStartRecording("pointer");
  }, [isPTT, onStartRecording]);

  const handleMicPointerUp = useCallback(() => {
    if (!isPTT) return;
    onStopRecording("pointer");
  }, [isPTT, onStopRecording]);

  const micTitle = isPTT
    ? "Hold to record"
    : listening ? "Stop listening" : passiveReplySpeaking ? "Assistant is speaking" : "Start voice";

  return (
    <div className="shrink-0 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 px-4" style={{ background: "var(--bg-primary)" }}>
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
                  className="absolute -top-2 -right-2 w-8 h-8 rounded-full flex items-center justify-center"
                  style={{ background: "var(--danger)", color: "#fff" }}
                  aria-label="Remove image"
                >
                  <X size={12} />
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
                <button
                  onClick={() => removePendingFile(i)}
                  className="w-8 h-8 flex items-center justify-center"
                  style={{ color: "var(--danger)" }}
                  aria-label="Remove file"
                >
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
            aria-label="Attach files"
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
              aria-label="Stop generating"
            >
              <Square size={16} />
            </button>
          ) : hasContent ? (
            <button
              onClick={onSend}
              className="p-2 rounded-xl shrink-0 transition-colors hover:opacity-90"
              style={{ background: "var(--accent-primary)", color: "#fff" }}
              aria-label="Send message"
            >
              <ArrowUp size={16} />
            </button>
          ) : kokoroOnline ? (
            <button
              onClick={passiveReplySpeaking ? undefined : isPTT ? undefined : handleMicClick}
              onPointerDown={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerDown : undefined}
              onPointerUp={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              onPointerCancel={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              onPointerLeave={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              disabled={passiveReplySpeaking}
              className={`p-2 rounded-xl shrink-0 transition-colors hover:opacity-80 ${listening ? "animate-pulse" : ""}`}
              style={{
                background: listening ? "var(--danger)" : "var(--surface-3)",
                color: listening ? "#fff" : "var(--text-muted)",
                touchAction: "none",
                opacity: passiveReplySpeaking ? 0.5 : 1,
              }}
              aria-label={micTitle}
            >
              <Mic size={16} />
            </button>
          ) : (
            <button
              onClick={onSend}
              className="p-2 rounded-xl shrink-0 opacity-40"
              style={{ background: "var(--surface-3)", color: "var(--text-muted)" }}
              disabled
              aria-label="Send message"
            >
              <ArrowUp size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
