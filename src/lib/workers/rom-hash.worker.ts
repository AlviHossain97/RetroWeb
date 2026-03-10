// Web Worker for ROM hashing (offloads from main thread)
self.onmessage = async (e: MessageEvent<{ id: string; data: ArrayBuffer }>) => {
  const { id, data } = e.data;
  try {
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hash = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    self.postMessage({ id, hash });
  } catch (err) {
    self.postMessage({ id, error: (err as Error).message });
  }
};
