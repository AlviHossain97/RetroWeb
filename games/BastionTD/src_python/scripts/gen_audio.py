"""Procedural audio generator for BastionTD.

Mirrors the synthesis math in audio_manager.py (the pygame implementation) and
emits WAV files for both the GBA butano/maxmod pipeline and the SDL build.

Outputs:
    gba_project/audio/<name>.wav      (consumed by butano's maxmod tool)
    assets/audio/<name>.wav            (consumed at runtime by SDL_mixer)

All files are 22050 Hz mono 8-bit unsigned PCM, which maxmod converts cleanly
and SDL_mixer plays directly.

Usage:
    python tools/gen_audio.py
"""
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050

ROOT = Path(__file__).resolve().parent.parent
GBA_OUT = ROOT / "gba_project" / "audio"
SDL_OUT = ROOT / "assets" / "audio"


def _sine(freq: float, duration: float, volume: float = 0.8) -> list[int]:
    n = int(SAMPLE_RATE * duration)
    amp = 32767 * volume
    return [int(amp * math.sin(2 * math.pi * freq * t / SAMPLE_RATE)) for t in range(n)]


def _square(freq: float, duration: float, volume: float = 0.5) -> list[int]:
    n = int(SAMPLE_RATE * duration)
    amp = int(32767 * volume)
    out = []
    for t in range(n):
        val = math.sin(2 * math.pi * freq * t / SAMPLE_RATE)
        out.append(amp if val >= 0 else -amp)
    return out


def _noise(duration: float, volume: float = 0.4) -> list[int]:
    n = int(SAMPLE_RATE * duration)
    amp = int(32767 * volume)
    return [random.randint(-amp, amp) for _ in range(n)]


def _sweep(start_freq: float, end_freq: float, duration: float,
           volume: float = 0.7, wave_kind: str = "sine") -> list[int]:
    n = int(SAMPLE_RATE * duration)
    amp = int(32767 * volume)
    out = []
    for t in range(n):
        ratio = t / max(1, n - 1)
        freq = start_freq + (end_freq - start_freq) * ratio
        phase = 2 * math.pi * freq * t / SAMPLE_RATE
        if wave_kind == "sine":
            val = math.sin(phase)
        else:
            val = 1.0 if math.sin(phase) >= 0 else -1.0
        out.append(int(amp * val))
    return out


def _envelope(samples: list[int], attack: float = 0.01, sustain: float = 1.0,
              release: float = 0.05) -> list[int]:
    n = len(samples)
    a = int(attack * SAMPLE_RATE)
    r = int(release * SAMPLE_RATE)
    out = []
    for i in range(n):
        if i < a:
            env = i / max(1, a)
        elif i >= n - r:
            env = (n - i) / max(1, r)
        else:
            env = sustain
        out.append(int(samples[i] * env))
    return out


def _mix(*layers: list[int]) -> list[int]:
    max_len = max(len(s) for s in layers)
    mixed = [0] * max_len
    for layer in layers:
        for i, v in enumerate(layer):
            mixed[i] += v
    peak = max(abs(s) for s in mixed) if mixed else 1
    if peak > 32767:
        scale = 32767 / peak
        mixed = [int(s * scale) for s in mixed]
    return mixed


def _concat(*parts: list[int]) -> list[int]:
    out = []
    for p in parts:
        out.extend(p)
    return out


def _silence(duration: float) -> list[int]:
    return [0] * int(SAMPLE_RATE * duration)


def _to_u8(samples: list[int]) -> bytes:
    """Convert signed 16-bit samples to unsigned 8-bit PCM."""
    out = bytearray(len(samples))
    for i, v in enumerate(samples):
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        # Scale to 0..255
        out[i] = (v >> 8) + 128
    return bytes(out)


def _write_wav(path: Path, samples: list[int]) -> None:
    data = _to_u8(samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)


def build_sfx() -> dict[str, list[int]]:
    """Return a dict of sfx name -> signed 16-bit samples (pygame parity)."""
    sfx = {}

    # place: rising 300->500Hz, 0.08s
    s = _sweep(300, 500, 0.08, volume=0.5)
    sfx["place"] = _envelope(s, attack=0.005, release=0.02)

    # shoot: noise burst 0.05s
    s = _noise(0.05, volume=0.25)
    sfx["shoot"] = _envelope(s, attack=0.002, release=0.015)

    # hit: noise + low tone 0.06s
    s = _mix(_noise(0.06, volume=0.2), _sine(150, 0.06, volume=0.3))
    sfx["hit"] = _envelope(s, attack=0.002, release=0.02)

    # enemy_death: descending 500->200 + noise 0.1s
    s = _mix(_sweep(500, 200, 0.1, volume=0.4), _noise(0.1, volume=0.15))
    sfx["enemy_death"] = _envelope(s, attack=0.005, release=0.03)

    # wave_start: two ascending tones 0.075s + 0.075s
    s = _concat(_sweep(300, 500, 0.075, volume=0.5),
                _sweep(400, 600, 0.075, volume=0.5))
    sfx["wave_start"] = _envelope(s, attack=0.005, release=0.03)

    # wave_clear: ascending arpeggio 4 notes
    s = _concat(*[_sine(f, 0.075, volume=0.5) for f in (400, 500, 600, 800)])
    sfx["wave_clear"] = _envelope(s, attack=0.005, release=0.05)

    # boss_spawn: rumble + low + rise 0.4s
    s = _mix(_noise(0.4, volume=0.2),
             _sine(60, 0.4, volume=0.3),
             _sweep(80, 400, 0.4, volume=0.4))
    sfx["boss_spawn"] = _envelope(s, attack=0.05, release=0.1)

    # base_hit: harsh descending square 0.15s
    s = _sweep(600, 150, 0.15, volume=0.6, wave_kind="square")
    sfx["base_hit"] = _envelope(s, attack=0.005, release=0.03)

    # upgrade: rising ding 500->900
    s = _sweep(500, 900, 0.1, volume=0.5)
    sfx["upgrade"] = _envelope(s, attack=0.003, release=0.03)

    # sell: 800 + 1200 jingle
    s = _concat(_sine(800, 0.05, volume=0.4), _sine(1200, 0.05, volume=0.4))
    sfx["sell"] = _envelope(s, attack=0.003, release=0.02)

    # menu_move: tiny click
    s = _noise(0.03, volume=0.15)
    sfx["menu_move"] = _envelope(s, attack=0.001, release=0.01)

    # menu_select: click + rise
    s = _concat(_noise(0.02, volume=0.2), _sweep(400, 700, 0.06, volume=0.4))
    sfx["menu_select"] = _envelope(s, attack=0.002, release=0.02)

    # game_over: descending minor 4 notes
    s = _concat(*[_sine(f, 0.1, volume=0.5) for f in (659, 523, 440, 330)])
    sfx["game_over"] = _envelope(s, attack=0.01, release=0.08)

    # victory: major fanfare
    s = _concat(*[_sine(f, 0.125, volume=0.5) for f in (523, 659, 784, 1047)])
    sfx["victory"] = _envelope(s, attack=0.005, release=0.08)

    return sfx


def build_bgm() -> dict[str, list[int]]:
    """BGM loops mirroring the pygame melody schedules."""
    bgm = {}

    def melody(notes: list[float], note_dur: float, volume: float) -> list[int]:
        parts = []
        for freq in notes:
            if freq > 0:
                parts.append(_square(freq, note_dur, volume=volume))
            else:
                parts.append(_silence(note_dur))
        return _envelope(_concat(*parts), attack=0.01, release=0.01)

    bgm["bgm_title"] = melody([262, 330, 392, 440, 392, 330], 0.5, volume=0.12)
    bgm["bgm_build"] = melody([262, 294, 330, 392, 330, 294, 262, 0], 0.3125, volume=0.15)
    bgm["bgm_wave"]  = melody([440, 523, 494, 440, 392, 440, 330, 0], 0.3125, volume=0.15)
    bgm["bgm_boss"]  = melody([330, 330, 349, 392, 349, 330, 311, 330], 0.25, volume=0.2)
    return bgm


def main() -> None:
    sfx = build_sfx()
    bgm = build_bgm()

    for name, samples in {**sfx, **bgm}.items():
        gba_path = GBA_OUT / f"{name}.wav"
        sdl_path = SDL_OUT / f"{name}.wav"
        _write_wav(gba_path, samples)
        _write_wav(sdl_path, samples)

    total = len(sfx) + len(bgm)
    print(f"wrote {total} wav files")
    print(f"  gba -> {GBA_OUT}")
    print(f"  sdl -> {SDL_OUT}")


if __name__ == "__main__":
    main()
