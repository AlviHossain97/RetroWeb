import { useRef } from "react";
import { Link } from "react-router";
import { type SystemInfo } from "../data/systemBrowserData";
import { saveBIOS, validateBiosFilename } from "../lib/storage/db";
import { toast } from "sonner";
import { UploadCloud, CheckCircle2, AlertCircle, PlayCircle, Gamepad2 } from "lucide-react";
import { getSystemColor } from "../lib/library/title-utils";

interface SystemCardProps {
  sys: SystemInfo;
  biosStatus: Record<string, boolean>;
  gameCount: number;
  onBiosChange: () => void;
}

export default function SystemCard({ sys, biosStatus, gameCount, onBiosChange }: SystemCardProps) {
  const isDoable = sys.tier === "doable";
  const needsBios = sys.bios.length > 0;
  const isBiosReady = !needsBios || sys.bios.every((b) => biosStatus[b]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const systemColor = getSystemColor(sys.id);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const file = e.target.files[0];
    const validation = validateBiosFilename(file.name);
    if (!validation.isValid || validation.systemId !== sys.id || !validation.expectedName) {
      toast.error(`Wrong file. Expected one of: ${sys.bios.join(", ")}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    try {
      const buffer = await file.arrayBuffer();
      const result = await saveBIOS(validation.expectedName, sys.id, new Uint8Array(buffer), {
        sourceFilename: file.name,
      });

      if (result.verifiedHash) {
        toast.success(`BIOS ${result.filename} verified and installed!`);
      } else if (result.sizeWarning) {
        toast.warning(`Installed ${result.filename}, but size looks unusual.`);
      } else {
        toast.success(`BIOS ${result.filename} installed!`);
      }

      onBiosChange();
    } catch {
      toast.error(`Failed to install BIOS: ${file.name}`);
    }

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div
      className="bg-card border border-border p-6 hover:border-primary/40 transition-all flex flex-col h-full relative overflow-hidden group rounded-xl card-hover"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      {/* Background accent */}
      <div
        className="absolute -right-10 -top-10 w-40 h-40 rounded-full blur-3xl opacity-10 pointer-events-none transition-opacity group-hover:opacity-20"
        style={{ background: systemColor }}
      />

      {/* Header */}
      <div className="flex justify-between items-start mb-4 z-10">
        <div className="flex items-center gap-4">
          <div
            className="p-3 border border-border rounded-xl group-hover:bg-secondary transition-colors"
            style={{ background: `${systemColor}08` }}
          >
            <Gamepad2 size={24} style={{ color: isDoable ? systemColor : "var(--muted-foreground)" }} />
          </div>
          <div>
            <h3 className="font-bold text-xl text-foreground leading-none mb-1">{sys.name}</h3>
            <p className="text-[11px] text-muted-foreground font-bold uppercase tracking-widest">{sys.manufacturer}</p>
          </div>
        </div>
      </div>

      {/* Meta Tags */}
      <div className="flex flex-wrap items-center gap-2 mb-5 z-10">
        <span className="px-2.5 py-1 text-[10px] uppercase tracking-widest font-bold bg-secondary text-foreground border border-border rounded-lg">
          {sys.era}
        </span>
        <span
          className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest border rounded-lg ${
            isDoable
              ? "bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/20"
              : "bg-destructive/10 text-destructive border-destructive/20"
          }`}
        >
          {sys.tier.replace("_", " ")}
        </span>
      </div>

      {/* Extensions */}
      <div className="mb-5 z-10 flex-grow">
        <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-3">Accepted Formats</p>
        <div className="flex flex-wrap gap-1.5">
          {sys.extensions.map((ext) => (
            <span
              key={ext}
              className="bg-[var(--surface-1)] text-muted-foreground px-2 py-1 font-mono text-[11px] border border-border rounded-lg"
            >
              .{ext}
            </span>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto pt-4 border-t border-border flex flex-col gap-3 z-10">
        {needsBios ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isBiosReady ? (
                <CheckCircle2 size={16} className="text-[var(--success)]" />
              ) : (
                <AlertCircle size={16} className="text-[var(--warning)]" />
              )}
              <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
                {isBiosReady ? "BIOS Ready" : "BIOS Missing"}
              </span>
            </div>

            {!isBiosReady && (
              <>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-[10px] uppercase font-bold tracking-widest bg-secondary hover:bg-[var(--surface-4)] text-foreground px-3 py-1.5 transition-colors border border-border flex items-center gap-1.5 rounded-lg"
                >
                  <UploadCloud size={14} />
                  Upload
                </button>
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-[var(--success)]/50" />
            <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground opacity-50">
              No BIOS required
            </span>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground font-bold uppercase tracking-widest">
            {gameCount === 1 ? "1 game" : `${gameCount} games`}
          </span>
          <Link
            to={needsBios && !isBiosReady ? "/bios" : "/"}
            className="text-[11px] font-bold text-primary hover:text-[var(--accent)] flex items-center gap-1.5 uppercase tracking-widest transition-colors"
          >
            <PlayCircle size={14} />
            {needsBios && !isBiosReady ? "Open BIOS Vault" : "View Library"}
          </Link>
        </div>
      </div>
    </div>
  );
}
