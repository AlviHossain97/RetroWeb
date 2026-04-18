import { useRef, useCallback } from "react";
import { Paperclip, ArrowUp, Mic, X, Square, ImagePlus, Sparkles } from "lucide-react";
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
  imageMode: boolean;
  imageGenerating: boolean;
  onToggleImageMode: () => void;
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
  imageMode, imageGenerating, onToggleImageMode,
  onSend, onCancelStream,
  onStartVoiceMode, onStopVoiceMode,
  onStartRecording, onStopRecording,
  onAddImages, onAddFiles,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const streaming = convState === "streaming";
  const busy = streaming || imageGenerating;
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

  const handleMicClick = useCallback(() => {
    if (isPTT) return;
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
    <div className="shrink-0 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 px-4">
      <div className="max-w-3xl mx-auto">
        {(pendingImages.length > 0 || pendingFiles.length > 0) && (
          <div className="flex flex-wrap gap-2 mb-2">
            {pendingImages.map((img, i) => (
              <div key={`img-${i}`} className="retro-list-item relative p-2">
                <img
                  src={`data:image/png;base64,${img}`}
                  alt="pending"
                  className="w-16 h-16 rounded-lg object-cover"
                  style={{ border: "2px solid var(--border-soft)" }}
                />
                <button
                  onClick={() => removePendingImage(i)}
                  className="retro-button retro-button--danger retro-icon-button absolute -top-2 -right-2 min-h-0"
                  style={{ width: "2rem", minWidth: "2rem", height: "2rem", padding: 0 }}
                  aria-label="Remove image"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
            {pendingFiles.map((f, i) => (
              <div
                key={`file-${i}`}
                className="retro-list-item flex items-center gap-1.5 px-3 py-2 text-xs"
                style={{ color: "var(--text-secondary)" }}
              >
                {f.name.length > 20 ? f.name.slice(0, 17) + "..." : f.name}
                <button
                  onClick={() => removePendingFile(i)}
                  className="retro-button retro-button--ghost retro-icon-button min-h-0"
                  style={{ width: "2rem", minWidth: "2rem", height: "2rem", padding: 0, color: "var(--danger)" }}
                  aria-label="Remove file"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        {imageMode && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 mb-2 rounded-xl text-xs"
            style={{ background: "color-mix(in srgb, var(--accent-primary) 10%, transparent)", color: "var(--accent-primary)" }}
          >
            <Sparkles size={12} />
            <span className="font-medium">Image generation mode</span>
            <span style={{ color: "var(--text-muted)" }}>— your prompt will generate artwork</span>
          </div>
        )}

        <div
          className="retro-input-shell flex items-end gap-2 rounded-[1.4rem] px-3 py-3"
          style={imageMode ? { borderColor: "var(--accent-primary)", borderWidth: "2px" } : undefined}
        >
          {/* Attach files */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="retro-button retro-button--ghost retro-icon-button min-h-0 shrink-0 text-[0.56rem]"
            aria-label="Attach files"
          >
            <Paperclip size={18} />
          </button>
          <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileChange} />

          {/* Image generation toggle */}
          <button
            onClick={onToggleImageMode}
            className={`retro-button ${imageMode ? "" : "retro-button--ghost"} retro-icon-button min-h-0 shrink-0 text-[0.56rem]`}
            aria-label={imageMode ? "Switch to chat mode" : "Switch to image generation"}
            title={imageMode ? "Back to chat" : "Generate art"}
          >
            <ImagePlus size={18} />
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={imageMode ? "Describe the artwork you want..." : "Message PiStation AI..."}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={busy}
            className="retro-textarea flex-1 resize-none text-sm py-2 px-1 placeholder:opacity-60"
            style={{ maxHeight: "160px" }}
          />

          {/* Action button */}
          {busy ? (
            <button
              onClick={imageGenerating ? undefined : onCancelStream}
              className="retro-button retro-button--danger retro-icon-button min-h-0 shrink-0 text-[0.56rem]"
              aria-label={imageGenerating ? "Generating image..." : "Stop generating"}
              disabled={imageGenerating}
            >
              {imageGenerating ? (
                <Sparkles size={16} className="animate-spin" />
              ) : (
                <Square size={16} />
              )}
            </button>
          ) : hasContent ? (
            <button
              onClick={onSend}
              className={`retro-button ${imageMode ? "" : ""} retro-icon-button min-h-0 shrink-0 text-[0.56rem]`}
              aria-label={imageMode ? "Generate image" : "Send message"}
            >
              {imageMode ? <Sparkles size={16} /> : <ArrowUp size={16} />}
            </button>
          ) : kokoroOnline && !imageMode ? (
            <button
              onClick={passiveReplySpeaking ? undefined : isPTT ? undefined : handleMicClick}
              onPointerDown={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerDown : undefined}
              onPointerUp={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              onPointerCancel={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              onPointerLeave={passiveReplySpeaking ? undefined : isPTT ? handleMicPointerUp : undefined}
              disabled={passiveReplySpeaking}
              className={`retro-button ${listening ? "retro-button--danger animate-pulse" : "retro-button--ghost"} retro-icon-button min-h-0 shrink-0 text-[0.56rem]`}
              style={{
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
              className="retro-button retro-button--ghost retro-icon-button min-h-0 shrink-0 text-[0.56rem] opacity-40"
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
