import pytest

from app.services.normalization import IngredientInputError, normalize_name, parse_ingredients


def keys(text):
    return [p.key for p in parse_ingredients(text)]


@pytest.mark.parametrize("text", ["", "   ", "\n\t", None])
def test_empty_input_is_rejected(text):
    with pytest.raises(IngredientInputError) as exc:
        parse_ingredients(text)
    assert exc.value.code == "empty_input"


@pytest.mark.parametrize("text", ["12345", "!!! ??? ...", "%%%, ###, 42"])
def test_input_without_ingredients_is_rejected(text):
    with pytest.raises(IngredientInputError) as exc:
        parse_ingredients(text)
    assert exc.value.code == "no_ingredients"


def test_too_long_input_is_rejected():
    with pytest.raises(IngredientInputError) as exc:
        parse_ingredients("sugar, " * 1000)
    assert exc.value.code == "input_too_long"


def test_too_many_ingredients_is_rejected():
    with pytest.raises(IngredientInputError) as exc:
        parse_ingredients(", ".join(f"ing{chr(97 + i % 26)}{chr(97 + i // 26)}" for i in range(200)))
    assert exc.value.code == "too_many_ingredients"


def test_case_and_whitespace_differences_normalize_identically():
    a = keys("SUGAR,  Whole Grain OATS , Salt")
    b = keys("sugar, whole grain oats, salt")
    assert a == b == ["sugar", "whole grain oats", "salt"]


def test_positions_are_one_based_and_ordered():
    parsed = parse_ingredients("oats, sugar, salt")
    assert [(p.key, p.position) for p in parsed] == [("oats", 1), ("sugar", 2), ("salt", 3)]


def test_sub_ingredients_inherit_parent_position():
    parsed = parse_ingredients("oats, chocolate chips (sugar, cocoa butter, soy lecithin), salt")
    positions = {p.key: p.position for p in parsed}
    assert positions["sugar"] == positions["cocoa butter"] == positions["soy lecithin"] == 2
    assert positions["salt"] == 3
    assert all(p.parent == "chocolate chips" for p in parsed if p.position == 2)


def test_functional_class_is_replaced_by_named_ingredients():
    assert keys("water, preservative (sodium benzoate), emulsifier: soy lecithin") == [
        "water", "sodium benzoate", "soy lecithin",
    ]


def test_e_number_formats_are_normalized():
    assert keys("E 330, e-211, INS 471, E150d") == ["e330", "e211", "e471", "e150d"]


def test_label_prefix_and_allergen_statement_are_removed():
    text = "Nutrition label\nIngredients: Wheat flour, sugar, salt. Contains: wheat. May contain nuts."
    assert keys(text) == ["wheat flour", "sugar", "salt"]


def test_less_than_two_percent_clause_is_a_separator():
    assert keys("oats, contains 2% or less of: salt, natural flavor") == ["oats", "salt", "natural flavor"]


def test_percentages_asterisks_and_organic_are_stripped():
    assert keys("Organic oats* (45%), cane sugar 10%") == ["oats", "cane sugar"]


def test_british_spellings_and_accents_normalize():
    assert normalize_name("Colour (Caramel)") == "color (caramel)"
    assert normalize_name("Flavouring") == "flavoring"
    assert normalize_name("Crème fraîche") == "creme fraiche"


def test_newline_separated_lists_are_supported():
    assert keys("water\nsugar\nlemon juice") == ["water", "sugar", "lemon juice"]


def test_ocr_hyphenation_across_lines_is_rejoined():
    assert keys("partially hydro-\ngenated soybean oil, salt")[0] == "partially hydrogenated soybean oil"


def test_single_source_annotation_builds_specific_candidate():
    parsed = parse_ingredients("lecithin (soy)")
    assert parsed[0].candidates[0] == "soy lecithin"


def test_trailing_and_is_removed():
    assert keys("sugar, salt, and natural flavor") == ["sugar", "salt", "natural flavor"]


# Real OCR output (Tesseract) from a photo of a cola bottle label: white text on a curved red
# label, with glare noise in other layout segments (tabs mark large horizontal gaps).
COLA_OCR = (
    "; i ag i bi o. cH ce —_.. a8 v ones So t . 3 ot Denes: \\ te.\n"
    "} CLASSIC _\n"
    "J Cola Drink Contains:\tpit \\\n"
    "Carbonated water,\tBe\n"
    "sugar, colour (150d),\tpa 1\n"
    "®\t_ foodacid (338),\tee\n"
    "i\tflavour, caffeine.\tae. oa\n"
    "CONTAINS CAFFEINE.\t3\n"
    "Made in New Zealand .\too t\n"
    "| NUTRITION INFORMATION\t“Pi :\n"
    "Serving size: 250 mL\teee a4\n"
    "o Energy A50kKJ — 5 180kJ 1\n"
)


def test_real_label_ocr_text_is_extracted():
    from app.services.normalization import extract_ingredient_section

    section = extract_ingredient_section(COLA_OCR)
    assert section == "Carbonated water, sugar, colour (150d), food acid (338), flavour, caffeine"
    parsed = parse_ingredients(section)
    assert [p.key for p in parsed] == ["carbonated water", "sugar", "e150d", "e338", "flavor", "caffeine"]
    assert [p.position for p in parsed] == [1, 2, 3, 4, 5, 6]
    assert parsed[2].display == "colour (150d)"
    assert parsed[3].display == "food acid (338)"


@pytest.mark.parametrize("text,expected", [
    ("Colour (150d)", ["e150d"]),
    ("food acid (330)", ["e330"]),
    ("Thickener (1422)", ["e1422"]),
    ("Preservative (211, 202)", ["e211", "e202"]),
    ("Antioxidant (307b)", ["e307b"]),
])
def test_bare_additive_numbers_from_au_nz_labels(text, expected):
    assert keys(text) == expected


def test_contains_label_introduces_list_but_allergen_contains_still_stops_it():
    assert keys("Cola Drink Contains: water, sugar, caffeine") == ["water", "sugar", "caffeine"]
    assert keys("Ingredients: oats, sugar. Contains: gluten") == ["oats", "sugar"]


def test_ocr_section_stops_at_list_end_but_keeps_abbreviations():
    from app.services.normalization import extract_ingredient_section

    assert extract_ingredient_section("Ingredients: water, sugar, red no. 40, salt. Made with love. Keep cool") == (
        "water, sugar, red no. 40, salt"
    )
