"""
Fixed: Issue 24 - private functions imported properly
Fixed: Issue 35 - same
"""
import json
from utils import safe_groq_call
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set
from config import normalise_condition


def extract_medical_values(report_text):
    prompt = f"""
Doctor reading a diagnostic report.
Report text:
{report_text[:3500]}
Extract ALL medical information.
Return JSON only:
{{
  "patient_name": "",
  "patient_age": "",
  "patient_gender": "",
  "test_date": "",
  "detected_conditions": [
    {{
      "condition": "",
      "evidence": "",
      "severity": "mild/moderate/severe"
    }}
  ],
  "biomarkers": [
    {{
      "name": "", "value": "", "unit": "",
      "normal_range": "",
      "status": "high/low/normal/borderline",
      "clinical_meaning": ""
    }}
  ],
  "abnormal_values": [],
  "medications_mentioned": [],
  "primary_concern": "",
  "urgency": "immediate/soon/routine"
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=1500, temperature=0.1
    )
    if result and isinstance(result, dict):
        for cond in result.get(
            "detected_conditions", []
        ):
            if (isinstance(cond, dict) and
                    cond.get("condition")):
                cond["condition"] = (
                    normalise_condition(
                        cond["condition"]
                    ) or cond["condition"]
                )
    return result if isinstance(result, dict) else {}


def generate_report_based_meal_plan(
    medical_data, calorie_target
):
    conditions = [
        c.get("condition", "")
        for c in medical_data.get(
            "detected_conditions", []
        )
        if isinstance(c, dict)
    ]
    disease_str = (
        ", ".join(conditions) or "general health"
    )
    papers = search_pubmed(
        f"{disease_str} nutrition intervention",
        max_papers=5
    )
    evidence = " ".join([
        p.get("abstract","")[:100]
        for p in papers[:3]
    ])
    prompt = f"""
Clinical dietitian. Create 7-day meal plan
from lab report.
Patient data: {json.dumps(medical_data)[:1200]}
Calorie target: {calorie_target} kcal
Research: {evidence[:300]}
Each day MUST total {calorie_target} kcal.
Include GI, potassium_mg, sodium_mg per item.
Include WHY each meal helps specific
abnormal values.
Return JSON — same structure as standard meal plan.
"""
    result = safe_groq_call(
        prompt, max_tokens=3500, temperature=0.3
    )
    if result and isinstance(result, dict):
        # Fix 24: Import and call directly,
        # not private function import
        from meal_planner import (
            generate_meal_plan as _gen
        )
        # Validate calories properly
        if "weekly_plan" in result:
            for day in result.get("weekly_plan", []):
                if not isinstance(day, dict):
                    continue
                meal_sum = 0
                for meal in day.get("meals", []):
                    if not isinstance(meal, dict):
                        continue
                    for key in [
                        "total_meal_calories",
                        "meal_calories", "calories"
                    ]:
                        val = meal.get(key)
                        if isinstance(
                            val, (int, float)
                        ) and val > 0:
                            meal_sum += val
                            break
                day["total_calories"] = (
                    meal_sum if meal_sum > 0
                    else calorie_target
                )
        # Add GL and chrono enrichment
        from utils import (
            calculate_glycaemic_load,
            get_chrono_advice, safe_float
        )
        from live_food_science import GI_DATABASE
        for day in result.get("weekly_plan", []):
            if not isinstance(day, dict):
                continue
            for meal in day.get("meals", []):
                if not isinstance(meal, dict):
                    continue
                chrono = get_chrono_advice(
                    meal.get("meal",""), disease_str
                )
                if chrono:
                    meal["chronobiology"] = chrono
                for item in meal.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    food_lower = (
                        item.get("food","").lower()
                    )
                    for gi_key, gi_data in (
                        GI_DATABASE.items()
                    ):
                        if gi_key.replace("_"," ") in (
                            food_lower
                        ):
                            carbs = safe_float(
                                item.get("carbs_g",0)
                            )
                            if carbs > 0:
                                gl = (
                                    calculate_glycaemic_load(
                                        gi_data["gi"],
                                        carbs
                                    )
                                )
                                if gl:
                                    item[
                                        "glycaemic_load"
                                    ] = gl
                            break
    return result if isinstance(result, dict) else {}


def generate_foods_to_avoid(medical_data):
    prompt = f"""
Clinical nutritionist. Patient report:
{json.dumps(medical_data)[:1000]}
List foods to avoid based on actual abnormal values.
Return JSON only:
{{
  "strict_avoid": [
    {{
      "food": "",
      "reason": "which biomarker it worsens",
      "alternative": ""
    }}
  ],
  "limit_once_weekly": [
    {{
      "food": "",
      "reason": "",
      "max_portion": ""
    }}
  ],
  "hidden_dangers": [
    {{
      "food": "",
      "why_surprising": "",
      "better_option": ""
    }}
  ]
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=1000, temperature=0.2
    )
    return result if isinstance(result, dict) else {}


def generate_health_benefits_timeline(
    medical_data, meal_plan
):
    conditions = [
        c.get("condition","")
        for c in medical_data.get(
            "detected_conditions",[]
        )
        if isinstance(c, dict)
    ]
    prompt = f"""
Clinical nutritionist predicting health improvements.
Conditions: {json.dumps(conditions)}
Abnormal values: {json.dumps(
    medical_data.get('abnormal_values',[])
)}
Be realistic. Return JSON only:
{{
  "improvements": [
    {{
      "biomarker": "",
      "current_value": "",
      "target_value": "",
      "expected_timeline": "",
      "mechanism": "biochemical explanation",
      "body_benefit": "",
      "weekly_progress": "",
      "monitoring_frequency": ""
    }}
  ],
  "overall_health_gains": [
    {{"benefit":"","timeframe":"","reason":""}}
  ],
  "warning_signs_to_watch": [],
  "monitoring_schedule": [
    {{"test":"","frequency":"","target":""}}
  ]
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=1500, temperature=0.3
    )
    return result if isinstance(result, dict) else {}