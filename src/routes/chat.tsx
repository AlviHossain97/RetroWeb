import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useChatHealth } from "./chat/useChatHealth";
import { useChatComposer } from "./chat/useChatComposer";
import { useChatTranscript } from "./chat/useChatTranscript";
import { useChatSend } from "./chat/useChatSend";
import { useChatVoice } from "./chat/useChatVoice";
import { ChatHeader } from "./chat/ChatHeader";
import { ChatModelPicker } from "./chat/ChatModelPicker";
import { ChatOverflowMenu } from "./chat/ChatOverflowMenu";
import { ChatMessages } from "./chat/ChatMessages";
import { ChatInput } from "./chat/ChatInput";
import { ChatVoiceBar } from "./chat/ChatVoiceBar";
import { ChatClearDialog } from "./chat/ChatClearDialog";
import { ChatVoiceSettingsModal } from "./chat/ChatVoiceSettingsModal";
import { DEFAULT_MODEL, type OverlayState } from "./chat/constants";

function isInteractiveElement(el: Element | null): boolean {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "BUTTON" || tag === "A") return true;
  if ((el as HTMLElement).isContentEditable) return true;
  if (el.closest('[role="textbox"], [role="button"], [contenteditable="true"], dialog, [role="dialog"]')) return true;
  return false;
}

export default function Chat() {
  // ── Hooks ──
  const health = useChatHealth();
  const composer = useChatComposer();
  const transcript = useChatTranscript();

  // Shell-owned state
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
  const [webMode, setWebMode] = useState<"auto" | "always" | "never">("auto");
  const [overlay, setOverlay] = useState<OverlayState>("none");

  // Ref to break circular dependency: voice needs send, send needs voice's TTS
  const sendRef = useRef<(text: string) => void>(() => {});

  // Voice hook
  const voice = useChatVoice({
    kokoroOnline: health.kokoroOnline,
    onTranscript: useCallback((text: string) => {
      sendRef.current(text);
    }, []),
  });

  // Create TTS session when voice mode is active
  const ttsSession = useMemo(() => {
    if (voice.voiceState !== "idle" && voice.voiceEnabled) {
      return voice.createTTSSession();
    }
    return null;
  }, [voice.voiceState, voice.voiceEnabled, voice.createTTSSession]);

  // Send hook
  const send = useChatSend({
    transcript,
    composer,
    model: selectedModel,
    webMode,
    nvidiaOnline: health.nvidiaOnline,
    ttsSession,
  });

  // Keep ref in sync
  sendRef.current = send.sendMessage;

  // Escape key closes overlays + Global T key for push-to-talk
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && overlay !== "none") {
        setOverlay("none");
        return;
      }
      if (
        e.key === "t" &&
        !e.repeat &&
        !e.metaKey && !e.ctrlKey && !e.altKey &&
        voice.activationMode === "push_to_talk" &&
        overlay === "none" &&
        !isInteractiveElement(document.activeElement) &&
        (voice.voiceState === "idle" || voice.voiceState === "error")
      ) {
        e.preventDefault();
        voice.startRecording("keyboard");
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === "t" && voice.activationMode === "push_to_talk") {
        voice.stopRecording("keyboard");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [overlay, voice.activationMode, voice.voiceState, voice.startRecording, voice.stopRecording]);

  const voiceActive = voice.voiceState !== "idle";

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      {/* Zone 1: Header */}
      <ChatHeader
        selectedModel={selectedModel}
        nvidiaOnline={health.nvidiaOnline}
        kokoroOnline={health.kokoroOnline}
        overlay={overlay}
        setOverlay={setOverlay}
      />

      {/* Floating overlays */}
      <div className="relative">
        {overlay === "modelPicker" && (
          <ChatModelPicker
            selectedModel={selectedModel}
            onSelect={(m) => { setSelectedModel(m); setOverlay("none"); }}
            onClose={() => setOverlay("none")}
          />
        )}
        {overlay === "overflowMenu" && (
          <ChatOverflowMenu
            webMode={webMode}
            setWebMode={setWebMode}
            voiceEnabled={voice.voiceEnabled}
            setVoiceEnabled={voice.setVoiceEnabled}
            hasMessages={transcript.messages.length > 0}
            onExport={transcript.exportAsMarkdown}
            onClear={() => setOverlay("clearConfirm")}
            onVoiceSettings={() => setOverlay("voiceSettings")}
            onClose={() => setOverlay("none")}
          />
        )}
      </div>

      {/* Zone 2: Messages */}
      <ChatMessages
        messages={transcript.messages}
        convState={send.convState}
        lastError={send.lastError}
        selectedModel={selectedModel}
        onQuickAction={(prompt) => send.sendMessage(prompt)}
        onRetry={() => send.sendMessage()}
      />

      {/* Voice status bar */}
      {voiceActive && (
        <ChatVoiceBar
          voiceState={voice.voiceState}
          activationMode={voice.activationMode}
          onStop={voice.stopVoiceMode}
        />
      )}

      {/* Zone 3: Input */}
      <ChatInput
        input={composer.input}
        setInput={composer.setInput}
        pendingImages={composer.pendingImages}
        pendingFiles={composer.pendingFiles}
        removePendingImage={composer.removePendingImage}
        removePendingFile={composer.removePendingFile}
        hasContent={composer.hasContent}
        convState={send.convState}
        voiceState={voice.voiceState}
        kokoroOnline={health.kokoroOnline}
        activationMode={voice.activationMode}
        onSend={() => send.sendMessage()}
        onCancelStream={send.cancelStream}
        onStartVoiceMode={voice.startVoiceMode}
        onStopVoiceMode={voice.stopVoiceMode}
        onStartRecording={voice.startRecording}
        onStopRecording={voice.stopRecording}
        onAddImages={composer.addImages}
        onAddFiles={composer.addFiles}
      />

      {/* Modal overlays */}
      {overlay === "clearConfirm" && (
        <ChatClearDialog
          onConfirm={() => { transcript.clearMessages(); setOverlay("none"); }}
          onCancel={() => setOverlay("none")}
        />
      )}
      {overlay === "voiceSettings" && (
        <ChatVoiceSettingsModal
          activationMode={voice.activationMode}
          setActivationMode={voice.setActivationMode}
          noiseSuppressionEnabled={voice.noiseSuppressionEnabled}
          setNoiseSuppressionEnabled={voice.setNoiseSuppressionEnabled}
          echoCancellationEnabled={voice.echoCancellationEnabled}
          setEchoCancellationEnabled={voice.setEchoCancellationEnabled}
          agcEnabled={voice.agcEnabled}
          setAgcEnabled={voice.setAgcEnabled}
          onClose={() => setOverlay("none")}
        />
      )}
    </div>
  );
}
