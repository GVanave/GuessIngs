from fastapi import APIRouter, Depends, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.models import User
from app.schemas import VoiceExtractionOut
from app.services.normalization import IngredientInputError, parse_ingredients
from app.services.speech import AudioError, transcribe, transcript_to_ingredients, validate_audio

router = APIRouter(prefix="/voice", tags=["voice"])

_STATUS = {"file_too_large": 413, "stt_unavailable": 503, "stt_failed": 502}


@router.post("/transcribe", response_model=VoiceExtractionOut,
             dependencies=[Depends(rate_limit("analyze", "rate_limit_analyze_per_minute"))])
async def transcribe_ingredients(file: UploadFile = File(...),
                                 language: str | None = Form(default=None, pattern="^[a-z]{2}$"),
                                 user: User = Depends(get_current_user)):
    """Transcribe a spoken ingredient list. The returned text is meant for the user to review, then
    POST to /api/analyses with ``source: "voice"`` like the scan flow."""
    settings = get_settings()
    data = await file.read(settings.max_audio_mb * 1024 * 1024 + 1)
    try:
        audio = validate_audio(data)
        transcript = await run_in_threadpool(transcribe, audio, language)
    except AudioError as exc:
        raise AppError(_STATUS.get(exc.code, 400), exc.code, exc.message)

    if not transcript.text:
        raise AppError(422, "no_speech", "We didn't hear anything. Read the ingredients aloud, closer to the microphone.")
    text = transcript_to_ingredients(transcript.text)
    try:
        parse_ingredients(text)
    except IngredientInputError:
        raise AppError(422, "no_ingredients_found",
                       "We couldn't hear an ingredient list. Say each ingredient, separated by short pauses or \"comma\".",
                       {"transcript": transcript.text})
    return VoiceExtractionOut(transcript=transcript.text, ingredients_text=text,
                              language=transcript.language, duration_seconds=transcript.duration_seconds)
