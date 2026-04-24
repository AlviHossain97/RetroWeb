import sys
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.voice_gateway import (  # noqa: E402
    BaseProviderSession,
    BaseVoiceProvider,
    ProviderSessionContext,
    VoiceGatewayService,
    VoiceProviderHealth,
    normalize_upstream_event,
)


class FakeSession(BaseProviderSession):
    async def configure(self, payload):
        self.payload = payload

    async def handle_command(self, payload):
        self.command = payload

    async def close(self):
        return None


class FakeProvider(BaseVoiceProvider):
    def __init__(self, name: str, *, available: bool, reason: str | None = None, fail_on_create: bool = False):
        self.name = name
        self.available = available
        self.reason = reason
        self.fail_on_create = fail_on_create

    async def health(self) -> VoiceProviderHealth:
        return VoiceProviderHealth(name=self.name, available=self.available, reason=self.reason)

    async def create_live_session(self, ctx: ProviderSessionContext) -> BaseProviderSession:
        if self.fail_on_create:
            raise RuntimeError(f"{self.name} boom")
        return FakeSession()


class VoiceGatewayServiceTests(IsolatedAsyncioTestCase):
    async def test_health_prefers_first_available_provider(self):
        service = VoiceGatewayService()
        service.providers = {
            "voicechat": FakeProvider("voicechat", available=True),
            "legacy": FakeProvider("legacy", available=True),
        }
        service._provider_order = lambda: ["voicechat", "legacy"]  # type: ignore[method-assign]

        health = await service.check_health()

        self.assertTrue(health.available)
        self.assertEqual(health.active_provider, "voicechat")
        self.assertTrue(health.fallback_capable)

    async def test_provider_creation_falls_back_when_primary_fails(self):
        service = VoiceGatewayService()
        service.providers = {
            "voicechat": FakeProvider("voicechat", available=True, fail_on_create=True),
            "legacy": FakeProvider("legacy", available=True),
        }

        async def sink(_event):
            return None

        provider_name, provider_session = await service._create_provider_session(  # noqa: SLF001
            record=type(
                "Record",
                (),
                {
                    "session_id": "voice_test",
                    "provider_order": ["voicechat", "legacy"],
                    "selected_provider": "voicechat",
                    "persona_prompt": "persona",
                    "context_snapshot": "ctx",
                    "max_session_seconds": 840,
                },
            )(),
            send_event=sink,
        )

        self.assertEqual(provider_name, "legacy")
        self.assertIsInstance(provider_session, FakeSession)


class VoiceGatewayNormalizationTests(IsolatedAsyncioTestCase):
    async def test_normalize_transcript_and_audio_events(self):
        transcript_events = normalize_upstream_event(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "item": {"transcript": "Hello there"},
            }
        )
        text_events = normalize_upstream_event(
            {
                "type": "response.output_text.delta",
                "delta": "General Kenobi",
            }
        )
        audio_events = normalize_upstream_event(
            {
                "type": "response.audio.delta",
                "delta": "YmVlZg==",
                "sample_rate_hz": 22050,
            }
        )

        self.assertEqual(transcript_events, [{"type": "user.transcript.final", "text": "Hello there"}])
        self.assertEqual(text_events, [{"type": "assistant.text.delta", "text": "General Kenobi"}])
        self.assertEqual(
            audio_events,
            [
                {
                    "type": "assistant.audio.chunk",
                    "audio": "YmVlZg==",
                    "sample_rate_hz": 22050,
                    "format": "pcm16",
                }
            ],
        )
