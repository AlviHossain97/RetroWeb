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

  // Escape key closes overlays
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && overlay !== "none") {
        setOverlay("none");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [overlay]);

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
          onStop={voice.toggleListening}
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
        onSend={() => send.sendMessage()}
        onCancelStream={send.cancelStream}
        onToggleListening={voice.toggleListening}
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
