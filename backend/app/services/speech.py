"""Voice-to-text: validate an audio clip, transcribe it and turn dictation into an ingredient list.

Transcription uses any OpenAI-compatible ``/audio/transcriptions`` endpoint (OpenAI Whisper, Groq,
or a self-hosted whisper server), configured with ``STT_API_URL`` / ``STT_API_KEY`` / ``STT_MODEL``.
Turning the transcript into ingredient text is deterministic, like the OCR path.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)


class AudioError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ValidatedAudio:
    data: bytes
    media_type: str
    extension: str


@dataclass
class Transcript:
    text: str
    language: str | None
    duration_seconds: float | None


MIN_AUDIO_BYTES = 1024


def _sniff(data: bytes) -> tuple[str, str] | None:
    """Detect the real audio container from magic bytes (never trust the client's content type)."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav", "wav"
    if data[:4] == b"\x1aE\xdf\xa3":
        return "audio/webm", "webm"
    if data[:4] == b"OggS":
        return "audio/ogg", "ogg"
    if data[:4] == b"fLaC":
        return "audio/flac", "flac"
    if data[4:8] == b"ftyp":
        return "audio/mp4", "m4a"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "audio/mpeg", "mp3"
    return None


def validate_audio(data: bytes) -> ValidatedAudio:
    settings = get_settings()
    if len(data) > settings.max_audio_mb * 1024 * 1024:
        raise AudioError("file_too_large", f"The recording is too large (maximum {settings.max_audio_mb} MB).")
    if len(data) < MIN_AUDIO_BYTES:
        raise AudioError("audio_too_short", "The recording is too short. Hold the button and read the ingredients aloud.")
    sniffed = _sniff(data)
    if sniffed is None:
        raise AudioError("unsupported_format", "Unsupported audio format. Use WAV, MP3, M4A, WebM, OGG or FLAC.")
    return ValidatedAudio(data=data, media_type=sniffed[0], extension=sniffed[1])


def transcribe(audio: ValidatedAudio, language: str | None = None) -> Transcript:
    """Send the clip to the speech-to-text service. Blocking — call from a thread pool."""
    settings = get_settings()
    if not settings.stt_available:
        raise AudioError("stt_unavailable", "Voice input is not configured on this server. Type the ingredients instead.")
    form = {"model": settings.stt_model, "response_format": "verbose_json",
            # A vocabulary hint noticeably improves additive and E-number recognition.
            "prompt": "Ingredients: sugar, wheat flour, palm oil, soy lecithin, E330, maltodextrin, xanthan gum."}
    if language:
        form["language"] = language
    try:
        res = httpx.post(
            settings.stt_api_url,
            headers={"Authorization": f"Bearer {settings.stt_api_key}"},
            data=form,
            files={"file": (f"recording.{audio.extension}", audio.data, audio.media_type)},
            timeout=settings.stt_timeout_seconds,
        )
        res.raise_for_status()
        body = res.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Speech-to-text request failed: %s", exc)
        raise AudioError("stt_failed", "We couldn't transcribe the recording. Please try again or type the ingredients.")
    text = (body.get("text") or "").strip() if isinstance(body, dict) else ""
    return Transcript(text=text, language=body.get("language"), duration_seconds=body.get("duration"))


# ------------------------------------------------------------ dictation ---
_SPOKEN = [
    (r"\b(?:open|left) (?:bracket|parenthesis|paren)\b", " ("),
    (r"\b(?:close|right) (?:bracket|parenthesis|paren)\b", ") "),
    (r"\b(?:comma|next(?: ingredient)?)\b", ","),
    (r"\b(?:full stop|period|end of list|that's it|that is all)\b", "."),
    (r"\b(\d+(?:\.\d+)?)\s*percent\b", r"\1%"),
    # "E four seven one" / "E 471" -> "E471"
    (r"\be[\s-]+(\d)\s*(\d)\s*(\d)(\s*[a-f]\b)?", lambda m: "E" + m[1] + m[2] + m[3] + (m[4] or "").strip()),
]
_DIGITS = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
           "six": "6", "seven": "7", "eight": "8", "nine": "9"}
_LEADIN = re.compile(r"^\s*(?:the\s+)?ingredients?\s*(?:are|is|list)?\s*[:,-]?\s*", re.IGNORECASE)


def _spelled_e_numbers(text: str) -> str:
    """Turn spelled-out digits after an 'E' into numbers: 'E three three oh' -> 'E 3 3 0'."""
    words = "|".join(_DIGITS)
    pattern = re.compile(rf"\be((?:[\s-]+(?:{words}|\d)){{3}})\b", re.IGNORECASE)
    return pattern.sub(lambda m: "E " + " ".join(_DIGITS.get(w.lower(), w) for w in re.split(r"[\s-]+", m[1].strip())), text)


def transcript_to_ingredients(transcript: str) -> str:
    """Convert dictated speech into comma-separated ingredient text for the normal analysis pipeline."""
    text = _LEADIN.sub("", transcript.strip())
    text = _spelled_e_numbers(text)
    for pattern, repl in _SPOKEN:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    sentences = [s for s in re.split(r"\.(?!\d)", text) if s.strip()]
    if sentences and "," in sentences[0]:
        text = sentences[0]  # a punctuated list ends at its first full stop; drop trailing chatter
    else:
        text = ", ".join(sentences)  # one ingredient per spoken sentence
    # " and " separates spoken items: all of them in an unpunctuated list, the last one in "a, b and c".
    # "mono and diglycerides" is a single ingredient.
    and_ = r"(?<!\bmono)\s+and\s+"
    if "," not in text:
        text = re.sub(and_, ", ", text, flags=re.IGNORECASE)
    else:
        text = re.sub(and_ + r"(?=[^,()]*$)", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", text))
    items = [" ".join(part.split()).strip(" .") for part in re.split(r"\s*,\s*", text)]
    return ", ".join(i for i in items if i)
