"""Deterministic keyword / E-number rules for ingredients not in the knowledge base."""

from __future__ import annotations

import re

from app.services.categories import Category as C

PATTERNS_VERSION = "patterns-2026.09"


def _e_number(key: str) -> int | None:
    m = re.fullmatch(r"e(\d{3,4})[a-z]{0,3}", key)
    return int(m.group(1)) if m else None


def classify_e_number(key: str) -> tuple[C, ...] | None:
    n = _e_number(key)
    if n is None:
        return None
    if 100 <= n <= 199:
        return (C.ARTIFICIAL_COLOR,)
    if 200 <= n <= 299:
        return (C.PRESERVATIVE,)
    if 310 <= n <= 321:
        return (C.PRESERVATIVE,)
    if 300 <= n <= 399:
        return (C.NEUTRAL_ADDITIVE,)
    if 400 <= n <= 499:
        return (C.EMULSIFIER,)
    if 620 <= n <= 650:
        return (C.ARTIFICIAL_FLAVOR,)
    if 950 <= n <= 969:
        return (C.ARTIFICIAL_SWEETENER,)
    if 1400 <= n <= 1452:
        return (C.EMULSIFIER,)
    if 500 <= n <= 599:
        return (C.NEUTRAL_ADDITIVE,)
    return None


# Ordered rules; first match wins.
_RULES: list[tuple[re.Pattern[str], tuple[C, ...]]] = [
    (re.compile(r"\bnon[- ]?hydrogenated\b"), ()),  # sentinel handled below
    (re.compile(r"\b(?:partially |fully )?hydrogenated\b|\bshortening\b"), (C.HYDROGENATED_OIL,)),
    (re.compile(r"\bartificial(?:ly)? sweeten|\bsugar alcohol|\bpolyol"), (C.ARTIFICIAL_SWEETENER,)),
    (re.compile(r"\bartificial(?:ly)? colou?r|\bfd ?& ?c\b|\b(?:red|yellow|blue|green) (?:no\.? ?)?\d{1,2}\b|\blake\b"),
     (C.ARTIFICIAL_COLOR,)),
    (re.compile(r"\bartificial(?:ly)? flavou?r|\bflavou?r enhancer|\bglutamate\b|\binosinate\b|\bguanylate\b"),
     (C.ARTIFICIAL_FLAVOR,)),
    (re.compile(r"\bnatural\b.*\bflavou?r|\bflavou?r.*\bnatural\b|\bextractives?\b"), (C.NEUTRAL_ADDITIVE,)),
    (re.compile(r"\bflavou?r(?:ing|ings|s|ed)?\b"), (C.ARTIFICIAL_FLAVOR,)),
    (re.compile(r"\b(?:natural|vegetable|fruit|plant)\b.*\bcolou?r|\bcolou?r\b.*\b(?:from|natural)\b"),
     (C.NEUTRAL_ADDITIVE,)),
    (re.compile(r"\bcolou?r(?:s|ing|ings)?\b|\bdye\b"), (C.ARTIFICIAL_COLOR,)),
    (re.compile(r"\b(?:benzoate|sorbate|propionate|nitrite|nitrate|sulfite|bisulfite|metabisulfite|paraben)s?\b|\bpreservatives?\b"),
     (C.PRESERVATIVE,)),
    (re.compile(r"\bgums?\b|\bmodified\b.*\bstarch\b|\bisolate\b|\bhydrolyzed\b|\bglycerides?\b|\blecithin\b|"
                r"\bpolysorbate\b|\bstearoyl\b|\bcarrageenan\b|\bemulsifi|\bstabiliz|\bthicken|\bphosphate\b|"
                r"\bcaseinate\b|\bmaltodextrin\b|\binteresterified\b|\bprotein concentrate\b.*\bmilk\b"),
     (C.EMULSIFIER,)),
    (re.compile(r"\bsugar[- ]free\b|\bno added sugar\b|\bunsweetened\b"), (C.UNKNOWN,)),
    (re.compile(r"\bsyrups?\b|\bsugars?\b|\bnectar\b|\bmolasses\b|\bdextrose\b|\bfructose\b|\bsucrose\b|"
                r"\bglucose\b|\bmaltose\b|\bjuice concentrate\b|\bcaramel\b"),
     (C.ADDED_SUGAR,)),
    (re.compile(r"\bwhole[- ]?(?:grain|wheat|meal)\b|\bwholemeal\b|\bbran\b|\bmillet\b|\boats?\b"),
     (C.FIBER_PROTEIN, C.WHOLE_FOOD)),
    (re.compile(r"\b(?:beans?|lentils?|chickpeas?|legumes?|dal|nuts?|seeds?)\b"),
     (C.FIBER_PROTEIN, C.WHOLE_FOOD)),
    (re.compile(r"\b(?:olive|avocado|canola|rapeseed|flaxseed|walnut)\b.*\boil\b"), (C.HEALTHY_FAT,)),
    (re.compile(r"\boils?\b|\bfats?\b|\bbutter\b|\bmargarine\b"), (C.CULINARY,)),
    (re.compile(r"\bflours?\b|\bstarch\b|\bsalt\b|\bvinegar\b"), (C.CULINARY,)),
    (re.compile(r"\bwater\b|\bacid\b|\bvitamin\b|\bculture[sd]?\b"), (C.NEUTRAL_ADDITIVE,)),
]


def classify_by_pattern(key: str) -> tuple[C, ...] | None:
    """Return categories for a normalized ingredient key, or ``None`` if no rule applies."""
    by_e = classify_e_number(key)
    if by_e:
        return by_e
    non_hydrogenated = bool(_RULES[0][0].search(key))
    for pattern, cats in _RULES[1:]:
        if non_hydrogenated and C.HYDROGENATED_OIL in cats:
            continue
        if pattern.search(key):
            if cats == (C.UNKNOWN,):
                return None
            return cats
    return None
