"""Ingredient categories shared by the classifier, the AI layer and the scoring engine."""

from enum import Enum


class Category(str, Enum):
    ADDED_SUGAR = "added_sugar"
    ARTIFICIAL_SWEETENER = "artificial_sweetener"
    HYDROGENATED_OIL = "hydrogenated_oil"
    ARTIFICIAL_COLOR = "artificial_color"
    ARTIFICIAL_FLAVOR = "artificial_flavor"
    PRESERVATIVE = "preservative"
    # Emulsifiers, thickeners, modified starches and other industrial
    # ultra-processing markers.
    EMULSIFIER = "emulsifier"
    FIBER_PROTEIN = "fiber_protein"
    HEALTHY_FAT = "healthy_fat"
    WHOLE_FOOD = "whole_food"
    # Salt, oils, butter, vinegar … (NOVA group 2 "processed culinary ingredients")
    CULINARY = "culinary"
    # Known additive that carries no penalty (e.g. citric acid, baking soda).
    NEUTRAL_ADDITIVE = "neutral_additive"
    UNKNOWN = "unknown"


# Categories that make a product NOVA 4 (ultra-processed) when present.
NOVA4_CATEGORIES = frozenset(
    {
        Category.ARTIFICIAL_SWEETENER,
        Category.HYDROGENATED_OIL,
        Category.ARTIFICIAL_COLOR,
        Category.ARTIFICIAL_FLAVOR,
        Category.EMULSIFIER,
    }
)

CATEGORY_LABELS: dict[Category, str] = {
    Category.ADDED_SUGAR: "Added sugar",
    Category.ARTIFICIAL_SWEETENER: "Artificial sweetener",
    Category.HYDROGENATED_OIL: "Hydrogenated oil",
    Category.ARTIFICIAL_COLOR: "Artificial color",
    Category.ARTIFICIAL_FLAVOR: "Artificial flavor",
    Category.PRESERVATIVE: "Preservative",
    Category.EMULSIFIER: "Emulsifier / ultra-processed marker",
    Category.FIBER_PROTEIN: "Whole-food fiber/protein source",
    Category.HEALTHY_FAT: "Healthy fat source",
    Category.WHOLE_FOOD: "Whole food",
    Category.CULINARY: "Culinary ingredient",
    Category.NEUTRAL_ADDITIVE: "Common additive",
    Category.UNKNOWN: "Unrecognized",
}

NEGATIVE_CATEGORIES = frozenset(
    {
        Category.ADDED_SUGAR,
        Category.ARTIFICIAL_SWEETENER,
        Category.HYDROGENATED_OIL,
        Category.ARTIFICIAL_COLOR,
        Category.ARTIFICIAL_FLAVOR,
        Category.PRESERVATIVE,
        Category.EMULSIFIER,
    }
)
POSITIVE_CATEGORIES = frozenset({Category.FIBER_PROTEIN, Category.HEALTHY_FAT})
