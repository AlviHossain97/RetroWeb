import asyncio
import json
import sys
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.stt.speechmatics_stt import (  # noqa: E402
    SpeechmaticsStreamingSTT,
    _extract_transcript,
)


class SpeechmaticsTranscriptExtractionTests(TestCase):
    def test_extracts_documented_metadata_transcript(self):
        message = {
            "message": "AddTranscript",
            "metadata": {"transcript": "  Hello from Speechmatics.  "},
            "results": [],
        }

        self.assertEqual(_extract_transcript(message), "Hello from Speechmatics.")

    def test_extracts_legacy_top_level_transcript(self):
        message = {"message": "AddTranscript", "transcript": "  Legacy transcript  "}

        self.assertEqual(_extract_transcript(message), "Legacy transcript")


class FakeSpeechmaticsSocket:
    def __init__(self):
        self.sent: list[str | bytes] = []
        self.closed = False

    async def send(self, payload):
        self.sent.append(payload)

    async def close(self):
        self.closed = True


class SpeechmaticsFinishTests(IsolatedAsyncioTestCase):
    async def test_finish_returns_latest_partial_when_final_is_missing(self):
        socket = FakeSpeechmaticsSocket()
        session = SpeechmaticsStreamingSTT(
            on_partial=lambda _text: asyncio.sleep(0),
            on_final_segment=lambda _text: asyncio.sleep(0),
            api_key="test",
        )
        session._ws = socket  # noqa: SLF001
        session._latest_partial = "partial speech was recognized"  # noqa: SLF001
        session._end_of_transcript.set()  # noqa: SLF001

        transcript = await session.finish()

        self.assertEqual(transcript, "partial speech was recognized")

    async def test_finish_uses_last_audio_added_seq_no_for_end_of_stream(self):
        socket = FakeSpeechmaticsSocket()
        session = SpeechmaticsStreamingSTT(
            on_partial=lambda _text: asyncio.sleep(0),
            on_final_segment=lambda _text: asyncio.sleep(0),
            api_key="test",
        )
        session._ws = socket  # noqa: SLF001
        session._audio_seq = 3  # noqa: SLF001
        session._first_audio_added_seq_no = 0  # noqa: SLF001
        session._last_audio_added_seq_no = 2  # noqa: SLF001
        session._end_of_transcript.set()  # noqa: SLF001

        await session.finish()

        self.assertTrue(socket.closed)
        eos = json.loads(socket.sent[0])
        self.assertEqual(eos, {"message": "EndOfStream", "last_seq_no": 2})
