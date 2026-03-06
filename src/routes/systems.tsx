import { useEffect, useState, useMemo, useCallback } from "react";
import { SYSTEMS, type SystemInfo } from "../data/systemBrowserData";
import { hasBIOS, getAllGames } from "../lib/storage/db";
import SystemCard from "../components/SystemCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Filter } from "lucide-react";

export default function Systems() {
    const [biosStatus, setBiosStatus] = useState<Record<string, Record<string, boolean>>>({});
    const [gameCounts, setGameCounts] = useState<Record<string, number>>({});
    const [searchQuery, setSearchQuery] = useState("");
    const [filterStatus, setFilterStatus] = useState<"all" | "ready" | "needs_setup">("all");

    useEffect(() => {
        let cancelled = false;

        const run = async () => {
            const [status, counts] = await Promise.all([
                (async () => {
                    const nextStatus: Record<string, Record<string, boolean>> = {};
                    for (const system of SYSTEMS) {
                        if (system.bios.length === 0) continue;
                        nextStatus[system.id] = {};
                        for (const biosFile of system.bios) {
                            nextStatus[system.id][biosFile] = await hasBIOS(biosFile);
                        }
                    }
                    return nextStatus;
                })(),
                (async () => {
                    const allGames = await getAllGames();
                    const nextCounts: Record<string, number> = {};
                    for (const game of allGames) {
                        nextCounts[game.system] = (nextCounts[game.system] || 0) + 1;
                    }
                    return nextCounts;
                })(),
            ]);

            if (!cancelled) {
                setBiosStatus(status);
                setGameCounts(counts);
            }
        };

        void run();
        return () => {
            cancelled = true;
        };
    }, []);

    const checkBios = useCallback(async () => {
        const status: Record<string, Record<string, boolean>> = {};
        for (const system of SYSTEMS) {
            if (system.bios.length > 0) {
                status[system.id] = {};
                for (const biosFile of system.bios) {
                    status[system.id][biosFile] = await hasBIOS(biosFile);
                }
            }
        }
        setBiosStatus(status);
    }, []);

    // Derived states and Filtering
    const filteredSystems = useMemo(() => {
        return SYSTEMS.filter(sys => {
            // Search Query
            const matchesSearch =
                sys.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                sys.manufacturer.toLowerCase().includes(searchQuery.toLowerCase()) ||
                sys.extensions.some(ext => ext.toLowerCase().includes(searchQuery.toLowerCase()));

            if (!matchesSearch) return false;

            // BIOS Status Filter
            const needsBios = sys.bios.length > 0;
            const isBiosReady = !needsBios || sys.bios.every(b => biosStatus[sys.id]?.[b]);

            if (filterStatus === "ready" && !isBiosReady) return false;
            if (filterStatus === "needs_setup" && isBiosReady) return false;

            return true;
        });
    }, [searchQuery, filterStatus, biosStatus]);

    const supportedSystems = filteredSystems.filter(s => s.tier === "doable");
    const experimentalSystems = filteredSystems.filter(s => s.tier === "experimental" || s.tier === "coming_soon");

    // Grouping helper
    const renderSystemGrid = (systems: SystemInfo[]) => {
        const sorted = [...systems].sort((a, b) => {
            const aNeedsBios = a.bios.length > 0 && !a.bios.every(biosFile => biosStatus[a.id]?.[biosFile]);
            const bNeedsBios = b.bios.length > 0 && !b.bios.every(biosFile => biosStatus[b.id]?.[biosFile]);
            if (aNeedsBios === bNeedsBios) return a.name.localeCompare(b.name);
            return aNeedsBios ? 1 : -1;
        });

        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sorted.map(sys => (
                    <SystemCard
                        key={sys.id}
                        sys={sys}
                        biosStatus={biosStatus[sys.id] || {}}
                        gameCount={gameCounts[sys.id] || 0}
                        onBiosChange={checkBios}
                    />
                ))}
            </div>
        );
    };

    return (
        <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8">
            <div className="mb-8">
                <h1 className="text-[32px] font-bold tracking-tight text-foreground mb-2">Supported Systems</h1>
                <p className="font-sans text-lg text-muted-foreground">
                    Your complete guide to what RetroWeb supports. Upload BIOS files to unlock CD-based systems.
                </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                    <input
                        type="text"
                        placeholder="Search systems, manufacturers, or extensions..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-card border border-border pl-11 pr-4 py-3 rounded-md focus:outline-none focus:border-primary text-sm transition-colors text-foreground"
                    />
                </div>

                <div className="relative min-w-[200px]">
                    <Filter className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value as "all" | "ready" | "needs_setup")}
                        className="w-full bg-card border border-border pl-11 pr-4 py-3 rounded-md focus:outline-none focus:border-primary text-sm appearance-none cursor-pointer transition-colors text-foreground"
                    >
                        <option value="all">All Statuses</option>
                        <option value="ready">Ready to Play</option>
                        <option value="needs_setup">Needs Setup (Missing BIOS)</option>
                    </select>
                </div>
            </div>

            <Tabs defaultValue="supported" className="w-full">
                <TabsList className="mb-8 bg-muted border border-border rounded-md p-1">
                    <TabsTrigger value="supported" className="rounded-sm font-sans text-xs uppercase tracking-widest font-bold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                        Fully Supported ({supportedSystems.length})
                    </TabsTrigger>
                    <TabsTrigger value="experimental" className="rounded-sm font-sans text-xs uppercase tracking-widest font-bold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                        Experimental ({experimentalSystems.length})
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="supported" className="mt-0 outline-none">
                    {renderSystemGrid(supportedSystems)}
                </TabsContent>

                <TabsContent value="experimental" className="mt-0 outline-none">
                    <div className="mb-6 p-4 border border-destructive/30 bg-[#1A0A0A] rounded-md shadow-sm text-sm text-destructive font-sans">
                        <strong className="font-bold">Warning:</strong> These systems are highly experimental and may crash the browser, run slowly, or have audio glitches.
                    </div>
                    {renderSystemGrid(experimentalSystems)}
                </TabsContent>
            </Tabs>
        </div>
    );
}
