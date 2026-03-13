import { spawn } from "child_process";
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
const whisperScript = resolve(__dirname, "scripts", "whisper-server.py");
const backendDir = resolve(__dirname, "backend");

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

// 1. Ollama — check if already running (systemd), start if not
import { execSync } from "child_process";
try {
  execSync("systemctl is-active --quiet ollama", { stdio: "ignore" });
  console.log("[Ollama] Already running via systemd");
} catch {
  try {
    execSync("curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null", { stdio: "ignore" });
    console.log("[Ollama] Already running");
  } catch {
    startService("Ollama", "ollama", ["serve"], {
      env: { OLLAMA_ORIGINS: "*" },
    });
  }
}

// 2. FastAPI backend
startService("FastAPI", "python3", [
  "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
], { cwd: backendDir });

// 3. Kokoro TTS (CUDA)
startService("Kokoro", "python3", [kokoroScript]);

// 4. Whisper STT (GPU)
startService("Whisper", "python3", [whisperScript], {
  env: { LD_LIBRARY_PATH: "/usr/local/lib/ollama/cuda_v12" },
});

// 5. Vite dev server
startService("Vite", "npx", ["vite", "--host", "0.0.0.0", "--port", "5173"]);

// 6. Pi Display — virtual framebuffer + browser + VNC server
// Renders the kiosk UI on the laptop GPU and streams to Pi via VNC
const VNC_DISPLAY = ":99";
const VNC_PORT = "5900";
const KIOSK_URL = "http://localhost:5173/kiosk";

// Start Xvfb (virtual display)
startService("Xvfb", "Xvfb", [VNC_DISPLAY, "-screen", "0", "1920x1080x24", "-ac"]);

// Wait for Xvfb, then launch browser + VNC
setTimeout(() => {
  // Launch Brave in kiosk mode on the virtual display
  startService("Browser", "brave-browser-stable", [
    "--kiosk",
    "--no-first-run",
    "--disable-infobars",
    "--disable-session-crashed-bubble",
    "--disable-translate",
    "--noerrdialogs",
    "--disable-extensions",
    "--user-data-dir=/tmp/pistation-kiosk-profile",
    "--window-size=1920,1080",
    "--window-position=0,0",
    KIOSK_URL,
  ], { env: { DISPLAY: VNC_DISPLAY } });

  // Start x11vnc sharing the virtual display (no password, view+control)
  startService("VNC", "x11vnc", [
    "-display", VNC_DISPLAY,
    "-rfbport", VNC_PORT,
    "-nopw",
    "-forever",
    "-shared",
    "-noxdamage",
    "-cursor", "arrow",
    "-ncache", "10",
  ]);
}, 2000);

console.log(`
  ┌─────────────────────────────────────────────┐
  │           PiStation — All Services          │
  ├─────────────────────────────────────────────┤
  │  XAMPP   → http://localhost/phpmyadmin      │
  │  Vite    → http://localhost:5173            │
  │  FastAPI → http://localhost:8000            │
  │  Ollama  → http://localhost:11434           │
  │  Kokoro  → http://localhost:8787  (TTS)     │
  │  Whisper → http://localhost:8786  (STT)     │
  │  VNC     → vnc://localhost:5900  (Pi view)  │
  ├─────────────────────────────────────────────┤
  │  Press Ctrl+C to stop all services.         │
  └─────────────────────────────────────────────┘
`);
