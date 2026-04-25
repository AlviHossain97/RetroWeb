"""Runtime factory for selecting the active target backend."""
from __future__ import annotations

import os

from runtime.gba_runtime import GBARuntime
from runtime.pygame_runtime import PygameRuntime


_RUNTIMES = {
    "pygame": PygameRuntime,
    "gba": GBARuntime,
}


def create_runtime(name: str | None = None):
    runtime_name = (name or os.getenv("MYTHICAL_TARGET", "pygame")).strip().lower()
    if runtime_name not in _RUNTIMES:
        valid = ", ".join(sorted(_RUNTIMES))
        raise ValueError(f"Unknown runtime target '{runtime_name}'. Valid targets: {valid}")
    return _RUNTIMES[runtime_name]()
