import pytest

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Ingredient
from app.services import ai
from app.services.categories import Category as C
from app.services.classifier import classify_all, classify_static
from app.services.knowledge_base import LOOKUP, lookup
from app.services.normalization import parse_ingredients
from app.services.patterns import classify_by_pattern


def static(text):
    return classify_static(parse_ingredients(text)[0])


@pytest.mark.parametrize("alias,canonical", [
    ("sucrose", "sugar"), ("HFCS", "high fructose corn syrup"), ("E211", "sodium benzoate"),
    ("soya lecithin", "soy lecithin"), ("Red 40", "allura red"), ("FD&C Yellow No. 5", "tartrazine"),
    ("E-471", "mono- and diglycerides"), ("INS 330", "citric acid"), ("Extra Virgin Olive Oil", "olive oil"),
    ("garbanzo beans", "chickpeas"), ("Colour (E150d)", "caramel color"), ("Acesulfame-K", "acesulfame potassium"),
])
def test_synonyms_resolve_to_canonical_names(alias, canonical):
    assert static(alias)[0] == canonical


def test_knowledge_base_has_no_conflicting_aliases():
    assert len(LOOKUP) > 400
    assert lookup("  SUGAR ") is not None


@pytest.mark.parametrize("key,expected", [
    ("partially hydrogenated rapeseed oil", (C.HYDROGENATED_OIL,)),
    ("non-hydrogenated palm oil", (C.CULINARY,)),
    ("strawberry flavoring", (C.ARTIFICIAL_FLAVOR,)),
    ("natural strawberry flavor", (C.NEUTRAL_ADDITIVE,)),
    ("tapioca syrup", (C.ADDED_SUGAR,)),
    ("sugar-free gum base", (C.EMULSIFIER,)),
    ("modified waxy maize starch", (C.EMULSIFIER,)),
    ("calcium benzoate", (C.PRESERVATIVE,)),
    ("e999", None),
    ("e129", (C.ARTIFICIAL_COLOR,)),
    ("e202", (C.PRESERVATIVE,)),
    ("e415", (C.EMULSIFIER,)),
    ("e960", (C.ARTIFICIAL_SWEETENER,)),
    ("sprouted whole grain spelt", (C.FIBER_PROTEIN, C.WHOLE_FOOD)),
    ("dragonfruit powder", None),
])
def test_deterministic_patterns(key, expected):
    assert classify_by_pattern(key) == expected


def test_hydrogenated_oil_is_not_confused_with_plain_oil():
    assert static("partially hydrogenated soybean oil")[1] == (C.HYDROGENATED_OIL,)
    assert static("soybean oil")[1] == (C.CULINARY,)


def _db():
    gen = get_db()
    return next(gen), gen


def test_unknown_ingredient_is_reported_and_neutral():
    db, gen = _db()
    outcome = classify_all(db, parse_ingredients("oats, xyzzyberry"))
    assert outcome.items[1].categories == (C.UNKNOWN,)
    assert outcome.items[1].source == "unknown"
    assert any("weren't recognized" in w for w in outcome.warnings)
    db.close()


def test_duplicates_are_flagged_after_classification():
    db, gen = _db()
    outcome = classify_all(db, parse_ingredients("sugar, oats, sucrose, SUGAR"))
    assert [i.is_duplicate for i in outcome.items] == [False, False, True, True]
    db.close()


def test_ai_classifications_are_cached_and_reused(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    calls = []

    def fake_classify(names):
        calls.append(list(names))
        return {n: ai.IngredientClassification(input_name=n, canonical_name="yacon syrup",
                                               categories=["added_sugar"], rationale="A sweet syrup.") for n in names}

    monkeypatch.setattr(ai, "classify", fake_classify)
    db, gen = _db()
    first = classify_all(db, parse_ingredients("oats, yacon nectarine blend"))
    db.commit()
    assert first.ai_used and first.items[1].categories == (C.ADDED_SUGAR,)
    second = classify_all(db, parse_ingredients("oats, yacon nectarine blend"))
    assert len(calls) == 1  # served from cache the second time
    assert second.items[1].categories == first.items[1].categories
    assert db.query(Ingredient).filter_by(name="yacon nectarine blend", source="ai").count() == 1
    db.close()


def test_ai_failure_falls_back_gracefully(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()

    def boom(names):
        raise ai.AIError("down")

    monkeypatch.setattr(ai, "classify", boom)
    db, gen = _db()
    outcome = classify_all(db, parse_ingredients("oats, mystery powder"))
    assert outcome.items[1].categories == (C.UNKNOWN,)
    assert any("temporarily unavailable" in w for w in outcome.warnings)
    db.close()


def test_ai_is_never_called_when_disabled(monkeypatch):
    monkeypatch.setattr(ai, "classify", lambda names: pytest.fail("AI must not be called"))
    db, gen = _db()
    classify_all(db, parse_ingredients("mystery powder"))
    db.close()
