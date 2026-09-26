"""Curated ingredient knowledge base.

Every entry maps a canonical ingredient name to its categories, plus the
synonyms / E-numbers that normalize to it. The knowledge base is the first and
authoritative classification source: AI classification is only consulted for
ingredients that are not covered here or by the deterministic patterns.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.categories import Category as C
from app.services.normalization import normalize_name

KB_VERSION = "kb-2026.09"


@dataclass(frozen=True)
class KBEntry:
    canonical: str
    categories: tuple[C, ...]
    synonyms: tuple[str, ...] = ()


_ENTRIES: list[KBEntry] = []


def _add(canonical: str, categories: tuple[C, ...] | C, *synonyms: str) -> None:
    cats = categories if isinstance(categories, tuple) else (categories,)
    _ENTRIES.append(KBEntry(canonical, cats, tuple(synonyms)))


S, SW, HY, COL, FLA, PRE, EMU = (
    C.ADDED_SUGAR,
    C.ARTIFICIAL_SWEETENER,
    C.HYDROGENATED_OIL,
    C.ARTIFICIAL_COLOR,
    C.ARTIFICIAL_FLAVOR,
    C.PRESERVATIVE,
    C.EMULSIFIER,
)
FP, HF, WF, CU, NA = C.FIBER_PROTEIN, C.HEALTHY_FAT, C.WHOLE_FOOD, C.CULINARY, C.NEUTRAL_ADDITIVE

# --- Added sugars & syrups ---------------------------------------------------
_add("sugar", (S, CU), "sucrose", "cane sugar", "white sugar", "granulated sugar", "beet sugar",
     "raw sugar", "raw cane sugar", "evaporated cane juice", "cane juice", "table sugar",
     "powdered sugar", "icing sugar", "caster sugar", "unrefined sugar", "demerara sugar",
     "turbinado sugar", "muscovado sugar", "coconut sugar", "palm sugar", "jaggery")
_add("brown sugar", (S, CU), "light brown sugar", "dark brown sugar")
_add("glucose syrup", S, "glucose", "glucose-fructose syrup", "glucose fructose syrup",
     "corn syrup", "corn syrup solids", "glucose syrup solids", "liquid glucose")
_add("high fructose corn syrup", (S, EMU), "hfcs", "high-fructose corn syrup", "isoglucose",
     "fructose-glucose syrup", "fructose glucose syrup")
_add("fructose", S, "crystalline fructose", "fruit sugar")
_add("dextrose", S, "dextrose monohydrate", "corn sugar")
_add("maltose", S, "malt sugar")
_add("invert sugar", S, "invert sugar syrup", "inverted sugar syrup", "golden syrup")
_add("honey", (S, CU), "raw honey")
_add("maple syrup", (S, CU), "pure maple syrup")
_add("agave syrup", S, "agave nectar", "agave")
_add("molasses", S, "blackstrap molasses", "treacle")
_add("rice syrup", S, "brown rice syrup", "rice malt syrup")
_add("malt syrup", S, "barley malt syrup", "malt extract", "barley malt extract")
_add("date syrup", S)
_add("fruit juice concentrate", S, "apple juice concentrate", "grape juice concentrate",
     "pear juice concentrate", "concentrated fruit juice", "fruit concentrate")
_add("lactose", S, "milk sugar")
_add("caramel", S, "caramel syrup")
_add("maltodextrin", (S, EMU), "maltodextrins")

# --- Artificial / non-nutritive sweeteners -----------------------------------
_add("aspartame", SW, "e951")
_add("sucralose", SW, "e955")
_add("acesulfame potassium", SW, "acesulfame k", "acesulfame-k", "ace-k", "e950")
_add("saccharin", SW, "sodium saccharin", "e954")
_add("cyclamate", SW, "sodium cyclamate", "e952")
_add("neotame", SW, "e961")
_add("advantame", SW, "e969")
_add("sorbitol", SW, "e420")
_add("maltitol", SW, "e965", "maltitol syrup")
_add("xylitol", SW, "e967")
_add("erythritol", SW, "e968")
_add("isomalt", SW, "e953")
_add("mannitol", SW, "e421")
_add("lactitol", SW, "e966")
_add("steviol glycosides", SW, "e960", "stevia extract", "reb a", "rebaudioside a", "stevia")

# --- Hydrogenated fats ------------------------------------------------------
_add("partially hydrogenated vegetable oil", HY, "partially hydrogenated oil",
     "partially hydrogenated soybean oil", "partially hydrogenated cottonseed oil",
     "partially hydrogenated palm oil", "partially hydrogenated canola oil",
     "partially hydrogenated palm kernel oil", "partially hydrogenated coconut oil")
_add("hydrogenated vegetable oil", HY, "hydrogenated oil", "hydrogenated soybean oil",
     "hydrogenated palm oil", "hydrogenated palm kernel oil", "hydrogenated cottonseed oil",
     "hydrogenated coconut oil", "hydrogenated rapeseed oil", "hydrogenated vegetable fat",
     "vanaspati", "shortening", "vegetable shortening", "hydrogenated fat")
_add("interesterified fat", (EMU,), "interesterified vegetable oil", "interesterified oil")

# --- Artificial colors ------------------------------------------------------
_add("allura red", COL, "red 40", "fd&c red no. 40", "fd&c red 40", "red no. 40", "red 40 lake",
     "e129", "allura red ac")
_add("tartrazine", COL, "yellow 5", "fd&c yellow no. 5", "fd&c yellow 5", "yellow no. 5",
     "yellow 5 lake", "e102")
_add("sunset yellow", COL, "yellow 6", "fd&c yellow no. 6", "fd&c yellow 6", "yellow no. 6",
     "yellow 6 lake", "e110", "sunset yellow fcf")
_add("brilliant blue", COL, "blue 1", "fd&c blue no. 1", "fd&c blue 1", "blue no. 1",
     "blue 1 lake", "e133", "brilliant blue fcf")
_add("indigo carmine", COL, "blue 2", "fd&c blue no. 2", "blue no. 2", "e132", "indigotine")
_add("erythrosine", COL, "red 3", "fd&c red no. 3", "red no. 3", "e127")
_add("fast green", COL, "green 3", "fd&c green no. 3", "e143")
_add("ponceau 4r", COL, "e124", "cochineal red a")
_add("carmoisine", COL, "e122", "azorubine")
_add("quinoline yellow", COL, "e104")
_add("caramel color", COL, "caramel colour", "caramel coloring", "e150", "e150a", "e150b",
     "e150c", "e150d", "caramel color iv", "sulphite ammonia caramel")
_add("titanium dioxide", COL, "e171")
_add("artificial color", COL, "artificial colors", "artificial colour", "artificial colours",
     "artificial coloring", "color added", "colour added", "artificial food coloring")

# --- Artificial flavors & enhancers -----------------------------------------
_add("artificial flavor", FLA, "artificial flavors", "artificial flavour", "artificial flavours",
     "artificial flavoring", "artificial flavouring", "nature identical flavor",
     "nature identical flavouring", "nature-identical flavoring substances", "flavouring",
     "flavoring", "flavourings", "flavorings", "added flavor", "added flavors")
_add("vanillin", FLA, "ethyl vanillin", "artificial vanilla", "vanillin (artificial flavor)")
_add("monosodium glutamate", FLA, "msg", "e621", "flavour enhancer e621", "sodium glutamate")
_add("disodium inosinate", FLA, "e631")
_add("disodium guanylate", FLA, "e627")
_add("disodium ribonucleotides", FLA, "e635")
_add("natural flavor", NA, "natural flavors", "natural flavour", "natural flavours",
     "natural flavoring", "natural flavouring", "natural vanilla flavor")
_add("vanilla extract", WF, "pure vanilla extract", "vanilla", "vanilla bean", "vanilla beans")

# --- Preservatives ----------------------------------------------------------
_add("sodium benzoate", PRE, "e211")
_add("potassium benzoate", PRE, "e212")
_add("benzoic acid", PRE, "e210")
_add("potassium sorbate", PRE, "e202")
_add("sorbic acid", PRE, "e200")
_add("calcium sorbate", PRE, "e203")
_add("calcium propionate", PRE, "e282")
_add("sodium propionate", PRE, "e281")
_add("propionic acid", PRE, "e280")
_add("sodium nitrite", PRE, "e250")
_add("sodium nitrate", PRE, "e251")
_add("potassium nitrate", PRE, "e252")
_add("sulfur dioxide", PRE, "sulphur dioxide", "e220")
_add("sodium metabisulfite", PRE, "sodium metabisulphite", "e223")
_add("potassium metabisulfite", PRE, "potassium metabisulphite", "e224")
_add("sodium sulfite", PRE, "sodium sulphite", "e221")
_add("bha", PRE, "butylated hydroxyanisole", "e320")
_add("bht", PRE, "butylated hydroxytoluene", "e321")
_add("tbhq", PRE, "tertiary butylhydroquinone", "tert-butylhydroquinone", "e319")
_add("propyl gallate", PRE, "e310")
_add("edta", PRE, "calcium disodium edta", "disodium edta", "e385")
_add("nisin", PRE, "e234")
_add("natamycin", PRE, "e235")
_add("methylparaben", PRE, "e218")

# --- Emulsifiers, thickeners, industrial markers ---------------------------
_add("lecithin", EMU, "e322", "e322i")
_add("soy lecithin", EMU, "soya lecithin", "soybean lecithin", "lecithin (soy)", "lecithin (soya)")
_add("sunflower lecithin", EMU, "lecithin (sunflower)")
_add("mono- and diglycerides", EMU, "mono and diglycerides", "mono & diglycerides",
     "mono and diglycerides of fatty acids", "mono- and diglycerides of fatty acids", "e471",
     "monoglycerides", "diglycerides")
_add("polysorbate 80", EMU, "e433", "polysorbate")
_add("polysorbate 60", EMU, "e435")
_add("datem", EMU, "diacetyl tartaric acid esters of mono- and diglycerides", "e472e")
_add("sodium stearoyl lactylate", EMU, "e481", "ssl")
_add("calcium stearoyl lactylate", EMU, "e482")
_add("polyglycerol polyricinoleate", EMU, "pgpr", "e476")
_add("sorbitan monostearate", EMU, "e491")
_add("carrageenan", EMU, "e407", "carrageenan gum")
_add("xanthan gum", EMU, "e415", "xanthan")
_add("guar gum", EMU, "e412")
_add("locust bean gum", EMU, "e410", "carob bean gum")
_add("gellan gum", EMU, "e418")
_add("cellulose gum", EMU, "carboxymethylcellulose", "sodium carboxymethylcellulose", "e466", "cmc")
_add("methylcellulose", EMU, "e461")
_add("microcrystalline cellulose", EMU, "e460", "cellulose powder", "powdered cellulose")
_add("modified starch", EMU, "modified food starch", "modified corn starch",
     "modified maize starch", "modified tapioca starch", "modified potato starch",
     "e1422", "e1442", "e1404", "e1412", "e1414", "e1420", "acetylated distarch adipate",
     "hydroxypropyl distarch phosphate")
_add("sodium caseinate", EMU, "caseinate", "calcium caseinate")
_add("soy protein isolate", EMU, "isolated soy protein", "soya protein isolate")
_add("hydrolyzed vegetable protein", EMU, "hydrolysed vegetable protein", "hvp",
     "hydrolyzed soy protein", "hydrolysed soy protein", "hydrolyzed corn protein")
_add("autolyzed yeast extract", FLA, "autolysed yeast extract", "yeast extract")
_add("polydextrose", EMU, "e1200")
_add("sodium phosphate", EMU, "disodium phosphate", "trisodium phosphate", "e339",
     "sodium aluminium phosphate", "sodium acid pyrophosphate", "e450", "sodium polyphosphate",
     "e452", "tetrasodium pyrophosphate")
_add("phosphoric acid", EMU, "e338")
_add("dimethylpolysiloxane", EMU, "e900", "polydimethylsiloxane")
_add("glycerin", EMU, "glycerol", "vegetable glycerin", "e422")

# --- Neutral / common additives --------------------------------------------
_add("citric acid", NA, "e330")
_add("caffeine", NA, "added caffeine")
_add("ascorbic acid", NA, "vitamin c", "e300", "sodium ascorbate", "e301")
_add("tocopherols", NA, "mixed tocopherols", "vitamin e", "e306", "e307", "rosemary extract")
_add("lactic acid", NA, "e270")
_add("malic acid", NA, "e296")
_add("acetic acid", NA, "e260")
_add("sodium citrate", NA, "e331", "trisodium citrate")
_add("potassium citrate", NA, "e332")
_add("calcium carbonate", NA, "e170")
_add("sodium bicarbonate", NA, "baking soda", "bicarbonate of soda", "e500", "sodium hydrogen carbonate")
_add("ammonium bicarbonate", NA, "e503")
_add("baking powder", NA, "raising agent", "leavening", "leavening agents")
_add("pectin", NA, "e440", "fruit pectin")
_add("agar", NA, "e406", "agar agar")
_add("gelatin", NA, "gelatine", "beef gelatin")
_add("yeast", NA, "baker's yeast", "active dry yeast", "dry yeast")
_add("enzymes", NA, "enzyme")
_add("cultures", NA, "live cultures", "live active cultures", "bacterial cultures",
     "probiotic cultures", "lactic cultures")
_add("paprika extract", NA, "e160c", "paprika oleoresin")
_add("beta-carotene", NA, "beta carotene", "e160a")
_add("annatto", NA, "e160b", "annatto extract")
_add("turmeric extract", NA, "curcumin", "e100")
_add("beetroot red", NA, "beet juice color", "e162", "beet juice concentrate (color)")
_add("spirulina extract", NA, "spirulina (color)")
_add("vitamins and minerals", NA, "vitamins", "minerals", "niacin", "thiamine", "riboflavin",
     "folic acid", "reduced iron", "iron", "zinc oxide", "vitamin d", "vitamin b12",
     "thiamine mononitrate", "vitamin a palmitate", "pyridoxine hydrochloride")
_add("water", NA, "filtered water", "purified water", "carbonated water", "sparkling water",
     "mineral water")

# --- Culinary ingredients ---------------------------------------------------
_add("salt", CU, "sea salt", "iodized salt", "table salt", "himalayan salt", "rock salt",
     "kosher salt", "sodium chloride")
_add("vinegar", CU, "white vinegar", "apple cider vinegar", "cider vinegar", "wine vinegar",
     "distilled vinegar", "balsamic vinegar", "rice vinegar")
_add("butter", CU, "unsalted butter", "salted butter", "cream butter")
_add("ghee", CU, "clarified butter")
_add("palm oil", CU, "palm fat", "palm olein", "vegetable oil (palm)", "palm kernel oil",
     "fractionated palm kernel oil")
_add("vegetable oil", CU, "vegetable oils", "vegetable fat", "vegetable fats")
_add("sunflower oil", CU, "sunflower seed oil")
_add("soybean oil", CU, "soy oil", "soya oil", "soya bean oil")
_add("corn oil", CU, "maize oil")
_add("cottonseed oil", CU)
_add("coconut oil", CU, "virgin coconut oil")
_add("cocoa butter", CU)
_add("lard", CU, "pork fat")
_add("starch", CU, "corn starch", "cornstarch", "maize starch", "potato starch",
     "tapioca starch", "wheat starch", "rice starch", "tapioca")
_add("refined wheat flour", CU, "wheat flour", "enriched flour", "enriched wheat flour",
     "white flour", "maida", "all-purpose flour", "all purpose flour", "bleached flour",
     "unbleached enriched flour", "enriched bleached flour", "plain flour", "fortified wheat flour")
_add("white rice", CU, "rice", "rice flour", "white rice flour", "polished rice")

# --- Healthy fats -----------------------------------------------------------
_add("olive oil", HF, "extra virgin olive oil", "virgin olive oil", "extra-virgin olive oil")
_add("avocado oil", HF)
_add("canola oil", HF, "rapeseed oil", "expeller pressed canola oil", "high oleic canola oil")
_add("flaxseed oil", HF, "linseed oil")
_add("walnut oil", HF)
_add("high oleic sunflower oil", HF)
_add("avocado", (HF, WF), "avocados")
_add("olives", (HF, WF), "olive", "black olives", "green olives")

# --- Whole-food fiber / protein sources -------------------------------------
_add("whole grain oats", (FP, WF), "oats", "rolled oats", "whole oats", "oat flakes",
     "whole grain rolled oats", "oatmeal", "steel cut oats", "oat bran", "oat flour",
     "whole oat flour", "whole grain oat flour")
_add("whole wheat flour", (FP, WF), "whole grain wheat", "whole wheat", "whole grain wheat flour",
     "wholemeal flour", "whole meal flour", "atta", "whole wheat atta", "wholewheat flour",
     "whole-wheat flour", "wheat bran")
_add("brown rice", (FP, WF), "whole grain brown rice", "brown rice flour", "whole grain rice")
_add("quinoa", (FP, WF), "quinoa flour", "red quinoa", "white quinoa")
_add("barley", (FP, WF), "whole grain barley", "pearl barley")
_add("buckwheat", (FP, WF), "buckwheat flour")
_add("millet", (FP, WF), "millet flour", "ragi", "finger millet", "bajra", "jowar", "sorghum",
     "sorghum flour")
_add("whole grain corn", (FP, WF), "whole corn", "whole grain cornmeal", "whole cornmeal")
_add("rye", (FP, WF), "whole grain rye", "rye flour", "whole rye flour")
_add("chickpeas", (FP, WF), "chickpea", "garbanzo beans", "chickpea flour", "besan",
     "gram flour", "chana dal")
_add("lentils", (FP, WF), "red lentils", "green lentils", "lentil flour", "masoor dal",
     "moong dal", "toor dal", "urad dal", "dal")
_add("beans", (FP, WF), "black beans", "kidney beans", "pinto beans", "navy beans",
     "white beans", "cannellini beans", "mung beans", "adzuki beans", "fava beans")
_add("peas", (FP, WF), "green peas", "split peas", "pea flour", "yellow peas")
_add("soybeans", (FP, WF), "soybean", "soya beans", "edamame", "whole soybeans")
_add("tofu", (FP, WF))
_add("tempeh", (FP, WF))
_add("almonds", (FP, HF, WF), "almond", "almond flour", "almond butter", "almond meal")
_add("peanuts", (FP, HF, WF), "peanut", "roasted peanuts", "peanut butter", "groundnuts")
_add("walnuts", (FP, HF, WF), "walnut")
_add("cashews", (FP, HF, WF), "cashew", "cashew nuts", "cashew butter")
_add("pistachios", (FP, HF, WF), "pistachio")
_add("hazelnuts", (FP, HF, WF), "hazelnut")
_add("pecans", (FP, HF, WF), "pecan")
_add("macadamia nuts", (FP, HF, WF), "macadamia")
_add("chia seeds", (FP, HF, WF), "chia", "chia seed")
_add("flaxseeds", (FP, HF, WF), "flaxseed", "flax seeds", "linseed", "ground flaxseed",
     "flax meal", "milled flaxseed")
_add("hemp seeds", (FP, HF, WF), "hemp hearts", "hulled hemp seeds")
_add("pumpkin seeds", (FP, HF, WF), "pepitas")
_add("sunflower seeds", (FP, HF, WF), "sunflower kernels")
_add("sesame seeds", (FP, HF, WF), "sesame", "tahini", "sesame paste")
_add("eggs", (FP, WF), "egg", "whole eggs", "egg whites", "egg white", "whole egg")
_add("milk", (FP, WF), "whole milk", "skim milk", "skimmed milk", "milk powder",
     "skimmed milk powder", "whole milk powder", "nonfat milk", "pasteurized milk", "toned milk")
_add("yogurt", (FP, WF), "yoghurt", "greek yogurt", "curd", "dahi")
_add("cheese", (FP, WF), "cheddar cheese", "mozzarella cheese", "parmesan cheese", "paneer",
     "cottage cheese")
_add("chicken", (FP, WF), "chicken breast")
_add("beef", (FP, WF))
_add("fish", (FP, WF), "salmon", "tuna", "sardines", "mackerel")
_add("whey protein", FP, "whey protein concentrate", "whey")
_add("pea protein", FP, "pea protein concentrate")
_add("inulin", FP, "chicory root fiber", "chicory root fibre", "chicory root extract")
_add("psyllium husk", FP, "psyllium", "isabgol")
_add("dates", (WF,), "date", "medjool dates", "date paste")
_add("raisins", (WF,), "sultanas")
_add("cocoa", (WF,), "cocoa powder", "cocoa solids", "cocoa mass", "cacao", "cacao powder",
     "unsweetened chocolate", "chocolate liquor", "cocoa liquor", "cocoa nibs",
     "alkalized cocoa", "cocoa processed with alkali")
_add("fruit", (WF,), "apples", "apple", "bananas", "banana", "strawberries", "blueberries",
     "raspberries", "mango", "cranberries", "cherries", "oranges", "pineapple", "coconut",
     "desiccated coconut", "lemon juice", "lime juice", "apple puree", "fruit puree")
_add("vegetables", (WF,), "tomatoes", "tomato", "tomato paste", "tomato puree", "onion", "onions",
     "garlic", "carrots", "carrot", "spinach", "potatoes", "potato", "bell peppers",
     "celery", "mushrooms", "cabbage", "broccoli", "kale", "beetroot", "sweet potato",
     "cauliflower", "pumpkin", "zucchini", "ginger", "chili", "green chili")
_add("spices", (WF,), "spice", "herbs", "black pepper", "pepper", "cumin", "turmeric",
     "cinnamon", "paprika", "oregano", "basil", "coriander", "cardamom", "cloves", "nutmeg",
     "chili powder", "garlic powder", "onion powder", "mustard seeds", "fennel", "thyme",
     "rosemary", "parsley", "dill", "bay leaf", "mixed spices", "garam masala", "curry leaves")
_add("cream", (CU,), "fresh cream", "heavy cream", "whipping cream")


def _key(text: str) -> str:
    # Aliases go through exactly the same normalization as user input.
    return normalize_name(text)


# Lookup table: normalized alias → entry. Built once at import.
LOOKUP: dict[str, KBEntry] = {}
for _entry in _ENTRIES:
    for _alias in (_entry.canonical, *_entry.synonyms):
        k = _key(_alias)
        if k in LOOKUP and LOOKUP[k].canonical != _entry.canonical:
            raise RuntimeError(f"Duplicate knowledge-base alias: {k!r}")
        LOOKUP[k] = _entry

ENTRIES_BY_CANONICAL: dict[str, KBEntry] = {e.canonical: e for e in _ENTRIES}


def lookup(name: str) -> KBEntry | None:
    return LOOKUP.get(_key(name))


def all_entries() -> list[KBEntry]:
    return list(_ENTRIES)
