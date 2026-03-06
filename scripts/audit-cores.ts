// scripts/audit-cores.ts
// Quick script to verify HTTP status of libretro wasm cores on the chosen CDN
const cores = [
    "fceumm",
    "snes9x",
    "mgba",
    "genesis_plus_gx",
    "duckstation",
    "stella",
    "smsplus",
    "mednafen_pce_fast"
];

const CDN_BASE = "https://cdn.jsdelivr.net/gh/arianrhodsandlot/retroarch-emscripten-build@v1.22.0/retroarch";

async function checkCore(core: string) {
    const jsUrl = `${CDN_BASE}/${core}_libretro.js`;
    const wasmUrl = `${CDN_BASE}/${core}_libretro.wasm`;

    const [jsRes, wasmRes] = await Promise.all([
        fetch(jsUrl, { method: 'HEAD' }),
        fetch(wasmUrl, { method: 'HEAD' })
    ]);

    return {
        core,
        js: jsRes.ok,
        wasm: wasmRes.ok,
        pass: jsRes.ok && wasmRes.ok
    };
}

async function runAudit() {
    console.log("Starting Core Availability Audit for v1.22.0 CDN path...");
    const results = [];
    for (const core of cores) {
        const res = await checkCore(core);
        results.push(res);
        console.log(`Core: ${res.core.padEnd(20)} JS: ${res.js ? '✅' : '❌'}  WASM: ${res.wasm ? '✅' : '❌'}`);
    }
}

runAudit();
