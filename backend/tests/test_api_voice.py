import io
import wave

import httpx
import pytest

from app.core.config import get_settings
from app.services import speech
from app.services.speech import transcript_to_ingredients


def wav_bytes(seconds: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buf.getvalue()


def upload(client, data, name="clip.wav", ctype="audio/wav", **form):
    return client.post("/api/voice/transcribe", files={"file": (name, data, ctype)}, data=form)


@pytest.fixture
def stt(monkeypatch):
    """Configure a fake speech-to-text service and capture the requests sent to it."""
    monkeypatch.setenv("STT_API_KEY", "test-key")
    get_settings.cache_clear()
    calls = []
    reply = {"text": "Rolled oats, sugar, sunflower oil, salt.", "language": "english", "duration": 3.2}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(200, json=reply, request=httpx.Request("POST", url))

    monkeypatch.setattr(speech.httpx, "post", fake_post)
    return {"calls": calls, "reply": reply}


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("Ingredients are sugar, wheat flour, palm oil.", "sugar, wheat flour, palm oil"),
        ("sugar comma wheat flour comma cocoa butter", "sugar, wheat flour, cocoa butter"),
        ("water and sugar and salt", "water, sugar, salt"),
        ("Ingredients are oats, sugar and salt.", "oats, sugar, salt"),
        ("sugar, mono and diglycerides", "sugar, mono and diglycerides"),
        ("Water. Sugar. Salt.", "Water, Sugar, Salt"),
        ("milk chocolate open bracket sugar, cocoa butter close bracket, hazelnuts 13 percent",
         "milk chocolate (sugar, cocoa butter), hazelnuts 13%"),
        ("sugar, emulsifier E four seven one, acid E 330", "sugar, emulsifier E471, acid E330"),
        ("sugar, salt, flour. Contains wheat.", "sugar, salt, flour"),
        ("vegetable oil 2.5 percent, salt", "vegetable oil 2.5%, salt"),
    ],
)
def test_transcript_to_ingredients(spoken, expected):
    assert transcript_to_ingredients(spoken) == expected


def test_voice_transcription_feeds_analysis(auth_client, stt):
    res = upload(auth_client, wav_bytes(), language="en")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ingredients_text"] == "Rolled oats, sugar, sunflower oil, salt"
    assert body["transcript"].startswith("Rolled oats") and body["duration_seconds"] == 3.2

    call = stt["calls"][0]
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert call["data"]["language"] == "en" and call["files"]["file"][2] == "audio/wav"

    analysis = auth_client.post("/api/analyses", json={"ingredients_text": body["ingredients_text"], "source": "voice"})
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["source"] == "voice"


def test_voice_requires_login(client, stt):
    assert upload(client, wav_bytes()).status_code == 401


def test_voice_not_configured(auth_client):
    res = upload(auth_client, wav_bytes())
    assert res.status_code == 503 and res.json()["error"]["code"] == "stt_unavailable"


def test_non_audio_file_is_rejected(auth_client, stt):
    res = upload(auth_client, b"#!/bin/sh\n" * 200, "clip.wav")
    assert res.status_code == 400 and res.json()["error"]["code"] == "unsupported_format"
    assert not stt["calls"]


def test_too_large_audio_is_rejected(auth_client, stt, monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_MB", "1")
    get_settings.cache_clear()
    res = upload(auth_client, wav_bytes(seconds=40))
    assert res.status_code == 413 and res.json()["error"]["code"] == "file_too_large"


def test_silence_returns_no_speech(auth_client, stt):
    stt["reply"].update(text="  ")
    res = upload(auth_client, wav_bytes())
    assert res.status_code == 422 and res.json()["error"]["code"] == "no_speech"


def test_stt_service_failure(auth_client, monkeypatch):
    monkeypatch.setenv("STT_API_KEY", "test-key")
    get_settings.cache_clear()

    def boom(url, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(speech.httpx, "post", boom)
    res = upload(auth_client, wav_bytes())
    assert res.status_code == 502 and res.json()["error"]["code"] == "stt_failed"
