from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.services import scoring as s
from app.services.knowledge_base import KB_VERSION, all_entries

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise AppError(503, "database_unavailable", "Database unavailable.")
    return {"status": "ok"}


@router.get("/meta/scoring-rules")
def scoring_rules():
    """Public, human-readable description of the deterministic scoring rules."""
    return {
        "scoring_version": s.SCORING_VERSION,
        "knowledge_base_version": KB_VERSION,
        "known_ingredients": sum(1 + len(e.synonyms) for e in all_entries()),
        "ai_enabled": get_settings().ai_available,
        "start": s.START_SCORE,
        "deductions": [
            {"rule": "Added sugar / syrups", "points": "−15 to −30",
             "detail": "1st ingredient −30 · 2nd–3rd −25 · 4th–5th −20 · 6th+ −15; −5 per extra sugar source; max −30"},
            {"rule": "Artificial sweetener", "points": f"−{s.SWEETENER_DEDUCTION} each", "detail": "e.g. sucralose, aspartame"},
            {"rule": "Hydrogenated oil", "points": f"−{s.HYDROGENATED_DEDUCTION}", "detail": "Hydrogenated or partially hydrogenated fats"},
            {"rule": "Artificial color", "points": f"−{s.ARTIFICIAL_COLOR_DEDUCTION} each", "detail": "e.g. Red 40, E102"},
            {"rule": "Artificial flavor", "points": f"−{s.ARTIFICIAL_FLAVOR_DEDUCTION} each", "detail": "Artificial flavors and enhancers like MSG"},
            {"rule": "Preservative", "points": f"−{s.PRESERVATIVE_DEDUCTION} each", "detail": "e.g. sodium benzoate, BHT"},
            {"rule": "Emulsifier / ultra-processed marker", "points": f"−{s.EMULSIFIER_DEDUCTION} each", "detail": "Emulsifiers, gums, modified starch, isolates"},
            {"rule": "High sodium", "points": f"−{s.SODIUM_DEDUCTION}", "detail": f"Only when sodium is provided and > {s.SODIUM_HIGH_MG_PER_100G} mg/100 g"},
            {"rule": "Ultra-processed (NOVA 4)", "points": f"−{s.NOVA4_DEDUCTION}", "detail": "Any sweetener, hydrogenated oil, color, flavor or emulsifier marker"},
        ],
        "additions": [
            {"rule": "Whole-food fiber/protein source", "points": f"+{s.FIBER_PROTEIN_BONUS} each (max +{s.FIBER_PROTEIN_MAX_BONUS})",
             "detail": f"Within the first {s.MEANINGFUL_POSITION} ingredients"},
            {"rule": "Healthy fat source", "points": f"+{s.HEALTHY_FAT_BONUS}", "detail": f"Within the first {s.MEANINGFUL_POSITION} ingredients"},
        ],
        "verdicts": [
            {"verdict": "GREEN", "range": f"{s.GREEN_MIN}–100"},
            {"verdict": "YELLOW", "range": f"{s.YELLOW_MIN}–{s.GREEN_MIN - 1}"},
            {"verdict": "RED", "range": f"0–{s.YELLOW_MIN - 1}"},
        ],
    }
