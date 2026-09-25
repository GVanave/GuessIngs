"""Deterministic ingredient-list parsing and normalization.

Turns free text (typed by a user or produced by OCR/AI extraction) into an
ordered list of ``ParsedIngredient`` objects. Parsing rules:

* Anything before an ``Ingredients:`` label is dropped, and allergen /
  nutrition / storage statements after the list are cut off.
* Top-level items are split on commas or semicolons (or on new lines when the
  text has no commas at all). Their 1-based index is the ingredient *position*.
* Parenthesised sub-ingredients (``chocolate chips (sugar, cocoa butter)``)
  are flattened and inherit the position of their parent.
* Functional class names (``emulsifier (soy lecithin)``) are replaced by the
  specific ingredients they name.
* Case, accents, percentages, E-number formats and British spellings are
  normalized so that equivalent inputs always produce identical keys.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MAX_TEXT_LENGTH = 5000
MAX_INGREDIENTS = 150
MAX_ITEM_LENGTH = 120


class IngredientInputError(ValueError):
    """Raised when the ingredient text cannot be parsed into ingredients."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ParsedIngredient:
    display: str
    candidates: list[str]
    position: int
    parent: str | None = None
    hints: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.candidates[0]


FUNCTIONAL_CLASSES = {
    "emulsifier", "emulsifiers", "emulsifying agent", "emulsifying agents",
    "preservative", "preservatives", "class ii preservative", "class ii preservatives",
    "color", "colors", "coloring", "food color", "food colors", "permitted synthetic food color",
    "permitted natural color", "color added", "colors added",
    "acidity regulator", "acidity regulators", "acidulant", "acidulants", "acid", "acids",
    "thickener", "thickeners", "thickening agent", "thickening agents",
    "stabilizer", "stabilizers", "gelling agent", "gelling agents",
    "sweetener", "sweeteners", "artificial sweetener", "artificial sweeteners",
    "antioxidant", "antioxidants", "raising agent", "raising agents",
    "leavening agent", "leavening agents", "flavor enhancer", "flavor enhancers",
    "humectant", "humectants", "anti-caking agent", "anti-caking agents", "anticaking agent",
    "firming agent", "glazing agent", "dough conditioner", "dough conditioners",
    "flour treatment agent", "vitamins", "minerals", "vitamin", "mineral",
    "to preserve freshness", "for freshness", "as a preservative", "preserved with",
    "to maintain freshness", "to protect flavor", "to protect freshness", "for color",
    "added for color", "a preservative", "an emulsifier", "stabilizers and thickeners",
    "emulsifier and stabilizer", "emulsifiers and stabilizers", "firming agents",
}

_SPELLING = [
    (r"colour", "color"),
    (r"flavour", "flavor"),
    (r"fibre", "fiber"),
    (r"stabilis", "stabiliz"),
    (r"emulsifi", "emulsifi"),
    (r"yoghurt", "yogurt"),
    (r"hydrolysed", "hydrolyzed"),
    (r"autolysed", "autolyzed"),
    (r"sulphite", "sulfite"),
    (r"sulphur", "sulfur"),
    (r"aluminium", "aluminum"),
]

_STOP_PATTERN = re.compile(
    r"(?:^|[.\n;])\s*(?:allergy advice|allergy information|allergens?\b|contains\s*:|"
    r"contains (?:milk|soy|soya|wheat|eggs?|tree nuts?|nuts?|peanuts?|fish|shellfish|sesame|gluten|mustard|celery)\b|"
    r"may contain|may also contain|made in a facility|produced in a facility|nutrition(?:al)? (?:facts|information)|"
    r"best before|use by|manufactured (?:by|for)|marketed by|packed by|store in|storage|keep refrigerated|"
    r"net (?:wt|weight|quantity)|distributed by|directions)",
    re.IGNORECASE,
)
_LABEL_PATTERN = re.compile(r"\bingredients?\s*(?:list)?\s*[:\-–]", re.IGNORECASE)
_LESS_THAN_PATTERN = re.compile(
    r"(?:contains\s+)?(?:less than|<)\s*\d+(?:\.\d+)?\s*%\s*(?:or less\s*)?(?:of\s*)?(?:each\s+of\s+)?(?:the following\s*)?:?"
    r"|contains\s+\d+(?:\.\d+)?\s*%\s*or\s+less\s+of\s*(?:the following\s*)?:?"
    r"|\d+(?:\.\d+)?\s*%\s*or\s+less\s+of\s*(?:the following\s*)?:?"
    r"|contains one or more of the following\s*:?",
    re.IGNORECASE,
)
_E_NUMBER = re.compile(r"\b(?:e|ins)\s*[-.]?\s*(\d{3,4})\s*([a-z]{0,3}|\([ivx]+\))?\b", re.IGNORECASE)
_PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*%")


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize_name(text: str) -> str:
    """Produce the canonical lookup key for a single ingredient name."""
    t = _strip_accents(unicodedata.normalize("NFKC", text)).lower()
    for pat, repl in _SPELLING:
        t = re.sub(pat, repl, t)
    t = _PERCENT.sub(" ", t)
    t = _E_NUMBER.sub(lambda m: f"e{m.group(1)}{(m.group(2) or '').strip('()')}", t)
    t = re.sub(r"[*†‡^•·®™©\"“”‘’`]", " ", t)
    t = re.sub(r"\b(?:certified\s+)?organic\b|\bnon[- ]?gmo\b|\bgmo[- ]free\b|\bnon[- ]genetically modified\b", " ", t)
    t = re.sub(r"\s*&\s*", " & ", t)
    t = re.sub(r"\s+", " ", t)
    t = t.strip(" .:;,-–_/\\'")
    t = re.sub(r"^(?:and|&|or)\s+", "", t)
    t = re.sub(r"\s+(?:and|&|or)$", "", t)
    return t.strip()


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    # Re-join words hyphenated across OCR line breaks.
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    label = _LABEL_PATTERN.search(text)
    if label:
        text = text[label.end():]
    stop = _STOP_PATTERN.search(text)
    if stop and stop.start() > 0:
        text = text[: stop.start()]
    text = _LESS_THAN_PATTERN.sub(",", text)
    text = text.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    return text


def _split_top_level(text: str, separators: str = ",;") -> list[str]:
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in separators and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _split_parenthetical(item: str) -> tuple[str, str | None, str]:
    """Split ``parent (inner) trailing`` → (parent, inner, trailing)."""
    start = item.find("(")
    if start == -1:
        return item, None, ""
    depth = 0
    for i in range(start, len(item)):
        if item[i] == "(":
            depth += 1
        elif item[i] == ")":
            depth -= 1
            if depth == 0:
                return item[:start], item[start + 1 : i], item[i + 1 :]
    # Unbalanced parenthesis: treat the rest as inner content.
    return item[:start], item[start + 1 :], ""


def _is_annotation(text: str) -> bool:
    key = normalize_name(text)
    if not key:
        return True
    if key in FUNCTIONAL_CLASSES:
        return True
    if re.fullmatch(r"e\d{3,4}[a-z]{0,3}", key):
        return True
    if re.fullmatch(r"[\d\s.,%<>]+", key):
        return True
    if re.match(r"^(?:from|contains|with|made from|derived from|source of|for|as|to|added)\b", key):
        return True
    return False


def _head_noun(text: str) -> str:
    words = normalize_name(text).split()
    return words[-1] if words else ""


def _has_letters(text: str) -> bool:
    return len(re.findall(r"[a-z]", text)) >= 2 or bool(re.fullmatch(r"e\d{3,4}[a-z]{0,3}", text))


# Generic head nouns that sub-ingredients can be combined with:
# "vegetable oil (sunflower, canola)" → "sunflower oil", "canola oil".
_GENERIC_NOUNS = {"oil", "oils", "fat", "fats", "flour", "flours", "starch", "lecithin", "protein",
                  "fiber", "syrup", "gum", "gums", "seeds", "nuts", "milk", "vinegar"}


def _expand(item: str, position: int, parent: str | None, out: list[ParsedIngredient]) -> None:
    # "Emulsifier: soy lecithin" → "soy lecithin"
    colon = re.match(r"^\s*([^:()]{2,40}):\s*(.+)$", item)
    if colon and normalize_name(colon.group(1)) in FUNCTIONAL_CLASSES:
        item = colon.group(2)

    head, inner, trailing = _split_parenthetical(item)
    head_key = normalize_name(head + (" " + trailing if trailing.strip() else ""))

    if inner is None:
        if head_key and _has_letters(head_key):
            out.append(ParsedIngredient(item.strip(), [head_key], position, parent))
        return

    inner_parts = _split_top_level(inner)
    annotations = [p for p in inner_parts if _is_annotation(p)]
    children = [p for p in inner_parts if not _is_annotation(p)]
    hints = [normalize_name(a) for a in annotations if re.fullmatch(r"e\d{3,4}[a-z]{0,3}", normalize_name(a))]

    if head_key in FUNCTIONAL_CLASSES or not head_key:
        for child in children:
            _expand(child, position, parent, out)
        for hint in hints if not children else []:
            out.append(ParsedIngredient(hint.upper(), [hint], position, parent))
        return

    if not children:
        out.append(ParsedIngredient(item.strip(), [head_key, *hints], position, parent, hints))
        return

    if len(children) == 1 and len(normalize_name(children[0]).split()) <= 2 and "(" not in children[0]:
        # "lecithin (soy)", "vegetable oil (palm)", "cheese (milk)"
        child_key = normalize_name(children[0])
        noun = _head_noun(head_key)
        candidates = [f"{child_key} {head_key}", f"{child_key} {noun}", head_key, child_key, *hints]
        seen: list[str] = []
        for c in candidates:
            if c and c not in seen:
                seen.append(c)
        out.append(ParsedIngredient(item.strip(), seen, position, parent, hints))
        return

    # Compound ingredient: flatten its sub-ingredients under the parent's position.
    noun = _head_noun(head_key)
    before = len(out)
    for child in children:
        _expand(child, position, head.strip() or parent, out)
    # "vegetable oil (sunflower, canola)" → try "sunflower oil", "canola oil"
    for parsed in out[before:]:
        combo = f"{parsed.key} {noun.rstrip('s') if noun in ('oils', 'fats', 'flours', 'gums') else noun}"
        if noun in _GENERIC_NOUNS and not parsed.key.endswith(noun) and combo not in parsed.candidates:
            parsed.candidates.append(combo)


def parse_ingredients(text: str | None) -> list[ParsedIngredient]:
    """Parse raw ingredient text into ordered, flattened ingredients (not yet de-duplicated)."""
    if text is None or not text.strip():
        raise IngredientInputError("empty_input", "Please enter an ingredient list.")
    if len(text) > MAX_TEXT_LENGTH:
        raise IngredientInputError(
            "input_too_long",
            f"The ingredient list is too long (maximum {MAX_TEXT_LENGTH} characters).",
        )
    cleaned = _clean_text(text)
    if "," in cleaned or ";" in cleaned:
        flat = re.sub(r"\s*\n\s*", " ", cleaned)
        items = _split_top_level(flat)
    else:
        items = [line for line in (ln.strip() for ln in cleaned.splitlines()) if line]
        if len(items) == 1:
            items = _split_top_level(items[0])

    parsed: list[ParsedIngredient] = []
    position = 0
    for item in items:
        if not _has_letters(normalize_name(item)):
            continue
        position += 1
        before = len(parsed)
        _expand(item, position, None, parsed)
        if len(parsed) == before:
            position -= 1

    if not parsed:
        raise IngredientInputError(
            "no_ingredients",
            "We couldn't find any ingredients in that text. Separate ingredients with commas.",
        )
    for p in parsed:
        if len(p.key) > MAX_ITEM_LENGTH:
            raise IngredientInputError(
                "unparseable_input",
                "Some text doesn't look like an ingredient list. Separate ingredients with commas.",
            )
    if len(parsed) > MAX_INGREDIENTS:
        raise IngredientInputError(
            "too_many_ingredients",
            f"That list has more than {MAX_INGREDIENTS} ingredients. Please check the text.",
        )
    return parsed


def extract_ingredient_section(text: str) -> str:
    """Return the ingredient section of a label text (label prefix and trailing statements removed)."""
    return " ".join(_clean_text(text).split())
