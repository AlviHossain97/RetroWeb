"""OpenAI-compatible STT Server using NVIDIA Parakeet TDT 0.6B v2 (NeMo), GPU-accelerated."""
import os, tempfile, subprocess, time, traceback
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

SPEECH_FILTER_CHAIN = ",".join([
    "highpass=f=120",
    "lowpass=f=4200",
    "afftdn=nf=-28",
    "acompressor=threshold=-20dB:ratio=3:attack=5:release=120",
])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

asr_model = None

def init_model():
    global asr_model
    import nemo.collections.asr as nemo_asr
    print("[Parakeet] Loading nvidia/parakeet-tdt-0.6b-v2 ...")
    asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2")
    # Move to GPU if available
    try:
        import torch
        if torch.cuda.is_available():
            asr_model = asr_model.cuda()
            print("[Parakeet] Model loaded on GPU (CUDA)")
        else:
            print("[Parakeet] CUDA not available, running on CPU")
    except Exception as exc:
        print(f"[Parakeet] GPU check failed, running on CPU: {exc}")
    return asr_model


def get_model():
    global asr_model
    if asr_model is None:
        return init_model()
    return asr_model


def convert_to_wav(input_path: str, wav_path: str, *, apply_filters: bool) -> subprocess.CompletedProcess:
    """Convert uploaded audio into mono 16kHz WAV, optionally with speech-focused filtering."""
    cmd = [
        "ffmpeg", "-y", "-nostdin",
        "-i", input_path,
        "-vn",
    ]
    if apply_filters:
        cmd.extend(["-af", SPEECH_FILTER_CHAIN])
    cmd.extend(["-ar", "16000", "-ac", "1", wav_path])
    return subprocess.run(cmd, capture_output=True, timeout=15)


@app.on_event("startup")
async def preload():
    import threading
    def _load():
        print("[Startup] Pre-loading Parakeet TDT model...")
        get_model()
    threading.Thread(target=_load, daemon=True).start()

@app.get("/health")
async def health():
    return {"status": "ok", "model": "nvidia/parakeet-tdt-0.6b-v2", "model_loaded": asr_model is not None}

@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form("nvidia/parakeet-tdt-0.6b-v2"),
):
    try:
        mdl = get_model()
        raw = await file.read()
        print(f"[Parakeet] Received {len(raw)} bytes ({file.filename})")

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        wav_path = tmp_path + ".wav"
        try:
            # Try filtered audio first for better speech isolation
            filtered_wav = tmp_path + ".filtered.wav"
            filtered_proc = convert_to_wav(tmp_path, filtered_wav, apply_filters=True)

            if filtered_proc.returncode == 0:
                use_wav = filtered_wav
            else:
                print(f"[Parakeet] Filtered ffmpeg failed, using plain audio: "
                      f"{filtered_proc.stderr.decode(errors='ignore')[:200]}")
                use_wav = wav_path

            # Always create plain wav as fallback
            plain_proc = convert_to_wav(tmp_path, wav_path, apply_filters=False)
            if plain_proc.returncode != 0:
                print(f"[Parakeet] ffmpeg conversion failed: {plain_proc.stderr.decode(errors='ignore')[:200]}")
                return {"text": ""}

            if use_wav == filtered_wav and filtered_proc.returncode != 0:
                use_wav = wav_path

            t0 = time.time()

            # Parakeet transcription — no initial_prompt, no hallucination risk
            output = mdl.transcribe([use_wav])
            text = output[0].text if hasattr(output[0], 'text') else str(output[0]).strip()

            # Fallback: if filtered audio gave empty result, try plain
            if not text and use_wav != wav_path:
                print("[Parakeet] Filtered audio empty, retrying with plain audio")
                output = mdl.transcribe([wav_path])
                text = output[0].text if hasattr(output[0], 'text') else str(output[0]).strip()

            elapsed = round((time.time() - t0) * 1000)
            print(f"[Parakeet] Transcribed: '{text}' ({elapsed}ms)")

        finally:
            for p in [tmp_path, wav_path, tmp_path + ".filtered.wav"]:
                try: os.unlink(p)
                except: pass

        return {"text": text}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"text": "", "error": str(e)}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8786)
