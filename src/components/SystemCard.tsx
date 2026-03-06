import { useRef } from "react";
import { Link } from "react-router";
import { type SystemInfo } from "../data/systemBrowserData";
import { saveBIOS, validateBiosFilename } from "../lib/storage/db";
import { toast } from "sonner";
import { UploadCloud, CheckCircle2, AlertCircle, PlayCircle, Gamepad2 } from "lucide-react";

interface SystemCardProps {
    sys: SystemInfo;
    biosStatus: Record<string, boolean>;
    gameCount: number;
    onBiosChange: () => void;
}

export default function SystemCard({ sys, biosStatus, gameCount, onBiosChange }: SystemCardProps) {
    const isDoable = sys.tier === "doable";
    const needsBios = sys.bios.length > 0;

    // Check if ALL required BIOS files are present
    const isBiosReady = !needsBios || sys.bios.every(b => biosStatus[b]);
    const fileInputRef = useRef<HTMLInputElement>(null);

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
                toast.success(`BIOS ${result.filename} verified and installed successfully!`);
            } else if (result.sizeWarning) {
                toast.warning(`Installed ${result.filename}, but size looks unusual.`);
            } else {
                toast.success(`BIOS ${result.filename} installed successfully!`);
            }

            onBiosChange();
        } catch {
            toast.error(`Failed to install BIOS: ${file.name}`);
        }

        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    return (
        <div className="bg-card border border-border p-6 hover:border-primary transition-colors flex flex-col h-full relative overflow-hidden group rounded-md shadow-sm">
            {/* Background Accent */}
            <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-10 pointer-events-none ${isDoable ? 'bg-primary' : 'bg-destructive'}`} />

            {/* Header */}
            <div className="flex justify-between items-start mb-4 z-10">
                <div className="flex items-center gap-4">
                    <div className="bg-[#111111] p-3 border border-border rounded-md group-hover:bg-muted transition-colors">
                        <Gamepad2 size={24} className={isDoable ? 'text-primary' : 'text-muted-foreground'} />
                    </div>
                    <div>
                        <h3 className="font-bold text-2xl text-foreground leading-none mb-1">{sys.name}</h3>
                        <p className="font-sans text-[11px] text-muted-foreground font-bold uppercase tracking-widest">{sys.manufacturer}</p>
                    </div>
                </div>
            </div>

            {/* Meta Tags */}
            <div className="flex flex-wrap items-center gap-2 mb-6 z-10">
                <span className="px-2 py-1 text-[10px] uppercase tracking-widest font-bold bg-muted text-foreground border border-border rounded-sm">
                    {sys.era}
                </span>
                <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest border rounded-sm ${isDoable ? 'bg-primary/10 text-primary border-primary/20' : 'bg-destructive/10 text-destructive border-destructive/20'
                    }`}>
                    {sys.tier.replace("_", " ")}
                </span>
            </div>

            {/* Extensions */}
            <div className="mb-6 z-10 flex-grow">
                <p className="font-sans text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-3">Accepted Formats</p>
                <div className="flex flex-wrap gap-2">
                    {sys.extensions.map(ext => (
                        <span key={ext} className="bg-[#111111] text-muted-foreground px-2 py-1 font-mono text-xs border border-border rounded-sm">
                            .{ext}
                        </span>
                    ))}
                </div>
            </div>

            {/* Actions / Status Footer */}
            <div className="mt-auto pt-5 border-t border-border flex flex-col gap-4 z-10">
                {/* BIOS Status */}
                {needsBios ? (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            {isBiosReady ? (
                                <CheckCircle2 size={16} className="text-green-500" />
                            ) : (
                                <AlertCircle size={16} className="text-yellow-500" />
                            )}
                            <span className="font-sans text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
                                {isBiosReady ? 'BIOS Ready' : 'BIOS Missing'}
                            </span>
                        </div>

                        {!isBiosReady && (
                            <>
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    className="font-sans text-[10px] uppercase font-bold tracking-widest bg-muted hover:bg-secondary text-foreground px-3 py-1.5 transition-colors border border-border flex items-center gap-1.5 rounded-sm"
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
                        <CheckCircle2 size={16} className="text-green-500/50" />
                        <span className="font-sans text-[11px] font-bold uppercase tracking-widest text-muted-foreground opacity-50">No BIOS required</span>
                    </div>
                )}

                {/* Library Link */}
                <div className="flex items-center justify-between mt-1">
                    <span className="font-sans text-xs text-muted-foreground font-bold uppercase tracking-widest">
                        {gameCount === 1 ? '1 game' : `${gameCount} games`}
                    </span>
                    <Link
                        to={needsBios && !isBiosReady ? "/bios" : "/"}
                        className="font-sans text-[11px] font-bold text-primary hover:text-destructive flex items-center gap-1.5 uppercase tracking-widest transition-colors"
                    >
                        <PlayCircle size={14} />
                        {needsBios && !isBiosReady ? "Open BIOS Vault" : "View Library"}
                    </Link>
                </div>
            </div>
        </div>
    );
}
