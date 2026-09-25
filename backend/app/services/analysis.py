"""End-to-end analysis pipeline: text → normalize → classify → score → persist."""

from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Analysis, AnalysisIngredient, Product, User, utcnow
from app.services import ai, insights
from app.services.categories import CATEGORY_LABELS, NEGATIVE_CATEGORIES, Category
from app.services.classifier import classify_all
from app.services.knowledge_base import KB_VERSION
from app.services.normalization import IngredientInputError, parse_ingredients
from app.services.patterns import PATTERNS_VERSION
from app.services.scoring import SCORING_VERSION, ScoringIngredient, score_ingredients

log = logging.getLogger(__name__)

DEFAULT_PRODUCT_NAME = "Untitled product"
_NEG = {c.value for c in NEGATIVE_CATEGORIES}


def input_hash(items: list[tuple[str, int, list[str]]], sodium: float | None) -> str:
    payload = json.dumps({"i": items, "na": sodium, "v": SCORING_VERSION}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _get_or_create_product(db: Session, user: User, name: str, brand: str | None, category: str) -> Product:
    stmt = select(Product).where(Product.user_id == user.id, func.lower(Product.name) == name.lower())
    if brand:
        stmt = stmt.where(func.lower(Product.brand) == brand.lower())
    else:
        stmt = stmt.where(Product.brand.is_(None))
    product = db.execute(stmt.limit(1)).scalar_one_or_none()
    if product is None:
        product = Product(user_id=user.id, name=name, brand=brand, category=category)
        db.add(product)
        db.flush()
    elif product.category != category:
        product.category = category
    return product


def run_analysis(
    db: Session,
    user: User,
    ingredients_text: str,
    product_name: str | None = None,
    brand: str | None = None,
    sodium_mg_per_100g: float | None = None,
    source: str = "manual",
    ocr_text: str | None = None,
) -> Analysis:
    settings = get_settings()
    try:
        parsed = parse_ingredients(ingredients_text)
    except IngredientInputError as exc:
        raise AppError(422, exc.code, exc.message)

    outcome = classify_all(db, parsed, allow_ai=True)
    scoring_items = [
        ScoringIngredient(name=i.canonical, categories=i.categories, position=i.position) for i in outcome.items
    ]
    result = score_ingredients(scoring_items, sodium_mg_per_100g)
    result_dict = result.to_dict()
    lines = result_dict["lines"]

    name = (product_name or "").strip() or DEFAULT_PRODUCT_NAME
    product_type = insights.detect_product_type(name, [i.canonical for i in outcome.items])
    explanation = insights.build_explanation(result.score, result.verdict.value, result.nova_group, lines)

    prefs = user.preferences or {}
    if settings.ai_available and prefs.get("ai_explanations", True):
        try:
            explanation["ai_summary"] = ai.explain(
                name,
                result.score,
                result.verdict.value,
                lines,
                [i.canonical for i in outcome.items if {c.value for c in i.categories} & _NEG],
                [i.canonical for i in outcome.items if set(i.categories) & {Category.FIBER_PROTEIN, Category.HEALTHY_FAT}],
            )
        except ai.AIError:
            log.info("AI explanation unavailable; using deterministic explanation only")

    product = _get_or_create_product(db, user, name, brand, product_type)
    analysis = Analysis(
        user_id=user.id,
        product_id=product.id,
        source=source,
        raw_text=ingredients_text,
        ocr_text=ocr_text,
        input_hash=input_hash(
            [(i.canonical, i.position, sorted(c.value for c in i.categories)) for i in outcome.items],
            sodium_mg_per_100g,
        ),
        sodium_mg_per_100g=sodium_mg_per_100g,
        score=result.score,
        verdict=result.verdict.value,
        nova_group=result.nova_group,
        breakdown=lines,
        explanation=explanation,
        alternatives=insights.build_alternatives(product_type, result.verdict.value, lines),
        warnings=outcome.warnings,
        scoring_version=SCORING_VERSION,
        knowledge_base_version=f"{KB_VERSION}+{PATTERNS_VERSION}",
        ai_model=settings.ai_model if outcome.ai_used or explanation.get("ai_summary") else None,
        ai_used=outcome.ai_used,
        created_at=utcnow(),
    )
    for idx, item in enumerate(outcome.items):
        analysis.ingredients.append(
            AnalysisIngredient(
                ingredient_id=item.ingredient_id,
                order_index=idx,
                position=item.position,
                display_name=item.display[:200],
                canonical_name=item.canonical[:160],
                parent=(item.parent or None) and item.parent[:200],
                categories=[c.value for c in item.categories],
                source=item.source,
                is_duplicate=item.is_duplicate,
            )
        )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis



def rescore(analysis: Analysis):
    """Recompute the score from the stored structured ingredient data."""
    items = [
        ScoringIngredient(name=i.canonical_name, categories=tuple(Category(c) for c in i.categories), position=i.position)
        for i in analysis.ingredients
    ]
    return score_ingredients(items, analysis.sodium_mg_per_100g)


# ------------------------------------------------------------ serialization --
def summary(analysis: Analysis) -> dict:
    return {
        "id": analysis.id,
        "product": analysis.product,
        "score": analysis.score,
        "verdict": analysis.verdict,
        "nova_group": analysis.nova_group,
        "source": analysis.source,
        "ingredient_count": sum(1 for i in analysis.ingredients if not i.is_duplicate),
        "created_at": analysis.created_at,
    }


def _history_alternatives(db: Session, analysis: Analysis) -> list[dict]:
    category = analysis.product.category
    if not category or category == "other":
        return []
    rows = db.execute(
        select(Analysis)
        .join(Product)
        .where(
            Analysis.user_id == analysis.user_id,
            Product.category == category,
            Analysis.product_id != analysis.product_id,
            Analysis.score > analysis.score,
        )
        .order_by(Analysis.score.desc(), Analysis.created_at.desc())
        .limit(6)
    ).scalars().all()
    seen: set = set()
    out = []
    for row in rows:
        if row.product_id in seen:
            continue
        seen.add(row.product_id)
        out.append({
            "kind": "history",
            "title": row.product.name,
            "description": f"You scanned this {insights.TYPE_LABELS.get(category, 'product').lower()} before and it scored higher.",
            "analysis_id": row.id,
            "score": row.score,
            "verdict": row.verdict,
        })
        if len(out) == 2:
            break
    return out


def detail(db: Session, analysis: Analysis) -> dict:
    ingredients = [
        {
            "display_name": i.display_name,
            "canonical_name": i.canonical_name,
            "position": i.position,
            "parent": i.parent,
            "categories": i.categories,
            "labels": [CATEGORY_LABELS[Category(c)] for c in i.categories],
            "source": i.source,
            "is_duplicate": i.is_duplicate,
        }
        for i in analysis.ingredients
    ]
    return {
        **summary(analysis),
        "raw_text": analysis.raw_text,
        "sodium_mg_per_100g": analysis.sodium_mg_per_100g,
        "breakdown": analysis.breakdown,
        "explanation": analysis.explanation,
        "ingredients": ingredients,
        "concerns": insights.concerns(ingredients),
        "positives": insights.positives(ingredients),
        "alternatives": _history_alternatives(db, analysis) + list(analysis.alternatives or []),
        "warnings": analysis.warnings or [],
        "scoring_version": analysis.scoring_version,
        "knowledge_base_version": analysis.knowledge_base_version,
        "ai_model": analysis.ai_model,
        "ai_used": analysis.ai_used,
        "input_hash": analysis.input_hash,
    }
