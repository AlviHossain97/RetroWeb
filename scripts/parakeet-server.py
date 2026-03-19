"""OpenAI-compatible STT Server using NVIDIA Parakeet TDT 0.6B v2 (NeMo), GPU-accelerated."""
import os, tempfile, subprocess, time, traceback, threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Suppress noisy NeMo/ONNX startup warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONWARNINGS"] = "ignore"

SPEECH_FILTER_CHAIN = ",".join([
    "highpass=f=120",
    "lowpass=f=4200",
    "afftdn=nf=-28",
    "acompressor=threshold=-20dB:ratio=3:attack=5:release=120",
])

stt_model = None
load_lock = threading.Lock()

def init_model():
    global stt_model
    import nemo.collections.asr as nemo_asr
    from omegaconf import OmegaConf

    print("[Parakeet] Loading nvidia/parakeet-tdt-0.6b-v2 ...")
    t0 = time.time()
    stt_model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2")

    # CRITICAL: Switch from greedy_batch → greedy to avoid CUDA graph crash.
    # greedy_batch uses CUDA graphs internally which causes:
    #   ValueError: not enough values to unpack (expected 6, got 5)
    # due to NeMo 2.7 / cuda-bindings 12.9 version mismatch.
    try:
        decoding_cfg = OmegaConf.create({
            "strategy": "greedy",
            "model_type": "tdt",
            "durations": [0, 1, 2, 3, 4],
            "greedy": {"max_symbols": 10},
        })
        stt_model.change_decoding_strategy(decoding_cfg)
        print("[Parakeet] Decoding: greedy (CUDA-graph-safe)")
    except Exception as e:
        print(f"[Parakeet] Warning: Could not set greedy decoding: {e}")

    # Move to GPU
    try:
        import torch
        if torch.cuda.is_available():
            stt_model = stt_model.cuda()
            print(f"[Parakeet] Model ready on GPU in {time.time()-t0:.1f}s")
        else:
            print(f"[Parakeet] Model ready on CPU in {time.time()-t0:.1f}s")
    except Exception as exc:
        print(f"[Parakeet] GPU failed ({exc}), running on CPU")
    return stt_model


def get_model():
    global stt_model
    if stt_model is None:
        with load_lock:
            if stt_model is None:
                return init_model()
    return stt_model


def convert_to_wav(input_path, wav_path, *, apply_filters=False):
    cmd = ["ffmpeg", "-y", "-nostdin", "-i", input_path, "-vn"]
    if apply_filters:
        cmd.extend(["-af", SPEECH_FILTER_CHAIN])
    cmd.extend(["-ar", "16000", "-ac", "1", wav_path])
    return subprocess.run(cmd, capture_output=True, timeout=15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=lambda: get_model(), daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "model": "nvidia/parakeet-tdt-0.6b-v2", "ready": stt_model is not None}


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form("nvidia/parakeet-tdt-0.6b-v2"),
):
    try:
        mdl = get_model()
        if mdl is None:
            return {"text": "", "error": "Model not loaded yet"}

        raw = await file.read()
        print(f"[Parakeet] Received {len(raw)} bytes ({file.filename})")

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        wav_path = tmp_path + ".wav"
        try:
            # Plain WAV conversion
            proc = convert_to_wav(tmp_path, wav_path)
            if proc.returncode != 0:
                print(f"[Parakeet] ffmpeg failed: {proc.stderr.decode(errors='ignore')[:200]}")
                return {"text": ""}

            # Also create filtered version
            filtered_wav = tmp_path + ".filtered.wav"
            filt_proc = convert_to_wav(tmp_path, filtered_wav, apply_filters=True)
            use_wav = filtered_wav if filt_proc.returncode == 0 else wav_path

            t0 = time.time()
            output = mdl.transcribe([use_wav])

            # Extract text from NeMo output
            if hasattr(output[0], 'text'):
                text = output[0].text
            elif isinstance(output[0], str):
                text = output[0]
            else:
                text = str(output[0])
            text = text.strip()

            # Fallback to plain audio if filtered gave nothing
            if not text and use_wav != wav_path:
                print("[Parakeet] Filtered empty, retrying plain...")
                output = mdl.transcribe([wav_path])
                if hasattr(output[0], 'text'):
                    text = output[0].text.strip()
                elif isinstance(output[0], str):
                    text = output[0].strip()

            elapsed = round((time.time() - t0) * 1000)
            print(f"[Parakeet] '{text}' ({elapsed}ms)")

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
