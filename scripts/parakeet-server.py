"""Parakeet ASR server — NVIDIA NeMo, GPU-accelerated.

OpenAI-compatible transcription endpoint on :8786:
    POST /v1/audio/transcriptions  (multipart form, field `file`, WAV)
    -> {"text": "..."}

Matches the contract the voice gateway's LegacyCascadeSession expects.
"""

from __future__ import annotations

import io
import os
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware


MODEL_NAME = os.environ.get("PARAKEET_MODEL", "nvidia/parakeet-tdt-1.1b")
DEVICE = os.environ.get("PARAKEET_DEVICE", "cuda")
# fp16 halves VRAM usage — required to fit the 1.1B model on an 8 GB laptop GPU
# alongside Kokoro + Sunshine + browser GPU contexts. Set to "0" to force fp32.
USE_HALF = os.environ.get("PARAKEET_HALF", "1") == "1"

# Reduce CUDA allocator fragmentation when multiple processes share the GPU.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


_model = None
_model_error: str | None = None
_load_lock = threading.Lock()


def _load_model():
    """Load the Parakeet model once. Heavy; runs in a background thread."""
    global _model, _model_error
    with _load_lock:
        if _model is not None or _model_error is not None:
            return
        try:
            import nemo.collections.asr as nemo_asr
            import torch

            print(f"[Parakeet] loading {MODEL_NAME} on {DEVICE} (half={USE_HALF}) ...", flush=True)
            # Load to CPU first, convert to fp16 on CPU, then move to GPU.
            # This avoids the fp32 spike on GPU (2x peak) that OOMs an 8 GB card.
            model = nemo_asr.models.ASRModel.from_pretrained(
                model_name=MODEL_NAME,
                map_location="cpu",
            )
            if DEVICE == "cuda" and torch.cuda.is_available():
                if USE_HALF:
                    model = model.half()
                torch.cuda.empty_cache()
                model = model.to("cuda")
            model.eval()

            # NeMo's CUDA-graph decoder path currently breaks against newer CUDA
            # driver APIs (cu_call returns 5 fields, code expects 6). Force the
            # plain PyTorch path instead — ~5-10% slower per batch but stable.
            try:
                from omegaconf import OmegaConf, open_dict
                decoding_cfg = model.cfg.decoding
                with open_dict(decoding_cfg):
                    if OmegaConf.select(decoding_cfg, "greedy") is not None:
                        decoding_cfg.greedy.use_cuda_graph_decoder = False
                        decoding_cfg.greedy.loop_labels = True
                model.change_decoding_strategy(decoding_cfg)
                print("[Parakeet] CUDA graph decoder disabled", flush=True)
            except Exception as exc:
                print(f"[Parakeet] warn: could not disable CUDA graphs: {exc}", flush=True)

            _model = model
            print("[Parakeet] model ready", flush=True)
        except Exception as exc:
            _model_error = f"{type(exc).__name__}: {exc}"
            print(f"[Parakeet] model load failed: {_model_error}", flush=True)


def get_model():
    if _model is None and _model_error is None:
        _load_model()
    if _model is None:
        raise RuntimeError(_model_error or "Parakeet model not loaded")
    return _model


@app.on_event("startup")
async def preload():
    threading.Thread(target=_load_model, daemon=True).start()


@app.get("/health")
async def health():
    return {
        "status": "ok" if _model is not None else ("loading" if _model_error is None else "error"),
        "model": MODEL_NAME,
        "model_loaded": _model is not None,
        "error": _model_error,
    }


def _transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """Write the WAV to a temp file and run NeMo's transcribe()."""
    model = get_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name
    try:
        results = model.transcribe([tmp_path])
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # NeMo returns a list. Each entry can be a string, a Hypothesis object with
    # .text, or a list of Hypothesis (for N-best). Normalize to a single string.
    def _extract(x):
        if isinstance(x, str):
            return x
        if hasattr(x, "text"):
            return x.text
        if isinstance(x, (list, tuple)) and x:
            return _extract(x[0])
        return ""

    text = _extract(results[0]) if results else ""
    return (text or "").strip()


# OpenAI-compatible endpoint used by the backend voice gateway.
@app.post("/v1/audio/transcriptions")
async def openai_transcriptions(
    file: UploadFile = File(...),
    model: str = Form(default=MODEL_NAME),  # noqa: ARG001 — accepted for compat, ignored
):
    raw = await file.read()
    text = _transcribe_wav_bytes(raw)
    return {"text": text}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8786)
