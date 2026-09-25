"""Deterministic, rule-based nutrition scoring engine.

This module is pure application code: it never calls an AI model, never reads
the clock, the database or any random source. Given the same structured
ingredient data it always returns exactly the same score, verdict and
breakdown. The AI layer only produces the *inputs* (classified ingredients).

Rules (version ``SCORING_VERSION``)
-----------------------------------
Start at 100, then apply:

Deductions
  * Added sugar / syrups — one deduction for the product, set by the position
    of the earliest added sugar:
        position 1 → −30, positions 2–3 → −25, positions 4–5 → −20, 6+ → −15
    plus −5 for every *additional* distinct added-sugar ingredient.
    The total sugar deduction is capped at −30.
  * Artificial sweetener: −10 each (distinct ingredient)
  * Hydrogenated / partially hydrogenated oil: −25 (once, if any present)
  * Artificial color: −8 each
  * Artificial flavor: −8 each
  * Preservative: −6 each
  * Emulsifier / ultra-processed marker: −5 each
  * Excessive sodium: −10, only when sodium (mg per 100 g) is supplied and is
    greater than 600 mg / 100 g (UK FSA "high" threshold of 1.5 g salt)
  * NOVA 4 (ultra-processed): −20 when any artificial sweetener, hydrogenated
    oil, artificial color, artificial flavor or emulsifier/UPF marker is present

Additions (only "meaningful" sources count: within the first 5 positions)
  * Whole-food fiber/protein source: +5 each, capped at +10
  * Healthy fat source: +5 (once)

The final score is clamped to 0–100.
Verdict: 80–100 GREEN, 50–79 YELLOW, 0–49 RED.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from app.services.categories import NOVA4_CATEGORIES, Category

SCORING_VERSION = "1.0.0"

START_SCORE = 100
SUGAR_POSITION_DEDUCTIONS = ((1, 30), (3, 25), (5, 20))  # (max position, points)
SUGAR_DEFAULT_DEDUCTION = 15
SUGAR_EXTRA_SOURCE_DEDUCTION = 5
SUGAR_MAX_DEDUCTION = 30
SWEETENER_DEDUCTION = 10
HYDROGENATED_DEDUCTION = 25
ARTIFICIAL_COLOR_DEDUCTION = 8
ARTIFICIAL_FLAVOR_DEDUCTION = 8
PRESERVATIVE_DEDUCTION = 6
EMULSIFIER_DEDUCTION = 5
SODIUM_DEDUCTION = 10
SODIUM_HIGH_MG_PER_100G = 600
NOVA4_DEDUCTION = 20
MEANINGFUL_POSITION = 5
FIBER_PROTEIN_BONUS = 5
FIBER_PROTEIN_MAX_BONUS = 10
HEALTHY_FAT_BONUS = 5

GREEN_MIN = 80
YELLOW_MIN = 50


class Verdict(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass(frozen=True)
class ScoringIngredient:
    name: str
    categories: tuple[Category, ...]
    position: int


@dataclass
class ScoreLine:
    code: str
    label: str
    points: int
    detail: str
    ingredients: list[str] = field(default_factory=list)


@dataclass
class ScoreResult:
    score: int
    raw_score: int
    verdict: Verdict
    nova_group: int
    lines: list[ScoreLine]
    scoring_version: str = SCORING_VERSION

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "raw_score": self.raw_score,
            "verdict": self.verdict.value,
            "nova_group": self.nova_group,
            "scoring_version": self.scoring_version,
            "lines": [asdict(line) for line in self.lines],
        }


def verdict_for(score: int) -> Verdict:
    if score >= GREEN_MIN:
        return Verdict.GREEN
    if score >= YELLOW_MIN:
        return Verdict.YELLOW
    return Verdict.RED


def sugar_position_deduction(position: int) -> int:
    for max_pos, points in SUGAR_POSITION_DEDUCTIONS:
        if position <= max_pos:
            return points
    return SUGAR_DEFAULT_DEDUCTION


def _with(ingredients: list[ScoringIngredient], category: Category) -> list[ScoringIngredient]:
    return [i for i in ingredients if category in i.categories]


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def nova_group(ingredients: list[ScoringIngredient]) -> int:
    """Deterministic NOVA estimate from ingredient categories."""
    if any(set(i.categories) & NOVA4_CATEGORIES for i in ingredients):
        return 4
    known = [i for i in ingredients if Category.UNKNOWN not in i.categories]
    if not known:
        return 3
    if all(Category.WHOLE_FOOD in i.categories or Category.FIBER_PROTEIN in i.categories for i in known) and (
        len(known) == len(ingredients)
    ):
        return 1
    if all(Category.CULINARY in i.categories or Category.NEUTRAL_ADDITIVE in i.categories for i in known):
        return 2
    return 3


def dedupe(ingredients: list[ScoringIngredient]) -> list[ScoringIngredient]:
    """Keep the first (highest-position) occurrence of every ingredient name."""
    seen: set[str] = set()
    out: list[ScoringIngredient] = []
    for ing in sorted(ingredients, key=lambda i: i.position):
        key = ing.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ing)
    return out


def score_ingredients(
    ingredients: list[ScoringIngredient], sodium_mg_per_100g: float | None = None
) -> ScoreResult:
    if not ingredients:
        raise ValueError("Cannot score an empty ingredient list")
    if sodium_mg_per_100g is not None and sodium_mg_per_100g < 0:
        raise ValueError("Sodium cannot be negative")

    items = dedupe(ingredients)
    lines: list[ScoreLine] = [
        ScoreLine("start", "Starting score", START_SCORE, "Every product starts at 100.")
    ]

    sugars = _with(items, Category.ADDED_SUGAR)
    if sugars:
        first = sugars[0]
        base = sugar_position_deduction(first.position)
        extra = SUGAR_EXTRA_SOURCE_DEDUCTION * (len(sugars) - 1)
        total = min(SUGAR_MAX_DEDUCTION, base + extra)
        detail = f"{first.name} is the {_ordinal(first.position)} ingredient (−{base})"
        if len(sugars) > 1:
            detail += f"; {len(sugars) - 1} more added-sugar source(s) (−{extra})"
        if base + extra > SUGAR_MAX_DEDUCTION:
            detail += f"; capped at −{SUGAR_MAX_DEDUCTION}"
        lines.append(ScoreLine("added_sugar", "Added sugar", -total, detail, [s.name for s in sugars]))

    per_item_rules = [
        (Category.ARTIFICIAL_SWEETENER, "artificial_sweetener", "Artificial sweetener", SWEETENER_DEDUCTION),
        (Category.ARTIFICIAL_COLOR, "artificial_color", "Artificial color", ARTIFICIAL_COLOR_DEDUCTION),
        (Category.ARTIFICIAL_FLAVOR, "artificial_flavor", "Artificial flavor", ARTIFICIAL_FLAVOR_DEDUCTION),
        (Category.PRESERVATIVE, "preservative", "Preservative", PRESERVATIVE_DEDUCTION),
        (Category.EMULSIFIER, "emulsifier", "Emulsifier / ultra-processed marker", EMULSIFIER_DEDUCTION),
    ]
    hydro = _with(items, Category.HYDROGENATED_OIL)
    if hydro:
        lines.append(
            ScoreLine(
                "hydrogenated_oil",
                "Hydrogenated oil",
                -HYDROGENATED_DEDUCTION,
                "Contains hydrogenated or partially hydrogenated fat (source of trans fats).",
                [h.name for h in hydro],
            )
        )
    for category, code, label, points in per_item_rules:
        matches = _with(items, category)
        if matches:
            lines.append(
                ScoreLine(
                    code,
                    label if len(matches) == 1 else f"{label} ×{len(matches)}",
                    -points * len(matches),
                    f"−{points} for each: " + ", ".join(m.name for m in matches),
                    [m.name for m in matches],
                )
            )

    if sodium_mg_per_100g is not None and sodium_mg_per_100g > SODIUM_HIGH_MG_PER_100G:
        lines.append(
            ScoreLine(
                "sodium",
                "High sodium",
                -SODIUM_DEDUCTION,
                f"{sodium_mg_per_100g:g} mg sodium per 100 g exceeds {SODIUM_HIGH_MG_PER_100G} mg.",
            )
        )

    nova = nova_group(items)
    if nova == 4:
        markers = [i.name for i in items if set(i.categories) & NOVA4_CATEGORIES]
        lines.append(
            ScoreLine(
                "nova4",
                "Ultra-processed (NOVA 4)",
                -NOVA4_DEDUCTION,
                "Contains industrial ingredients or cosmetic additives typical of ultra-processed food.",
                markers,
            )
        )

    fiber = [i for i in _with(items, Category.FIBER_PROTEIN) if i.position <= MEANINGFUL_POSITION]
    if fiber:
        bonus = min(FIBER_PROTEIN_MAX_BONUS, FIBER_PROTEIN_BONUS * len(fiber))
        lines.append(
            ScoreLine(
                "fiber_protein",
                "Whole-food fiber/protein source",
                bonus,
                f"+{FIBER_PROTEIN_BONUS} each within the first {MEANINGFUL_POSITION} ingredients"
                + (f", capped at +{FIBER_PROTEIN_MAX_BONUS}" if FIBER_PROTEIN_BONUS * len(fiber) > bonus else ""),
                [f.name for f in fiber],
            )
        )
    fats = [i for i in _with(items, Category.HEALTHY_FAT) if i.position <= MEANINGFUL_POSITION]
    if fats:
        lines.append(
            ScoreLine(
                "healthy_fat",
                "Healthy fat source",
                HEALTHY_FAT_BONUS,
                f"Healthy fat within the first {MEANINGFUL_POSITION} ingredients.",
                [f.name for f in fats],
            )
        )

    raw = sum(line.points for line in lines)
    score = max(0, min(100, raw))
    if raw < 0:
        lines.append(ScoreLine("floor", "Minimum score applied", -raw, "Scores cannot go below 0."))
    elif raw > 100:
        lines.append(ScoreLine("cap", "Maximum score applied", 100 - raw, "Scores cannot exceed 100."))

    return ScoreResult(score=score, raw_score=raw, verdict=verdict_for(score), nova_group=nova, lines=lines)
