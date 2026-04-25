"""No-op audio adapter used for non-desktop targets and tests."""
from __future__ import annotations


class NullAudioManager:
    def set_map_audio(self, *_args, **_kwargs):
        return None

    def update(self, *_args, **_kwargs):
        return None

    def play_music(self, *_args, **_kwargs):
        return None

    def stop_music(self, *_args, **_kwargs):
        return None

    def play_sfx(self, *_args, **_kwargs):
        return None

    def notify_combat_hit(self, *_args, **_kwargs):
        return None

    def notify_boss_active(self, *_args, **_kwargs):
        return None

    def notify_boss_defeated(self, *_args, **_kwargs):
        return None
