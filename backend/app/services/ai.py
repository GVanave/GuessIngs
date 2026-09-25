"""Claude-powered extraction, normalization, classification and explanation.

The AI layer only ever returns *structured data* (validated with Pydantic);
it never decides the score. When no API key is configured, or a call fails,
callers fall back to the deterministic OCR/knowledge-base pipeline.
"""

from __future__ import annotations

import base64
import logging
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.categories import Category

log = logging.getLogger(__name__)

AI_PROMPT_VERSION = "prompts-2026.09"


class AIError(RuntimeError):
    """The AI service was unavailable or returned an unusable response."""


# ---------------------------------------------------------------- schemas ---
class LabelExtraction(BaseModel):
    is_food_label: bool = Field(description="True if the image/text contains a food product ingredient list")
    legible: bool = Field(description="False if the ingredient text is too blurry, cut off or unreadable")
    product_name: str | None = Field(description="Product name if visible, else null")
    brand: str | None = Field(description="Brand if visible, else null")
    ingredients_text: str = Field(
        description="The ingredient list exactly as printed, in order, comma separated, "
        "keeping parentheses for sub-ingredients. Fix obvious OCR errors only. Empty if none."
    )
    sodium_mg_per_100g: float | None = Field(
        description="Sodium in mg per 100 g/ml if a nutrition table states it (convert salt g ×400 → mg sodium), else null"
    )


class IngredientClassification(BaseModel):
    input_name: str = Field(description="The ingredient name exactly as given in the request")
    canonical_name: str = Field(description="Common English name, lowercase, singular where natural")
    categories: list[
        Literal[
            "added_sugar",
            "artificial_sweetener",
            "hydrogenated_oil",
            "artificial_color",
            "artificial_flavor",
            "preservative",
            "emulsifier",
            "fiber_protein",
            "healthy_fat",
            "whole_food",
            "culinary",
            "neutral_additive",
            "unknown",
        ]
    ]
    rationale: str = Field(description="One short sentence explaining the classification")


class ClassificationBatch(BaseModel):
    items: list[IngredientClassification]


class Explanation(BaseModel):
    summary: str = Field(description="2-3 sentence plain-language explanation of the score for a shopper")


# ---------------------------------------------------------------- prompts ---
EXTRACTION_SYSTEM = (
    "You read food packaging. Extract the ingredient list from the label precisely as printed. "
    "Do not invent ingredients. If the label is not a food ingredient list, set is_food_label=false. "
    "If the ingredient text is present but too blurry or cut off to read reliably, set legible=false."
)

CLASSIFICATION_SYSTEM = """You classify food ingredients into fixed categories for a rule-based scoring engine.
Assign every category that applies:
- added_sugar: sugars and syrups added as sweeteners (sugar, syrups, honey, juice concentrates, dextrose, maltodextrin)
- artificial_sweetener: non-nutritive or sugar-alcohol sweeteners (sucralose, aspartame, stevia extract, sorbitol, erythritol)
- hydrogenated_oil: hydrogenated or partially hydrogenated fats, shortening
- artificial_color: synthetic or added colors (Red 40, E1xx colors, caramel color, titanium dioxide)
- artificial_flavor: artificial flavors, 'flavoring', flavor enhancers (MSG, E62x)
- preservative: antimicrobial or synthetic antioxidant preservatives (benzoates, sorbates, nitrites, BHA/BHT, TBHQ)
- emulsifier: emulsifiers, thickeners, gums, modified starches, protein isolates, and other industrial ultra-processing markers
- fiber_protein: meaningful whole-food fiber or protein sources (whole grains, legumes, nuts, seeds, eggs, dairy, meat, fish)
- healthy_fat: sources of mostly unsaturated fat (olive/avocado/canola oil, nuts, seeds, avocado)
- whole_food: minimally processed foods (fruit, vegetables, whole grains, nuts, spices)
- culinary: processed culinary ingredients (salt, refined oils, butter, refined flour, starch, vinegar)
- neutral_additive: common additives with no known concern (citric acid, baking soda, vitamins, natural flavor, water)
- unknown: only if you genuinely cannot identify the ingredient
Return exactly one item per input, with input_name copied verbatim."""


def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.ai_available:
        raise AIError("AI is not configured")
    return anthropic.Anthropic(
        api_key=settings.anthropic_api_key, timeout=settings.ai_timeout_seconds, max_retries=2
    )


def _parse(system: str, content: list[dict] | str, schema: type[BaseModel], max_tokens: int = 8000):
    settings = get_settings()
    try:
        response = _client().messages.parse(
            model=settings.ai_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=schema,
            output_config={"effort": "low"},
        )
    except anthropic.RateLimitError as exc:
        raise AIError("AI rate limit reached") from exc
    except anthropic.APIStatusError as exc:
        log.warning("AI request failed with status %s", exc.status_code)
        raise AIError("AI request failed") from exc
    except anthropic.APIConnectionError as exc:
        raise AIError("AI service unreachable") from exc
    except Exception as exc:  # validation or unexpected SDK errors
        log.warning("AI request failed: %s", type(exc).__name__)
        raise AIError("AI request failed") from exc

    if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
        raise AIError(f"AI response unusable ({response.stop_reason})")
    return response.parsed_output


def extract_label(image_bytes: bytes | None, media_type: str | None, ocr_text: str | None) -> LabelExtraction:
    content: list[dict] = []
    if image_bytes and media_type:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                },
            }
        )
    hint = f"\n\nTesseract OCR output (may contain errors):\n<ocr>\n{ocr_text[:4000]}\n</ocr>" if ocr_text else ""
    content.append({"type": "text", "text": "Extract the ingredient list and product details." + hint})
    return _parse(EXTRACTION_SYSTEM, content, LabelExtraction)


def classify(names: list[str]) -> dict[str, IngredientClassification]:
    if not names:
        return {}
    listing = "\n".join(f"- {n}" for n in names)
    batch: ClassificationBatch = _parse(
        CLASSIFICATION_SYSTEM, f"Classify these ingredients:\n{listing}", ClassificationBatch
    )
    wanted = set(names)
    out: dict[str, IngredientClassification] = {}
    for item in batch.items:
        if item.input_name in wanted and item.categories:
            # Validate against the enum (defence in depth).
            item.categories = [c for c in item.categories if c in Category._value2member_map_] or ["unknown"]
            out[item.input_name] = item
    return out


def explain(product_name: str, score: int, verdict: str, lines: list[dict], concerns: list[str], positives: list[str]) -> str:
    facts = "\n".join(f"- {line['label']}: {line['points']:+d} ({line['detail']})" for line in lines)
    prompt = (
        f"Product: {product_name}\nFinal score: {score}/100 ({verdict}). The score is already final; "
        f"do not change or recompute it.\nScore breakdown:\n{facts}\n"
        f"Ingredients to watch: {', '.join(concerns) or 'none'}\nPositive ingredients: {', '.join(positives) or 'none'}\n"
        "Write a friendly, factual explanation for a shopper. No medical claims."
    )
    result: Explanation = _parse(
        "You explain food ingredient scores clearly and neutrally.", prompt, Explanation, max_tokens=2000
    )
    return result.summary
