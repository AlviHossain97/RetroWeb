"""Kokoro TTS Server — FastAPI, GPU-accelerated via ONNX CUDA provider."""
import os, io, time, site, ctypes
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import numpy as np

# Pre-load NVIDIA shared libs so ONNX CUDA provider can find them
_nvidia_base = Path(site.getusersitepackages()) / "nvidia"
if _nvidia_base.is_dir():
    for _lib in sorted(_nvidia_base.glob("*/lib/*.so*")):
        if _lib.is_file() and not _lib.name.endswith(".a"):
            try:
                ctypes.CDLL(str(_lib), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass

os.environ.setdefault("ONNX_PROVIDER", "CUDAExecutionProvider")

MODEL_DIR = Path(__file__).parent / "kokoro-models"
MODEL_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

kokoro = None
voice_cache: dict[str, np.ndarray] = {}

def get_kokoro():
    global kokoro
    if kokoro is None:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    return kokoro

def get_voice_style(voice_name: str) -> np.ndarray:
    if voice_name not in voice_cache:
        k = get_kokoro()
        voice_cache[voice_name] = k.get_voice_style(voice_name)
    return voice_cache[voice_name]

@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    def _load():
        t0 = time.time()
        print("[Startup] Pre-loading Kokoro with CUDA...")
        k = get_kokoro()
        print(f"[Startup] Kokoro loaded in {time.time()-t0:.1f}s, provider: {k.sess.get_providers()}")
        # Pre-cache default voice
        get_voice_style("af_heart")
        print("[Startup] Default voice cached")
    threading.Thread(target=_load, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.2

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": kokoro is not None}

@app.get("/voices")
async def voices():
    k = get_kokoro()
    return {"voices": k.get_voices()}

@app.post("/tts")
async def tts(req: TTSRequest):
    import soundfile as sf
    k = get_kokoro()
    voice_style = get_voice_style(req.voice)
    samples, sample_rate = k.create(req.text, voice=voice_style, speed=req.speed)
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/wav")

class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: str = "af_heart"
    speed: float = 1.2
    response_format: str = "mp3"

@app.post("/v1/audio/speech")
async def speech_openai(req: SpeechRequest):
    import soundfile as sf
    t0 = time.time()
    k = get_kokoro()
    voice_style = get_voice_style(req.voice)
    samples, sample_rate = k.create(req.input, voice=voice_style, speed=req.speed)
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    buf.seek(0)
    ms = round((time.time() - t0) * 1000)
    print(f"[TTS] Generated {len(samples)/sample_rate:.1f}s audio in {ms}ms: '{req.input[:60]}'")
    return StreamingResponse(buf, media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8787)