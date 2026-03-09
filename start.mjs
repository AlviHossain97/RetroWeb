import { spawn } from "child_process";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ollamaPath = resolve(process.env.LOCALAPPDATA, "Programs", "Ollama", "ollama.exe");
const kokoroScript = resolve(__dirname, "scripts", "kokoro-tts-server.py");

const services = [];

function startService(name, cmd, args, opts = {}) {
  const proc = spawn(cmd, args, {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, ...opts.env },
    shell: true,
  });

  proc.stdout.on("data", (d) => {
    for (const line of d.toString().split("\n").filter(Boolean))
      console.log(`[${name}] ${line}`);
  });
  proc.stderr.on("data", (d) => {
    for (const line of d.toString().split("\n").filter(Boolean))
      console.log(`[${name}] ${line}`);
  });
  proc.on("exit", (code) => {
    console.log(`[${name}] exited with code ${code}`);
  });

  services.push({ name, proc });
  return proc;
}

// Graceful shutdown
function cleanup() {
  console.log("\nShutting down all services...");
  for (const { name, proc } of services) {
    if (!proc.killed) {
      console.log(`  Stopping ${name} (PID ${proc.pid})`);
      proc.kill("SIGTERM");
    }
  }
  setTimeout(() => process.exit(0), 2000);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
process.on("SIGHUP", cleanup);

console.log("Starting all services...\n");

// 1. Ollama
startService("Ollama", ollamaPath, ["serve"], {
  env: { OLLAMA_ORIGINS: "*" },
});

// 2. Kokoro TTS/STT
startService("Kokoro", "py", [kokoroScript]);

// 3. Vite dev server
startService("Vite", "npx", ["vite", "--host", "0.0.0.0", "--port", "5173"]);

console.log(`
  Services starting:
    Vite    → http://localhost:5173
    Ollama  → http://localhost:11434
    Kokoro  → http://localhost:8787

  Press Ctrl+C to stop all services.
`);
