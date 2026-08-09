"""
Fixed: Issue 19 - model created once not per call
Fixed: Issue 30 - single model instance
"""
import json
from cache_manager import cache_get, cache_set
from config import GEMINI_API_KEY, GEMINI_MODEL, _key_valid

# Fix 19 and 30: Module-level single instance
_gemini_model = None
_gemini_error = None


def _get_gemini_model():
    """
    Fix 19: Returns cached model instance.
    Only creates once per session.
    """
    global _gemini_model, _gemini_error
    if _gemini_model is not None:
        return _gemini_model, None
    if _gemini_error is not None:
        return None, _gemini_error
    if not _key_valid(GEMINI_API_KEY):
        _gemini_error = (
            "Gemini API key not configured. "
            "Add GEMINI_API_KEY to .env file."
        )
        return None, _gemini_error
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(
            GEMINI_MODEL
        )
        return _gemini_model, None
    except ImportError:
        _gemini_error = (
            "google-generativeai not installed. "
            "Run: pip install google-generativeai"
        )
        return None, _gemini_error
    except Exception as e:
        _gemini_error = str(e)
        return None, _gemini_error


def analyze_food_image(image_bytes, user_conditions=None):
    model, err = _get_gemini_model()
    if not model:
        return {"error": err}
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        conditions_ctx = (
            f"Patient conditions: "
            f"{', '.join(user_conditions)}"
            if user_conditions else ""
        )
        prompt = f"""
Clinical nutritionist analysing food photo.
{conditions_ctx}
Identify all visible foods. Return JSON only:
{{
  "foods_detected": [
    {{
      "name": "", "portion_estimate": "",
      "calories": 0, "protein_g": 0,
      "carbs_g": 0, "fat_g": 0,
      "fiber_g": 0, "sodium_mg": 0,
      "gi": 0, "health_score": 7.5,
      "key_nutrients": []
    }}
  ],
  "total_calories": 0,
  "total_protein_g": 0,
  "meal_type": "breakfast/lunch/dinner/snack",
  "health_rating": "excellent/good/moderate/poor",
  "condition_compatibility": {{
    "good_for": [], "bad_for": []
  }},
  "improvement_suggestions": [],
  "eat_this_because": "biochemical explanation"
}}
"""
        response = model.generate_content([prompt, img])
        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {"error": str(e)}

def analyze_indian_thali(image_bytes, patient_context=None):
    """
    Specifically designed for South Indian thali analysis.
    Calculates total meal GI, K:Na ratio, protein adequacy,
    and condition compatibility for the whole plate.
    """
    model, err = _get_gemini_model()
    if not model:
        return {"error": err}

    conditions = []
    glucose    = 0
    if patient_context and isinstance(patient_context, dict):
        disease = patient_context.get("disease","")
        if disease:
            conditions.append(disease)
        glucose = safe_float(
            patient_context.get("glucose"), 0
        )

    condition_ctx = (
        f"Patient has: {', '.join(conditions)}. "
        f"Fasting glucose: {glucose} mg/dL."
        if conditions else ""
    )

    try:
        from PIL import Image
        import io
        img    = Image.open(io.BytesIO(image_bytes))
        prompt = f"""
You are a clinical nutritionist analysing an Indian thali.
{condition_ctx}

Analyse this plate as a COMPLETE MEAL, not individual items.
Calculate the TOTAL nutritional impact of eating everything.

Return JSON only:
{{
  "plate_type": "South Indian/North Indian/Mixed",
  "items_identified": [
    {{
      "item": "rice",
      "estimated_portion_g": 200,
      "gi": 72,
      "carbs_g": 44,
      "protein_g": 4,
      "fat_g": 0.5,
      "fiber_g": 0.5,
      "calories": 200,
      "potassium_mg": 55,
      "sodium_mg": 5
    }}
  ],
  "total_meal": {{
    "total_calories": 0,
    "total_carbs_g": 0,
    "total_protein_g": 0,
    "total_fat_g": 0,
    "total_fiber_g": 0,
    "total_potassium_mg": 0,
    "total_sodium_mg": 0,
    "meal_gi_weighted": 0,
    "meal_glycaemic_load": 0,
    "kna_ratio": 0,
    "protein_adequacy_percent": 0
  }},
  "condition_analysis": {{
    "suitable_for_condition": true,
    "specific_concern": "",
    "biggest_issue": "e.g. too much white rice — GL 45",
    "biggest_strength": "e.g. excellent sambar protein"
  }},
  "swaps_to_improve": [
    {{
      "current_item": "white rice 200g",
      "swap_to": "parboiled rice 150g",
      "reason": "GI 38 vs 72 — reduces GL by 40%",
      "impact": "glucose spike reduced by 35%"
    }}
  ],
  "meal_timing_advice": "",
  "what_to_add": "one simple addition to improve nutrition",
  "overall_score": 7.5,
  "clinical_verdict": "suitable/avoid/modify"
}}
"""
        response = model.generate_content([prompt, img])
        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

        # Auto-log to session if patient is logged in
        result["logged_to_diary"] = False
        return result

    except Exception as e:
        return {"error": str(e)}


def analyze_food_label(image_bytes, patient_context=None):
    """
    Reads packaged food nutrition label.
    Tells patient if this product is suitable for their condition.
    """
    model, err = _get_gemini_model()
    if not model:
        return {"error": err}

    disease = ""
    if patient_context and isinstance(patient_context, dict):
        disease = patient_context.get("disease","")

    try:
        from PIL import Image
        import io
        img    = Image.open(io.BytesIO(image_bytes))
        prompt = f"""
Read this nutrition label on a packaged food product.
Patient condition: {disease}

Return JSON only:
{{
  "product_name": "",
  "serving_size_g": 0,
  "per_serving": {{
    "calories": 0,
    "total_fat_g": 0,
    "saturated_fat_g": 0,
    "sodium_mg": 0,
    "total_carbs_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "protein_g": 0
  }},
  "ingredients_of_concern": [],
  "additives_found": [],
  "verdict_for_condition": "suitable/avoid/occasionally",
  "reason": "why suitable or not for this patient",
  "daily_budget_impact": {{
    "sodium_percent_of_daily_limit": 0,
    "sugar_percent_of_daily_limit": 0,
    "calorie_percent_of_daily_target": 0
  }},
  "better_alternative": "suggest a better product or food"
}}
"""
        response = model.generate_content([prompt, img])
        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {"error": str(e)}