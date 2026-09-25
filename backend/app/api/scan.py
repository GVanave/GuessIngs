import logging

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.models import User
from app.schemas import ExtractionOut
from app.services import ai
from app.services.normalization import IngredientInputError, extract_ingredient_section, parse_ingredients
from app.services.ocr import ImageError, assess_quality, run_ocr, validate_image

router = APIRouter(prefix="/scan", tags=["scan"])
log = logging.getLogger(__name__)

MIN_OCR_CONFIDENCE = 45


@router.post("/extract", response_model=ExtractionOut,
             dependencies=[Depends(rate_limit("analyze", "rate_limit_analyze_per_minute"))])
async def extract(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    settings = get_settings()
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        image = await run_in_threadpool(validate_image, data)
    except ImageError as exc:
        raise AppError(400 if exc.code != "file_too_large" else 413, exc.code, exc.message)

    quality = assess_quality(image.image)
    try:
        ocr = await run_in_threadpool(run_ocr, image.image)
        ocr_text, confidence = ocr.text, ocr.confidence
    except ImageError as exc:
        if not settings.ai_available:
            raise AppError(502, exc.code, exc.message)
        ocr_text, confidence = "", 0.0

    if settings.ai_available:
        try:
            extraction = await run_in_threadpool(ai.extract_label, image.data, image.media_type, ocr_text)
        except ai.AIError:
            log.warning("AI extraction failed; falling back to OCR text")
            extraction = None
        if extraction is not None:
            if not extraction.is_food_label:
                raise AppError(422, "not_ingredient_label",
                               "We couldn't find an ingredient list in this photo. Photograph the ingredients panel.")
            if not extraction.legible or not extraction.ingredients_text.strip():
                raise AppError(422, "low_quality_image",
                               "The ingredient text is hard to read. " + (" ".join(quality) or "Try a sharper, closer photo."),
                               {"tips": quality})
            return ExtractionOut(
                ingredients_text=extraction.ingredients_text.strip(),
                product_name=extraction.product_name,
                brand=extraction.brand,
                sodium_mg_per_100g=extraction.sodium_mg_per_100g,
                ocr_text=ocr_text,
                ocr_confidence=round(confidence, 1),
                ai_used=True,
                quality_warnings=quality,
            )

    # Deterministic OCR-only path.
    text = extract_ingredient_section(ocr_text)
    if confidence < MIN_OCR_CONFIDENCE or len(text) < 3:
        raise AppError(422, "low_quality_image",
                       "We couldn't read the label clearly. " + (" ".join(quality) or "Try a sharper, closer, well-lit photo."),
                       {"tips": quality, "ocr_confidence": round(confidence, 1)})
    try:
        parse_ingredients(text)
    except IngredientInputError:
        raise AppError(422, "no_ingredients_found",
                       "We couldn't find an ingredient list in this photo. Photograph the ingredients panel or type them in.")
    return ExtractionOut(
        ingredients_text=text,
        product_name=None,
        brand=None,
        sodium_mg_per_100g=None,
        ocr_text=ocr_text,
        ocr_confidence=round(confidence, 1),
        ai_used=False,
        quality_warnings=quality,
    )
