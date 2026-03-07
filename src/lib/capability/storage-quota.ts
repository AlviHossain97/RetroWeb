export function formatBytes(bytes: number, decimals = 2) {
    if (!+bytes) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export async function getStorageEstimate() {
    if (navigator.storage && navigator.storage.estimate) {
        const { usage, quota } = await navigator.storage.estimate();
        return {
            usedMB: Math.round((usage ?? 0) / 1024 / 1024),
            totalMB: Math.round((quota ?? 0) / 1024 / 1024),
            percentUsed: Math.round(((usage ?? 0) / (quota ?? 1)) * 100),
        };
    }
    return null;
}
