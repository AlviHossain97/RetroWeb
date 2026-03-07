export function getThreadingCapability() {
    const hasSharedArrayBuffer = typeof SharedArrayBuffer !== 'undefined';
    const isCrossOriginIsolated = self.crossOriginIsolated === true;

    return {
        canUseThreads: hasSharedArrayBuffer && isCrossOriginIsolated,
        reason: !hasSharedArrayBuffer
            ? 'SharedArrayBuffer not available'
            : !isCrossOriginIsolated
                ? 'Cross-origin isolation not enabled'
                : 'ready',
    };
}
