import { useEffect, useState } from "react";
import { getAllSaves, deleteSave, type SaveData, db } from "../lib/storage/db";
import { formatBytes } from "../lib/capability/storage-quota";
import { toast } from "sonner";
import { Save, Download, Trash2, Clock, Upload } from "lucide-react";

export default function SavesVault() {
    const [saves, setSaves] = useState<SaveData[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const allSaves = await getAllSaves();
            // Sort by most recent first
            allSaves.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
            setSaves(allSaves);
        } catch (error) {
            console.error("Failed to load saves:", error);
            toast.error("Failed to load storage data");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleExport = (save: SaveData) => {
        try {
            // Guarantee plain ArrayBuffer instead of possible SharedArrayBuffer from Uint8Array.buffer
            const buffer = new Uint8Array(save.data).buffer;
            const blob = new Blob([buffer], { type: "application/octet-stream" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;

            // Construct filename
            const ext = save.type === 'state' ? '.state' : '.srm';
            let exportName = save.filename;
            // if it already has an ext we might just append it, or replace. 
            // for safety we just append it if not present
            if (!exportName.endsWith(ext)) {
                exportName += ext;
            }
            if (save.type === 'state' && save.slot !== undefined) {
                exportName = exportName.replace('.state', `_slot${save.slot}.state`);
            }

            a.download = exportName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            toast.success(`Exported ${exportName}`);
        } catch (err) {
            console.error(err);
            toast.error("Export failed.");
        }
    };

    const handleDelete = async (id?: number) => {
        if (!id) return;
        if (confirm("Are you sure you want to delete this save? This cannot be undone.")) {
            try {
                await deleteSave(id);
                toast.success("Save deleted");
                loadData();
            } catch (err) {
                console.error(err);
                toast.error("Failed to delete save");
            }
        }
    };

    // Very simple global import (just looks for .srm or .state)
    const handleImportClick = () => {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".srm,.state";
        input.multiple = true;

        input.onchange = async (e) => {
            const files = (e.target as HTMLInputElement).files;
            if (!files || files.length === 0) return;

            let successCount = 0;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const type = file.name.endsWith('.state') ? 'state' : 'srm';
                let baseName = file.name;
                let slot: number | undefined = undefined;

                if (type === 'state') {
                    // Try to parse `_slotX` from filename
                    const match = file.name.match(/_slot(\d+)\.state$/i);
                    if (match) {
                        slot = parseInt(match[1]);
                        baseName = file.name.replace(`_slot${match[1]}.state`, '');
                    } else {
                        baseName = file.name.replace('.state', '');
                        slot = 0; // default to 0 if unknown
                    }
                } else if (file.name.endsWith('.srm')) {
                    baseName = file.name.replace('.srm', '');
                }

                try {
                    const buffer = await file.arrayBuffer();

                    if (type === 'state') {
                        // Assuming system is generic/'unknown' for manual imports unless parsed
                        await db.saves.add({ filename: baseName, system: 'manual', type: 'state', data: new Uint8Array(buffer), timestamp: new Date(), slot });
                    } else {
                        // For SRAM, we don't use 'add' logic normally but we can use db.saves.put safely
                        // However we need an ID or it creates dupes. We can try to overwrite.
                        const existingId = await db.saves.where({ filename: baseName, type: 'sram' }).primaryKeys();
                        if (existingId.length > 0) {
                            await db.saves.update(existingId[0] as number, { data: new Uint8Array(buffer), timestamp: new Date() });
                        } else {
                            await db.saves.add({ filename: baseName, system: 'manual', type: 'sram', data: new Uint8Array(buffer), timestamp: new Date() });
                        }
                    }
                    successCount++;
                } catch (err) {
                    console.error("Import error for", file.name, err);
                }
            }
            if (successCount > 0) {
                toast.success(`Imported ${successCount} save file(s)`);
                loadData();
            }
        };
        input.click();
    };

    // Calculate totals
    const totalSRAMBytes = saves.filter(s => s.type === 'sram').reduce((acc, s) => acc + s.data.byteLength, 0);
    const totalStateBytes = saves.filter(s => s.type === 'state').reduce((acc, s) => acc + s.data.byteLength, 0);

    return (
        <div className="flex flex-col h-full bg-background text-foreground overflow-hidden">
            <header className="flex-none p-8 border-b border-border bg-card">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div>
                        <h1 className="text-[32px] font-bold tracking-tight flex items-center gap-3 text-foreground mb-1">
                            <Save className="text-primary" size={32} />
                            Save Management
                        </h1>
                        <p className="font-sans text-muted-foreground text-lg">Manage SRAM and Save States across all games.</p>
                    </div>

                    <button
                        onClick={handleImportClick}
                        className="bg-primary hover:bg-destructive text-primary-foreground px-6 py-3 font-sans font-bold flex items-center gap-2 transition-colors rounded-md"
                    >
                        <Upload size={18} /> Import Saves
                    </button>
                </div>
            </header>

            <main className="flex-1 overflow-y-auto p-6">
                <div className="max-w-6xl mx-auto space-y-8">

                    {/* Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-card p-6 border border-border rounded-md shadow-sm">
                            <h3 className="font-sans text-xs text-muted-foreground font-bold uppercase tracking-widest mb-3">Total SRAM Used</h3>
                            <div className="flex items-end gap-3">
                                <p className="font-bold text-[40px] leading-none text-foreground">{formatBytes(totalSRAMBytes)}</p>
                                <p className="font-sans text-sm text-muted-foreground mb-1">{saves.filter(s => s.type === 'sram').length} files</p>
                            </div>
                        </div>
                        <div className="bg-card p-6 border border-border rounded-md shadow-sm">
                            <h3 className="font-sans text-xs text-muted-foreground font-bold uppercase tracking-widest mb-3">Total States Used</h3>
                            <div className="flex items-end gap-3">
                                <p className="font-bold text-[40px] leading-none text-primary">{formatBytes(totalStateBytes)}</p>
                                <p className="font-sans text-sm text-muted-foreground mb-1">{saves.filter(s => s.type === 'state').length} files</p>
                            </div>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="text-center py-12 font-sans text-muted-foreground animate-pulse">Scanning storage...</div>
                    ) : (
                        <div className="space-y-4">
                            {saves.map(save => (
                                <div key={save.id} className="bg-card border border-border rounded-md p-5 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-primary transition-colors group shadow-sm">
                                    <div className="flex items-center gap-5">
                                        <div className={`p-4 rounded-sm ${save.type === 'state' ? 'bg-[#111111] text-foreground' : 'bg-primary/10 text-primary'}`}>
                                            <Save size={24} strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <h3 className="font-sans font-bold text-xl text-foreground mb-1">{save.filename}</h3>
                                            <div className="flex flex-wrap items-center gap-4 font-sans text-xs text-muted-foreground uppercase tracking-widest">
                                                <span className={`px-2 py-1 font-bold rounded-sm ${save.type === 'state' ? 'bg-muted text-foreground' : 'bg-primary/20 text-primary'}`}>
                                                    {save.type} {save.type === 'state' && save.slot !== undefined ? `(SLOT ${save.slot})` : ''}
                                                </span>
                                                <span className="flex items-center gap-1.5 border border-border px-2 py-1 rounded-sm">
                                                    <Clock size={12} className="text-primary" />
                                                    {save.timestamp.toLocaleString()}
                                                </span>
                                                <span className="font-mono text-muted-foreground tracking-normal">{formatBytes(save.data.byteLength)}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex gap-3 shrink-0 pt-4 md:pt-0 border-t border-border md:border-t-0 my-auto">
                                        <button
                                            onClick={() => handleExport(save)}
                                            className="px-5 py-2 font-sans text-xs font-bold tracking-widest uppercase bg-muted border border-border text-foreground hover:bg-secondary transition-colors flex items-center justify-center gap-2 rounded-sm"
                                            title="Export Save"
                                        >
                                            <Download size={14} /> Export
                                        </button>
                                        <button
                                            onClick={() => handleDelete(save.id)}
                                            className="px-4 py-2 bg-[#1A0A0A] border border-destructive/30 text-destructive hover:bg-destructive hover:text-white transition-colors flex justify-center items-center rounded-sm"
                                            title="Delete Save"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {saves.length === 0 && (
                                <div className="text-center py-20 border border-dashed border-border rounded-md bg-card">
                                    <Save className="mx-auto text-muted-foreground mb-6" size={64} strokeWidth={1} />
                                    <h3 className="font-bold text-[32px] text-foreground mb-3">No Saves Found</h3>
                                    <p className="font-sans text-muted-foreground">Play some games to generate SRAM and Save States.</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
