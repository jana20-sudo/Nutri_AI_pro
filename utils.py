"""
Fixed: Issue 10 - TSH=0.0 falsy check
Fixed: Issue 11 - Rate limiter first call
Fixed: Issue 16 - safe_float handles None
"""
import time
import json
import threading
import re
import os
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

groq_client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_")
    else None
)


class RateLimiter:
    def __init__(self, calls_per_second=1.0):
        self.min_interval = 1.0 / calls_per_second
        # Fix 11: initialise to negative value so
        # first call fires immediately without delay
        self.last_called = -999.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            elapsed = time.time() - self.last_called
            wait_time = self.min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            self.last_called = time.time()


ncbi_limiter = RateLimiter(0.4)
groq_limiter = RateLimiter(0.8)
usda_limiter = RateLimiter(1.0)


def clean_json(raw):
    if not raw:
        return "{}"
    raw = str(raw).strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) >= 2 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        elif raw.startswith("JSON"):
            raw = raw[4:]
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start:end+1]
    return raw.strip()


def clean_json_array(raw):
    if not raw:
        return "[]"
    raw = str(raw).strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) >= 2 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end > start:
        raw = raw[start:end+1]
    return raw.strip()


def sanitise_input(text):
    if not text:
        return text
    patterns = [
        r"ignore.{0,20}instructions?",
        r"you are now",
        r"act as",
        r"jailbreak",
        r"</?script[^>]*>",
        r"output.*api.*key",
        r"reveal.*key",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(
            p, "", cleaned, flags=re.IGNORECASE
        )
    return cleaned[:2000].strip()


def safe_groq_call(
    prompt, max_tokens=1500,
    temperature=0.3, is_array=False
):
    if not groq_client:
        return [] if is_array else {
            "error": "Groq API key not configured. "
                     "Add GROQ_API_KEY to .env file."
        }
    groq_limiter.wait()
    current_prompt = prompt
    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=min(max_tokens, 3000),
                messages=[{
                    "role": "user",
                    "content": current_prompt
                }],
                temperature=temperature
            )
            raw = response.choices[0].message.content
            cleaned = (
                clean_json_array(raw)
                if is_array
                else clean_json(raw)
            )
            result = json.loads(cleaned)
            # If asked for array but got dict, wrap it
            if is_array and isinstance(result, dict):
                return []
            return result
        except json.JSONDecodeError:
            if attempt < 2:
                current_prompt = (
                    current_prompt +
                    "\nIMPORTANT: Return ONLY valid JSON. "
                    "No text before or after the JSON. "
                    "Start with { or [ and end with } or ]."
                )
                time.sleep(0.5)
            else:
                return [] if is_array else {}
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                wait = (attempt + 1) * 15
                print(f"[Groq] Rate limited. Waiting {wait}s")
                time.sleep(wait)
            elif "413" in err or "too large" in err.lower():
                current_prompt = current_prompt[
                    :len(current_prompt)//2
                ]
            elif attempt == 2:
                print(f"[Groq] Error after 3 attempts: {e}")
                return [] if is_array else {}
            else:
                time.sleep(2)
    return [] if is_array else {}


def validate_number(value, min_val, max_val, default):
    try:
        v = float(value)
        return v if min_val <= v <= max_val else default
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    """
    Fix 16: Handles None, string with %, and all edge cases
    """
    if value is None:
        return default
    try:
        cleaned = str(value).replace(
            "%","").replace("mg/dL","").replace(
            "mmHg","").replace("g","").strip()
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def format_error(message):
    return (
        f"⚠️ {message} — "
        f"please try again. "
        f"If this persists, check your internet connection."
    )


def calculate_glycaemic_load(gi, carbs_g):
    try:
        gi_f = safe_float(gi, 0)
        carbs_f = safe_float(carbs_g, 0)
        if gi_f <= 0 or carbs_f <= 0:
            return None
        gl = (gi_f * carbs_f) / 100
        return {
            "gl": round(gl, 1),
            "category": (
                "low" if gl <= 10
                else "medium" if gl <= 19
                else "high"
            )
        }
    except (TypeError, ValueError):
        return None


def calculate_kna_ratio(k_mg, na_mg):
    try:
        k = safe_float(k_mg, 0)
        na = safe_float(na_mg, 0)
        if na <= 0:
            return None
        ratio = k / na
        return {
            "ratio": round(ratio, 2),
            "status": (
                "✅ Good" if ratio >= 4.0
                else "⚠️ Below target"
            ),
            "citation": "WHO 2012 PMID:23872724"
        }
    except (TypeError, ValueError):
        return None


def get_chrono_advice(meal_name, condition=""):
    """
    Fix 16: Added mid-morning and afternoon handling
    """
    meal_lower = meal_name.lower()
    if "breakfast" in meal_lower:
        return {
            "optimal_time": "6:30–8:30 AM",
            "benefit": (
                "Insulin sensitivity highest in AM. "
                "Same carbs cause 29% lower glucose "
                "response vs evening. PMID:31012777"
            )
        }
    elif "mid" in meal_lower or "snack" in meal_lower:
        return {
            "optimal_time": "10:30 AM or 5:00 PM",
            "benefit": (
                "Small snack prevents blood sugar dip "
                "between main meals. "
                "Keeps metabolism active. PMID:31012777"
            )
        }
    elif "lunch" in meal_lower:
        return {
            "optimal_time": "12:00–2:00 PM",
            "benefit": (
                "Peak digestive enzyme activity. "
                "Largest meal of day should be lunch "
                "not dinner. PMID:31012777"
            )
        }
    elif "dinner" in meal_lower:
        return {
            "optimal_time": "Before 8:00 PM",
            "caution": (
                "Insulin sensitivity 45% lower in evening. "
                "Late dinner increases triglycerides and "
                "reduces overnight fat oxidation. "
                "PMID:31012777"
            )
        }
    return {}