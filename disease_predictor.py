"""
Fixed: Issue 20 - PubMed only called when needed
Fixed: Issue 31 - same
"""
import json
from utils import safe_groq_call, safe_float
from cache_manager import cache_get, cache_set


def _framingham_cvd(
    age, gender, total_chol, hdl,
    systolic, on_bp_meds, smoker, diabetic
):
    pts = 0
    if gender == "Male":
        if age >= 65: pts += 12
        elif age >= 60: pts += 11
        elif age >= 55: pts += 10
        elif age >= 50: pts += 8
        elif age >= 45: pts += 6
        elif age >= 40: pts += 3
    else:
        if age >= 65: pts += 14
        elif age >= 60: pts += 12
        elif age >= 55: pts += 10
        elif age >= 50: pts += 8
        elif age >= 45: pts += 6
        elif age >= 40: pts += 3

    if total_chol < 160: pts += 0
    elif total_chol < 200: pts += 1
    elif total_chol < 240: pts += 2
    elif total_chol < 280: pts += 3
    else: pts += 4

    if hdl >= 60: pts -= 2
    elif hdl >= 50: pts -= 1
    elif hdl < 40: pts += 2

    if not on_bp_meds:
        if systolic >= 160: pts += 4
        elif systolic >= 140: pts += 3
        elif systolic >= 130: pts += 2
        elif systolic >= 120: pts += 1
    else:
        if systolic >= 160: pts += 6
        elif systolic >= 140: pts += 5
        elif systolic >= 130: pts += 4
        elif systolic >= 120: pts += 3

    if smoker: pts += 4
    if diabetic: pts += 2

    risk_m = {
        -3:1,-2:2,-1:2,0:3,1:4,2:4,3:6,4:7,5:9,
        6:11,7:14,8:18,9:22,10:27,11:33,12:40,13:47
    }
    risk_f = {
        -2:1,-1:2,0:2,1:2,2:3,3:3,4:4,5:5,6:6,
        7:7,8:8,9:9,10:11,11:13,12:15,13:17,14:20
    }
    table = risk_m if gender == "Male" else risk_f
    pts = max(-3, min(13, pts))
    closest = min(
        table.keys(), key=lambda x: abs(x - pts)
    )
    pct = table[closest]
    return {
        "risk_percent": pct,
        "level": (
            "High" if pct >= 20
            else "Moderate" if pct >= 10
            else "Low"
        ),
        "guideline": "Framingham PMID:9486607"
    }


def _findrisc_diabetes(
    age, bmi, waist_cm, gender,
    active, fam_history, glucose_history
):
    pts = 0
    if age >= 65: pts += 4
    elif age >= 55: pts += 3
    elif age >= 45: pts += 2
    if bmi >= 30: pts += 3
    elif bmi >= 25: pts += 1
    # Fix: Use BMI proxy only if waist not provided
    if waist_cm and safe_float(waist_cm, 0) > 0:
        wc = safe_float(waist_cm, 0)
        if gender == "Male":
            if wc >= 102: pts += 4
            elif wc >= 90: pts += 3
        else:
            if wc >= 88: pts += 4
            elif wc >= 80: pts += 3
    else:
        # Waist not provided — use BMI as proxy
        # with conservative estimate
        if bmi >= 32: pts += 3
        elif bmi >= 28: pts += 1
    if not active: pts += 2
    if glucose_history: pts += 5
    if fam_history == "first_degree": pts += 5
    elif fam_history == "second_degree": pts += 3

    if pts < 7: pct, level = 1, "Low"
    elif pts < 12: pct, level = 4, "Slightly Elevated"
    elif pts < 15: pct, level = 17, "Moderate"
    elif pts < 21: pct, level = 33, "High"
    else: pct, level = 50, "Very High"

    return {
        "risk_percent": pct,
        "level": level,
        "guideline": "FINDRISC PMID:12709467",
        "waist_used": waist_cm is not None
    }


def predict_disease_risk(
    biomarkers, age, gender, bmi, lifestyle
):
    """
    Fix 20: PubMed only called for AI explanation,
    not for mathematical scoring.
    Mathematical scores are always fast.
    """
    results = {}
    results["cvd"] = _framingham_cvd(
        age=age, gender=gender,
        total_chol=safe_float(
            biomarkers.get("total_cholesterol"), 200
        ),
        hdl=safe_float(biomarkers.get("hdl"), 50),
        systolic=safe_float(
            biomarkers.get("systolic_bp"), 120
        ),
        on_bp_meds=lifestyle.get(
            "on_bp_medication", False
        ),
        smoker=lifestyle.get("smoker", False),
        diabetic=safe_float(
            biomarkers.get("fasting_glucose"), 90
        ) >= 126
    )
    results["diabetes"] = _findrisc_diabetes(
        age=age, bmi=bmi,
        waist_cm=lifestyle.get("waist_cm"),
        gender=gender,
        active=lifestyle.get(
            "activity_level", "sedentary"
        ) not in ["sedentary"],
        fam_history=lifestyle.get(
            "family_diabetes", "none"
        ),
        glucose_history=safe_float(
            biomarkers.get("fasting_glucose"), 90
        ) >= 100
    )
    sys = safe_float(biomarkers.get("systolic_bp"), 120)
    if sys >= 180: htn_class = "Hypertensive Crisis"
    elif sys >= 140: htn_class = "Stage 2 Hypertension"
    elif sys >= 130: htn_class = "Stage 1 Hypertension"
    elif sys >= 120: htn_class = "Elevated"
    else: htn_class = "Normal"
    htn_risk = 0
    if sys >= 140: htn_risk += 5
    elif sys >= 130: htn_risk += 3
    if bmi >= 30: htn_risk += 3
    elif bmi >= 25: htn_risk += 1
    if lifestyle.get("high_sodium_diet"): htn_risk += 2
    if lifestyle.get("high_stress"): htn_risk += 2
    if age >= 55: htn_risk += 2
    results["hypertension"] = {
        "current_classification": htn_class,
        "risk_percent": min(htn_risk * 4, 60),
        "level": (
            "High" if htn_risk * 4 > 40
            else "Moderate" if htn_risk * 4 > 20
            else "Low"
        ),
        "guideline": "ACC/AHA 2017 PMID:29133354"
    }

    # Fix 20: AI explanation only called if needed
    # and results are already computed fast above
    cache_key = f"riskexp_{str(biomarkers)[:50]}"
    cached = cache_get(cache_key)
    ai_exp = cached

    if not ai_exp:
        # Only call PubMed for explanation context
        from pubmed_fetcher import search_pubmed
        papers = search_pubmed(
            "cardiovascular diabetes risk "
            "food intervention nutrition",
            max_papers=5
        )
        evidence = " ".join([
            p.get("abstract","")[:120]
            for p in papers[:3]
        ])
        prompt = f"""
Risk profiles: {json.dumps(results)}
Patient: Age {age}, Gender {gender}, BMI {bmi}
Research: {evidence[:500]}
For each disease give:
- why this patient specifically
- top 3 foods with mechanism and citation
- key lifestyle change
Return JSON only:
{{
  "risk_explanations": {{
    "cvd": {{
      "why_this_patient": "",
      "top_foods": [
        {{"food":"","mechanism":"","citation":""}}
      ],
      "key_lifestyle_change": ""
    }},
    "diabetes": {{
      "why_this_patient": "",
      "top_foods": [],
      "key_lifestyle_change": ""
    }},
    "hypertension": {{
      "why_this_patient": "",
      "top_foods": [],
      "key_lifestyle_change": ""
    }}
  }},
  "biological_age_estimate": "",
  "most_urgent": ""
}}
"""
        ai_exp = safe_groq_call(
            prompt, max_tokens=1500, temperature=0.2
        )
        if ai_exp and isinstance(ai_exp, dict):
            cache_set(cache_key, ai_exp)

    return {
        "risks": results,
        "ai_explanation": (
            ai_exp if isinstance(ai_exp, dict) else {}
        )
    }