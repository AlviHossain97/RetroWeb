import { useRef } from "react";
import { Link } from "react-router";
import { type SystemInfo } from "../data/systemBrowserData";
import { saveBIOS, validateBiosFilename } from "../lib/storage/db";
import { toast } from "sonner";
import { UploadCloud, CheckCircle2, AlertCircle, Gamepad2, ChevronRight } from "lucide-react";

interface SystemCardProps {
  sys: SystemInfo;
  biosStatus: Record<string, boolean>;
  gameCount: number;
  onBiosChange: () => void;
}

const SYSTEM_ACCENT_COLORS: Record<string, string> = {
  nes: '#e53e3e', snes: '#805ad5', gb: '#2b6cb0', gbc: '#276749',
  gba: '#2c5282', genesis: '#4a5568', psx: '#1a365d', n64: '#2f855a',
  default: '#cc0000',
};

export default function SystemCard({ sys, biosStatus, gameCount, onBiosChange }: SystemCardProps) {
  const isDoable = sys.tier === "doable";
  const needsBios = sys.bios.length > 0;
  const isBiosReady = !needsBios || sys.bios.every(b => biosStatus[b]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const accentColor = SYSTEM_ACCENT_COLORS[sys.id] ?? SYSTEM_ACCENT_COLORS.default;

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const validation = validateBiosFilename(file.name);
    if (!validation.isValid || validation.systemId !== sys.id || !validation.expectedName) {
      toast.error(`Wrong file. Expected one of: ${sys.bios.join(", ")}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    try {
      const buffer = await file.arrayBuffer();
      const result = await saveBIOS(validation.expectedName, sys.id, new Uint8Array(buffer), { sourceFilename: file.name });
      toast[result.verifiedHash ? 'success' : result.sizeWarning ? 'warning' : 'success'](
        result.verifiedHash ? `verified ${result.filename}` : result.sizeWarning ? `${result.filename} size unusual` : `${result.filename} installed`
      );
      onBiosChange();
    } catch { toast.error(`Failed to install: ${file.name}`); }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div
      className="group relative rounded-xl p-4 transition-all duration-200 cursor-default"
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--border-soft)',
        boxShadow: 'var(--shadow-sm)',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = accentColor + '60';
        (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px ${accentColor}30`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-soft)';
        (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-sm)';
      }}
    >
      <div className="flex items-start gap-4">
        <div
          className="shrink-0 w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ background: accentColor + '20', border: `1px solid ${accentColor}40` }}
        >
          <Gamepad2 size={22} style={{ color: accentColor }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-bold text-base leading-tight truncate" style={{ color: 'var(--text-primary)' }}>{sys.name}</h3>
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0"
              style={{
                background: isDoable ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
                color: isDoable ? '#22c55e' : '#f59e0b',
                border: `1px solid ${isDoable ? 'rgba(34,197,94,0.3)' : 'rgba(245,158,11,0.3)'}`,
              }}
            >
              {isDoable ? 'Supported' : sys.tier.replace('_', ' ')}
            </span>
          </div>

          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            {sys.manufacturer} · {sys.era} · {gameCount === 1 ? '1 game' : `${gameCount} games`}
          </p>

          <div className="flex flex-wrap gap-1 mb-3">
            {sys.extensions.map(ext => (
              <span
                key={ext}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{ background: 'var(--surface-3)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)' }}
              >
                .{ext}
              </span>
            ))}
          </div>

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              {needsBios ? (
                isBiosReady ? (
                  <>
                    <CheckCircle2 size={13} className="text-green-500" />
                    <span className="text-[11px] font-medium" style={{ color: '#22c55e' }}>BIOS Ready</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={13} className="text-yellow-500" />
                    <span className="text-[11px] font-medium" style={{ color: '#f59e0b' }}>BIOS Required</span>
                  </>
                )
              ) : (
                <>
                  <CheckCircle2 size={13} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                  <span className="text-[11px]" style={{ color: 'var(--text-muted)', opacity: 0.5 }}>No BIOS needed</span>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              {needsBios && !isBiosReady && (
                <>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[11px] font-bold px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5"
                    style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)' }}
                  >
                    <UploadCloud size={12} /> Upload BIOS
                  </button>
                  <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
                </>
              )}
              <Link
                to={needsBios && !isBiosReady ? "/bios" : "/"}
                className="text-[11px] font-bold px-3 py-1 rounded-lg transition-colors flex items-center gap-1 opacity-0 group-hover:opacity-100"
                style={{ background: accentColor + '20', color: accentColor }}
              >
                {needsBios && !isBiosReady ? 'BIOS Vault' : 'Library'} <ChevronRight size={11} />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
