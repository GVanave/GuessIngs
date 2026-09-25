import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.services import ai

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def label_image(lines, size=(1400, 500), fmt="PNG", blur=False) -> bytes:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT, 40)
    except OSError:  # pragma: no cover
        font = ImageFont.load_default()
    y = 40
    for line in lines:
        draw.text((40, y), line, fill="black", font=font)
        y += 60
    if blur:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(12))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def upload(client, data, name="label.png", ctype="image/png"):
    return client.post("/api/scan/extract", files={"file": (name, data, ctype)})


def test_ocr_extracts_ingredients_from_label(auth_client):
    data = label_image(["INGREDIENTS: Rolled oats, sugar,", "sunflower oil, salt, cinnamon.",
                        "Contains: gluten."])
    res = upload(auth_client, data)
    assert res.status_code == 200, res.text
    body = res.json()
    text = body["ingredients_text"].lower()
    assert "rolled oats" in text and "salt" in text and "gluten" not in text
    assert body["ai_used"] is False and body["ocr_confidence"] > 45
    # The extracted text can be analyzed directly.
    analysis = auth_client.post("/api/analyses", json={"ingredients_text": body["ingredients_text"], "source": "camera",
                                                       "ocr_text": body["ocr_text"]})
    assert analysis.status_code == 201
    assert analysis.json()["source"] == "camera"


def test_invalid_image_is_rejected(auth_client):
    res = upload(auth_client, b"this is not an image at all", "evil.png")
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_image"


def test_disguised_file_type_is_rejected(auth_client):
    gif = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(gif, format="GIF")
    res = upload(auth_client, gif.getvalue(), "photo.png", "image/png")
    assert res.status_code == 400 and res.json()["error"]["code"] == "unsupported_format"


def test_empty_file_is_rejected(auth_client):
    res = upload(auth_client, b"")
    assert res.status_code == 400 and res.json()["error"]["code"] == "empty_file"


def test_tiny_image_is_low_quality(auth_client):
    res = upload(auth_client, label_image(["sugar"], size=(120, 80)))
    assert res.status_code == 400 and res.json()["error"]["code"] == "low_quality_image"


def test_oversized_upload_is_rejected(auth_client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    big = io.BytesIO()
    Image.effect_noise((1500, 1500), 100).convert("RGB").save(big, format="PNG")
    assert len(big.getvalue()) > 1024 * 1024
    res = upload(auth_client, big.getvalue())
    assert res.status_code == 413 and res.json()["error"]["code"] == "file_too_large"


def test_blank_or_blurry_photo_gives_recovery_tips(auth_client):
    res = upload(auth_client, label_image(["Ingredients: oats, sugar, salt"], blur=True))
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] in ("low_quality_image", "no_ingredients_found")
    assert "photo" in body["message"].lower() or "label" in body["message"].lower()


def test_scan_requires_auth(client):
    assert upload(client, label_image(["oats"])).status_code == 401


@pytest.fixture
def ai_on(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()


def test_ai_extraction_path(auth_client, ai_on, monkeypatch):
    seen = {}

    def fake_extract(image_bytes, media_type, ocr_text):
        seen["media_type"] = media_type
        return ai.LabelExtraction(is_food_label=True, legible=True, product_name="Oat Crunch", brand="Acme",
                                  ingredients_text="Whole grain oats, sugar, salt", sodium_mg_per_100g=420)

    monkeypatch.setattr(ai, "extract_label", fake_extract)
    res = upload(auth_client, label_image(["Ingredients: oats, sugar, salt"]))
    assert res.status_code == 200
    body = res.json()
    assert body["ai_used"] and body["product_name"] == "Oat Crunch" and body["sodium_mg_per_100g"] == 420
    assert seen["media_type"] == "image/png"


def test_ai_detects_non_label_photo(auth_client, ai_on, monkeypatch):
    monkeypatch.setattr(ai, "extract_label", lambda *a: ai.LabelExtraction(
        is_food_label=False, legible=True, product_name=None, brand=None, ingredients_text="", sodium_mg_per_100g=None))
    res = upload(auth_client, label_image(["Hello world"]))
    assert res.status_code == 422 and res.json()["error"]["code"] == "not_ingredient_label"


def test_ai_failure_falls_back_to_ocr(auth_client, ai_on, monkeypatch):
    def boom(*a):
        raise ai.AIError("down")

    monkeypatch.setattr(ai, "extract_label", boom)
    res = upload(auth_client, label_image(["INGREDIENTS: Rolled oats, sugar, salt."]))
    assert res.status_code == 200
    assert res.json()["ai_used"] is False
