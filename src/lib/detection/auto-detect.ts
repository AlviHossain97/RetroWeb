import coreMap from "../../data/coreMap.json";

interface CoreMapEntry {
    extensions: string[];
    preferredCore: string;
}

export interface DetectionResult {
    systemId: string;
    coreId: string;
    errorMessage?: string;
}

export function detectSystemByExtension(filename: string): DetectionResult | null {
    const extMatch = filename.match(/\.[^.]+$/);
    if (!extMatch) {
        return { systemId: '', coreId: '', errorMessage: "File has no extension." };
    }

    const ext = extMatch[0].toLowerCase();

    if (ext === '.chd') {
        // Disc image handling requires magic bytes/deeper check or explicit user selection for PS1/Saturn/SegaCD
        return { systemId: 'cd', coreId: '', errorMessage: "CHD detected. Please select system manually." };
    }

    const map = coreMap as Record<string, CoreMapEntry>;
    for (const [systemId, systemInfo] of Object.entries(map)) {
        if (systemInfo.extensions.includes(ext)) {
            return {
                systemId,
                coreId: systemInfo.preferredCore,
            };
        }
    }

    return { systemId: '', coreId: '', errorMessage: `Unknown extension: ${ext}` };
}
