import json
from pubmed_fetcher import search_pubmed_microbiome
from utils import safe_groq_call
from cache_manager import cache_get, cache_set

def generate_microbiome_recommendations(disease, recommended_foods):
    cache_key = f"mb_{disease[:30]}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    papers = search_pubmed_microbiome(disease, max_papers=15)
    abstracts = " ".join([
        p.get("abstract","")[:200] for p in papers[:8]
    ])

    prompt = f"""
Gut microbiome specialist.
Condition: {disease}
Foods recommended: {recommended_foods}
Research from PubMed: {abstracts[:1500]}

Extract ONLY from research abstracts.
Return JSON only:
{{
  "dysbiosis_risk": "assessment based on condition",
  "gut_condition_connection": "how gut affects condition",
  "beneficial_bacteria": [
    {{
      "bacteria": "full strain name",
      "benefit_for_condition": "",
      "mechanism": "",
      "found_in_foods": [],
      "evidence_strength": "strong/moderate/limited"
    }}
  ],
  "prebiotic_foods": [
    {{
      "food": "", "fiber_type": "",
      "feeds_bacteria": "", "preparation_tip": ""
    }}
  ],
  "probiotic_recommendations": [
    {{
      "strain": "", "dose_cfu": "",
      "timing": "", "evidence_level": ""
    }}
  ],
  "foods_harming_microbiome": [],
  "gut_healing_protocol": [
    {{"week": "Week 1", "action": "", "reason": ""}}
  ]
}}
"""
    result = safe_groq_call(prompt, max_tokens=1500, temperature=0.3)
    if result:
        cache_set(cache_key, result)
    return result or {}