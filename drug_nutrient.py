"""
Fixed: Issue 23 - expanded drug key matching
Fixed: Issue 34 - PPI and statin variants covered
Fixed: Issue 33 - MAO inhibitor hardcoded check
"""
import json
from fda_fetcher import fetch_drug_from_fda
from pubmed_fetcher import search_pubmed
from utils import safe_groq_call
from cache_manager import cache_get, cache_set

# Fix 23: Expanded with more drug class keywords
DRUG_DEPLETIONS = {
    "metformin": {
        "depletes": "Vitamin B12",
        "mechanism": (
            "Reduces intrinsic factor production"
        ),
        "supplement": "B12 500mcg daily",
        "citation": "PMID:20488910"
    },
    "statin": {
        "depletes": "CoQ10",
        "mechanism": (
            "Blocks mevalonate pathway used for CoQ10"
        ),
        "supplement": "CoQ10 100-200mg daily",
        "citation": "PMID:15652226"
    },
    "atorvastatin": {
        "depletes": "CoQ10",
        "mechanism": "Statin class — blocks mevalonate",
        "supplement": "CoQ10 100mg daily",
        "citation": "PMID:15652226"
    },
    "rosuvastatin": {
        "depletes": "CoQ10",
        "mechanism": "Statin class — blocks mevalonate",
        "supplement": "CoQ10 100mg daily",
        "citation": "PMID:15652226"
    },
    "simvastatin": {
        "depletes": "CoQ10",
        "mechanism": "Statin class — blocks mevalonate",
        "supplement": "CoQ10 100mg daily",
        "citation": "PMID:15652226"
    },
    "omeprazole": {
        "depletes": ["Magnesium", "B12", "Iron"],
        "mechanism": (
            "Reduced gastric acid impairs "
            "mineral absorption"
        ),
        "supplement": "Magnesium glycinate 300mg",
        "citation": "PMID:21131987"
    },
    "pantoprazole": {
        "depletes": ["Magnesium", "B12", "Iron"],
        "mechanism": (
            "PPI class — reduced gastric acid"
        ),
        "supplement": "Magnesium glycinate 300mg",
        "citation": "PMID:21131987"
    },
    "lansoprazole": {
        "depletes": ["Magnesium", "B12", "Iron"],
        "mechanism": "PPI class — reduced gastric acid",
        "supplement": "Magnesium glycinate 300mg",
        "citation": "PMID:21131987"
    },
    "rabeprazole": {
        "depletes": ["Magnesium", "B12", "Iron"],
        "mechanism": "PPI class — reduced gastric acid",
        "supplement": "Magnesium glycinate 300mg",
        "citation": "PMID:21131987"
    },
    "amlodipine": {
        "depletes": "CoQ10",
        "mechanism": (
            "Calcium channel blockers reduce CoQ10"
        ),
        "supplement": "CoQ10 100mg",
        "citation": "PMID:15652226"
    },
    "warfarin": {
        "food_interaction": "Vitamin K foods",
        "avoid": "Inconsistent Vitamin K intake",
        "note": (
            "Keep Vitamin K intake consistent, not zero. "
            "Sudden increase in leafy greens will "
            "reduce warfarin effect."
        ),
        "citation": "PMID:11781535"
    },
    "frusemide": {
        "depletes": ["Potassium", "Magnesium", "Zinc"],
        "mechanism": "Loop diuretic increases renal loss",
        "supplement": "Potassium-rich foods + Mg",
        "citation": "PMID:8892063"
    },
    "furosemide": {
        "depletes": ["Potassium", "Magnesium", "Zinc"],
        "mechanism": "Loop diuretic increases renal loss",
        "supplement": "Potassium-rich foods + Mg",
        "citation": "PMID:8892063"
    }
}

# Fix 33: MAO inhibitors hardcoded — not left to AI
MAO_INHIBITORS = [
    "phenelzine", "tranylcypromine",
    "isocarboxazid", "selegiline",
    "rasagiline", "moclobemide",
    "linezolid"
]

MAO_DANGEROUS_FOODS = [
    "curd", "yogurt", "aged cheese",
    "idli batter", "dosa batter",
    "fermented foods", "red wine",
    "beer", "soy sauce", "pickles",
    "preserved meat"
]


def _check_mao_inhibitor(medications):
    """
    Fix 33: Hardcoded MAO check.
    Never relies on AI to catch this.
    """
    meds_lower = [m.lower() for m in medications]
    for mao_drug in MAO_INHIBITORS:
        if any(mao_drug in med for med in meds_lower):
            return {
                "mao_detected": True,
                "drug": mao_drug,
                "warning": (
                    f"CRITICAL: {mao_drug} is a MAO inhibitor. "
                    f"The following foods can cause dangerous "
                    f"hypertensive crisis (BP spike to 200+): "
                    f"{', '.join(MAO_DANGEROUS_FOODS)}. "
                    f"These must be strictly excluded from "
                    f"ALL meal plans."
                ),
                "foods_to_exclude": MAO_DANGEROUS_FOODS
            }
    return {"mao_detected": False}


def check_drug_nutrient_interactions(
    medications, recommended_foods, nutrients
):
    if not medications:
        return {}
    cache_key = (
        f"drug_"
        f"{'_'.join(str(m)[:10] for m in medications[:3])}"
    )
    cached = cache_get(cache_key)
    if cached:
        return cached

    drug_data = {}
    for med in medications:
        if med.strip():
            drug_data[med] = fetch_drug_from_fda(med)

    # Fix 23: Check all drug keys including full names
    depletions = []
    for med in medications:
        med_lower = med.lower()
        for drug_key, depl_data in (
            DRUG_DEPLETIONS.items()
        ):
            # Check if drug key is in medication name
            if drug_key in med_lower:
                depletions.append({
                    "medication": med,
                    "depletion_data": depl_data
                })
                break

    # Fix 33: Hardcoded MAO check runs always
    mao_check = _check_mao_inhibitor(medications)

    papers = search_pubmed(
        f"{' '.join(str(m) for m in medications[:2])} "
        f"food nutrient interaction absorption",
        max_papers=6
    )
    evidence = " ".join([
        p.get("abstract","")[:120]
        for p in papers[:3]
    ])

    prompt = f"""
Clinical pharmacist. Check drug-food interactions.
Medications: {medications}
FDA data: {json.dumps(drug_data)[:600]}
Recommended foods: {recommended_foods}
Research: {evidence[:400]}

Return JSON only:
{{
  "interactions": [
    {{
      "drug": "",
      "food_or_nutrient": "",
      "mechanism": "",
      "severity": "critical/moderate/minor",
      "recommendation": "",
      "source": "FDA/PubMed"
    }}
  ],
  "timing_schedule": [
    {{
      "medication": "",
      "take_at": "",
      "eat_before_after": ""
    }}
  ]
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=1200, temperature=0.2
    )
    if not isinstance(result, dict):
        result = {}

    # Inject known depletions
    if depletions:
        result["nutrient_depletions"] = [
            {
                "drug": d["medication"],
                "depletes": str(
                    d["depletion_data"].get(
                        "depletes", ""
                    )
                ),
                "supplement_recommendation": (
                    d["depletion_data"].get(
                        "supplement", ""
                    )
                ),
                "citation": d["depletion_data"].get(
                    "citation", ""
                )
            }
            for d in depletions
        ]

    # Fix 33: Always inject MAO warning if detected
    result["mao_check"] = mao_check
    if mao_check.get("mao_detected"):
        result["mao_warning"] = mao_check["warning"]
        result["mao_exclude_foods"] = (
            mao_check["foods_to_exclude"]
        )

    cache_set(cache_key, result)
    return result