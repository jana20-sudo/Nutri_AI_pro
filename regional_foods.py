import json
from utils import safe_groq_call
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set

def get_regional_alternatives(western_foods, conditions, region):
    cache_key = (
        f"reg_{region[:15]}_"
        f"{'_'.join(str(c) for c in conditions[:2])[:20]}"
    )
    cached = cache_get(cache_key)
    if cached:
        return cached

    papers = search_pubmed(
        f"traditional Indian food {region} "
        f"{' '.join(str(c) for c in conditions[:2])} "
        f"medicinal nutrition",
        max_papers=10,
        topic_type="traditional medicine"
    )
    evidence = " ".join([
        p.get("abstract","")[:150] for p in papers[:5]
    ])
    prompt = f"""
Traditional Indian nutritionist for {region}.
Patient conditions: {conditions}
Western foods recommended: {western_foods}
Research: {evidence[:600]}

Generate Indian regional alternatives with PubMed evidence.
Return JSON only:
{{
  "regional_meal_plan": {{
    "morning_rituals": [
      {{
        "item": "", "local_name": "",
        "preparation": "", "benefit": "",
        "active_compound": "",
        "pubmed_evidence": "strong/moderate/traditional",
        "citation": ""
      }}
    ],
    "breakfast": [
      {{
        "western_equivalent": "",
        "indian_alternative": "", "local_name": "",
        "preparation": "", "portion": "",
        "calories_approx": 0,
        "key_nutrients": [],
        "why_better_locally": "",
        "antinutrient_note": ""
      }}
    ],
    "lunch": [],
    "dinner": [],
    "snacks": [],
    "traditional_superfoods": [
      {{
        "item": "", "local_name": "",
        "form": "", "dose": "",
        "benefit": "", "active_compound": "",
        "evidence_level": "strong/moderate/traditional",
        "citation": ""
      }}
    ],
    "spices_as_medicine": [
      {{
        "spice": "", "condition": "",
        "daily_amount": "", "how_to_use": "",
        "mechanism": "", "citation": ""
      }}
    ],
    "local_foods_to_modify": [
      {{
        "food": "", "reason": "",
        "healthier_modification": ""
      }}
    ]
  }}
}}
"""
    result = safe_groq_call(prompt, max_tokens=2500, temperature=0.3)
    if result:
        cache_set(cache_key, result)
    return result or {}