"""
audio_manager.py - Procedural audio generation for Bastion TD.
All sounds generated at init using sine/square/noise wave math.
No external files. Uses only pygame + stdlib (no numpy).
"""
import math
import random
import struct
import array

try:
    import pygame
    import pygame.mixer
    _MIXER_AVAILABLE = True
except Exception:
    _MIXER_AVAILABLE = False

from settings import *

SAMPLE_RATE = 22050


def _make_sound_buffer(samples):
    """Convert a list of signed 16-bit integer samples into a pygame.mixer.Sound."""
    # Clamp samples to valid range
    clamped = [max(-32767, min(32767, int(s))) for s in samples]
    raw = struct.pack(f"<{len(clamped)}h", *clamped)
    return pygame.mixer.Sound(buffer=raw)


def _sine(freq, duration, volume=0.8, sample_rate=SAMPLE_RATE):
    """Generate sine wave samples."""
    n = int(sample_rate * duration)
    amp = int(32767 * volume)
    return [int(amp * math.sin(2 * math.pi * freq * t / sample_rate)) for t in range(n)]


def _square(freq, duration, volume=0.5, sample_rate=SAMPLE_RATE):
    """Generate square wave samples."""
    n = int(sample_rate * duration)
    amp = int(32767 * volume)
    samples = []
    for t in range(n):
        val = math.sin(2 * math.pi * freq * t / sample_rate)
        samples.append(amp if val >= 0 else -amp)
    return samples


def _noise(duration, volume=0.4, sample_rate=SAMPLE_RATE):
    """Generate white noise samples."""
    n = int(sample_rate * duration)
    amp = int(32767 * volume)
    return [random.randint(-amp, amp) for _ in range(n)]


def _sweep(start_freq, end_freq, duration, volume=0.7, wave="sine", sample_rate=SAMPLE_RATE):
    """Generate a frequency sweep (rising or descending tone)."""
    n = int(sample_rate * duration)
    amp = int(32767 * volume)
    samples = []
    for t in range(n):
        ratio = t / max(1, n - 1)
        freq = start_freq + (end_freq - start_freq) * ratio
        phase = 2 * math.pi * freq * t / sample_rate
        if wave == "sine":
            val = math.sin(phase)
        else:
            val = 1.0 if math.sin(phase) >= 0 else -1.0
        samples.append(int(amp * val))
    return samples


def _apply_envelope(samples, attack=0.01, decay=0.0, sustain_level=1.0, release=0.05,
                    sample_rate=SAMPLE_RATE):
    """Apply a simple ADSR-like envelope to samples."""
    n = len(samples)
    attack_samples = int(attack * sample_rate)
    release_samples = int(release * sample_rate)
    result = []
    for i in range(n):
        if i < attack_samples:
            env = i / max(1, attack_samples)
        elif i >= n - release_samples:
            remaining = n - i
            env = remaining / max(1, release_samples)
        else:
            env = sustain_level
        result.append(int(samples[i] * env))
    return result


def _mix(samples_list):
    """Mix multiple sample lists together (sum and clamp)."""
    max_len = max(len(s) for s in samples_list)
    mixed = [0] * max_len
    for samps in samples_list:
        for i in range(len(samps)):
            mixed[i] += samps[i]
    # Normalize if clipping
    peak = max(abs(s) for s in mixed) if mixed else 1
    if peak > 32767:
        scale = 32767 / peak
        mixed = [int(s * scale) for s in mixed]
    return mixed


def _concat(samples_list):
    """Concatenate multiple sample lists sequentially."""
    result = []
    for s in samples_list:
        result.extend(s)
    return result


class AudioManager:
    """Generates and manages all game sounds procedurally."""

    def __init__(self):
        self.sounds = {}
        self._bgm_channel = None
        self._current_bgm = None
        self._available = False

        if not _MIXER_AVAILABLE:
            return

        try:
            # Generate all sounds
            self._generate_sfx()
            self._generate_bgm()
            self._available = True
            # Reserve channel 0 for BGM
            if pygame.mixer.get_num_channels() < 8:
                pygame.mixer.set_num_channels(8)
            self._bgm_channel = pygame.mixer.Channel(0)
        except Exception:
            self._available = False

    def _generate_sfx(self):
        """Generate all SFX sounds."""
        # place: rising tone 300->500Hz, 0.08s
        s = _sweep(300, 500, 0.08, volume=0.5)
        s = _apply_envelope(s, attack=0.005, release=0.02)
        self.sounds["place"] = _make_sound_buffer(s)

        # shoot: quick noise burst, 0.05s
        s = _noise(0.05, volume=0.25)
        s = _apply_envelope(s, attack=0.002, release=0.015)
        self.sounds["shoot"] = _make_sound_buffer(s)

        # hit: noise + low tone, 0.06s
        n = _noise(0.06, volume=0.2)
        t = _sine(150, 0.06, volume=0.3)
        s = _mix([n, t])
        s = _apply_envelope(s, attack=0.002, release=0.02)
        self.sounds["hit"] = _make_sound_buffer(s)

        # enemy_death: descending tone + noise, 0.1s
        sw = _sweep(500, 200, 0.1, volume=0.4)
        n = _noise(0.1, volume=0.15)
        s = _mix([sw, n])
        s = _apply_envelope(s, attack=0.005, release=0.03)
        self.sounds["enemy_death"] = _make_sound_buffer(s)

        # wave_start: two ascending tones, 0.15s
        t1 = _sweep(300, 500, 0.075, volume=0.5)
        t2 = _sweep(400, 600, 0.075, volume=0.5)
        s = _concat([t1, t2])
        s = _apply_envelope(s, attack=0.005, release=0.03)
        self.sounds["wave_start"] = _make_sound_buffer(s)

        # wave_clear: ascending arpeggio, 0.3s
        notes = [400, 500, 600, 800]
        parts = []
        note_dur = 0.075
        for freq in notes:
            parts.append(_sine(freq, note_dur, volume=0.5))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.005, release=0.05)
        self.sounds["wave_clear"] = _make_sound_buffer(s)

        # boss_spawn: low rumble + rising, 0.4s
        rumble = _noise(0.4, volume=0.2)
        low = _sine(60, 0.4, volume=0.3)
        rise = _sweep(80, 400, 0.4, volume=0.4)
        s = _mix([rumble, low, rise])
        s = _apply_envelope(s, attack=0.05, release=0.1)
        self.sounds["boss_spawn"] = _make_sound_buffer(s)

        # base_hit: harsh descending, 0.15s
        s = _sweep(600, 150, 0.15, volume=0.6, wave="square")
        s = _apply_envelope(s, attack=0.005, release=0.03)
        self.sounds["base_hit"] = _make_sound_buffer(s)

        # upgrade: rising ding, 0.1s
        s = _sweep(500, 900, 0.1, volume=0.5)
        s = _apply_envelope(s, attack=0.003, release=0.03)
        self.sounds["upgrade"] = _make_sound_buffer(s)

        # sell: coin jingle, 0.1s
        t1 = _sine(800, 0.05, volume=0.4)
        t2 = _sine(1200, 0.05, volume=0.4)
        s = _concat([t1, t2])
        s = _apply_envelope(s, attack=0.003, release=0.02)
        self.sounds["sell"] = _make_sound_buffer(s)

        # menu_move: tiny click, 0.03s
        s = _noise(0.03, volume=0.15)
        s = _apply_envelope(s, attack=0.001, release=0.01)
        self.sounds["menu_move"] = _make_sound_buffer(s)

        # menu_select: click + rise, 0.08s
        click = _noise(0.02, volume=0.2)
        rise = _sweep(400, 700, 0.06, volume=0.4)
        s = _concat([click, rise])
        s = _apply_envelope(s, attack=0.002, release=0.02)
        self.sounds["menu_select"] = _make_sound_buffer(s)

        # game_over: descending minor, 0.4s
        # E5 -> C5 -> A4 -> E4 (minor feel)
        notes = [659, 523, 440, 330]
        parts = []
        for freq in notes:
            parts.append(_sine(freq, 0.1, volume=0.5))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.01, release=0.08)
        self.sounds["game_over"] = _make_sound_buffer(s)

        # victory: major fanfare, 0.5s
        # C5 -> E5 -> G5 -> C6 (major arpeggio)
        notes = [523, 659, 784, 1047]
        parts = []
        for freq in notes:
            parts.append(_sine(freq, 0.125, volume=0.5))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.005, release=0.08)
        self.sounds["victory"] = _make_sound_buffer(s)

    def _generate_bgm(self):
        """Generate BGM loops as square wave melodies."""
        # bgm_build: gentle major melody, square wave 2.5s loop
        # C4 D4 E4 G4 E4 D4 C4 rest (major, gentle)
        build_notes = [262, 294, 330, 392, 330, 294, 262, 0]
        note_dur = 0.3125  # 2.5s / 8 notes
        parts = []
        for freq in build_notes:
            if freq > 0:
                parts.append(_square(freq, note_dur, volume=0.15))
            else:
                parts.append([0] * int(SAMPLE_RATE * note_dur))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.01, release=0.01)
        self.sounds["bgm_build"] = _make_sound_buffer(s)

        # bgm_wave: tense minor melody, faster tempo 2.5s loop
        # A4 C5 B4 A4 G4 A4 E4 rest (minor, tense)
        wave_notes = [440, 523, 494, 440, 392, 440, 330, 0]
        note_dur = 0.3125
        parts = []
        for freq in wave_notes:
            if freq > 0:
                parts.append(_square(freq, note_dur, volume=0.15))
            else:
                parts.append([0] * int(SAMPLE_RATE * note_dur))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.01, release=0.01)
        self.sounds["bgm_wave"] = _make_sound_buffer(s)

        # bgm_boss: aggressive fast 2s loop
        # E4 E4 F4 G4 F4 E4 D#4 E4 (chromatic, fast, aggressive)
        boss_notes = [330, 330, 349, 392, 349, 330, 311, 330]
        note_dur = 0.25  # 2s / 8 notes
        parts = []
        for freq in boss_notes:
            parts.append(_square(freq, note_dur, volume=0.2))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.005, release=0.005)
        self.sounds["bgm_boss"] = _make_sound_buffer(s)

        # bgm_title: calm, inviting 3s loop
        # C4 E4 G4 A4 G4 E4 (major, calm)
        title_notes = [262, 330, 392, 440, 392, 330]
        note_dur = 0.5  # 3s / 6 notes
        parts = []
        for freq in title_notes:
            parts.append(_square(freq, note_dur, volume=0.12))
        s = _concat(parts)
        s = _apply_envelope(s, attack=0.02, release=0.02)
        self.sounds["bgm_title"] = _make_sound_buffer(s)

    def set_sfx_enabled(self, enabled):
        """Enable or disable SFX playback."""
        self._sfx_enabled = enabled

    def play(self, sound_name):
        """Play a named SFX once."""
        if not self._available or not getattr(self, '_sfx_enabled', True):
            return
        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()

    def play_bgm(self, bgm_name):
        """Stop current BGM and loop the new one on a dedicated channel."""
        if not self._available:
            return
        if self._current_bgm == bgm_name:
            return
        self.stop_bgm()
        sound = self.sounds.get(bgm_name)
        if sound and self._bgm_channel:
            self._bgm_channel.play(sound, loops=-1)
            self._current_bgm = bgm_name

    def stop_bgm(self):
        """Stop the current BGM."""
        if not self._available:
            return
        if self._bgm_channel:
            self._bgm_channel.stop()
        self._current_bgm = None
