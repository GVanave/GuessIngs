"""Image validation, quality checks and Tesseract OCR."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from app.core.config import get_settings

log = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MIN_DIMENSION = 200
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ImageError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ValidatedImage:
    image: Image.Image
    media_type: str
    data: bytes


@dataclass
class OcrResult:
    text: str
    confidence: float  # 0–100 mean word confidence


def validate_image(data: bytes) -> ValidatedImage:
    settings = get_settings()
    if not data:
        raise ImageError("empty_file", "The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ImageError("file_too_large", f"Images must be smaller than {settings.max_upload_mb} MB.")
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()  # structural check; image must be reopened afterwards
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, ValueError):
        raise ImageError("invalid_image", "That file isn't a valid image. Please upload a JPG, PNG or WEBP photo.")
    if fmt not in ALLOWED_FORMATS:
        raise ImageError("unsupported_format", "Unsupported image type. Please upload a JPG, PNG or WEBP photo.")
    image = ImageOps.exif_transpose(image)
    if min(image.size) < MIN_DIMENSION:
        raise ImageError(
            "low_quality_image",
            "The image resolution is too low to read. Move closer to the label or use a sharper photo.",
        )
    return ValidatedImage(image=image, media_type=ALLOWED_FORMATS[fmt], data=data)


def assess_quality(image: Image.Image) -> list[str]:
    """Return human-readable quality problems (empty list if the image looks fine)."""
    gray = image.convert("L")
    gray.thumbnail((800, 800))
    stat = ImageStat.Stat(gray)
    brightness, contrast = stat.mean[0], stat.stddev[0]
    issues: list[str] = []
    # Only flag exposure when the text has also lost contrast: a crisp label on white paper is bright but fine.
    if brightness < 40 and contrast < 30:
        issues.append("The photo is very dark. Try better lighting.")
    elif brightness > 235 and contrast < 20:
        issues.append("The photo is overexposed. Avoid glare and direct light.")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).var[0]
    if sharpness < 60:
        issues.append("The photo looks blurry. Hold the camera steady and tap to focus.")
    return issues


def _prepare_for_ocr(image: Image.Image) -> Image.Image:
    gray = ImageOps.autocontrast(image.convert("L"))
    width, height = gray.size
    if max(width, height) < 1600:
        scale = 1600 / max(width, height)
        gray = gray.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    elif max(width, height) > 3500:
        gray.thumbnail((3500, 3500))
    return gray.filter(ImageFilter.SHARPEN)


def _join_line(words: list[tuple[int, int, int, str]]) -> str:
    """Join a line's words, marking large horizontal gaps (other columns, glare noise) with a tab."""
    words = sorted(words)
    heights = sorted(h for _, _, h, _ in words)
    gap_limit = 2.5 * heights[len(heights) // 2]
    out = words[0][3]
    for (left, width, _, _), (next_left, _, _, word) in zip(words, words[1:], strict=False):
        out += ("\t" if next_left - (left + width) > gap_limit else " ") + word
    return out


def run_ocr(image: Image.Image) -> OcrResult:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - dependency is required
        raise ImageError("ocr_unavailable", "Text recognition is temporarily unavailable.") from exc

    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    prepared = _prepare_for_ocr(image)
    try:
        data = pytesseract.image_to_data(
            prepared, config="--oem 1 --psm 6", output_type=pytesseract.Output.DICT, timeout=30
        )
    except (pytesseract.TesseractNotFoundError, RuntimeError, OSError) as exc:
        log.error("OCR failed: %s", type(exc).__name__)
        raise ImageError("ocr_failed", "We couldn't read text from this image. Try again or type the ingredients.") from exc

    lines: dict[tuple[int, int, int], list[tuple[int, int, int, str]]] = {}
    confidences: list[float] = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        conf = float(data["conf"][i])
        if not word or conf < 0:
            continue
        confidences.append(conf)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append((data["left"][i], data["width"][i], data["height"][i], word))
    text = "\n".join(_join_line(words) for _, words in sorted(lines.items()))
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return OcrResult(text=text, confidence=confidence)
