"""
Fixed: Issue 13 - compound name matching
Fixed: Issue 14 - urllib.parse.quote
"""
import requests
import json
import urllib.parse
from cache_manager import cache_get, cache_set
from utils import safe_groq_call, ncbi_limiter
from config import PUBCHEM_BASE

GI_DATABASE = {
    "foxtail_millet": {
        "gi": 50, "citation": "PMID:21382369"
    },
    "ragi": {"gi": 54, "citation": "PMID:12792661"},
    "finger_millet": {
        "gi": 54, "citation": "PMID:12792661"
    },
    "pearl_millet": {
        "gi": 55, "citation": "PMID:19179055"
    },
    "kambu": {"gi": 55, "citation": "PMID:19179055"},
    "kodo_millet": {
        "gi": 49, "citation": "PMID:25080901"
    },
    "barnyard_millet": {
        "gi": 50, "citation": "PMID:25080901"
    },
    "white_rice": {
        "gi": 72, "citation": "PMID:12792661"
    },
    "brown_rice": {
        "gi": 55, "citation": "PMID:12792661"
    },
    "parboiled_rice": {
        "gi": 38, "citation": "PMID:7498065"
    },
    "horsegram": {
        "gi": 29, "citation": "PMID:11978262"
    },
    "kollu": {"gi": 29, "citation": "PMID:11978262"},
    "green_moong": {
        "gi": 29, "citation": "PMID:12792661"
    },
    "chickpea": {
        "gi": 28, "citation": "PMID:12792661"
    },
    "rajma": {"gi": 29, "citation": "PMID:12792661"},
    "oats": {"gi": 55, "citation": "PMID:12792661"},
    "banana": {"gi": 51, "citation": "PMID:12792661"},
    "apple": {"gi": 36, "citation": "PMID:12792661"},
    "guava": {"gi": 28, "citation": "PMID:12792661"},
    "pomegranate": {
        "gi": 35, "citation": "PMID:23140422"
    },
    "white_bread": {
        "gi": 75, "citation": "PMID:12792661"
    },
}

SYNERGIES = [
    {
        "food1": "Turmeric",
        "food2": "Black Pepper",
        "effect": (
            "Curcumin bioavailability increased 2000%"
        ),
        "mechanism": (
            "Piperine inhibits glucuronidation of "
            "curcumin, dramatically increasing "
            "systemic exposure"
        ),
        "practical": (
            "Always add black pepper to turmeric dishes"
        ),
        "citation": "PMID:9619120"
    },
    {
        "food1": "Spinach/Iron foods",
        "food2": "Lemon/Vitamin C",
        "effect": "Iron absorption increased 2-6x",
        "mechanism": (
            "Ascorbic acid reduces Fe3+ to Fe2+ enabling "
            "DMT1 transporter absorption"
        ),
        "practical": "Squeeze lemon on dal and greens",
        "citation": "PMID:6940487"
    },
    {
        "food1": "Tomato",
        "food2": "Oil/Fat",
        "effect": "Lycopene absorption increased 4-5x",
        "mechanism": (
            "Lycopene is lipophilic — requires fat for "
            "micellarisation. Cooking isomerises "
            "trans to cis lycopene"
        ),
        "practical": (
            "Cook tomato in oil, never eat raw for lycopene"
        ),
        "citation": "PMID:10799377"
    },
    {
        "food1": "Dal",
        "food2": "Rice",
        "effect": (
            "Complete protein — all 9 essential amino acids"
        ),
        "mechanism": (
            "Rice is lysine-deficient. Dal is "
            "methionine-deficient. Together PDCAAS "
            "approaches 1.0"
        ),
        "practical": (
            "Dal rice at same meal — traditional "
            "wisdom validated"
        ),
        "citation": "PMID:1399905"
    },
    {
        "food1": "Fermented foods",
        "food2": "Iron/zinc rich foods",
        "effect": "Mineral absorption improved 2-3x",
        "mechanism": (
            "Fermentation reduces phytic acid 60-70% "
            "via microbial phytase"
        ),
        "practical": (
            "Eat fermented idli/curd with iron-rich meals"
        ),
        "citation": "PMID:9265895"
    }
]

ANTINUTRIENTS = {
    "phytic_acid": {
        "found_in": [
            "millet", "ragi", "bajra", "jowar",
            "legume", "dal", "whole grain", "rice bran",
            "horsegram", "kollu"
        ],
        "blocks": ["iron","zinc","calcium","magnesium"],
        "solutions": [
            {
                "method": "Fermentation 12-24h",
                "reduction": "60-90%",
                "citation": "PMID:9265895"
            },
            {
                "method": "Soaking 8-12h",
                "reduction": "20-50%",
                "citation": "PMID:2778584"
            },
            {
                "method": "Sprouting 24-48h",
                "reduction": "40-60%",
                "citation": "PMID:11678491"
            }
        ]
    },
    "oxalic_acid": {
        "found_in": [
            "spinach", "palak", "beet", "rhubarb",
            "sweet potato", "keerai"
        ],
        "blocks": ["calcium","iron"],
        "solutions": [
            {
                "method": "Blanching 1-2 min",
                "reduction": "30-50%",
                "citation": "PMID:16870090"
            }
        ]
    },
    "tannins": {
        "found_in": [
            "tea", "coffee", "jowar", "sorghum",
            "tamarind"
        ],
        "blocks": ["iron","zinc"],
        "solutions": [
            {
                "method": (
                    "Drink tea 1hr away from meals"
                ),
                "reduction": "60-90% inhibition removed",
                "citation": "PMID:6940487"
            }
        ]
    },
    "goitrogens": {
        "found_in": [
            "raw cabbage", "raw broccoli",
            "raw cauliflower", "bajra", "cassava",
            "tapioca"
        ],
        "blocks": ["thyroid iodine uptake"],
        "solutions": [
            {
                "method": "Cook thoroughly",
                "reduction": "60-90%",
                "citation": "PMID:1547802"
            }
        ]
    }
}

COOKING_RETENTION = {
    "vitamin_c": {
        "raw": "100%",
        "steaming_5min": "90%",
        "boiling_5min": "70%",
        "pressure_cooking": "55%",
        "note": (
            "Most heat-sensitive nutrient. "
            "Water-soluble — leaches into cooking water"
        ),
        "citation": "PMID:17127425"
    },
    "carotenoids": {
        "raw": "baseline",
        "cooked_with_fat": "+35-50%",
        "note": (
            "Cooking breaks cell walls. "
            "Fat required for absorption."
        ),
        "citation": "PMID:10799377"
    },
    "iron_cast_iron": {
        "effect": (
            "Increases iron content 2-3x when "
            "cooking acidic foods"
        ),
        "mechanism": (
            "Iron leaches from kadai into acidic food"
        ),
        "practical": (
            "Cook tamarind-based dishes in iron kadai"
        ),
        "citation": "PMID:3400937"
    }
}

# Fix 13: Multiple keys per compound for flexible matching
PHYTOCHEMICALS = {
    "charantin": {
        "food": "bitter gourd (pavakkai)",
        "aliases": ["bitter gourd","pavakkai","karela"],
        "mechanism": (
            "Activates AMPK pathway — same target as "
            "Metformin. Increases GLUT4 translocation "
            "independent of insulin"
        ),
        "effect": "Reduces fasting glucose 10-25 mg/dL",
        "dose": "50-100ml juice daily",
        "citation": "PMID:21290983"
    },
    "allicin": {
        "food": "garlic (poondu)",
        "aliases": ["garlic","poondu","lahsun"],
        "activation": (
            "Crush and wait 10 minutes before cooking"
        ),
        "mechanism": (
            "Inhibits ACE enzyme, reducing angiotensin II"
        ),
        "effect": "Reduces systolic BP 6-10 mmHg",
        "citation": "PMID:17895726"
    },
    "galactomannan": {
        "food": "fenugreek (vendayam)",
        "aliases": [
            "fenugreek","vendayam","methi","vendhayam"
        ],
        "mechanism": (
            "Viscous gel delays glucose absorption. "
            "4-hydroxyisoleucine directly stimulates "
            "insulin secretion"
        ),
        "effect": (
            "Reduces post-meal glucose spike 15-20%"
        ),
        "dose": (
            "1 tsp soaked overnight, "
            "drink water morning"
        ),
        "citation": "PMID:3567067"
    },
    "beta_glucan": {
        "food": "oats, pearl millet (kambu)",
        "aliases": ["oat","oats","kambu","pearl millet"],
        "mechanism": (
            "Traps bile acids, forcing liver to use "
            "cholesterol for new bile synthesis"
        ),
        "effect": "Reduces LDL 5-8% per 3g/day",
        "dose": "3g/day minimum",
        "citation": "PMID:9614169"
    },
    "punicalagin": {
        "food": "pomegranate",
        "aliases": ["pomegranate","anar","mathalam"],
        "mechanism": (
            "Inhibits LDL oxidation via "
            "copper-catalysed peroxidation"
        ),
        "effect": "Reduces LDL oxidation 40-50%",
        "citation": "PMID:16277814"
    },
    "curcumin": {
        "food": "turmeric (manjal)",
        "aliases": ["turmeric","manjal","haldi"],
        "mechanism": (
            "Inhibits NF-kB inflammatory pathway. "
            "Reduces COX-2 expression"
        ),
        "bioavailability_note": (
            "Requires black pepper for 2000% enhancement"
        ),
        "effect": "Reduces CRP 0.3-2.4 mg/L",
        "citation": "PMID:9619120"
    }
}


def get_gi(food_name):
    food_lower = food_name.lower().replace(" ","_")
    # Try exact key match first
    if food_lower in GI_DATABASE:
        return GI_DATABASE[food_lower]
    # Try partial match
    for key, data in GI_DATABASE.items():
        key_words = key.replace("_"," ")
        if (key_words in food_lower or
                food_lower in key_words or
                any(w in food_lower
                    for w in key_words.split()
                    if len(w) > 3)):
            return data
    return None


def get_phytochemical(compound_name):
    """
    Fix 13: Searches aliases not just exact key match.
    Handles multi-word compound names from Groq.
    """
    if not compound_name:
        return {}
    compound_lower = compound_name.lower()
    # Check exact keys
    for key, data in PHYTOCHEMICALS.items():
        if key in compound_lower:
            return data
    # Check aliases
    for key, data in PHYTOCHEMICALS.items():
        aliases = data.get("aliases", [])
        if any(alias.lower() in compound_lower
               for alias in aliases):
            return data
    # Check food names
    for key, data in PHYTOCHEMICALS.items():
        food = data.get("food","").lower()
        if any(w in compound_lower
               for w in food.split()
               if len(w) > 3):
            return data
    return {}


def get_antinutrients_for_food(food_name):
    """
    Fix 29: Expanded to match Indian food names
    including ragi, horsegram, etc.
    """
    if not food_name:
        return []
    food_lower = food_name.lower()
    results = []
    for anti_name, data in ANTINUTRIENTS.items():
        for source in data.get("found_in", []):
            source_words = source.lower().split()
            # Check if any word of the source
            # appears in the food name
            if any(
                word in food_lower
                for word in source_words
                if len(word) > 3
            ):
                results.append({
                    "antinutrient": anti_name,
                    "blocks": data["blocks"],
                    "solutions": data["solutions"]
                })
                break
    return results


def fetch_compound_pubchem(compound_name):
    """
    Fix 14: Use urllib.parse.quote instead of
    requests.utils.quote
    """
    cache_key = f"pc_{compound_name[:30]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    ncbi_limiter.wait()
    try:
        encoded = urllib.parse.quote(
            compound_name, safe=""
        )
        url = f"{PUBCHEM_BASE}/compound/name/{encoded}/JSON"
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return {}
        compound = r.json().get(
            "PC_Compounds", [{}]
        )[0]
        cid = (
            compound.get("id", {})
            .get("id", {})
            .get("cid")
        )
        result = {
            "cid": cid,
            "name": compound_name,
            "url": (
                f"https://pubchem.ncbi.nlm.nih.gov"
                f"/compound/{cid}"
            )
        }
        cache_set(cache_key, result)
        return result
    except Exception as e:
        print(f"[PubChem] Error: {e}")
        return {}