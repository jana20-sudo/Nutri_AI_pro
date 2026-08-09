"""
Fixed: Issue 21 - deep copy prevents mutation
Fixed: Issue 22 - disliked_foods passed to swap
"""
import json
import copy
from utils import (
    safe_groq_call, calculate_glycaemic_load,
    calculate_kna_ratio, get_chrono_advice, safe_float
)
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set
from live_food_science import GI_DATABASE, SYNERGIES


def _validate_calories(meal_plan, target):
    if not meal_plan or "weekly_plan" not in meal_plan:
        return meal_plan
    for day in meal_plan.get("weekly_plan", []):
        if not isinstance(day, dict):
            continue
        meals = day.get("meals", [])
        meal_sum = 0
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            for key in [
                "total_meal_calories",
                "meal_calories", "calories"
            ]:
                val = meal.get(key)
                if (isinstance(val, (int, float))
                        and val > 0):
                    meal_sum += val
                    break
        if meal_sum <= 0:
            continue
        day["total_calories"] = meal_sum
        if (abs(meal_sum - target) /
                max(target, 1)) > 0.15:
            scale = target / meal_sum
            for meal in meals:
                if not isinstance(meal, dict):
                    continue
                for key in [
                    "total_meal_calories",
                    "meal_calories", "calories"
                ]:
                    if (key in meal and
                            isinstance(
                                meal[key], (int, float)
                            )):
                        meal[key] = round(
                            meal[key] * scale
                        )
                        break
                for item in meal.get("items", []):
                    if isinstance(item, dict):
                        for field in [
                            "calories", "protein_g",
                            "carbs_g", "fat_g",
                            "fiber_g", "potassium_mg",
                            "sodium_mg"
                        ]:
                            if (field in item and
                                    isinstance(
                                        item[field],
                                        (int, float)
                                    )):
                                item[field] = round(
                                    item[field] * scale,
                                    1
                                )
            day["total_calories"] = target
    return meal_plan


def _enrich_gl_chrono(meal_plan, condition):
    for day in meal_plan.get("weekly_plan", []):
        if not isinstance(day, dict):
            continue
        total_k = total_na = 0
        for meal in day.get("meals", []):
            if not isinstance(meal, dict):
                continue
            meal_name = meal.get("meal", "")
            chrono = get_chrono_advice(
                meal_name, condition
            )
            if chrono:
                meal["chronobiology"] = chrono
            for item in meal.get("items", []):
                if not isinstance(item, dict):
                    continue
                food_lower = (
                    item.get("food", "").lower()
                )
                for gi_key, gi_data in (
                    GI_DATABASE.items()
                ):
                    key_words = gi_key.replace("_"," ")
                    if (key_words in food_lower or
                            food_lower in key_words or
                            any(w in food_lower
                                for w in
                                key_words.split()
                                if len(w) > 3)):
                        carbs = safe_float(
                            item.get("carbs_g", 0)
                        )
                        if carbs > 0:
                            gl = calculate_glycaemic_load(
                                gi_data["gi"], carbs
                            )
                            if gl:
                                item["glycaemic_load"] = gl
                                item["gi"] = gi_data["gi"]
                                item["gi_citation"] = (
                                    gi_data.get(
                                        "citation", ""
                                    )
                                )
                        break
                k = safe_float(
                    item.get("potassium_mg", 0)
                )
                na = safe_float(
                    item.get("sodium_mg", 0)
                )
                total_k += k
                total_na += na
        if total_k > 0 and total_na > 0:
            day["kna_ratio"] = calculate_kna_ratio(
                total_k, total_na
            )
    return meal_plan


def generate_meal_plan(
    disease, recommended_foods,
    calorie_target, user_context,
    metabolic_profile=None,
    seasonal_foods=None,
    diet_restrictions=None,
    disliked_foods=None
):
    effective_cal = calorie_target
    if (metabolic_profile and
            isinstance(metabolic_profile, dict)):
        pb = (
            metabolic_profile.get("personalised_bmr")
            or metabolic_profile.get("effective_bmr")
        )
        if pb:
            effective_cal = int(pb) - 200

    cache_key = (
        f"meal_{disease[:25]}_{effective_cal}_"
        f"{user_context.get('bmi','')}_"
        f"{str(diet_restrictions)[:15]}"
    )
    cached = cache_get(cache_key)
    if cached:
        return _validate_calories(
            # Fix 21: deep copy prevents session state mutation
            copy.deepcopy(cached), effective_cal
        )

    papers = search_pubmed(
        f"{disease} dietary intervention "
        f"randomised trial",
        max_papers=6
    )
    evidence = " ".join([
        p.get("abstract","")[:120]
        for p in papers[:3]
    ])

    macro = {"protein": 30, "carbs": 40, "fat": 30}
    if (metabolic_profile and
            isinstance(metabolic_profile, dict)):
        mr = metabolic_profile.get(
            "macro_ratios", {}
        )
        if mr:
            macro = {
                "protein": mr.get("protein_percent", 30),
                "carbs": mr.get("carb_percent", 40),
                "fat": mr.get("fat_percent", 30)
            }

    seasonal_note = ""
    if (seasonal_foods and
            isinstance(seasonal_foods, dict)):
        avail = [
            f.get("food", "")
            for f in seasonal_foods.get(
                "available_now", []
            )
            if isinstance(f, dict)
        ][:4]
        if avail:
            seasonal_note = (
                f"Prioritise seasonal foods: "
                f"{', '.join(avail)}"
            )

    restriction_note = ""
    if diet_restrictions:
        excl = diet_restrictions.get("exclude", [])
        if excl:
            restriction_note = (
                f"EXCLUDE these ingredients: "
                f"{', '.join(excl)}"
            )

    dislike_note = ""
    if disliked_foods:
        dislike_note = (
            f"AVOID (patient dislikes): "
            f"{', '.join(disliked_foods)}"
        )

    gi_examples = [
        f"{k.replace('_',' ')}: GI={v['gi']} "
        f"({v['citation']})"
        for k, v in list(GI_DATABASE.items())[:5]
    ]

    prompt = f"""
Clinical dietitian AND food scientist.
Create precise 7-day meal plan.

RULES:
- Each day MUST total EXACTLY {effective_cal} kcal
- Include GI and GL for carbohydrate foods
- Include potassium_mg and sodium_mg per item
- Biochemical WHY for each meal
- Physical activity synergising with each meal
- Include food synergy combinations
- For millets: note fermentation benefit

Condition: {disease}
Target: {effective_cal} kcal/day
Macros: Protein {macro['protein']}%,
        Carbs {macro['carbs']}%,
        Fat {macro['fat']}%
{seasonal_note}
{restriction_note}
{dislike_note}
Recommended foods: {recommended_foods}
GI references: {', '.join(gi_examples)}
Research: {evidence[:400]}

Return JSON only:
{{
  "calorie_target": {effective_cal},
  "primary_goals": [],
  "weekly_plan": [
    {{
      "day": "Monday",
      "total_calories": {effective_cal},
      "total_protein_g": 0,
      "total_fiber_g": 0,
      "total_potassium_mg": 0,
      "total_sodium_mg": 0,
      "meals": [
        {{
          "meal": "Breakfast",
          "time": "7:00 AM",
          "total_meal_calories": 0,
          "items": [
            {{
              "food": "",
              "portion": "",
              "calories": 0,
              "protein_g": 0,
              "carbs_g": 0,
              "fat_g": 0,
              "fiber_g": 0,
              "potassium_mg": 0,
              "sodium_mg": 0,
              "active_compound": "",
              "preparation_note": ""
            }}
          ],
          "why_this_meal": "",
          "synergistic_combination": "",
          "body_process_activated": "",
          "physical_activity": "",
          "activity_duration": "",
          "activity_benefit": ""
        }}
      ]
    }}
  ],
  "weekly_tips": [],
  "food_science_notes": []
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=3500, temperature=0.3
    )
    if result and isinstance(result, dict):
        result = _validate_calories(result, effective_cal)
        result = _enrich_gl_chrono(result, disease)
        cache_set(cache_key, result)
    return result if isinstance(result, dict) else {}


def generate_meal_swap(
    original_meal, condition,
    calorie_target, region,
    disliked_foods=None
):
    """
    Fix 22: Now receives and uses disliked_foods list
    """
    dislike_note = ""
    if disliked_foods:
        dislike_note = (
            f"EXCLUDE these disliked foods: "
            f"{', '.join(disliked_foods)}"
        )
    prompt = f"""
Replace this meal with an equally nutritious
alternative.
Original: {json.dumps(original_meal)}
Condition: {condition}
Target calories: {calorie_target} kcal
Region: {region}
{dislike_note}
Same total calories. Different foods.
Return same JSON structure with different foods.
"""
    return safe_groq_call(prompt, max_tokens=800)