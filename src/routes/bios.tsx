import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Cpu, Trash2, UploadCloud, CheckCircle2, AlertCircle, HardDrive, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { SYSTEMS } from "../data/systemBrowserData";
import {
  getAllBIOSFiles,
  getExpectedBiosSize,
  getKnownBiosHashes,
  hasBIOS,
  removeBIOS,
  saveBIOS,
  validateBiosFilename,
} from "../lib/storage/db";
import { formatBytes } from "../lib/capability/storage-quota";

interface BiosUploadResult {
  filename: string;
  system: string;
  status: "verified" | "unverified" | "size-warning" | "invalid" | "failed";
  message: string;
}

export default function BiosVault() {
  const [biosStatus, setBiosStatus] = useState<Record<string, Record<string, boolean>>>({});
  const [biosSizes, setBiosSizes] = useState<Record<string, number>>({});
  const [biosMeta, setBiosMeta] = useState<Record<string, { hashMd5?: string; verifiedHash?: boolean; expectedSize?: number; installedAt?: number }>>({});
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [lastResults, setLastResults] = useState<BiosUploadResult[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      const statuses: Record<string, Record<string, boolean>> = {};
      const sizes: Record<string, number> = {};

      for (const system of SYSTEMS) {
        if (system.bios.length === 0) continue;

        statuses[system.id] = {};
        for (const biosFile of system.bios) {
          const exists = await hasBIOS(biosFile);
          statuses[system.id][biosFile] = exists;
        }
      }

      const allBios = await getAllBIOSFiles();
      const metaEntries: Record<string, { hashMd5?: string; verifiedHash?: boolean; expectedSize?: number; installedAt?: number }> = {};

      for (const entry of allBios) {
        sizes[entry.filename] = entry.size;
        metaEntries[entry.filename] = {
          hashMd5: entry.hashMd5,
          verifiedHash: entry.verifiedHash,
          expectedSize: entry.expectedSize,
          installedAt: entry.installedAt,
        };
      }

      if (!cancelled) {
        setBiosStatus(statuses);
        setBiosSizes(sizes);
        setBiosMeta(metaEntries);
        setIsLoading(false);
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, []);

  const loadData = async () => {
    setIsLoading(true);

    const statuses: Record<string, Record<string, boolean>> = {};
    const sizes: Record<string, number> = {};

    for (const system of SYSTEMS) {
      if (system.bios.length === 0) continue;

      statuses[system.id] = {};
      for (const biosFile of system.bios) {
        const exists = await hasBIOS(biosFile);
        statuses[system.id][biosFile] = exists;
      }
    }

    const allBios = await getAllBIOSFiles();
    const metaEntries: Record<string, { hashMd5?: string; verifiedHash?: boolean; expectedSize?: number; installedAt?: number }> = {};

    for (const entry of allBios) {
      sizes[entry.filename] = entry.size;
      metaEntries[entry.filename] = {
        hashMd5: entry.hashMd5,
        verifiedHash: entry.verifiedHash,
        expectedSize: entry.expectedSize,
        installedAt: entry.installedAt,
      };
    }

    setBiosStatus(statuses);
    setBiosSizes(sizes);
    setBiosMeta(metaEntries);
    setIsLoading(false);
  };

  const handleFileUpload = async (files: FileList | File[]) => {
    const results: BiosUploadResult[] = [];

    for (const file of Array.from(files)) {
      const validation = validateBiosFilename(file.name);
      if (!validation.isValid || !validation.systemId || !validation.expectedName) {
        results.push({
          filename: file.name,
          system: "unknown",
          status: "invalid",
          message: "Unrecognized BIOS filename",
        });
        continue;
      }

      try {
        const buffer = new Uint8Array(await file.arrayBuffer());

        const expectedSize = getExpectedBiosSize(validation.expectedName);
        if (expectedSize && Math.abs(buffer.byteLength - expectedSize) > expectedSize * 0.15) {
          toast.warning(
            `${validation.expectedName} looks unusual: expected around ${Math.round(expectedSize / 1024)}KB, got ${Math.round(buffer.byteLength / 1024)}KB.`
          );
        }

        const knownHashes = getKnownBiosHashes(validation.expectedName);
        const saveResult = await saveBIOS(validation.expectedName, validation.systemId, buffer, {
          sourceFilename: file.name,
        });

        if (saveResult.sizeWarning) {
          results.push({
            filename: saveResult.filename,
            system: saveResult.system,
            status: "size-warning",
            message: saveResult.sizeWarning,
          });
        } else if (saveResult.verifiedHash) {
          results.push({
            filename: saveResult.filename,
            system: saveResult.system,
            status: "verified",
            message: "MD5 hash verified",
          });
        } else {
          results.push({
            filename: saveResult.filename,
            system: saveResult.system,
            status: "unverified",
            message:
              knownHashes.length > 0
                ? "Hash not recognized, but file was installed"
                : "Installed (no known hash list for this BIOS)",
          });
        }
      } catch (error) {
        console.error("Failed to install BIOS", error);
        results.push({
          filename: file.name,
          system: validation.systemId,
          status: "failed",
          message: "Failed to install BIOS",
        });
      }
    }

    setLastResults(results);

    const verifiedCount = results.filter((result) => result.status === "verified").length;
    const warningCount = results.filter((result) => result.status === "size-warning" || result.status === "unverified").length;
    const failedCount = results.filter((result) => result.status === "failed" || result.status === "invalid").length;

    if (verifiedCount > 0) {
      toast.success(`✅ ${verifiedCount} BIOS file${verifiedCount === 1 ? "" : "s"} verified and installed.`);
    }
    if (warningCount > 0) {
      toast.warning(`⚠️ ${warningCount} BIOS file${warningCount === 1 ? "" : "s"} installed with warnings.`);
    }
    if (failedCount > 0) {
      toast.error(`❌ ${failedCount} BIOS file${failedCount === 1 ? "" : "s"} failed.`);
    }

    const ps1Ready = await hasBIOS("scph5501.bin");
    if (ps1Ready && results.some((result) => result.system === "ps1" && ["verified", "unverified", "size-warning"].includes(result.status))) {
      toast.success("✅ PlayStation 1 BIOS installed — PS1 games are now playable!");
    }

    await loadData();
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDelete = async (filename: string) => {
    if (!window.confirm(`Are you sure you want to delete ${filename}?`)) return;

    await removeBIOS(filename);
    toast.success(`Deleted ${filename}`);
    await loadData();
  };

  const stats = useMemo(() => {
    let totalRequired = 0;
    let totalInstalled = 0;
    let totalSize = 0;

    for (const system of SYSTEMS) {
      totalRequired += system.bios.length;
      for (const biosFile of system.bios) {
        if (biosStatus[system.id]?.[biosFile]) {
          totalInstalled++;
        }
      }
    }

    Object.values(biosSizes).forEach((size) => {
      totalSize += size;
    });

    const completion = totalRequired === 0 ? 100 : Math.round((totalInstalled / totalRequired) * 100);
    return { totalRequired, totalInstalled, totalSize, completion };
  }, [biosStatus, biosSizes]);

  return (
    <div className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-8 flex flex-col h-full">
      <div className="mb-8">
        <h1 className="text-[32px] font-bold tracking-tight text-foreground mb-2 flex items-center gap-3">
          <Cpu className="text-primary" />
          BIOS Vault
        </h1>
        <p className="font-sans text-muted-foreground text-lg">Manage firmware files required for specific emulators.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-card border border-border p-6">
          <p className="font-sans text-xs text-muted-foreground font-bold mb-2 uppercase tracking-widest">Global Readiness</p>
          <div className="flex items-end gap-2 mb-4">
            <span className="font-bold text-[40px] leading-none text-foreground">{stats.completion}%</span>
            <span className="font-sans text-muted-foreground mb-1">completed</span>
          </div>
          <div className="w-full bg-[#111111] h-1.5 overflow-hidden">
            <div className="bg-primary h-full transition-all duration-500" style={{ width: `${stats.completion}%` }} />
          </div>
        </div>

        <div className="bg-card border border-border p-6 flex flex-col justify-center">
          <p className="font-sans text-xs text-muted-foreground font-bold mb-3 uppercase tracking-widest">Vault Status</p>
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-green-500">
              <CheckCircle2 size={18} />
              <span className="font-bold text-2xl text-foreground leading-none">{stats.totalInstalled}</span>
              <span className="font-sans text-sm text-muted-foreground">installed</span>
            </div>
            <div className="flex items-center gap-3 text-destructive">
              <AlertCircle size={18} />
              <span className="font-bold text-2xl text-foreground leading-none">{Math.max(0, stats.totalRequired - stats.totalInstalled)}</span>
              <span className="font-sans text-sm text-muted-foreground">missing</span>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border p-6 flex flex-col justify-center">
          <p className="font-sans text-xs text-muted-foreground font-bold mb-3 uppercase tracking-widest">Storage Used</p>
          <div className="flex items-center gap-4">
            <HardDrive className="text-muted-foreground" size={32} strokeWidth={1.5} />
            <div>
              <p className="font-bold text-[32px] leading-none text-foreground mb-1">{formatBytes(stats.totalSize)}</p>
              <p className="font-sans text-xs text-muted-foreground">IndexedDB Storage</p>
            </div>
          </div>
        </div>
      </div>

      <div
        className={`p-8 text-center transition-colors cursor-pointer mb-8 flex flex-col items-center justify-center gap-4 border border-dashed rounded-md shadow-sm ${isDragging ? "border-primary bg-primary/5" : "border-border bg-card hover:border-primary/50"
          }`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          if (event.dataTransfer.files?.length) {
            void handleFileUpload(event.dataTransfer.files);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadCloud size={48} className={isDragging ? "text-primary" : "text-muted-foreground"} strokeWidth={1.5} />
        <div>
          <h3 className="font-bold text-2xl text-foreground mb-2">Batch Upload BIOS</h3>
          <p className="font-sans text-sm text-muted-foreground">Drop one or more BIOS files here, or click to browse.</p>
        </div>
        <input
          type="file"
          multiple
          className="hidden"
          ref={fileInputRef}
          onChange={(event) => {
            if (event.target.files?.length) {
              void handleFileUpload(event.target.files);
            }
          }}
        />
      </div>

      {lastResults.length > 0 && (
        <div className="mb-8 bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-neutral-800 bg-neutral-950/60">
            <h2 className="font-bold">Latest Upload Summary</h2>
          </div>
          <div className="divide-y divide-neutral-800/60">
            {lastResults.map((result, index) => (
              <div key={`${result.filename}-${index}`} className="p-3 text-sm flex items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-neutral-100">{result.filename}</p>
                  <p className="text-xs text-neutral-500">{result.message}</p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded border ${result.status === "verified"
                    ? "text-green-400 border-green-400/30 bg-green-500/10"
                    : result.status === "failed" || result.status === "invalid"
                      ? "text-red-400 border-red-400/30 bg-red-500/10"
                      : "text-yellow-300 border-yellow-300/30 bg-yellow-500/10"
                    }`}
                >
                  {result.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-card border border-border flex-1 flex flex-col">
        <div className="p-5 border-b border-border bg-[#111111]">
          <h2 className="font-bold text-xl tracking-wide text-foreground">Required Firmware List</h2>
        </div>

        {isLoading ? (
          <div className="p-8 font-sans text-muted-foreground text-center">Loading BIOS status...</div>
        ) : (
          <div className="divide-y divide-border">
            {SYSTEMS.filter((system) => system.bios.length > 0).map((system) => (
              <div key={system.id} className="p-6 flex flex-col lg:flex-row lg:items-start gap-6 hover:bg-[#111111] transition-colors">
                <div className="lg:w-1/4 shrink-0">
                  <h3 className="font-bold text-2xl text-foreground mb-1">{system.name}</h3>
                  <p className="font-sans text-xs text-muted-foreground uppercase tracking-widest font-bold">{system.tier.replace("_", " ")}</p>
                  {system.id === "ps1" && (
                    <button
                      onClick={() => navigate("/systems")}
                      className="mt-4 font-sans text-xs text-primary hover:text-destructive font-bold uppercase tracking-widest transition-colors"
                    >
                      Browse Systems →
                    </button>
                  )}
                </div>

                <div className="flex-1 space-y-3">
                  {system.bios.map((biosFile) => {
                    const installed = biosStatus[system.id]?.[biosFile];
                    const expectedSize = getExpectedBiosSize(biosFile);
                    const metadata = biosMeta[biosFile.toLowerCase()] ?? biosMeta[biosFile];

                    return (
                      <div key={biosFile} className="flex items-center justify-between border border-border p-4 bg-[#111111] rounded-sm gap-4 hover:border-primary transition-colors">
                        <div className="flex items-center gap-4 min-w-0">
                          {installed ? <CheckCircle2 size={20} className="text-green-500 shrink-0" /> : <AlertCircle size={20} className="text-destructive shrink-0" />}
                          <div className="min-w-0">
                            <p className="font-mono text-sm text-foreground mb-1 truncate">{biosFile}</p>
                            <div className="flex flex-wrap items-center gap-3 font-sans text-[11px] text-muted-foreground uppercase tracking-wider">
                              <span>{installed ? `Installed • ${formatBytes(biosSizes[biosFile.toLowerCase()] ?? biosSizes[biosFile] ?? 0)}` : "Missing"}</span>
                              {expectedSize && <span>EXPECTED: ~{Math.round(expectedSize / 1024)}KB</span>}
                              {metadata?.verifiedHash && (
                                <span className="text-green-500 inline-flex items-center gap-1">
                                  <ShieldCheck size={12} /> VERIFIED
                                </span>
                              )}
                              {installed && metadata && metadata.verifiedHash === false && (
                                <span className="text-yellow-500 font-bold">HASH UNKNOWN</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {installed && (
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleDelete(biosFile);
                            }}
                            className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                            title="Remove BIOS"
                          >
                            <Trash2 size={18} />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
