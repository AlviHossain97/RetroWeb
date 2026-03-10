import { useEffect, useState } from "react";
import { getAllSaves, deleteSave, type SaveData, db } from "../lib/storage/db";
import { formatBytes } from "../lib/capability/storage-quota";
import { toast } from "sonner";
import { Save, Download, Trash2, Clock, Upload, Database, HardDrive, Layers } from "lucide-react";

type FilterType = "all" | "sram" | "state";

export default function SavesVault() {
  const [saves, setSaves] = useState<SaveData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const allSaves = await getAllSaves();
      allSaves.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
      setSaves(allSaves);
    } catch (error) {
      console.error("Failed to load saves:", error);
      toast.error("Failed to load storage data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleExport = (save: SaveData) => {
    try {
      const buffer = new Uint8Array(save.data).buffer;
      const blob = new Blob([buffer], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const ext = save.type === 'state' ? '.state' : '.srm';
      let exportName = save.filename;
      if (!exportName.endsWith(ext)) exportName += ext;
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
          const match = file.name.match(/_slot(\d+)\.state$/i);
          if (match) { slot = parseInt(match[1]); baseName = file.name.replace(`_slot${match[1]}.state`, ''); }
          else { baseName = file.name.replace('.state', ''); slot = 0; }
        } else if (file.name.endsWith('.srm')) {
          baseName = file.name.replace('.srm', '');
        }
        try {
          const buffer = await file.arrayBuffer();
          if (type === 'state') {
            await db.saves.add({ filename: baseName, system: 'manual', type: 'state', data: new Uint8Array(buffer), timestamp: new Date(), slot });
          } else {
            const existingId = await db.saves.where({ filename: baseName, type: 'sram' }).primaryKeys();
            if (existingId.length > 0) {
              await db.saves.update(existingId[0] as number, { data: new Uint8Array(buffer), timestamp: new Date() });
            } else {
              await db.saves.add({ filename: baseName, system: 'manual', type: 'sram', data: new Uint8Array(buffer), timestamp: new Date() });
            }
          }
          successCount++;
        } catch (err) { console.error("Import error for", file.name, err); }
      }
      if (successCount > 0) { toast.success(`Imported ${successCount} save file(s)`); loadData(); }
    };
    input.click();
  };

  const sramSaves = saves.filter(s => s.type === 'sram');
  const stateSaves = saves.filter(s => s.type === 'state');
  const totalSRAMBytes = sramSaves.reduce((acc, s) => acc + s.data.byteLength, 0);
  const totalStateBytes = stateSaves.reduce((acc, s) => acc + s.data.byteLength, 0);
  const totalBytes = totalSRAMBytes + totalStateBytes;

  const filteredSaves = saves.filter(s => {
    if (filter === "sram") return s.type === 'sram';
    if (filter === "state") return s.type === 'state';
    return true;
  });

  const FILTER_TABS: { key: FilterType; label: string }[] = [
    { key: "all", label: "All" },
    { key: "sram", label: "SRAM" },
    { key: "state", label: "States" },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <header className="flex-none px-6 pt-8 pb-6" style={{ borderBottom: '1px solid var(--border-soft)' }}>
        <div className="max-w-7xl mx-auto flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5 mb-1" style={{ color: 'var(--text-primary)' }}>
              <Save size={22} style={{ color: 'var(--accent-primary)' }} />
              Save Management
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Manage SRAM and Save States across all games.</p>
          </div>
          <button
            onClick={handleImportClick}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-colors"
            style={{ background: 'var(--accent-primary)', color: '#fff' }}
          >
            <Upload size={15} /> Import
          </button>
        </div>

        {/* Stats chips */}
        <div className="max-w-7xl mx-auto flex flex-wrap gap-3">
          {[
            { icon: <Database size={14} />, label: 'Total saves', value: saves.length.toString() },
            { icon: <HardDrive size={14} />, label: 'SRAM files', value: sramSaves.length.toString() },
            { icon: <Layers size={14} />, label: 'Save states', value: stateSaves.length.toString() },
            { icon: <Clock size={14} />, label: 'Total size', value: formatBytes(totalBytes) },
          ].map(chip => (
            <div key={chip.label} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-soft)', color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--accent-primary)' }}>{chip.icon}</span>
              <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{chip.value}</span>
              <span>{chip.label}</span>
            </div>
          ))}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          {/* Filter pills */}
          <div className="flex gap-2 mb-4">
            {FILTER_TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className="px-3 py-1 rounded-full text-xs font-bold transition-colors"
                style={{
                  background: filter === tab.key ? 'var(--accent-primary)' : 'var(--surface-2)',
                  color: filter === tab.key ? '#fff' : 'var(--text-muted)',
                  border: `1px solid ${filter === tab.key ? 'var(--accent-primary)' : 'var(--border-soft)'}`,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-[60px] rounded-xl animate-pulse" style={{ background: 'var(--surface-1)' }} />
              ))}
            </div>
          ) : filteredSaves.length === 0 ? (
            <div className="text-center py-20 rounded-xl" style={{ border: '1px dashed var(--border-soft)' }}>
              <Save className="mx-auto mb-4" size={48} strokeWidth={1} style={{ color: 'var(--text-muted)' }} />
              <h3 className="font-bold text-xl mb-2" style={{ color: 'var(--text-primary)' }}>No Saves Found</h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Play some games to generate SRAM and Save States.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {filteredSaves.map((save, idx) => (
                <div
                  key={save.id}
                  className="flex items-center gap-3 px-4 rounded-xl transition-all duration-150"
                  style={{
                    height: 60,
                    background: idx % 2 === 0 ? 'var(--surface-1)' : 'var(--bg-primary)',
                    border: '1px solid var(--border-soft)',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-primary)'; (e.currentTarget as HTMLElement).style.background = 'var(--surface-2)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-soft)'; (e.currentTarget as HTMLElement).style.background = idx % 2 === 0 ? 'var(--surface-1)' : 'var(--bg-primary)'; }}
                >
                  {/* Thumbnail or Icon */}
                  {save.image ? (
                    <div className="shrink-0 w-12 h-8 rounded overflow-hidden border" style={{ borderColor: 'var(--border-soft)' }}>
                      <img src={save.image} alt="" className="w-full h-full object-cover" />
                    </div>
                  ) : (
                    <div className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: save.type === 'state' ? 'rgba(139,92,246,0.15)' : 'rgba(204,0,0,0.15)', border: `1px solid ${save.type === 'state' ? 'rgba(139,92,246,0.3)' : 'rgba(204,0,0,0.3)'}` }}>
                      <Save size={14} style={{ color: save.type === 'state' ? '#8b5cf6' : 'var(--accent-primary)' }} />
                    </div>
                  )}

                  {/* Filename */}
                  <span className="font-medium text-sm flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{save.filename}</span>

                  {/* Type badge */}
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase shrink-0 hidden sm:inline" style={{ background: save.type === 'state' ? 'rgba(139,92,246,0.15)' : 'rgba(204,0,0,0.15)', color: save.type === 'state' ? '#8b5cf6' : 'var(--accent-primary)', border: `1px solid ${save.type === 'state' ? 'rgba(139,92,246,0.3)' : 'rgba(204,0,0,0.3)'}` }}>
                    {save.type === 'state' ? `State${save.slot !== undefined ? ` · Slot ${save.slot}` : ''}` : 'SRAM'}
                  </span>

                  {/* Timestamp */}
                  <span className="text-[11px] shrink-0 hidden md:block" style={{ color: 'var(--text-muted)' }}>
                    {save.timestamp.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>

                  {/* Size */}
                  <span className="text-[11px] font-mono shrink-0 w-14 text-right hidden sm:block" style={{ color: 'var(--text-muted)' }}>
                    {formatBytes(save.data.byteLength)}
                  </span>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 shrink-0 ml-1">
                    <button
                      onClick={() => handleExport(save)}
                      className="p-1.5 rounded-lg transition-colors"
                      style={{ color: 'var(--text-muted)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)'; (e.currentTarget as HTMLElement).style.background = 'var(--surface-3)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)'; (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      title="Export"
                    >
                      <Download size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(save.id)}
                      className="p-1.5 rounded-lg transition-colors"
                      style={{ color: 'var(--text-muted)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#ef4444'; (e.currentTarget as HTMLElement).style.background = 'rgba(239,68,68,0.1)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)'; (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
