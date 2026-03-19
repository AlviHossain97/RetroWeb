"""OpenAI-compatible Whisper STT Server using faster-whisper, GPU-accelerated when available."""
import os, tempfile, subprocess, time, traceback
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

SPEECH_FILTER_CHAIN = ",".join([
    "highpass=f=120",
    "lowpass=f=4200",
    "afftdn=nf=-28",
    "acompressor=threshold=-20dB:ratio=3:attack=5:release=120",
])

FOREGROUND_SPEAKER_PROMPT = (
    "Transcribe only the clearest foreground speaker closest to the microphone. "
    "Ignore background voices, TV audio, music, fan noise, and ambient room sounds."
)

RELAXED_PROMPT = (
    "Transcribe the main speaker clearly and prefer nearby speech over distant sounds."
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

whisper_model = None
whisper_device = None
whisper_compute_type = None

def init_model(prefer_cpu: bool = False):
    global whisper_model, whisper_device, whisper_compute_type

    if not prefer_cpu:
        try:
            whisper_model = WhisperModel("small", device="cuda", compute_type="float16")
            whisper_device = "cuda"
            whisper_compute_type = "float16"
            print("[Whisper] faster-whisper ready on GPU")
            return whisper_model
        except Exception as exc:
            print(f"[Whisper] CUDA unavailable, falling back to CPU: {exc}")

    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    whisper_device = "cpu"
    whisper_compute_type = "int8"
    print("[Whisper] faster-whisper ready on CPU")
    return whisper_model


def get_model(prefer_cpu: bool = False, force_reload: bool = False):
    global whisper_model
    if whisper_model is None or force_reload:
        return init_model(prefer_cpu=prefer_cpu)
    if prefer_cpu and whisper_device != "cpu":
        return init_model(prefer_cpu=True)
    return whisper_model


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


def build_transcribe_kwargs(*, use_vad: bool, prompt: str | None):
    kwargs = {
        "language": "en",
        "beam_size": 5,
        "best_of": 5,
        "temperature": 0,
        "condition_on_previous_text": False,
    }
    if use_vad:
        kwargs["vad_filter"] = True
        kwargs["vad_parameters"] = {"min_silence_duration_ms": 350, "speech_pad_ms": 120}
    else:
        kwargs["vad_filter"] = False
    if prompt:
        kwargs["initial_prompt"] = prompt
    return kwargs


def run_transcription(wav_path: str, *, use_vad: bool, prompt: str | None) -> str:
    last_error = None

    for prefer_cpu in (False, True):
        attempted_model = None
        try:
            attempted_model = get_model(
                prefer_cpu=prefer_cpu,
                force_reload=prefer_cpu and whisper_device != "cpu",
            )
            kwargs = build_transcribe_kwargs(use_vad=use_vad, prompt=prompt)
            segments, _ = attempted_model.transcribe(wav_path, **kwargs)
            text = " ".join(s.text.strip() for s in segments).strip()
            backend = f"{whisper_device}/{whisper_compute_type}"
            print(f"[Whisper] Pass result on {backend}: '{text}'")
            if text:
                return text
        except Exception as exc:
            last_error = exc
            backend = f"{whisper_device}/{whisper_compute_type}" if whisper_device else "uninitialized"
            print(f"[Whisper] Transcription pass failed on {backend}: {exc}")

    if last_error:
        raise last_error
    return ""

@app.on_event("startup")
async def preload():
    import threading
    def _load():
        print("[Startup] Pre-loading faster-whisper...")
        get_model()
    threading.Thread(target=_load, daemon=True).start()

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": whisper_model is not None}

@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form("Systran/faster-whisper-small"),
):
    try:
        get_model()
        raw = await file.read()
        print(f"[Whisper] Received {len(raw)} bytes ({file.filename})")

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        try:
            filtered_wav_path = tmp_path + ".filtered.wav"
            plain_wav_path = tmp_path + ".plain.wav"

            filtered_proc = convert_to_wav(tmp_path, filtered_wav_path, apply_filters=True)
            if filtered_proc.returncode != 0:
                print(
                    "[Whisper] Filtered ffmpeg conversion failed, will retry with plain audio: "
                    f"{filtered_proc.stderr.decode(errors='ignore')[:200]}"
                )

            plain_proc = convert_to_wav(tmp_path, plain_wav_path, apply_filters=False)
            if plain_proc.returncode != 0:
                print(f"[Whisper] Plain ffmpeg conversion failed: {plain_proc.stderr.decode(errors='ignore')[:200]}")
                return {"text": ""}

            t0 = time.time()
            text = ""

            if filtered_proc.returncode == 0:
                text = run_transcription(
                    filtered_wav_path,
                    use_vad=True,
                    prompt=FOREGROUND_SPEAKER_PROMPT,
                )

            if not text:
                print("[Whisper] Filtered pass was empty, retrying with unfiltered audio")
                text = run_transcription(
                    plain_wav_path,
                    use_vad=True,
                    prompt=RELAXED_PROMPT,
                )

            if not text:
                print("[Whisper] VAD pass was empty, retrying plain audio without VAD")
                text = run_transcription(
                    plain_wav_path,
                    use_vad=False,
                    prompt=RELAXED_PROMPT,
                )

            elapsed = round((time.time() - t0) * 1000)
            print(f"[Whisper] Transcribed: '{text}' ({elapsed}ms)")
        finally:
            try: os.unlink(tmp_path)
            except: pass
            try: os.unlink(filtered_wav_path)
            except: pass
            try: os.unlink(plain_wav_path)
            except: pass

        return {"text": text}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"text": "", "error": str(e)}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8786)
