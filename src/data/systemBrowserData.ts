export interface SystemInfo {
    id: string;
    name: string;
    manufacturer: "Nintendo" | "Sega" | "Sony" | "Other";
    era: string;
    tier: "doable" | "experimental" | "coming_soon";
    extensions: string[];
    bios: string[];
    iconUrl?: string; // TBD fallback if needed, we'll try lucide icons or simple SVGs first
}

export const SYSTEMS: SystemInfo[] = [
    {
        id: "nes",
        name: "Nintendo Entertainment System",
        manufacturer: "Nintendo",
        era: "1983 · 8-bit",
        tier: "doable",
        extensions: ["nes", "zip"],
        bios: []
    },
    {
        id: "snes",
        name: "Super Nintendo",
        manufacturer: "Nintendo",
        era: "1990 · 16-bit",
        tier: "doable",
        extensions: ["smc", "sfc", "zip"],
        bios: []
    },
    {
        id: "gb",
        name: "Game Boy Series",
        manufacturer: "Nintendo",
        era: "1989/1998/2001 · Handheld",
        tier: "doable",
        extensions: ["gb", "gbc", "gba", "zip"],
        bios: []
    },
    {
        id: "genesis",
        name: "Sega Genesis / Mega Drive",
        manufacturer: "Sega",
        era: "1988 · 16-bit",
        tier: "doable",
        extensions: ["md", "smd", "gen", "bin", "zip"],
        bios: []
    },
    {
        id: "ps1",
        name: "PlayStation 1",
        manufacturer: "Sony",
        era: "1994 · 32-bit",
        tier: "doable",
        extensions: ["chd"],
        bios: ["scph5501.bin"]
    },
    {
        id: "n64",
        name: "Nintendo 64",
        manufacturer: "Nintendo",
        era: "1996 · 64-bit",
        tier: "experimental",
        extensions: ["n64", "z64", "zip"],
        bios: []
    }
];
