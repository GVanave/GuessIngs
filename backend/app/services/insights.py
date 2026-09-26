"""Deterministic explanations, ingredient highlights and better alternatives."""

from __future__ import annotations

import re

from app.services.categories import CATEGORY_LABELS, NEGATIVE_CATEGORIES, POSITIVE_CATEGORIES, Category

CONCERN_REASONS: dict[Category, str] = {
    Category.ADDED_SUGAR: "Added sugar adds calories without nutrients; the earlier it appears, the more there is.",
    Category.ARTIFICIAL_SWEETENER: "Non-nutritive sweetener; may affect appetite and gut comfort in some people.",
    Category.HYDROGENATED_OIL: "Hydrogenated fats can contain trans fats, which raise LDL cholesterol.",
    Category.ARTIFICIAL_COLOR: "Synthetic color with no nutritional value; some are linked to hyperactivity in children.",
    Category.ARTIFICIAL_FLAVOR: "Added flavoring or enhancer used to mimic or intensify taste.",
    Category.PRESERVATIVE: "Chemical preservative used to extend shelf life.",
    Category.EMULSIFIER: "Emulsifier, thickener or industrial ingredient typical of ultra-processed food.",
}
POSITIVE_REASONS: dict[Category, str] = {
    Category.FIBER_PROTEIN: "Whole-food source of fiber and/or protein.",
    Category.HEALTHY_FAT: "Source of mostly unsaturated, heart-friendly fats.",
    Category.WHOLE_FOOD: "Minimally processed whole food.",
}


def concerns(ingredients: list[dict]) -> list[dict]:
    out = []
    for ing in ingredients:
        if ing["is_duplicate"]:
            continue
        cats = [Category(c) for c in ing["categories"]]
        bad = [c for c in cats if c in NEGATIVE_CATEGORIES]
        if bad:
            out.append(
                {
                    "name": ing["display_name"],
                    "canonical_name": ing["canonical_name"],
                    "position": ing["position"],
                    "categories": [c.value for c in bad],
                    "labels": [CATEGORY_LABELS[c] for c in bad],
                    "reason": CONCERN_REASONS[bad[0]],
                }
            )
    return out


def positives(ingredients: list[dict]) -> list[dict]:
    out = []
    for ing in ingredients:
        if ing["is_duplicate"]:
            continue
        cats = [Category(c) for c in ing["categories"]]
        if any(c in NEGATIVE_CATEGORIES for c in cats):
            continue
        good = [c for c in cats if c in POSITIVE_CATEGORIES or c == Category.WHOLE_FOOD]
        if good:
            primary = next((c for c in good if c in POSITIVE_CATEGORIES), good[0])
            out.append(
                {
                    "name": ing["display_name"],
                    "canonical_name": ing["canonical_name"],
                    "position": ing["position"],
                    "categories": [c.value for c in good],
                    "labels": [CATEGORY_LABELS[c] for c in good],
                    "reason": POSITIVE_REASONS[primary],
                }
            )
    return out


VERDICT_HEADLINES = {
    "GREEN": "A good choice based on its ingredients.",
    "YELLOW": "An okay choice — fine occasionally, but there are better options.",
    "RED": "Best limited — this product has several ingredients of concern.",
}


def build_explanation(score: int, verdict: str, nova_group: int, lines: list[dict]) -> dict:
    deductions = sorted((ln for ln in lines if ln["points"] < 0 and ln["code"] not in ("cap",)), key=lambda ln: ln["points"])
    bonuses = [ln for ln in lines if ln["points"] > 0 and ln["code"] not in ("start", "floor")]
    factors = [f"{ln['label']} ({ln['points']:+d})" for ln in deductions if ln["code"] != "floor"]
    parts = [f"This product scored {score}/100, which is {verdict}."]
    if factors:
        parts.append("The biggest factors lowering the score: " + ", ".join(factors[:3]) + ".")
    else:
        parts.append("No ingredients of concern were found.")
    if bonuses:
        parts.append("It earns points for: " + ", ".join(f"{b['label'].lower()} ({b['points']:+d})" for b in bonuses) + ".")
    if nova_group == 4:
        parts.append("Its ingredients indicate an ultra-processed food (NOVA group 4).")
    return {
        "headline": VERDICT_HEADLINES[verdict],
        "summary": " ".join(parts),
        "ai_summary": None,
        "key_factors": [ln["label"] for ln in deductions[:3] if ln["code"] != "floor"],
    }


# ------------------------------------------------------------- alternatives --
PRODUCT_TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("snack_bar", re.compile(r"\b(bar|bars|protein bar|granola bar|energy bar)\b")),
    ("soft_drink", re.compile(r"\b(soda|cola|coke|pepsi|soft drink|energy drink|lemonade|carbonated|fizzy)\b")),
    ("breakfast_cereal", re.compile(r"\b(cereal|flakes|granola|muesli|loops|puffs|corn flakes)\b")),
    ("cookies", re.compile(r"\b(cookie|cookies|biscuit|biscuits|cracker|crackers|wafer)\b")),
    ("chips", re.compile(r"\b(chips|crisps|nachos|puffs|namkeen|bhujia)\b")),
    ("chocolate", re.compile(r"\b(chocolate|candy|confection|gummy|gummies|toffee)\b")),
    ("yogurt", re.compile(r"\b(yogurt|yoghurt|curd|dahi|skyr)\b")),
    ("bread", re.compile(r"\b(bread|bun|buns|loaf|roll|rolls|tortilla|wrap|pita)\b")),
    ("noodles", re.compile(r"\b(noodles|ramen|instant noodles|pasta|macaroni|spaghetti)\b")),
    ("sauce", re.compile(r"\b(sauce|ketchup|dressing|mayonnaise|mayo|spread|dip|salsa)\b")),
    ("ice_cream", re.compile(r"\b(ice cream|frozen dessert|gelato|kulfi)\b")),
    ("juice", re.compile(r"\b(juice|nectar|fruit drink|smoothie)\b")),
    ("nut_butter", re.compile(r"\b(peanut butter|almond butter|nut butter|hazelnut spread)\b")),
]

TYPE_LABELS = {
    "soft_drink": "Soft drink", "breakfast_cereal": "Breakfast cereal", "snack_bar": "Snack bar",
    "cookies": "Cookies & crackers", "chips": "Chips & savory snacks", "chocolate": "Chocolate & candy",
    "yogurt": "Yogurt", "bread": "Bread & wraps", "noodles": "Noodles & pasta", "sauce": "Sauces & spreads",
    "ice_cream": "Ice cream", "juice": "Juice", "nut_butter": "Nut butter", "other": "Packaged food",
}

SWAPS: dict[str, list[tuple[str, str]]] = {
    "soft_drink": [("Sparkling water with citrus", "Same fizz with no sugar or sweeteners."),
                   ("Unsweetened iced tea", "Flavorful and naturally low in calories.")],
    "breakfast_cereal": [("Plain rolled oats with fruit", "Whole grain fiber; you control the sweetness."),
                         ("Unsweetened muesli", "Whole grains, nuts and seeds without added sugar.")],
    "snack_bar": [("Nut & date bar (≤5 ingredients)", "Whole-food ingredients, no syrups or isolates."),
                  ("A handful of nuts and a piece of fruit", "Protein, healthy fat and fiber.")],
    "cookies": [("Whole-grain crackers with short ingredient lists", "More fiber, less sugar."),
                ("Oat-based cookies without hydrogenated fat", "Look for whole oats as the first ingredient.")],
    "chips": [("Roasted chickpeas or makhana", "Crunchy, with protein and fiber."),
              ("Plain popcorn", "A whole grain with a simple ingredient list.")],
    "chocolate": [("Dark chocolate (70%+ cocoa)", "Cocoa first, less sugar, fewer additives."),
                  ("Dates or dried fruit with nuts", "Naturally sweet whole foods.")],
    "yogurt": [("Plain unsweetened yogurt with fresh fruit", "Protein without added sugar or thickeners.")],
    "bread": [("100% whole-wheat or whole-grain bread", "Whole grain listed first, no preservatives."),
              ("Sourdough from a bakery", "Short ingredient list: flour, water, salt.")],
    "noodles": [("Whole-wheat or millet noodles", "More fiber and no flavor-enhancer sachet."),
                ("Legume pasta (lentil or chickpea)", "Higher protein and fiber.")],
    "sauce": [("Olive-oil based dressings", "Healthy fats, fewer additives."),
              ("Homemade salsa or chutney", "Fresh vegetables without preservatives.")],
    "ice_cream": [("Frozen banana 'nice cream'", "Just fruit, naturally sweet."),
                  ("Ice cream with a short ingredient list", "Milk, cream, sugar — no gums or colors.")],
    "juice": [("Whole fruit", "Keeps the fiber that juice removes."),
              ("Water infused with fruit slices", "Flavor without concentrated sugar.")],
    "nut_butter": [("100% nut butter (just nuts, maybe salt)", "No hydrogenated oil or added sugar.")],
    "other": [("Look for a shorter ingredient list", "Fewer additives usually means less processing."),
              ("Choose whole-food ingredients first", "Whole grains, legumes, nuts or vegetables near the top.")],
}

RULE_TIPS = {
    "added_sugar": ("Choose an unsweetened version", "Sugar is a top ingredient here; unsweetened options avoid that deduction."),
    "artificial_sweetener": ("Pick products without sweeteners", "Lightly sweetened with fruit is a better option."),
    "hydrogenated_oil": ("Avoid hydrogenated fats", "Look for olive, canola or sunflower oil instead."),
    "artificial_color": ("Skip artificial colors", "Choose products colored with foods like beet or turmeric, or none at all."),
    "artificial_flavor": ("Prefer natural flavors", "Products flavored with real ingredients score better."),
    "preservative": ("Try fresher alternatives", "Refrigerated or bakery versions often skip preservatives."),
    "nova4": ("Go less processed", "Minimally processed foods avoid the ultra-processed penalty."),
    "sodium": ("Look for low-sodium options", "Aim for under 600 mg sodium per 100 g."),
}


def detect_product_type(product_name: str, ingredient_keys: list[str]) -> str:
    haystack = product_name.lower()
    for type_code, pattern in PRODUCT_TYPES:
        if pattern.search(haystack):
            return type_code
    joined = " ".join(ingredient_keys[:3])
    if "carbonated water" in joined:
        return "soft_drink"
    return "other"


def build_alternatives(product_type: str, verdict: str, lines: list[dict]) -> list[dict]:
    items: list[dict] = []
    if verdict != "GREEN" or product_type != "other":
        for title, desc in SWAPS.get(product_type, SWAPS["other"]):
            items.append({"kind": "swap", "title": title, "description": desc})
    codes = [ln["code"] for ln in sorted(lines, key=lambda ln: ln["points"]) if ln["points"] < 0]
    for code in codes:
        if code in RULE_TIPS and len([i for i in items if i["kind"] == "tip"]) < 3:
            title, desc = RULE_TIPS[code]
            items.append({"kind": "tip", "title": title, "description": desc})
    return items
