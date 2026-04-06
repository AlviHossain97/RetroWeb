import { spawn, execSync } from "child_process";
import { resolve, dirname, join } from "path";
import { fileURLToPath } from "url";
import { existsSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Ensure Node 22+ is on PATH (Vite 7 requires it)
const node22Dir = join(process.env.HOME || "/home/alvi", ".local", "node22", "bin");
if (existsSync(node22Dir)) {
  process.env.PATH = `${node22Dir}:${process.env.PATH}`;
}
const kokoroScript = resolve(__dirname, "scripts", "kokoro-tts-server.py");
const parakeetScript = resolve(__dirname, "scripts", "parakeet-server.py");
const backendDir = resolve(__dirname, "backend");

const python3 = "python3";

const services = [];

function startService(name, cmd, args, opts = {}) {
  const proc = spawn(cmd, args, {
    stdio: ["ignore", "pipe", "pipe"],
    cwd: opts.cwd || __dirname,
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

console.log("Starting all PiStation services...\n");

// 0. XAMPP (MySQL/phpMyAdmin) — start if not already running
try {
  execSync("pgrep -x mysqld > /dev/null 2>&1", { stdio: "ignore" });
  console.log("[XAMPP] MySQL already running");
} catch {
  console.log("[XAMPP] Starting XAMPP (MySQL + Apache)...");
  try {
    execSync("/opt/lampp/lampp start", { stdio: "inherit", timeout: 15000 });
  } catch (e) {
    console.log("[XAMPP] Warning: could not start XAMPP —", e.message);
  }
}

// 1. FastAPI backend
startService("FastAPI", python3, [
  "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
], { cwd: backendDir });

// 2. Kokoro TTS (CUDA)
startService("Kokoro", python3, [kokoroScript]);

// 3. Parakeet STT (GPU)
startService("Parakeet", python3, [parakeetScript], {
  env: { LD_LIBRARY_PATH: "/usr/local/lib/ollama/cuda_v12" },
});

// 4. Vite dev server
startService("Vite", "npx", ["vite", "--host", "0.0.0.0", "--port", "5173"]);

// 5. Sunshine — NVENC game stream host for Pi (Moonlight client)
// Streams the full desktop to the Pi with hardware encoding
try {
  execSync("pgrep -x sunshine > /dev/null 2>&1", { stdio: "ignore" });
  console.log("[Sunshine] Already running");
} catch {
  startService("Sunshine", "sunshine", []);
}

// 6. Dashboard stream for Pi kiosk display (Xvfb + Brave + FFmpeg → UDP)
// Set PI_IP env var to enable, e.g.: PI_IP=192.168.1.100 npm start
const piIp = process.env.PI_IP;
if (piIp) {
  const dashStreamScript = resolve(__dirname, "scripts", "dashboard-stream.sh");
  startService("DashStream", "bash", [dashStreamScript], {
    env: { PI_IP: piIp },
  });
} else {
  console.log("[DashStream] Skipped — set PI_IP env var to enable (e.g. PI_IP=192.168.1.100)");
}

console.log(`
  ┌──────────────────────────────────────────────────┐
  │             PiStation — All Services             │
  ├──────────────────────────────────────────────────┤
  │  XAMPP      → http://localhost/phpmyadmin        │
  │  Vite      → http://localhost:5173              │
  │  FastAPI   → http://localhost:8000              │
  │  NVIDIA    → integrate.api.nvidia.com (LLM)    │
  │  Kokoro    → http://localhost:8787  (TTS)       │
  │  Parakeet  → http://localhost:8786  (STT)       │
  │  Sunshine  → https://localhost:47990 (stream)   │
  │  DashStream→ udp://${piIp || "<PI_IP>"}:5004 (kiosk)   │
  ├──────────────────────────────────────────────────┤
  │  Pi: launch "RetroWeb" → Moonlight connects     │
  │  Pi: mpv udp://0.0.0.0:5004 --fs --no-cache    │
  │  Press Ctrl+C to stop all services.             │
  └──────────────────────────────────────────────────┘
`);
