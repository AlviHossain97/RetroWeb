import fs from 'fs';
import path from 'path';
import https from 'https';
import { fileURLToPath } from 'url';

import coreMap from '../src/data/coreMap.json' with { type: 'json' };

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CDN_BASE = "https://cdn.jsdelivr.net/gh/arianrhodsandlot/retroarch-emscripten-build@v1.22.0/retroarch";

function download(url: string, dest: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(dest);
        https.get(url, (response) => {
            if (response.statusCode === 200) {
                response.pipe(file);
                file.on('finish', () => {
                    file.close(() => resolve());
                });
            } else if (response.statusCode === 301 || response.statusCode === 302) {
                if (response.headers.location) {
                    download(response.headers.location, dest).then(resolve).catch(reject);
                } else {
                    reject("Redirect without location");
                }
            } else {
                fs.unlink(dest, () => reject(`Server responded with ${response.statusCode}: ${response.statusMessage}`));
            }
        }).on('error', (err) => {
            fs.unlink(dest, () => reject(err.message));
        });
    });
}

async function main() {
    console.log("Downloading cores to public folder...");

    for (const [, cfg] of Object.entries(coreMap)) {
        const core = cfg.preferredCore;
        const version = cfg.coreVersion;

        const dir = path.join(__dirname, `../public/cores/${core}/${version}`);
        fs.mkdirSync(dir, { recursive: true });

        const jsPath = path.join(dir, `${core}_libretro.js`);
        const jsUrl = `${CDN_BASE}/${core}_libretro.js`;

        const wasmPath = path.join(dir, `${core}_libretro.wasm`);
        const wasmUrl = `${CDN_BASE}/${core}_libretro.wasm`;

        if (!fs.existsSync(jsPath)) {
            console.log(`Downloading ${core} JS...`);
            await download(jsUrl, jsPath).catch(err => console.error(`Failed: ${jsUrl} - ${err}`));
        } else {
            console.log(`Exists: ${jsPath}`);
        }

        if (!fs.existsSync(wasmPath)) {
            console.log(`Downloading ${core} WASM...`);
            await download(wasmUrl, wasmPath).catch(err => console.error(`Failed: ${wasmUrl} - ${err}`));
        } else {
            console.log(`Exists: ${wasmPath}`);
        }
    }

    console.log("Done downloading cores.");
}

main().catch(console.error);
