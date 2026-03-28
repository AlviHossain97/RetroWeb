import { useState, useCallback, useRef } from "react";
import { NVIDIA_BASE, PISTATION_API, SENTENCE_END, CLAUSE_END } from "./constants";
import type { Message, ConvState } from "./constants";
import type { useChatTranscript } from "./useChatTranscript";
import type { useChatComposer } from "./useChatComposer";
import { checkAndUnlock } from "../../lib/achievements";

export interface TTSSession {
  flush(text: string, force?: boolean): void;
  finish(): Promise<void>;
  cancel(): void;
  isPlaying(): boolean;
}

export function useChatSend(opts: {
  transcript: ReturnType<typeof useChatTranscript>;
  composer: ReturnType<typeof useChatComposer>;
  model: string;
  webMode: string;
  nvidiaOnline: boolean;
  ttsSession?: TTSSession | null;
}) {
  const { transcript, composer, model, webMode, nvidiaOnline, ttsSession } = opts;
  const [convState, setConvState] = useState<ConvState>("idle");
  const [lastError, setLastError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const processingRef = useRef(false);

  const sendMessage = useCallback(async (directText?: string) => {
    let text = (directText ?? composer.input).trim();
    // Append file contents as context
    if (composer.pendingFiles.length > 0 && !directText) {
      const fileContext = composer.pendingFiles.map(f => `[File: ${f.name}]\n${f.content}`).join("\n\n");
      text = text ? `${text}\n\n${fileContext}` : fileContext;
    }
    const images = !directText ? [...composer.pendingImages] : undefined;
    if (!text && (!images || images.length === 0)) return;
    if (!text) text = "What's in this image?";
    if (convState === "streaming" || processingRef.current || !nvidiaOnline || !model) return;
    processingRef.current = true;
    setLastError(null);
    if (!directText) {
      composer.clearComposer();
    }

    const userMsg: Message = { role: "user", content: text, images: images && images.length > 0 ? images : undefined };
    const assistantMsg: Message = { role: "assistant", content: "" };
    // Capture history before appending — avoids stale closure issues
    const previousMessages = [...transcript.messages];
    transcript.appendUser(userMsg);
    transcript.appendAssistant(assistantMsg);
    setConvState("streaming");

    // Achievement triggers
    void checkAndUnlock("ai_chat");
    if (images && images.length > 0) void checkAndUnlock("screenshot_ai");

    // TTS buffering state
    const isVoice = !!ttsSession;
    let sentenceBuffer = "";
    let chunkIndex = 0;

    const flushSentence = (force?: boolean) => {
      const trimmed = sentenceBuffer.trim();
      if (!trimmed || !isVoice || !ttsSession) return;
      // First chunk: fire on the very first word boundary
      if (chunkIndex === 0 && trimmed.includes(" ")) {
        ttsSession.flush(trimmed);
        sentenceBuffer = "";
        chunkIndex++;
        return;
      }
      const isSentenceEnd = SENTENCE_END.test(trimmed);
      const isClauseEnd = CLAUSE_END.test(trimmed) && trimmed.length >= 40;
      const isOverflow = trimmed.length >= 120;
      if (force || isSentenceEnd || isClauseEnd || isOverflow) {
        ttsSession.flush(trimmed);
        sentenceBuffer = "";
        chunkIndex++;
      }
    };

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      // Fetch gaming data context
      let gamingContext = "";
      try {
        const ctxRes = await fetch(`${PISTATION_API}/ai/context`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text }),
          signal: AbortSignal.timeout(3000),
        });
        if (ctxRes.ok) {
          const ctxData = await ctxRes.json();
          gamingContext = ctxData.context || "";
        }
      } catch { /* backend unavailable */ }

      const personaBase = "You are a helpful PiStation assistant, an AI for a retro gaming dashboard platform.";
      const dataBlock = gamingContext ? `\n\nHere is the user's real gaming data from their PiStation:\n${gamingContext}\n\nUse this data to answer questions about their gaming habits, stats, and history accurately.` : "";
      const voiceInstructions = isVoice ? " IMPORTANT: Your response will be read aloud by a text-to-speech engine. Do NOT use any markdown formatting whatsoever — no asterisks, no bold, no italic, no headers, no bullet points, no numbered lists, no code blocks. Write in plain conversational text only. Keep responses short and punchy (2-4 sentences max)." : "";

      // Web Grounding
      let webSources: { id: number; title: string; url: string; snippet: string }[] = [];
      let systemAppend = "";
      let grounded = false;
      let groundingFailed = false;

      if (webMode !== "never") {
        transcript.patchLastAssistant({ content: "\ud83d\udd0d Searching the web..." });
        try {
          const hist = previousMessages.slice(-6).map(m => ({ role: m.role, content: m.content }));
          const groundRes = await fetch(`${PISTATION_API}/ai/ground`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text, history: hist, mode: webMode }),
            signal: AbortSignal.timeout(30000),
          });
          if (groundRes.ok) {
            const groundData = await groundRes.json();
            if (groundData.error) {
              groundingFailed = true;
            } else if (groundData.grounded) {
              grounded = true;
              webSources = groundData.sources || [];
              systemAppend = groundData.system_append || "";
            }
          } else {
            groundingFailed = true;
          }
        } catch {
          groundingFailed = true;
        }

        if (webMode === "always" && groundingFailed) {
          transcript.patchLastAssistant({
            content: "\u26a0\ufe0f Web verification is currently unavailable, so I can't provide a verified answer right now. Please try again in a moment, or switch to Auto/Never web mode.",
          });
          setConvState("error");
          setLastError("Web grounding unavailable");
          processingRef.current = false;
          return;
        }

        transcript.patchLastAssistant({ content: "" });
      }

      const systemPrompt = `${personaBase} You can help with tips, cheats, walkthroughs, gaming analytics, and general retro gaming knowledge. Be concise and helpful.${voiceInstructions}${dataBlock}\n${systemAppend}`;

      const apiMessages = [
        { role: "system", content: systemPrompt },
        ...[...previousMessages, userMsg].map(m => ({
          role: m.role,
          content: m.content,
        })),
      ];

      const res = await fetch(`${NVIDIA_BASE}/v1/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          messages: apiMessages,
          max_tokens: 4096,
          stream: true,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) throw new Error("Stream failed");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";
      let sseBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split("\n");
        sseBuffer = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const payload = trimmed.slice(6);
          if (payload === "[DONE]") break;
          try {
            const json = JSON.parse(payload);
            const token = json.choices?.[0]?.delta?.content;
            if (token) {
              full += token;
              sentenceBuffer += token;
              transcript.patchLastAssistant({
                content: full,
                grounded,
                sources: webSources.length > 0 ? webSources : undefined,
              });
              flushSentence();
            }
          } catch { /* skip malformed */ }
        }
      }

      // Flush remaining text to TTS
      flushSentence(true);

      // Wait for TTS to finish
      if (ttsSession) {
        ttsSession.finish().catch(() => {});
      }

      setConvState("idle");
    } catch (err) {
      if (controller.signal.aborted) {
        // User cancelled — just go idle
        setConvState("idle");
      } else {
        const errorMsg = "Sorry, I couldn't connect to the AI. Check your NVIDIA API key and internet connection.";
        transcript.patchLastAssistant({ content: errorMsg });
        setConvState("error");
        setLastError(errorMsg);
      }
      if (ttsSession) {
        ttsSession.cancel();
      }
    } finally {
      processingRef.current = false;
      abortRef.current = null;
    }
  }, [composer, convState, nvidiaOnline, model, transcript, webMode, ttsSession]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { convState, lastError, sendMessage, cancelStream };
}
