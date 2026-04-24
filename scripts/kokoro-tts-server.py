"""Kokoro TTS + Whisper STT Server — FastAPI, GPU-accelerated."""
import os, io
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MODEL_DIR = Path(__file__).parent / "kokoro-models"
MODEL_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

kokoro = None
whisper_model = None

def get_kokoro():
    global kokoro
    if kokoro is None:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    return kokoro

def get_whisper():
    global whisper_model
    if whisper_model is None:
        import whisper
        whisper_model = whisper.load_model("base", device="cuda")
    return whisper_model

# Pre-load models at startup. STT is handled by parakeet-server.py; we only
# need Kokoro here, so the Whisper preload path is skipped.
@app.on_event("startup")
async def preload():
    import threading
    def _load():
        print("[Startup] Pre-loading Kokoro...")
        get_kokoro()
        print("[Startup] Kokoro ready")
    threading.Thread(target=_load, daemon=True).start()

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.2

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": kokoro is not None, "whisper_loaded": whisper_model is not None}

@app.get("/voices")
async def voices():
    k = get_kokoro()
    return {"voices": k.get_voices()}

@app.post("/stt")
async def stt(audio: UploadFile = File(...)):
    import tempfile, subprocess, numpy as np, torch
    model = get_whisper()
    raw = await audio.read()
    # Write to temp, convert webm→raw PCM via ffmpeg pipe (faster than file I/O)
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
            capture_output=True, timeout=5
        )
        if proc.returncode == 0 and len(proc.stdout) > 0:
            audio_np = np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768.0
            result = model.transcribe(audio_np, language="en")
            text = (result.get("text") or "").strip()
        else:
            text = ""
    finally:
        try: os.unlink(tmp_path)
        except: pass
    return {"text": text}

@app.post("/tts")
async def tts(req: TTSRequest):
    import soundfile as sf
    k = get_kokoro()
    samples, sample_rate = k.create(req.text, voice=req.voice, speed=req.speed)
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
    k = get_kokoro()
    samples, sample_rate = k.create(req.input, voice=req.voice, speed=req.speed)
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8787)