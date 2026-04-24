import { useState, useEffect, useCallback, useMemo } from "react";
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
import { DEFAULT_MODEL, PISTATION_API, type OverlayState, type GeneratedImage } from "./chat/constants";

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
  const [imageMode, setImageMode] = useState(false);
  const [imageGenerating, setImageGenerating] = useState(false);

  // Voice hook
  const voice = useChatVoice({
    voiceAvailable: health.voiceAvailable,
    selectedModel,
    transcript,
  });

  // Text-chat TTS: when voice is enabled, assistant replies to typed messages
  // are spoken aloud. The session is null when voice is off so TTS is skipped.
  const ttsSession = useMemo(
    () => voice.createTTSSession(),
    [voice.createTTSSession, voice.voiceEnabled],
  );

  // Send hook
  const send = useChatSend({
    transcript,
    composer,
    model: selectedModel,
    webMode,
    nvidiaOnline: health.nvidiaOnline,
    ttsSession,
    onAssistantTurnRecovered: voice.recoverAfterAssistantTurn,
  });

  // ── Image generation handler ──
  const handleImageGenerate = useCallback(async () => {
    const prompt = composer.input.trim();
    if (!prompt || imageGenerating || voice.voiceModeActive) return;

    transcript.appendUser({ role: "user", content: prompt });
    composer.clearComposer();
    setImageGenerating(true);
    transcript.appendAssistant({ role: "assistant", content: "" });

    try {
      const resp = await fetch(`${PISTATION_API}/ai/generate-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `Generation failed (${resp.status})`);
      }

      const data = await resp.json();
      const genImage: GeneratedImage = {
        base64: data.imageBase64,
        mimeType: data.mimeType,
        prompt: data.finalPrompt,
        title: data.title || "",
        stylePreset: data.stylePreset || "",
      };

      transcript.patchLastAssistant({
        content: data.title ? `Here's your generated artwork: "${data.title}"` : "Here's your generated artwork!",
        generatedImage: genImage,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Image generation failed";
      transcript.patchLastAssistant({ content: `Image generation error: ${msg}` });
    } finally {
      setImageGenerating(false);
    }
  }, [composer, transcript, imageGenerating]);

  const handleSend = useCallback(() => {
    if (voice.voiceModeActive) return;
    if (imageMode) {
      handleImageGenerate();
    } else {
      send.sendMessage();
    }
  }, [imageMode, handleImageGenerate, send, voice.voiceModeActive]);

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

  const voiceActive = voice.voiceModeActive;

  return (
    <div className="retro-chat-shell flex-1 flex flex-col h-full overflow-hidden">
      {/* Zone 1: Header */}
      <ChatHeader
        selectedModel={selectedModel}
        nvidiaOnline={health.nvidiaOnline}
        voiceAvailable={health.voiceAvailable}
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
        onQuickAction={(prompt) => { if (!voice.voiceModeActive) send.sendMessage(prompt); }}
        onRetry={() => { if (!voice.voiceModeActive) send.retryLastMessage(); }}
      />

      {/* Voice status bar */}
      {voiceActive && (
        <ChatVoiceBar
          voiceState={voice.voiceState}
          activationMode={voice.activationMode}
          liveTranscript={voice.liveTranscript}
          provider={voice.activeProvider ?? health.voiceProvider}
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
        voiceModeActive={voice.voiceModeActive}
        voiceAvailable={health.voiceAvailable && voice.voiceEnabled}
        activationMode={voice.activationMode}
        imageMode={imageMode}
        imageGenerating={imageGenerating}
        onToggleImageMode={() => { if (!voice.voiceModeActive) setImageMode(!imageMode); }}
        onSend={handleSend}
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
