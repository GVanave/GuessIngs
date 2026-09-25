import json

import pytest

from app.services.categories import Category as C
from app.services.scoring import (
    ScoringIngredient as I,
)
from app.services.scoring import (
    Verdict,
    score_ingredients,
    sugar_position_deduction,
    verdict_for,
)


def points(result, code):
    return sum(line.points for line in result.lines if line.code == code)


def neutral(n, start=1):
    return [I(f"water{i}", (C.NEUTRAL_ADDITIVE,), start + i) for i in range(n)]


def test_empty_list_raises():
    with pytest.raises(ValueError):
        score_ingredients([])


def test_negative_sodium_raises():
    with pytest.raises(ValueError):
        score_ingredients(neutral(1), sodium_mg_per_100g=-1)


def test_clean_product_scores_100_green():
    r = score_ingredients([I("apple", (C.WHOLE_FOOD,), 1)])
    assert r.score == 100 and r.verdict is Verdict.GREEN and r.nova_group == 1


@pytest.mark.parametrize("position,expected", [(1, 30), (2, 25), (3, 25), (4, 20), (5, 20), (6, 15), (12, 15)])
def test_sugar_position_rules(position, expected):
    assert sugar_position_deduction(position) == expected
    items = neutral(position - 1) + [I("sugar", (C.ADDED_SUGAR,), position)]
    assert points(score_ingredients(items), "added_sugar") == -expected


def test_extra_sugar_sources_add_five_each_and_cap_at_thirty():
    items = neutral(5) + [I("sugar", (C.ADDED_SUGAR,), 6), I("dextrose", (C.ADDED_SUGAR,), 7)]
    assert points(score_ingredients(items), "added_sugar") == -20
    items += [I("honey", (C.ADDED_SUGAR,), 8), I("glucose syrup", (C.ADDED_SUGAR,), 9), I("molasses", (C.ADDED_SUGAR,), 10)]
    assert points(score_ingredients(items), "added_sugar") == -30


def test_artificial_sweeteners_deduct_ten_each():
    r = score_ingredients(neutral(1) + [I("sucralose", (C.ARTIFICIAL_SWEETENER,), 2), I("aspartame", (C.ARTIFICIAL_SWEETENER,), 3)])
    assert points(r, "artificial_sweetener") == -20


def test_hydrogenated_oil_deducts_25_once():
    r = score_ingredients([I("phvo", (C.HYDROGENATED_OIL,), 1), I("hvo", (C.HYDROGENATED_OIL,), 2)])
    assert points(r, "hydrogenated_oil") == -25


def test_artificial_colors_and_flavors_deduct_eight_each():
    r = score_ingredients([I("red 40", (C.ARTIFICIAL_COLOR,), 1), I("yellow 5", (C.ARTIFICIAL_COLOR,), 2),
                           I("artificial flavor", (C.ARTIFICIAL_FLAVOR,), 3)])
    assert points(r, "artificial_color") == -16
    assert points(r, "artificial_flavor") == -8


def test_preservatives_deduct_six_each():
    r = score_ingredients([I("sodium benzoate", (C.PRESERVATIVE,), 1), I("potassium sorbate", (C.PRESERVATIVE,), 2)])
    assert points(r, "preservative") == -12
    assert r.nova_group != 4  # preservatives alone are not NOVA 4 markers


def test_emulsifiers_deduct_five_each_and_trigger_nova4():
    r = score_ingredients([I("oats", (C.WHOLE_FOOD,), 1), I("soy lecithin", (C.EMULSIFIER,), 2), I("xanthan gum", (C.EMULSIFIER,), 3)])
    assert points(r, "emulsifier") == -10
    assert points(r, "nova4") == -20
    assert r.nova_group == 4


@pytest.mark.parametrize("sodium,expected", [(None, 0), (0, 0), (600, 0), (600.1, -10), (1500, -10)])
def test_sodium_only_when_provided_and_above_threshold(sodium, expected):
    assert points(score_ingredients(neutral(1), sodium_mg_per_100g=sodium), "sodium") == expected


def test_fiber_protein_bonus_only_counts_first_five_positions_and_caps():
    items = [I("oats", (C.FIBER_PROTEIN,), 1), I("lentils", (C.FIBER_PROTEIN,), 2), I("chia", (C.FIBER_PROTEIN,), 3)]
    assert points(score_ingredients(items), "fiber_protein") == 10
    late = neutral(5) + [I("oats", (C.FIBER_PROTEIN,), 6)]
    assert points(score_ingredients(late), "fiber_protein") == 0


def test_healthy_fat_bonus_once():
    r = score_ingredients([I("olive oil", (C.HEALTHY_FAT,), 1), I("almonds", (C.HEALTHY_FAT,), 2)])
    assert points(r, "healthy_fat") == 5


def test_score_never_exceeds_100():
    r = score_ingredients([I("oats", (C.FIBER_PROTEIN, C.HEALTHY_FAT), 1), I("nuts", (C.FIBER_PROTEIN,), 2)])
    assert r.raw_score == 115
    assert r.score == 100
    assert any(line.code == "cap" for line in r.lines)
    assert sum(line.points for line in r.lines) == 100


def test_score_never_goes_below_zero():
    items = [
        I("sugar", (C.ADDED_SUGAR,), 1), I("phvo", (C.HYDROGENATED_OIL,), 2),
        I("red 40", (C.ARTIFICIAL_COLOR,), 3), I("yellow 5", (C.ARTIFICIAL_COLOR,), 4),
        I("blue 1", (C.ARTIFICIAL_COLOR,), 5), I("flavor", (C.ARTIFICIAL_FLAVOR,), 6),
        I("sucralose", (C.ARTIFICIAL_SWEETENER,), 7), I("bht", (C.PRESERVATIVE,), 8),
    ]
    r = score_ingredients(items, sodium_mg_per_100g=900)
    assert r.raw_score < 0
    assert r.score == 0 and r.verdict is Verdict.RED
    assert sum(line.points for line in r.lines) == 0


@pytest.mark.parametrize("score,verdict", [
    (100, "GREEN"), (80, "GREEN"), (79, "YELLOW"), (50, "YELLOW"), (49, "RED"), (0, "RED"),
])
def test_verdict_boundaries(score, verdict):
    assert verdict_for(score).value == verdict


@pytest.mark.parametrize("deductions,expected_score,expected_verdict", [
    # 100 - 20 (sugar at pos 4) = 80 → GREEN boundary
    ([("sugar", C.ADDED_SUGAR, 4)], 80, "GREEN"),
    # 100 - 15 (pos 6) - 6 = 79 → YELLOW boundary
    ([("sugar", C.ADDED_SUGAR, 6), ("benzoate", C.PRESERVATIVE, 7)], 79, "YELLOW"),
    # 100 - 25 (hydro) - 5 (emu) - 20 (nova) = 50 → YELLOW lower boundary
    ([("hvo", C.HYDROGENATED_OIL, 5), ("lecithin", C.EMULSIFIER, 6)], 50, "YELLOW"),
    # 100 - 10 (sweetener) - 8 (color) - 8 (flavor) - 5 (emu) - 20 (nova) = 49 → RED upper boundary
    ([("sucralose", C.ARTIFICIAL_SWEETENER, 6), ("red 40", C.ARTIFICIAL_COLOR, 7),
      ("flavor", C.ARTIFICIAL_FLAVOR, 8), ("lecithin", C.EMULSIFIER, 9)], 49, "RED"),
    # 100 - 5 - 8 - 6 - 20 = 61
    ([("lecithin", C.EMULSIFIER, 6), ("red 40", C.ARTIFICIAL_COLOR, 7), ("sorbate", C.PRESERVATIVE, 8),
      ("salt", C.CULINARY, 9)], 61, "YELLOW"),
])
def test_score_boundaries_end_to_end(deductions, expected_score, expected_verdict):
    items = neutral(5) + [I(n, (c,), p) for n, c, p in deductions]
    r = score_ingredients(items)
    assert (r.score, r.verdict.value) == (expected_score, expected_verdict)


def test_duplicates_are_counted_once_at_first_position():
    r = score_ingredients([I("oats", (C.WHOLE_FOOD,), 1), I("sugar", (C.ADDED_SUGAR,), 7), I("sugar", (C.ADDED_SUGAR,), 2)])
    assert points(r, "added_sugar") == -25


def test_unknown_ingredients_do_not_change_score():
    base = score_ingredients([I("oats", (C.FIBER_PROTEIN,), 1)])
    with_unknown = score_ingredients([I("oats", (C.FIBER_PROTEIN,), 1), I("zzz", (C.UNKNOWN,), 2)])
    assert base.score == with_unknown.score


def test_same_input_always_produces_same_result():
    items = [I("sugar", (C.ADDED_SUGAR,), 2), I("oats", (C.FIBER_PROTEIN,), 1), I("bht", (C.PRESERVATIVE,), 3)]
    first = score_ingredients(items).to_dict()
    for _ in range(50):
        assert score_ingredients(list(items)).to_dict() == first
    # Input order does not matter; positions do.
    assert score_ingredients(list(reversed(items))).to_dict() == first


def test_breakdown_sums_to_final_score_and_is_json_serializable():
    items = [I("oats", (C.FIBER_PROTEIN,), 1), I("sugar", (C.ADDED_SUGAR,), 2), I("bht", (C.PRESERVATIVE,), 3)]
    r = score_ingredients(items)
    data = json.loads(json.dumps(r.to_dict()))
    assert sum(line["points"] for line in data["lines"]) == data["score"] == 100 - 25 - 6 + 5
    assert data["lines"][0] == {"code": "start", "label": "Starting score", "points": 100,
                                "detail": "Every product starts at 100.", "ingredients": []}
