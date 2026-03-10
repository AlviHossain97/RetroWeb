import { useState, useRef, useCallback } from "react";
import { Copy, Check, Wifi, WifiOff, Users, X } from "lucide-react";
import { NetplaySession, type NetplayRole, type NetplayState, type NetplayInput } from "../lib/netplay/session";
import { toast } from "sonner";

interface NetplayPanelProps {
  onRemoteInput?: (input: NetplayInput) => void;
  onSessionChange?: (session: NetplaySession | null) => void;
}

export default function NetplayPanel({ onRemoteInput, onSessionChange }: NetplayPanelProps) {
  const [role, setRole] = useState<NetplayRole | null>(null);
  const [state, setState] = useState<NetplayState | null>(null);
  const [offerText, setOfferText] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [localCode, setLocalCode] = useState("");
  const [step, setStep] = useState<"pick" | "host-waiting" | "host-paste" | "guest-paste" | "guest-waiting" | "connected">("pick");
  const [copied, setCopied] = useState(false);
  const sessionRef = useRef<NetplaySession | null>(null);

  const handleStateChange = useCallback((s: NetplayState) => {
    setState(s);
    if (s.connected) setStep("connected");
  }, []);

  const handleRemoteInput = useCallback((input: NetplayInput) => {
    onRemoteInput?.(input);
  }, [onRemoteInput]);

  const handleHost = async () => {
    const session = new NetplaySession("host", handleStateChange, handleRemoteInput);
    sessionRef.current = session;
    onSessionChange?.(session);
    setRole("host");
    try {
      const offer = await session.createOffer();
      setLocalCode(offer);
      setStep("host-waiting");
    } catch {
      toast.error("Failed to create offer");
    }
  };

  const handleHostAcceptAnswer = async () => {
    if (!sessionRef.current || !answerText.trim()) return;
    try {
      await sessionRef.current.acceptAnswer(answerText.trim());
      toast.success("Connecting...");
      setStep("connected");
    } catch {
      toast.error("Invalid answer code");
    }
  };

  const handleJoin = async () => {
    if (!offerText.trim()) return;
    const session = new NetplaySession("guest", handleStateChange, handleRemoteInput);
    sessionRef.current = session;
    onSessionChange?.(session);
    setRole("guest");
    try {
      const answer = await session.acceptOffer(offerText.trim());
      setLocalCode(answer);
      setStep("guest-waiting");
    } catch {
      toast.error("Invalid host code");
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(localCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Copied to clipboard");
  };

  const handleDisconnect = () => {
    sessionRef.current?.destroy();
    sessionRef.current = null;
    onSessionChange?.(null);
    setRole(null);
    setState(null);
    setOfferText("");
    setAnswerText("");
    setLocalCode("");
    setStep("pick");
  };

  const isConnected = state?.connected ?? false;

  return (
    <div className="rounded-xl p-4" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Users size={16} /> Netplay
        </h3>
        {isConnected && (
          <span className="flex items-center gap-1 text-xs font-medium" style={{ color: "#22c55e" }}>
            <Wifi size={12} /> Connected
          </span>
        )}
        {role && !isConnected && step !== "connected" && (
          <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            <WifiOff size={12} /> Waiting...
          </span>
        )}
      </div>

      {step === "pick" && (
        <div className="flex flex-col gap-2">
          <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
            Peer-to-peer multiplayer. No server needed — share a code with your friend.
          </p>
          <button
            onClick={() => void handleHost()}
            className="w-full px-4 py-3 rounded-lg text-sm font-medium transition-colors"
            style={{ background: "var(--accent-primary)", color: "#fff" }}
          >
            🎮 Host Game (Player 1)
          </button>
          <div className="text-xs text-center my-1" style={{ color: "var(--text-muted)" }}>— or —</div>
          <div className="flex gap-2">
            <input
              value={offerText}
              onChange={(e) => setOfferText(e.target.value)}
              placeholder="Paste host code here..."
              className="flex-1 px-3 py-2 rounded-lg text-xs"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)", color: "var(--text-primary)" }}
            />
            <button
              onClick={() => void handleJoin()}
              disabled={!offerText.trim()}
              className="px-4 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
              style={{ background: "var(--accent-primary)", color: "#fff" }}
            >
              Join
            </button>
          </div>
        </div>
      )}

      {step === "host-waiting" && (
        <div className="flex flex-col gap-2">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Share this code with Player 2:
          </p>
          <div className="relative">
            <textarea
              readOnly
              value={localCode}
              rows={3}
              className="w-full px-3 py-2 rounded-lg text-[10px] font-mono resize-none"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)", color: "var(--text-secondary)" }}
            />
            <button onClick={handleCopy} className="absolute top-2 right-2 p-1.5 rounded" style={{ background: "var(--surface-3)" }}>
              {copied ? <Check size={12} style={{ color: "#22c55e" }} /> : <Copy size={12} style={{ color: "var(--text-muted)" }} />}
            </button>
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Once they give you their answer code, paste it below:
          </p>
          <div className="flex gap-2">
            <input
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="Paste answer code..."
              className="flex-1 px-3 py-2 rounded-lg text-xs"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)", color: "var(--text-primary)" }}
            />
            <button
              onClick={() => void handleHostAcceptAnswer()}
              disabled={!answerText.trim()}
              className="px-4 py-2 rounded-lg text-xs font-medium disabled:opacity-40"
              style={{ background: "var(--accent-primary)", color: "#fff" }}
            >
              Connect
            </button>
          </div>
        </div>
      )}

      {step === "guest-waiting" && (
        <div className="flex flex-col gap-2">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Send this answer code back to the host:
          </p>
          <div className="relative">
            <textarea
              readOnly
              value={localCode}
              rows={3}
              className="w-full px-3 py-2 rounded-lg text-[10px] font-mono resize-none"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)", color: "var(--text-secondary)" }}
            />
            <button onClick={handleCopy} className="absolute top-2 right-2 p-1.5 rounded" style={{ background: "var(--surface-3)" }}>
              {copied ? <Check size={12} style={{ color: "#22c55e" }} /> : <Copy size={12} style={{ color: "var(--text-muted)" }} />}
            </button>
          </div>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Waiting for host to accept...
          </p>
        </div>
      )}

      {step === "connected" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 p-3 rounded-lg" style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)" }}>
            <Wifi size={16} style={{ color: "#22c55e" }} />
            <div>
              <p className="text-sm font-medium" style={{ color: "#22c55e" }}>Connected!</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                You are Player {role === "host" ? "1" : "2"}. Input is being synced.
              </p>
            </div>
          </div>
        </div>
      )}

      {role && (
        <button
          onClick={handleDisconnect}
          className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs transition-colors"
          style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
        >
          <X size={12} /> Disconnect
        </button>
      )}
    </div>
  );
}
