import json
from utils import safe_groq_call, sanitise_input
from cache_manager import cache_get, cache_set

def map_symptoms_to_medical(user_text):
    if not user_text:
        return {}
    clean = sanitise_input(user_text)
    cache_key = f"sym_{clean[:60]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    prompt = f"""
You are a medical AI. Convert patient language to clinical terms.
Handle English, Tamil, Hindi, mixed language.

Patient says: "{clean}"

Return JSON only:
{{
  "identified_symptoms": [
    {{
      "patient_said": "exact phrase",
      "medical_term": "clinical term",
      "possible_conditions": ["condition1"],
      "urgency": "emergency/high/medium/low",
      "body_system": "cardiovascular/endocrine/etc"
    }}
  ],
  "extracted_measurements": [
    {{
      "name": "blood pressure",
      "value": "160/100",
      "unit": "mmHg",
      "status": "high/normal/low"
    }}
  ],
  "primary_condition_guess": "most likely condition",
  "pubmed_search_keywords": ["keyword1 nutrition"],
  "is_emergency": false,
  "emergency_message": "",
  "missing_information": ["what would help diagnose"]
}}
"""
    result = safe_groq_call(prompt, max_tokens=1000, temperature=0.1)
    if result:
        cache_set(cache_key, result)
    return result or {}


def auto_collect_missing_data(symptom_map):
    missing = symptom_map.get("missing_information", [])
    if not missing:
        return []
    prompt = f"""
Generate 3 clinical follow-up questions for missing: {missing}
Make questions conversational not form-like.
Return JSON array only:
[{{"question": "text", "purpose": "clinical reason"}}]
"""
    result = safe_groq_call(
        prompt, max_tokens=500, is_array=True
    )
    return result if isinstance(result, list) else []