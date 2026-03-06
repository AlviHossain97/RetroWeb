import { test } from "node:test";
import assert from "node:assert/strict";

import { BlobReader, BlobWriter, ZipWriter } from "@zip.js/zip.js";

import {
  NormalizeError,
  detectSystemFromHeader,
  normalizeROM,
} from "../src/lib/emulation/rom-normalizer.ts";

const TEXT_ENCODER = new TextEncoder();

async function makeZip(entries) {
  const writer = new ZipWriter(new BlobWriter(), {
    bufferedWrite: true,
    level: 0,
  });

  for (const entry of entries) {
    const fileBlob = entry.blob instanceof Blob ? entry.blob : new Blob([entry.blob]);
    await writer.add(entry.name, new BlobReader(fileBlob), {
      level: 0,
      bufferedWrite: true,
    });
  }

  return writer.close();
}

function nesBlob() {
  // iNES signature + minimal payload
  return new Blob([new Uint8Array([0x4e, 0x45, 0x53, 0x1a, 0x01, 0x01, 0x00, 0x00])]);
}

function gbaBlob() {
  // ARM branch opcode signature used by many GBA ROM headers
  return new Blob([new Uint8Array([0x2e, 0x00, 0x00, 0xea, 0x00, 0x00, 0x00, 0x00])]);
}

test("normalizeROM: passes through bare .gba and maps to gb runtime system", async () => {
  const file = new File([gbaBlob()], "Super Mario Advance 4.gba");
  const normalized = await normalizeROM(file);

  assert.equal(normalized.extension, ".gba");
  assert.equal(normalized.detectedSystem, "gba");
  assert.equal(normalized.systemId, "gb");
  assert.equal(normalized.filename, "Super Mario Advance 4.gba");
});

test("normalizeROM: .zip with .gba extracts and detects GBA from header", async () => {
  const zipBlob = await makeZip([
    { name: "Super Mario Advance 4 (Europe).gba", blob: gbaBlob() },
  ]);
  const file = new File([zipBlob], "sma4.zip");

  const normalized = await normalizeROM(file);

  assert.equal(normalized.extension, ".gba");
  assert.equal(normalized.filename, "Super Mario Advance 4 (Europe).gba");
  assert.equal(normalized.originalFilename, "sma4.zip");
  assert.equal(normalized.detectedSystem, "gba");
});

test("normalizeROM: .zip with ROM + text ignores text and loads ROM", async () => {
  const zipBlob = await makeZip([
    { name: "README.txt", blob: TEXT_ENCODER.encode("hello") },
    { name: "game.nes", blob: nesBlob() },
  ]);
  const file = new File([zipBlob], "bundle.zip");

  const normalized = await normalizeROM(file);

  assert.equal(normalized.extension, ".nes");
  assert.equal(normalized.detectedSystem, "nes");
  assert.equal(normalized.systemId, "nes");
});

test("normalizeROM: .zip with multiple ROMs throws zip_multiple_roms with candidates", async () => {
  const zipBlob = await makeZip([
    { name: "a.nes", blob: nesBlob() },
    { name: "b.gba", blob: gbaBlob() },
  ]);

  await assert.rejects(
    async () => normalizeROM(new File([zipBlob], "multi.zip")),
    (error) => {
      assert.ok(error instanceof NormalizeError);
      assert.equal(error.code, "zip_multiple_roms");
      assert.ok(Array.isArray(error.candidates));
      assert.equal(error.candidates?.length, 2);
      return true;
    }
  );
});

test("normalizeROM: .zip with no ROM throws zip_no_rom", async () => {
  const zipBlob = await makeZip([{ name: "notes.txt", blob: TEXT_ENCODER.encode("no rom") }]);

  await assert.rejects(
    async () => normalizeROM(new File([zipBlob], "notes.zip")),
    (error) => {
      assert.ok(error instanceof NormalizeError);
      assert.equal(error.code, "zip_no_rom");
      return true;
    }
  );
});

test("normalizeROM: unsupported extension throws unsupported_format", async () => {
  await assert.rejects(
    async () => normalizeROM(new File([TEXT_ENCODER.encode("x")], "bad.exe")),
    (error) => {
      assert.ok(error instanceof NormalizeError);
      assert.equal(error.code, "unsupported_format");
      return true;
    }
  );
});

test("detectSystemFromHeader: detects gba header bytes", async () => {
  const system = await detectSystemFromHeader(gbaBlob());
  assert.equal(system, "gba");
});

test("detectSystemFromHeader: detects nes header bytes", async () => {
  const system = await detectSystemFromHeader(nesBlob());
  assert.equal(system, "nes");
});
