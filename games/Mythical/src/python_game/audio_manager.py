"""
Audio manager — procedural sound generation and BGM.
Generates all sounds at startup using wave math. No external files needed.
On GBA: Maxmod tracker playback + DMA sound channels.
"""

import pygame
import struct
import io
import math
import random


def _make_wav(samples, sample_rate=22050):
    """Convert float samples [-1,1] to a pygame Sound via WAV bytes."""
    buf = io.BytesIO()
    n = len(samples)
    # WAV header
    buf.write(b"RIFF")
    data_size = n * 2
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    for s in samples:
        s = max(-1.0, min(1.0, s))
        buf.write(struct.pack("<h", int(s * 32000)))
    buf.seek(0)
    return pygame.mixer.Sound(buf)


def _tone(freq, duration, vol=0.3, decay=True, sr=22050):
    n = int(sr * duration)
    out = []
    for i in range(n):
        t = i / sr
        env = vol * (1 - i / n if decay else 1)
        out.append(math.sin(2 * math.pi * freq * t) * env)
    return out


def _noise(duration, vol=0.15, sr=22050):
    n = int(sr * duration)
    return [random.uniform(-vol, vol) * (1 - i / n) for i in range(n)]


def _square(freq, duration, vol=0.2, sr=22050):
    n = int(sr * duration)
    out = []
    for i in range(n):
        t = i / sr
        env = vol * (1 - i / n)
        v = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        out.append(v * env)
    return out


def _mix(*tracks):
    length = max(len(t) for t in tracks)
    out = [0.0] * length
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    mx = max(abs(s) for s in out) or 1
    return [s / mx * 0.5 for s in out]


def _melody(notes, dur_each=0.15, vol=0.2, wave="square", sr=22050):
    """Generate a melody from a list of (freq, duration_multiplier) tuples."""
    out = []
    for freq, dur_mult in notes:
        d = dur_each * dur_mult
        if freq == 0:
            out.extend([0.0] * int(sr * d))
        elif wave == "square":
            out.extend(_square(freq, d, vol, sr))
        else:
            out.extend(_tone(freq, d, vol, True, sr))
    return out


class AudioManager:
    def __init__(self):
        self.sounds = {}
        self.music_playing = ""
        self.music_channel = None
        self.sfx_volume = 0.5
        self.music_volume = 0.3
        # Dynamic audio state machine
        self._audio_state = "title"  # title | explore | combat | boss
        self._combat_timer = 0.0  # seconds since last combat action
        self._combat_cooldown = 5.0  # no enemies hit for this long → explore
        self._map_name = "village"
        self._generate_sounds()

    def _generate_sounds(self):
        sr = 22050
        # SFX
        self.sounds["sword"] = _make_wav(
            _mix(_noise(0.08, 0.4), _tone(800, 0.06, 0.3, True)), sr
        )
        self.sounds["hit"] = _make_wav(
            _mix(_noise(0.1, 0.5), _tone(200, 0.08, 0.4, True)), sr
        )
        self.sounds["hurt"] = _make_wav(
            _mix(_tone(300, 0.1, 0.4), _tone(200, 0.15, 0.3)), sr
        )
        self.sounds["enemy_death"] = _make_wav(
            _mix(_tone(400, 0.05, 0.3), _tone(200, 0.1, 0.3), _noise(0.15, 0.2)), sr
        )
        self.sounds["pickup"] = _make_wav(
            _mix(_tone(600, 0.08, 0.3), _tone(800, 0.08, 0.3)), sr
        )
        self.sounds["chest"] = _make_wav(
            _mix(_tone(400, 0.1, 0.3), _tone(500, 0.1, 0.3), _tone(600, 0.15, 0.3)), sr
        )
        self.sounds["menu_move"] = _make_wav(_square(440, 0.04, 0.15), sr)
        self.sounds["menu_select"] = _make_wav(
            _mix(_square(440, 0.06, 0.2), _square(660, 0.08, 0.2)), sr
        )
        self.sounds["quest"] = _make_wav(
            _mix(_tone(523, 0.15, 0.3), _tone(659, 0.15, 0.3), _tone(784, 0.2, 0.3)), sr
        )
        self.sounds["boss_hit"] = _make_wav(
            _mix(_noise(0.15, 0.5), _tone(150, 0.12, 0.5, True)), sr
        )
        self.sounds["boss_slam"] = _make_wav(
            _mix(_noise(0.3, 0.6), _tone(80, 0.25, 0.5, True), _tone(60, 0.3, 0.4)), sr
        )
        self.sounds["death"] = _make_wav(
            _mix(_tone(400, 0.2, 0.4), _tone(300, 0.2, 0.4), _tone(200, 0.3, 0.4)), sr
        )

        # Victory fanfare
        fanfare_notes = [
            (523, 1),
            (659, 1),
            (784, 1),
            (0, 0.5),
            (784, 2),
            (880, 1),
            (1047, 3),
        ]
        self.sounds["victory"] = _make_wav(
            _melody(fanfare_notes, 0.12, 0.25, "sine"), sr
        )

        # BGM loops (short phrases that loop)
        self._gen_village_bgm(sr)
        self._gen_dungeon_bgm(sr)
        self._gen_boss_bgm(sr)
        self._gen_title_bgm(sr)
        self._gen_ruins_bgm(sr)
        self._gen_ruins_boss_bgm(sr)
        self._gen_sanctum_bgm(sr)
        self._gen_sanctum_boss_bgm(sr)
        # Additional SFX for new systems
        self._generate_extra_sounds()

    def _gen_village_bgm(self, sr):
        # Gentle major key melody
        notes = [
            (392, 2),
            (440, 1),
            (494, 2),
            (523, 1),
            (494, 1),
            (440, 2),
            (392, 2),
            (0, 1),
            (330, 2),
            (392, 1),
            (440, 2),
            (494, 1),
            (440, 1),
            (392, 2),
            (330, 2),
            (0, 1),
        ]
        self.sounds["bgm_village"] = _make_wav(_melody(notes, 0.18, 0.12, "sine"), sr)

    def _gen_dungeon_bgm(self, sr):
        # Minor key, tension
        notes = [
            (220, 2),
            (262, 1),
            (220, 1),
            (196, 2),
            (220, 1),
            (0, 1),
            (262, 2),
            (294, 1),
            (262, 1),
            (220, 2),
            (196, 2),
            (0, 1),
        ]
        self.sounds["bgm_dungeon"] = _make_wav(_melody(notes, 0.2, 0.12, "square"), sr)

    def _gen_boss_bgm(self, sr):
        # Fast, aggressive
        notes = [
            (330, 1),
            (0, 0.5),
            (330, 1),
            (392, 1),
            (440, 1),
            (0, 0.5),
            (392, 1),
            (330, 1),
            (294, 1),
            (330, 2),
            (0, 0.5),
            (440, 1),
            (0, 0.5),
            (440, 1),
            (523, 1),
            (494, 1),
            (0, 0.5),
            (440, 1),
            (392, 1),
            (330, 1),
            (294, 2),
            (0, 1),
        ]
        self.sounds["bgm_boss"] = _make_wav(_melody(notes, 0.1, 0.15, "square"), sr)

    def _gen_title_bgm(self, sr):
        notes = [
            (262, 2),
            (330, 2),
            (392, 2),
            (523, 3),
            (0, 1),
            (494, 2),
            (440, 2),
            (392, 2),
            (330, 3),
            (0, 2),
        ]
        self.sounds["bgm_title"] = _make_wav(_melody(notes, 0.2, 0.1, "sine"), sr)

    def _gen_ruins_bgm(self, sr):
        # Dark, eerie minor key — slow haunting atmosphere for the Haunted Ruins
        notes = [
            (185, 3),
            (196, 2),
            (165, 3),
            (185, 2),
            (0, 1),
            (220, 2),
            (196, 2),
            (185, 2),
            (165, 3),
            (0, 2),
            (165, 2),
            (185, 1),
            (196, 2),
            (220, 2),
            (185, 3),
            (0, 2),
        ]
        self.sounds["bgm_ruins"] = _make_wav(_melody(notes, 0.22, 0.1, "square"), sr)

    def _gen_ruins_boss_bgm(self, sr):
        # Undead battle — dissonant, aggressive minor for the ruins depths
        notes = [
            (220, 1),
            (0, 0.5),
            (220, 1),
            (233, 1),
            (220, 1),
            (0, 0.5),
            (196, 2),
            (220, 1),
            (0, 0.5),
            (185, 1),
            (196, 1),
            (220, 2),
            (233, 1),
            (0, 0.5),
            (233, 1),
            (247, 1),
            (220, 1),
            (0, 0.5),
            (196, 1),
            (185, 1),
            (165, 1),
            (185, 2),
            (0, 1),
        ]
        self.sounds["bgm_ruins_boss"] = _make_wav(
            _melody(notes, 0.1, 0.15, "square"), sr
        )

    def _gen_sanctum_bgm(self, sr):
        # Ethereal high notes — floating, otherworldly for the Mythic Sanctum halls
        notes = [
            (523, 3),
            (587, 2),
            (659, 2),
            (698, 3),
            (0, 1),
            (659, 2),
            (587, 2),
            (523, 3),
            (494, 2),
            (0, 1),
            (523, 2),
            (659, 2),
            (784, 3),
            (698, 2),
            (659, 3),
            (0, 2),
        ]
        self.sounds["bgm_sanctum"] = _make_wav(_melody(notes, 0.2, 0.1, "sine"), sr)

    def _gen_sanctum_boss_bgm(self, sr):
        # Final boss — sweeping, most intense square-wave theme for the throne room
        notes = [
            (440, 1),
            (0, 0.5),
            (440, 1),
            (494, 1),
            (523, 1),
            (0, 0.5),
            (494, 1),
            (440, 1),
            (415, 1),
            (440, 2),
            (0, 0.5),
            (523, 1),
            (0, 0.5),
            (523, 1),
            (587, 1),
            (659, 1),
            (0, 0.5),
            (587, 1),
            (523, 1),
            (494, 1),
            (440, 2),
            (415, 1),
            (440, 3),
        ]
        self.sounds["bgm_sanctum_boss"] = _make_wav(
            _melody(notes, 0.08, 0.16, "square"), sr
        )

    def _generate_extra_sounds(self):
        """Generate additional SFX for new systems."""
        sr = 22050
        # Level-up fanfare
        lvl_notes = [
            (523, 1),
            (659, 1),
            (784, 1),
            (880, 2),
            (0, 0.5),
            (784, 1),
            (1047, 3),
        ]
        self.sounds["levelup"] = _make_wav(_melody(lvl_notes, 0.08, 0.2, "sine"), sr)
        # Craft sound
        self.sounds["craft"] = _make_wav(
            _mix(_tone(400, 0.08, 0.25), _tone(600, 0.1, 0.25), _noise(0.06, 0.1)), sr
        )
        # Fast travel whoosh
        self.sounds["fast_travel"] = _make_wav(
            _mix(
                _tone(300, 0.3, 0.3, True),
                _tone(600, 0.2, 0.2, True),
                _noise(0.25, 0.1),
            ),
            sr,
        )
        # Animal sounds (simplified)
        self.sounds["animal_hurt"] = _make_wav(
            _mix(_tone(500, 0.08, 0.3), _tone(400, 0.06, 0.2)), sr
        )
        # Ice / frost hit
        self.sounds["ice_hit"] = _make_wav(
            _mix(_tone(800, 0.06, 0.2), _tone(600, 0.08, 0.2), _noise(0.05, 0.15)), sr
        )
        # Fire hit
        self.sounds["fire_hit"] = _make_wav(
            _mix(_noise(0.1, 0.4), _tone(200, 0.1, 0.3, True)), sr
        )
        # Environmental kill
        self.sounds["env_kill"] = _make_wav(
            _mix(_tone(700, 0.1, 0.4), _tone(1000, 0.08, 0.3), _noise(0.15, 0.3)), sr
        )
        # Weather ambient (looping)
        self._gen_rain_ambient(sr)
        self._gen_wind_ambient(sr)
        # Dynamic combat BGM layer
        self._gen_combat_layer(sr)

    def _gen_rain_ambient(self, sr):
        samples = [
            random.uniform(-0.08, 0.08) * (1 + 0.3 * math.sin(i / sr * 3))
            for i in range(sr * 3)
        ]
        self.sounds["bgm_rain_ambient"] = _make_wav(samples, sr)

    def _gen_wind_ambient(self, sr):
        samples = [
            random.uniform(-0.06, 0.06) * abs(math.sin(i / sr * 0.5))
            for i in range(sr * 4)
        ]
        self.sounds["bgm_wind_ambient"] = _make_wav(samples, sr)

    def _gen_combat_layer(self, sr):
        # Fast-paced percussion layer that plays over explore BGM during combat
        combat_notes = [
            (196, 1),
            (0, 0.5),
            (220, 1),
            (196, 1),
            (0, 0.5),
            (262, 2),
            (220, 1),
            (0, 0.5),
            (196, 1),
            (220, 1),
            (0, 0.5),
            (294, 2),
        ]
        self.sounds["bgm_combat_layer"] = _make_wav(
            _melody(combat_notes, 0.09, 0.12, "square"), sr
        )

    # ── Dynamic audio state ───────────────────────────────────────────

    def notify_combat_start(self):
        """Call when combat begins (first enemy engaged)."""
        self._combat_timer = self._combat_cooldown
        if self._audio_state == "explore":
            self._audio_state = "combat"
            self._transition_to_combat()

    def notify_combat_hit(self):
        """Call on each attack landed to keep combat music active."""
        self._combat_timer = self._combat_cooldown

    def notify_boss_active(self):
        if self._audio_state != "boss":
            self._audio_state = "boss"
            if self._map_name in (
                "ruins",
                "ruins_approach",
                "ruins_depths",
                "ruins_boss",
            ):
                self.play_music("ruins_boss")
            elif self._map_name in (
                "sanctum",
                "sanctum_halls",
                "throne_room",
                "sanctum_boss",
            ):
                self.play_music("sanctum_boss")
            else:
                self.play_music("boss")

    def notify_boss_defeated(self):
        self._audio_state = "explore"
        # Resume exploration music for the current map
        self.play_music(self._map_name)

    def update(self, dt: float):
        """Advance dynamic audio state (call each game tick)."""
        if self._audio_state == "combat":
            self._combat_timer -= dt
            if self._combat_timer <= 0:
                self._audio_state = "explore"
                self._transition_to_explore()

    def set_map_audio(self, map_name: str):
        self._map_name = map_name
        if self._audio_state not in ("combat", "boss"):
            self._audio_state = "explore"
            self.play_music(map_name)

    def _transition_to_combat(self):
        # Pitch up / layer combat percussion over current track
        # For simplicity: switch to a faster variant of the current map BGM
        combat_key = f"bgm_{self._map_name}_combat"
        if combat_key not in self.sounds:
            # Fallback: continue playing current exploration music
            return
        self.play_music(f"{self._map_name}_combat")

    def _transition_to_explore(self):
        if self._audio_state != "boss":
            self.play_music(self._map_name)

    # ─────────────────────────────────────────────────────────────────

    def play_sfx(self, name):
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self.sfx_volume)
            snd.play()

    def play_music(self, name):
        if name == self.music_playing:
            return
        self.stop_music()
        snd = self.sounds.get(f"bgm_{name}")
        if snd:
            snd.set_volume(self.music_volume)
            self.music_channel = snd.play(-1)
            self.music_playing = name

    def stop_music(self):
        if self.music_channel:
            self.music_channel.stop()
        self.music_playing = ""

    def set_sfx_volume(self, vol):
        self.sfx_volume = max(0.0, min(1.0, vol))

    def set_music_volume(self, vol):
        self.music_volume = max(0.0, min(1.0, vol))
        if self.music_channel:
            snd = self.sounds.get(f"bgm_{self.music_playing}")
            if snd:
                snd.set_volume(self.music_volume)
