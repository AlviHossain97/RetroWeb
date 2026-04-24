"""Realtime voice gateway with provider fallback for PiStation."""

from __future__ import annotations

import asyncio
import audioop
import base64
import contextlib
import io
import json
import time
import uuid
import wave
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse, urlunparse

import httpx
import websockets
from fastapi import WebSocket
from pydantic import BaseModel

from app.config import get_settings
from app.services.ai_context_service import fetch_context

VOICE_INPUT_SAMPLE_RATE = 16000
VOICE_OUTPUT_SAMPLE_RATE = 22050
VOICE_INPUT_FORMAT = "pcm16"
VOICE_OUTPUT_FORMAT = "pcm16"
VOICE_AUDIO_CHUNK_MS = 80
VOICE_DEFAULT_PERSONA = (
    "You are a helpful PiStation assistant, an AI for a retro gaming dashboard platform. "
    "Speak naturally, stay concise, and avoid markdown, bullets, lists, or code blocks. "
    "Keep answers conversational and easy to hear aloud."
)

NORMALIZED_EVENT_TYPES = {
    "session.ready",
    "session.expiring",
    "provider.changed",
    "user.transcript.delta",
    "user.transcript.final",
    "assistant.text.delta",
    "assistant.text.final",
    "assistant.audio.chunk",
    "assistant.interrupted",
    "turn.end",
    "warning",
    "error",
}

UPSTREAM_USER_DELTA_TYPES = {
    "conversation.item.input_audio_transcription.delta",
    "input_audio.transcription.delta",
    "transcript.delta",
    "user.transcript.delta",
}
UPSTREAM_USER_FINAL_TYPES = {
    "conversation.item.input_audio_transcription.completed",
    "conversation.item.input_audio_transcription.final",
    "input_audio.transcription.completed",
    "input_audio.transcription.final",
    "transcript.completed",
    "transcript.final",
    "user.transcript.final",
}
UPSTREAM_ASSISTANT_TEXT_DELTA_TYPES = {
    "assistant.text.delta",
    "response.output_text.delta",
    "response.text.delta",
    "output_text.delta",
    "text.delta",
}
UPSTREAM_ASSISTANT_TEXT_FINAL_TYPES = {
    "assistant.text.final",
    "response.output_text.completed",
    "response.output_text.done",
    "response.text.completed",
    "response.text.done",
    "text.completed",
    "text.done",
}
UPSTREAM_ASSISTANT_AUDIO_TYPES = {
    "assistant.audio.chunk",
    "response.audio.delta",
    "response.output_audio.delta",
    "audio.delta",
}
UPSTREAM_INTERRUPTED_TYPES = {
    "assistant.interrupted",
    "response.interrupted",
}
UPSTREAM_TURN_END_TYPES = {
    "turn.end",
    "response.completed",
    "response.done",
}


class VoiceProviderHealth(BaseModel):
    name: str
    available: bool
    reason: str | None = None


class VoiceHealthResponse(BaseModel):
    available: bool
    active_provider: str | None
    providers: list[VoiceProviderHealth]
    fallback_capable: bool
    reason: str | None = None


class VoiceSessionResponse(BaseModel):
    session_id: str
    ws_path: str
    provider: str
    input_sample_rate_hz: int = VOICE_INPUT_SAMPLE_RATE
    output_sample_rate_hz: int = VOICE_OUTPUT_SAMPLE_RATE
    input_format: str = VOICE_INPUT_FORMAT
    output_format: str = VOICE_OUTPUT_FORMAT
    max_session_seconds: int


@dataclass
class VoiceSessionRecord:
    session_id: str
    provider_order: list[str]
    selected_provider: str
    persona_prompt: str
    context_snapshot: str
    created_at: float
    max_session_seconds: int


@dataclass
class ProviderSessionContext:
    session_id: str
    persona_prompt: str
    context_snapshot: str
    max_session_seconds: int
    selected_provider: str
    send_event: Callable[[dict[str, Any]], Awaitable[None]]


def _coerce_ws_url(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        parsed = parsed._replace(scheme="wss" if parsed.scheme == "https" else "ws")
    return urlunparse(parsed)


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(text: str | None) -> bytes:
    if not text:
        return b""
    return base64.b64decode(text.encode("ascii"))


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _nested(payload: Any, *path: Any) -> Any:
    cur: Any = payload
    for key in path:
        if isinstance(key, int):
            if not isinstance(cur, list) or key >= len(cur):
                return None
            cur = cur[key]
            continue
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def chunk_pcm16_audio(
    pcm_bytes: bytes,
    *,
    sample_rate_hz: int = VOICE_OUTPUT_SAMPLE_RATE,
    chunk_ms: int = VOICE_AUDIO_CHUNK_MS,
) -> list[bytes]:
    if not pcm_bytes:
        return []
    bytes_per_sample = 2
    chunk_size = max(bytes_per_sample, int(sample_rate_hz * (chunk_ms / 1000.0)) * bytes_per_sample)
    return [pcm_bytes[i:i + chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]


def wav_to_pcm16_mono_22050(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if nchannels > 1:
        frames = audioop.tomono(frames, sampwidth, 0.5, 0.5)
        nchannels = 1
    if sampwidth != 2:
        frames = audioop.lin2lin(frames, sampwidth, 2)
        sampwidth = 2
    if framerate != VOICE_OUTPUT_SAMPLE_RATE:
        frames, _ = audioop.ratecv(frames, 2, nchannels, framerate, VOICE_OUTPUT_SAMPLE_RATE, None)
    return frames


def build_voice_system_prompt(persona_prompt: str, context_snapshot: str) -> str:
    data_block = (
        f"\n\nHere is the user's real gaming data from their PiStation:\n{context_snapshot}\n\n"
        "Use this data when it is relevant to the spoken question."
        if context_snapshot
        else ""
    )
    return f"{persona_prompt}{data_block}"


def normalize_conversation_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not history:
        return normalized
    for item in history[-12:]:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant", "system"} or not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def normalize_upstream_event(payload: dict[str, Any]) -> list[dict[str, Any]]:
    event_type = str(payload.get("type", "")).strip()
    if not event_type:
        return []
    if event_type in NORMALIZED_EVENT_TYPES:
        return [payload]

    normalized: list[dict[str, Any]] = []
    text = _first_non_empty(
        payload.get("text"),
        payload.get("delta"),
        payload.get("transcript"),
        payload.get("content"),
        _nested(payload, "item", "transcript"),
        _nested(payload, "response", "text"),
        _nested(payload, "response", "output_text"),
    )
    audio_b64 = _first_non_empty(
        payload.get("audio"),
        payload.get("audio_base64"),
        payload.get("delta"),
        _nested(payload, "audio", "data"),
        _nested(payload, "audio", "delta"),
    )

    if event_type in UPSTREAM_USER_DELTA_TYPES and text:
        normalized.append({"type": "user.transcript.delta", "text": text})
    elif event_type in UPSTREAM_USER_FINAL_TYPES and text:
        normalized.append({"type": "user.transcript.final", "text": text})
    elif event_type in UPSTREAM_ASSISTANT_TEXT_DELTA_TYPES and text:
        normalized.append({"type": "assistant.text.delta", "text": text})
    elif event_type in UPSTREAM_ASSISTANT_TEXT_FINAL_TYPES and text:
        normalized.append({"type": "assistant.text.final", "text": text})
    elif event_type in UPSTREAM_ASSISTANT_AUDIO_TYPES and audio_b64:
        normalized.append(
            {
                "type": "assistant.audio.chunk",
                "audio": audio_b64,
                "sample_rate_hz": payload.get("sample_rate_hz", VOICE_OUTPUT_SAMPLE_RATE),
                "format": payload.get("format", VOICE_OUTPUT_FORMAT),
            }
        )
    elif event_type in UPSTREAM_INTERRUPTED_TYPES:
        normalized.append({"type": "assistant.interrupted"})
    elif event_type in UPSTREAM_TURN_END_TYPES:
        if text:
            normalized.append({"type": "assistant.text.final", "text": text})
        normalized.append({"type": "turn.end"})
    elif event_type == "warning":
        normalized.append({"type": "warning", "message": _first_non_empty(payload.get("message"), text)})
    elif event_type == "error":
        normalized.append({"type": "error", "message": _first_non_empty(payload.get("message"), text)})

    return normalized


class BaseProviderSession:
    async def configure(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    async def handle_command(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class BaseVoiceProvider:
    name = "base"

    async def health(self) -> VoiceProviderHealth:
        raise NotImplementedError

    async def create_live_session(self, ctx: ProviderSessionContext) -> BaseProviderSession:
        raise NotImplementedError


class NemotronVoiceChatSession(BaseProviderSession):
    def __init__(self, ctx: ProviderSessionContext, *, upstream_url: str, api_key: str, model: str):
        self.ctx = ctx
        self.upstream_url = _coerce_ws_url(upstream_url)
        self.api_key = api_key
        self.model = model
        self.upstream: websockets.ClientConnection | None = None
        self.reader_task: asyncio.Task[None] | None = None
        self.selected_model = model

    async def start(self) -> None:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        self.upstream = await websockets.connect(
            self.upstream_url,
            additional_headers=headers,
            max_size=8 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
            open_timeout=10,
        )
        self.reader_task = asyncio.create_task(self._read_upstream())
        await self._send_upstream(
            {
                "type": "session.configure",
                "session": {
                    "model": self.model,
                    "persona_prompt": self.ctx.persona_prompt,
                    "context_snapshot": self.ctx.context_snapshot,
                    "input_audio_format": VOICE_INPUT_FORMAT,
                    "output_audio_format": VOICE_OUTPUT_FORMAT,
                    "input_sample_rate_hz": VOICE_INPUT_SAMPLE_RATE,
                    "output_sample_rate_hz": VOICE_OUTPUT_SAMPLE_RATE,
                },
            }
        )

    async def _send_upstream(self, payload: dict[str, Any]) -> None:
        if not self.upstream:
            raise RuntimeError("Nemotron upstream socket is not connected")
        await self.upstream.send(json.dumps(payload))

    async def _read_upstream(self) -> None:
        assert self.upstream is not None
        try:
            async for raw in self.upstream:
                if isinstance(raw, bytes):
                    await self.ctx.send_event(
                        {
                            "type": "assistant.audio.chunk",
                            "audio": _b64_encode(raw),
                            "sample_rate_hz": VOICE_OUTPUT_SAMPLE_RATE,
                            "format": VOICE_OUTPUT_FORMAT,
                        }
                    )
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await self.ctx.send_event(
                        {"type": "warning", "message": "VoiceChat upstream sent non-JSON text data"}
                    )
                    continue
                for event in normalize_upstream_event(payload):
                    await self.ctx.send_event(event)
        except websockets.ConnectionClosed:
            await self.ctx.send_event({"type": "warning", "message": "VoiceChat upstream disconnected"})
        except Exception as exc:
            await self.ctx.send_event({"type": "error", "message": f"VoiceChat upstream error: {exc}"})

    async def configure(self, payload: dict[str, Any]) -> None:
        selected_model = str(payload.get("selected_model", "")).strip()
        if selected_model:
            self.selected_model = selected_model
        await self._send_upstream(
            {
                "type": "session.configure",
                "session": {
                    "model": self.selected_model or self.model,
                    "activation_mode": payload.get("activation_mode"),
                    "conversation_history": normalize_conversation_history(payload.get("conversation_history")),
                    "client": payload.get("client", {}),
                },
            }
        )

    async def handle_command(self, payload: dict[str, Any]) -> None:
        await self._send_upstream(payload)

    async def close(self) -> None:
        if self.reader_task:
            self.reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reader_task
        if self.upstream:
            await self.upstream.close()


class NemotronVoiceChatProvider(BaseVoiceProvider):
    name = "voicechat"

    async def health(self) -> VoiceProviderHealth:
        settings = get_settings()
        if not settings.nvidia_voicechat_enabled:
            return VoiceProviderHealth(name=self.name, available=False, reason="VoiceChat is disabled")
        if not settings.nvidia_api_key:
            return VoiceProviderHealth(name=self.name, available=False, reason="NVIDIA API key missing")
        if not settings.nvidia_voicechat_upstream_url:
            return VoiceProviderHealth(name=self.name, available=False, reason="VoiceChat upstream URL missing")
        return VoiceProviderHealth(name=self.name, available=True)

    async def create_live_session(self, ctx: ProviderSessionContext) -> BaseProviderSession:
        settings = get_settings()
        session = NemotronVoiceChatSession(
            ctx,
            upstream_url=settings.nvidia_voicechat_upstream_url,
            api_key=settings.nvidia_api_key,
            model=settings.nvidia_voicechat_model,
        )
        await session.start()
        return session


class LegacyCascadeSession(BaseProviderSession):
    def __init__(self, ctx: ProviderSessionContext, *, stt_url: str, tts_url: str):
        settings = get_settings()
        self.ctx = ctx
        self.stt_url = stt_url.rstrip("/")
        self.tts_url = tts_url.rstrip("/")
        self.settings = settings
        self.selected_model = settings.nvidia_model
        self.history: list[dict[str, str]] = []
        self.recording = False
        self.input_buffer = bytearray()
        self.turn_lock = asyncio.Lock()
        self.cancel_event = asyncio.Event()
        self.processing_task: asyncio.Task[None] | None = None

    async def configure(self, payload: dict[str, Any]) -> None:
        selected_model = str(payload.get("selected_model", "")).strip()
        if selected_model:
            self.selected_model = selected_model
        self.history = normalize_conversation_history(payload.get("conversation_history"))

    async def handle_command(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("type")
        if event_type == "input_audio.start":
            await self._cancel_active_turn(send_interrupt=True)
            self.recording = True
            self.input_buffer.clear()
            return

        if event_type == "input_audio.chunk":
            if self.recording:
                self.input_buffer.extend(_b64_decode(payload.get("audio")))
            return

        if event_type == "input_audio.stop":
            if not self.recording:
                return
            self.recording = False
            pcm_bytes = bytes(self.input_buffer)
            self.input_buffer.clear()
            if not pcm_bytes:
                await self.ctx.send_event({"type": "warning", "message": "No voice audio captured"})
                return
            self.processing_task = asyncio.create_task(self._process_turn(pcm_bytes))
            return

        if event_type == "response.cancel":
            await self._cancel_active_turn(send_interrupt=True)
            return

    async def _cancel_active_turn(self, *, send_interrupt: bool) -> None:
        self.cancel_event.set()
        if send_interrupt:
            await self.ctx.send_event({"type": "assistant.interrupted"})

    async def _process_turn(self, pcm_bytes: bytes) -> None:
        async with self.turn_lock:
            self.cancel_event = asyncio.Event()
            try:
                transcript = await self._transcribe_audio(pcm_bytes)
                if self.cancel_event.is_set():
                    await self.ctx.send_event({"type": "assistant.interrupted"})
                    await self.ctx.send_event({"type": "turn.end"})
                    return
                if not transcript:
                    await self.ctx.send_event({"type": "warning", "message": "Could not transcribe voice input"})
                    await self.ctx.send_event({"type": "turn.end"})
                    return

                await self.ctx.send_event({"type": "user.transcript.final", "text": transcript})
                self.history.append({"role": "user", "content": transcript})

                response_text = await self._stream_assistant_response(transcript)
                if self.cancel_event.is_set():
                    await self.ctx.send_event({"type": "assistant.interrupted"})
                    await self.ctx.send_event({"type": "turn.end"})
                    return

                if response_text:
                    self.history.append({"role": "assistant", "content": response_text})
                    await self._speak_response(response_text)

                if self.cancel_event.is_set():
                    await self.ctx.send_event({"type": "assistant.interrupted"})
                await self.ctx.send_event({"type": "turn.end"})
            except Exception as exc:
                await self.ctx.send_event({"type": "error", "message": f"Legacy voice error: {exc}"})
                await self.ctx.send_event({"type": "turn.end"})

    async def _transcribe_audio(self, pcm_bytes: bytes) -> str:
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(VOICE_INPUT_SAMPLE_RATE)
            wf.writeframes(pcm_bytes)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.stt_url}/v1/audio/transcriptions",
                data={"model": "nvidia/parakeet-tdt-0.6b-v2"},
                files={"file": ("audio.wav", wav_io.getvalue(), "audio/wav")},
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("text", "")).strip()

    async def _stream_assistant_response(self, transcript: str) -> str:
        if not self.settings.nvidia_api_key:
            raise RuntimeError("NVIDIA API key not configured")

        system_prompt = build_voice_system_prompt(self.ctx.persona_prompt, self.ctx.context_snapshot)
        messages = [{"role": "system", "content": system_prompt}, *self.history]
        messages.append({"role": "user", "content": transcript})

        full_text = ""
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0)) as client:
            async with client.stream(
                "POST",
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.nvidia_api_key}"},
                json={
                    "model": self.selected_model or self.settings.nvidia_model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.4,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if self.cancel_event.is_set():
                        break
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    # Do NOT route through _first_non_empty — that strips whitespace,
                    # which concatenates tokens like " there" + " How" into "thereHow".
                    token = _nested(data, "choices", 0, "delta", "content")
                    if not isinstance(token, str) or token == "":
                        continue
                    full_text += token
                    await self.ctx.send_event({"type": "assistant.text.delta", "text": token})

        final_text = full_text.strip()
        if final_text and not self.cancel_event.is_set():
            await self.ctx.send_event({"type": "assistant.text.final", "text": final_text})
        return final_text

    async def _speak_response(self, text: str) -> None:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.tts_url}/v1/audio/speech",
                json={
                    "model": "kokoro",
                    "input": text,
                    "voice": "af_heart",
                    "speed": 1.2,
                    "response_format": "wav",
                },
            )
            response.raise_for_status()
            pcm16 = wav_to_pcm16_mono_22050(response.content)

        for index, chunk in enumerate(chunk_pcm16_audio(pcm16)):
            if self.cancel_event.is_set():
                break
            await self.ctx.send_event(
                {
                    "type": "assistant.audio.chunk",
                    "audio": _b64_encode(chunk),
                    "format": VOICE_OUTPUT_FORMAT,
                    "sample_rate_hz": VOICE_OUTPUT_SAMPLE_RATE,
                    "sequence": index,
                }
            )

    async def close(self) -> None:
        await self._cancel_active_turn(send_interrupt=False)
        if self.processing_task:
            self.processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.processing_task


class LegacyCascadeProvider(BaseVoiceProvider):
    name = "legacy"

    async def health(self) -> VoiceProviderHealth:
        settings = get_settings()
        if not settings.voice_local_stt_url or not settings.voice_local_tts_url:
            return VoiceProviderHealth(name=self.name, available=False, reason="Local STT/TTS URLs not configured")

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                stt = await client.get(f"{settings.voice_local_stt_url.rstrip('/')}/health")
                tts = await client.get(f"{settings.voice_local_tts_url.rstrip('/')}/health")
            except Exception as exc:
                return VoiceProviderHealth(name=self.name, available=False, reason=f"Local voice services unavailable: {exc}")

        if not stt.is_success:
            return VoiceProviderHealth(name=self.name, available=False, reason="Local STT health check failed")
        if not tts.is_success:
            return VoiceProviderHealth(name=self.name, available=False, reason="Local TTS health check failed")
        return VoiceProviderHealth(name=self.name, available=True)

    async def create_live_session(self, ctx: ProviderSessionContext) -> BaseProviderSession:
        settings = get_settings()
        return LegacyCascadeSession(
            ctx,
            stt_url=settings.voice_local_stt_url,
            tts_url=settings.voice_local_tts_url,
        )


class VoiceGatewayService:
    def __init__(self) -> None:
        self.providers: dict[str, BaseVoiceProvider] = {
            "voicechat": NemotronVoiceChatProvider(),
            "legacy": LegacyCascadeProvider(),
        }
        self.sessions: dict[str, VoiceSessionRecord] = {}

    def _provider_order(self) -> list[str]:
        settings = get_settings()
        seen: list[str] = []
        for raw_name in settings.voice_provider_order:
            name = raw_name.strip().lower()
            if name and name in self.providers and name not in seen:
                seen.append(name)
        if not seen:
            seen = ["voicechat", "legacy"]
        return seen

    def _purge_expired(self) -> None:
        now = time.time()
        stale_ids = [
            session_id
            for session_id, record in self.sessions.items()
            if now - record.created_at > max(record.max_session_seconds, 60) * 2
        ]
        for session_id in stale_ids:
            self.sessions.pop(session_id, None)

    async def check_health(self) -> VoiceHealthResponse:
        order = self._provider_order()
        provider_healths: list[VoiceProviderHealth] = []
        available_names: list[str] = []

        for name in order:
            health = await self.providers[name].health()
            provider_healths.append(health)
            if health.available:
                available_names.append(name)

        active_provider = available_names[0] if available_names else None
        reason = None if active_provider else (
            next((health.reason for health in provider_healths if health.reason), "No voice providers available")
        )
        return VoiceHealthResponse(
            available=bool(active_provider),
            active_provider=active_provider,
            providers=provider_healths,
            fallback_capable=len(available_names) > 1,
            reason=reason,
        )

    async def create_session(self) -> VoiceSessionResponse:
        self._purge_expired()
        health = await self.check_health()
        if not health.available or not health.active_provider:
            raise RuntimeError(health.reason or "No voice providers available")

        settings = get_settings()
        try:
            context_snapshot = fetch_context()
        except Exception as exc:
            print(f"[VOICE] Context snapshot unavailable: {exc}")
            context_snapshot = ""

        session_id = f"voice_{uuid.uuid4().hex}"
        record = VoiceSessionRecord(
            session_id=session_id,
            provider_order=self._provider_order(),
            selected_provider=health.active_provider,
            persona_prompt=VOICE_DEFAULT_PERSONA,
            context_snapshot=context_snapshot,
            created_at=time.time(),
            max_session_seconds=settings.voice_session_max_seconds,
        )
        self.sessions[session_id] = record
        return VoiceSessionResponse(
            session_id=session_id,
            ws_path=f"/api/pistation/ai/voice/realtime?session_id={session_id}",
            provider=record.selected_provider,
            max_session_seconds=record.max_session_seconds,
        )

    async def _create_provider_session(
        self,
        record: VoiceSessionRecord,
        send_event: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> tuple[str, BaseProviderSession]:
        last_error: Exception | None = None
        for name in record.provider_order:
            provider = self.providers[name]
            health = await provider.health()
            if not health.available:
                last_error = RuntimeError(health.reason or f"{name} unavailable")
                continue
            ctx = ProviderSessionContext(
                session_id=record.session_id,
                persona_prompt=record.persona_prompt,
                context_snapshot=record.context_snapshot,
                max_session_seconds=record.max_session_seconds,
                selected_provider=name,
                send_event=send_event,
            )
            try:
                return name, await provider.create_live_session(ctx)
            except Exception as exc:
                print(f"[VOICE] Provider {name} failed to create session: {exc}")
                last_error = exc
        raise RuntimeError(str(last_error or "No voice providers available"))

    async def accept_websocket(self, websocket: WebSocket, session_id: str) -> None:
        record = self.sessions.get(session_id)
        if not record:
            await websocket.close(code=4404)
            return

        await websocket.accept()

        async def safe_send(event: dict[str, Any]) -> None:
            try:
                await websocket.send_json(event)
            except Exception:
                pass

        try:
            active_provider, provider_session = await self._create_provider_session(record, safe_send)
        except Exception as exc:
            await safe_send({"type": "error", "message": f"Voice session failed to start: {exc}"})
            await websocket.close(code=1011)
            self.sessions.pop(session_id, None)
            return

        if active_provider != record.selected_provider:
            await safe_send(
                {
                    "type": "provider.changed",
                    "provider": active_provider,
                    "reason": f"Fell back from {record.selected_provider}",
                }
            )

        expiry_seconds = max(5, min(30, record.max_session_seconds // 8))
        expiry_task = asyncio.create_task(self._send_expiry_warning(record, safe_send, expiry_seconds))
        await safe_send(
            {
                "type": "session.ready",
                "provider": active_provider,
                "session_id": session_id,
                "input_sample_rate_hz": VOICE_INPUT_SAMPLE_RATE,
                "output_sample_rate_hz": VOICE_OUTPUT_SAMPLE_RATE,
                "input_format": VOICE_INPUT_FORMAT,
                "output_format": VOICE_OUTPUT_FORMAT,
                "max_session_seconds": record.max_session_seconds,
            }
        )

        try:
            while True:
                payload = await websocket.receive_json()
                event_type = str(payload.get("type", "")).strip()
                if not event_type:
                    await safe_send({"type": "warning", "message": "Ignored voice event without a type"})
                    continue
                if event_type == "session.close":
                    break
                if event_type == "session.configure":
                    await provider_session.configure(payload)
                    continue
                await provider_session.handle_command(payload)
        except Exception as exc:
            await safe_send({"type": "warning", "message": f"Voice socket closed: {exc}"})
        finally:
            expiry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await expiry_task
            await provider_session.close()
            self.sessions.pop(session_id, None)
            with contextlib.suppress(Exception):
                await websocket.close()

    async def _send_expiry_warning(
        self,
        record: VoiceSessionRecord,
        send_event: Callable[[dict[str, Any]], Awaitable[None]],
        seconds_remaining: int,
    ) -> None:
        delay = max(1, record.max_session_seconds - seconds_remaining)
        await asyncio.sleep(delay)
        await send_event(
            {
                "type": "session.expiring",
                "seconds_remaining": seconds_remaining,
                "session_id": record.session_id,
            }
        )


@lru_cache
def get_voice_gateway_service() -> VoiceGatewayService:
    return VoiceGatewayService()
