import { useState, useEffect } from "react";
import { NVIDIA_BASE, KOKORO_BASE } from "./constants";

export function useChatHealth() {
  const [nvidiaOnline, setNvidiaOnline] = useState(false);
  const [kokoroOnline, setKokoroOnline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${NVIDIA_BASE}/v1/models`, { signal: AbortSignal.timeout(8000) });
        if (!cancelled) setNvidiaOnline(res.ok);
      } catch { if (!cancelled) setNvidiaOnline(false); }
      try {
        const kRes = await fetch(`${KOKORO_BASE}/health`, { signal: AbortSignal.timeout(8000) });
        if (!cancelled) setKokoroOnline(kRes.ok);
      } catch { if (!cancelled) setKokoroOnline(false); }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return { nvidiaOnline, kokoroOnline };
}
