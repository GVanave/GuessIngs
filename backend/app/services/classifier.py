"""Ingredient classification: knowledge base → deterministic patterns → cache → AI.

Knowledge-base and pattern matches are always recomputed and therefore fully
deterministic. AI classifications are persisted in the ``ingredients`` table
the first time an ingredient is seen, and read back from there afterwards, so
a given ingredient is always classified the same way.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Ingredient
from app.services import ai
from app.services.categories import Category
from app.services.knowledge_base import KB_VERSION, lookup
from app.services.normalization import ParsedIngredient
from app.services.patterns import PATTERNS_VERSION, classify_by_pattern

log = logging.getLogger(__name__)

AI_BATCH_LIMIT = 60


@dataclass
class ClassifiedIngredient:
    display: str
    key: str
    canonical: str
    categories: tuple[Category, ...]
    position: int
    parent: str | None
    source: str  # kb | pattern | ai | unknown
    ingredient_id: object | None = None
    is_duplicate: bool = False


@dataclass
class ClassificationOutcome:
    items: list[ClassifiedIngredient]
    ai_used: bool
    warnings: list[str]


def classify_static(parsed: ParsedIngredient) -> tuple[str, tuple[Category, ...], str] | None:
    """Deterministic classification without DB or AI. Returns (canonical, categories, source)."""
    for candidate in parsed.candidates:
        entry = lookup(candidate)
        if entry:
            return entry.canonical, entry.categories, "kb"
    for candidate in parsed.candidates:
        cats = classify_by_pattern(candidate)
        if cats:
            return candidate, cats, "pattern"
    return None


def _cached(db: Session, keys: list[str]) -> dict[str, Ingredient]:
    if not keys:
        return {}
    rows = db.execute(select(Ingredient).where(Ingredient.name.in_(keys))).scalars().all()
    return {row.name: row for row in rows}


def _store(db: Session, key: str, canonical: str, cats: tuple[Category, ...], source: str,
           version: str, rationale: str | None = None) -> Ingredient:
    existing = db.execute(select(Ingredient).where(Ingredient.name == key)).scalar_one_or_none()
    if existing is not None:
        if existing.source != "ai" and (existing.categories != [c.value for c in cats] or existing.classifier_version != version):
            existing.categories = [c.value for c in cats]
            existing.canonical_name = canonical
            existing.source = source
            existing.classifier_version = version
        return existing
    row = Ingredient(
        name=key, canonical_name=canonical, categories=[c.value for c in cats], source=source,
        classifier_version=version, rationale=rationale,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        # Another request stored the same ingredient concurrently.
        return db.execute(select(Ingredient).where(Ingredient.name == key)).scalar_one()
    return row


def classify_all(db: Session, parsed: list[ParsedIngredient], allow_ai: bool = True) -> ClassificationOutcome:
    settings = get_settings()
    warnings: list[str] = []
    ai_used = False
    results: list[ClassifiedIngredient | None] = [None] * len(parsed)
    pending: dict[str, list[int]] = {}

    for idx, p in enumerate(parsed):
        static = classify_static(p)
        if static:
            canonical, cats, source = static
            version = KB_VERSION if source == "kb" else PATTERNS_VERSION
            row = _store(db, canonical if source == "kb" else p.key, canonical, cats, source, version)
            results[idx] = ClassifiedIngredient(p.display, p.key, canonical, cats, p.position, p.parent, source, row.id)
        else:
            pending.setdefault(p.key, []).append(idx)

    cache = _cached(db, list(pending))
    for key, row in cache.items():
        if row.source == "ai":
            cats = tuple(Category(c) for c in row.categories)
            for idx in pending.pop(key):
                p = parsed[idx]
                results[idx] = ClassifiedIngredient(p.display, key, row.canonical_name, cats, p.position, p.parent, "ai", row.id)

    if pending and allow_ai and settings.ai_available:
        names = list(pending)[:AI_BATCH_LIMIT]
        try:
            classified = ai.classify(names)
            ai_used = True
        except ai.AIError as exc:
            log.warning("AI classification unavailable: %s", exc)
            classified = {}
            warnings.append("Some ingredients couldn't be identified because the AI classifier is temporarily unavailable.")
        version = f"{settings.ai_model}/{ai.AI_PROMPT_VERSION}"
        for key, item in classified.items():
            cats = tuple(Category(c) for c in item.categories)
            if cats == (Category.UNKNOWN,):
                continue
            row = _store(db, key, item.canonical_name.strip().lower()[:160] or key, cats, "ai", version, item.rationale[:500])
            for idx in pending.pop(key):
                p = parsed[idx]
                results[idx] = ClassifiedIngredient(p.display, key, row.canonical_name, cats, p.position, p.parent, "ai", row.id)

    for key, indices in pending.items():
        for idx in indices:
            p = parsed[idx]
            results[idx] = ClassifiedIngredient(p.display, key, key, (Category.UNKNOWN,), p.position, p.parent, "unknown")

    items = [r for r in results if r is not None]
    seen: set[str] = set()
    for item in items:
        if item.canonical in seen:
            item.is_duplicate = True
        seen.add(item.canonical)
    unknown = [i.display for i in items if i.source == "unknown"]
    if unknown:
        warnings.append(
            f"{len(unknown)} ingredient(s) weren't recognized and don't affect the score: " + ", ".join(unknown[:8])
        )
    return ClassificationOutcome(items=items, ai_used=ai_used, warnings=warnings)
