// Helper to hash ROMs via Web Worker (keeps UI thread responsive)
let worker: Worker | null = null;
let idCounter = 0;
const pending = new Map<string, { resolve: (hash: string) => void; reject: (err: Error) => void }>();

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL("./rom-hash.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (e: MessageEvent<{ id: string; hash?: string; error?: string }>) => {
      const { id, hash, error } = e.data;
      const p = pending.get(id);
      if (!p) return;
      pending.delete(id);
      if (error) p.reject(new Error(error));
      else p.resolve(hash!);
    };
  }
  return worker;
}

export function hashROMInWorker(data: ArrayBuffer): Promise<string> {
  return new Promise((resolve, reject) => {
    const id = String(++idCounter);
    pending.set(id, { resolve, reject });
    getWorker().postMessage({ id, data }, [data]);
  });
}

export function terminateHashWorker() {
  if (worker) {
    worker.terminate();
    worker = null;
    pending.clear();
  }
}
