import { useState, useEffect } from "react";
import { NVIDIA_BASE, PISTATION_API } from "./constants";
import type { VoiceHealthResponse } from "./voiceProtocol";

export function useChatHealth() {
  const [nvidiaOnline, setNvidiaOnline] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [voiceProvider, setVoiceProvider] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${NVIDIA_BASE}/v1/models`, { signal: AbortSignal.timeout(8000) });
        if (!cancelled) setNvidiaOnline(res.ok);
      } catch { if (!cancelled) setNvidiaOnline(false); }
      try {
        const voiceRes = await fetch(`${PISTATION_API}/ai/voice/health`, { signal: AbortSignal.timeout(8000) });
        if (!voiceRes.ok) throw new Error(`voice health ${voiceRes.status}`);
        const voiceData = await voiceRes.json() as VoiceHealthResponse;
        if (!cancelled) {
          setVoiceAvailable(!!voiceData.available);
          setVoiceProvider(voiceData.active_provider ?? null);
        }
      } catch {
        if (!cancelled) {
          setVoiceAvailable(false);
          setVoiceProvider(null);
        }
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return { nvidiaOnline, voiceAvailable, voiceProvider };
}
