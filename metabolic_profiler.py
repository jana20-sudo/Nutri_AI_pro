"""
Fixed: Issue 10 - TSH=0.0 falsy check
Fixed: Issue 27 - same issue
"""
import json
from utils import safe_groq_call, safe_float
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set


def classify_metabolic_type(biomarkers, symptoms, lifestyle):
    clean_bm = {
        k: v for k, v in biomarkers.items()
        if v is not None
    }
    cache_key = f"meta_{str(clean_bm)[:50]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    papers = search_pubmed(
        "metabolic phenotype biomarker "
        "classification insulin resistance",
        max_papers=8
    )
    abstracts = " ".join([
        p.get("abstract","")[:200]
        for p in papers[:4]
    ])
    prompt = f"""
Metabolic medicine specialist.
Use phenotypic proxy method.
Biomarkers: {json.dumps(clean_bm)}
Symptoms: {symptoms}
Lifestyle: {json.dumps(lifestyle)}
Research: {abstracts[:800]}

Return JSON only:
{{
  "metabolic_archetype": "one of: Insulin Resistant / Inflammatory / Lipid Dysregulation / Methylation Impaired / Adrenal Cortisol / Thyroid Influenced",
  "archetype_description": "clinical explanation",
  "confidence": "high/medium/low",
  "bmr_adjustment_percent": -8,
  "bmr_adjustment_reason": "why",
  "absorption_efficiency_percent": 88,
  "personalised_bmr": 1650,
  "macro_ratios": {{
    "protein_percent": 30,
    "carb_percent": 40,
    "fat_percent": 30,
    "rationale": "why these for this type"
  }},
  "foods_uniquely_beneficial": [],
  "foods_uniquely_harmful": []
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=1500, temperature=0.2
    )
    if result and isinstance(result, dict):
        cache_set(cache_key, result)
    return result if isinstance(result, dict) else {}


def calculate_personalised_bmr(
    weight, height, age, gender, profile, biomarkers
):
    """
    Fix 10 and 27: TSH checked with explicit None check
    not truthiness check so TSH=0.0 is handled correctly.
    """
    if gender == "Male":
        base = (
            (10 * weight) + (6.25 * height)
            - (5 * age) + 5
        )
    else:
        base = (
            (10 * weight) + (6.25 * height)
            - (5 * age) - 161
        )

    adjustments = []
    reasons = []

    # From profile
    adj = safe_float(
        profile.get("bmr_adjustment_percent"), 0
    )
    if adj != 0:
        adjustments.append(adj)
        reason = profile.get("bmr_adjustment_reason","")
        if reason:
            reasons.append(reason)

    # Fix 10 and 27: use explicit None check
    # not truthiness check — TSH=0.0 is valid
    tsh = biomarkers.get("tsh")
    if tsh is not None:
        tsh_f = safe_float(tsh, 2.0)
        if tsh_f > 6.0:
            adjustments.append(-15)
            reasons.append("Overt hypothyroidism")
        elif tsh_f > 4.5:
            adjustments.append(-8)
            reasons.append("Subclinical hypothyroidism")
        elif tsh_f < 0.4:
            # Hyperthyroid — increases BMR
            adjustments.append(+10)
            reasons.append(
                "Hyperthyroid state — elevated BMR"
            )

    # Cap at ±20%
    total = max(-20, min(15, sum(adjustments)))
    absorption_raw = profile.get(
        "absorption_efficiency_percent", 95
    )
    absorption = safe_float(absorption_raw, 95) / 100
    absorption = max(0.75, min(1.0, absorption))

    adjusted = base * (1 + total / 100)
    effective = adjusted * absorption

    return {
        "base_bmr": round(base),
        "total_adjustment_percent": total,
        "adjustment_reasons": [
            r for r in reasons if r
        ],
        "personalised_bmr": round(adjusted),
        "effective_bmr": round(effective),
        "absorption_efficiency": round(absorption * 100),
        "explanation": (
            f"Standard BMR: {round(base)} kcal. "
            f"Your adjusted BMR: "
            f"{round(adjusted)} kcal "
            f"({total:+.0f}% from metabolic factors). "
            f"After absorption efficiency "
            f"({round(absorption*100)}%): "
            f"{round(effective)} kcal effective."
        )
    }