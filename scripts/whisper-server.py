"""OpenAI-compatible Whisper STT Server using faster-whisper, GPU-accelerated."""
import os, tempfile, subprocess
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

model = None

def get_model():
    global model
    if model is None:
        model = WhisperModel("small", device="cuda", compute_type="float16")
    return model

@app.on_event("startup")
async def preload():
    import threading
    def _load():
        print("[Startup] Pre-loading faster-whisper...")
        get_model()
        print("[Startup] faster-whisper ready on GPU")
    threading.Thread(target=_load, daemon=True).start()

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form("Systran/faster-whisper-small"),
):
    m = get_model()
    raw = await file.read()
    print(f"[Whisper] 📝 Received {len(raw)} bytes ({file.filename})")

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        # Convert webm to wav via ffmpeg
        wav_path = tmp_path + ".wav"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=10
        )
        if proc.returncode != 0:
            print(f"[Whisper] ❌ ffmpeg conversion failed: {proc.stderr.decode()[:200]}")
            return {"text": ""}

        import time
        t0 = time.time()
        segments, _ = m.transcribe(wav_path, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        elapsed = round((time.time() - t0) * 1000)
        print(f"[Whisper] ✅ Transcribed: '{text}' ({elapsed}ms)")
    finally:
        try: os.unlink(tmp_path)
        except: pass
        try: os.unlink(tmp_path + ".wav")
        except: pass

    return {"text": text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8786)
