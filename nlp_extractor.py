"""
Fixed: Issue 15 - generate_final_report
always returns string
"""
import json
from utils import safe_groq_call
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set


def extract_insights_from_papers(disease, papers):
    if not papers:
        return {}
    cache_key = f"insights_{disease[:40]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    abstracts = ""
    for i, p in enumerate(papers[:12]):
        abstracts += (
            f"\nPaper {i+1} "
            f"(PMID:{p.get('pmid','')}):\n"
            f"Title: {p.get('title','')}\n"
            f"Abstract: {p.get('abstract','')[:300]}\n"
        )
    prompt = f"""
Clinical nutritionist reading research papers about:
{disease}
Extract ONLY from these abstracts. No prior knowledge.

{abstracts}

Return JSON only:
{{
  "condition_explanation": "3-4 sentence explanation",
  "normal_ranges": "biomarker ranges mentioned",
  "pathophysiology": "what happens in body",
  "causing_factors": [],
  "beneficial_nutrients": [
    {{
      "nutrient": "name",
      "mechanism": "biochemical mechanism from papers",
      "evidence_strength": "strong/moderate/limited",
      "pmid_source": "PMID number"
    }}
  ],
  "beneficial_foods": [],
  "foods_to_avoid": [],
  "lifestyle_factors": [],
  "key_references": []
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=2000, temperature=0.1
    )
    if result and isinstance(result, dict):
        cache_set(cache_key, result)
    return result if isinstance(result, dict) else {}


def generate_follow_up_questions(disease, user_context):
    prompt = f"""
Clinical nutritionist. Patient has: {disease}
Current info: {json.dumps(user_context)[:500]}
Generate 4 targeted clinical follow-up questions.
Return JSON array only:
[{{"question": "text", "purpose": "clinical reason"}}]
"""
    result = safe_groq_call(
        prompt, max_tokens=600, is_array=True
    )
    return result if isinstance(result, list) else []


def generate_final_report(
    disease, insights, user_context, ranked_foods
):
    """
    Fix 15: Always returns string, never dict.
    """
    prompt = f"""
Write a clinical nutrition report as flowing text.
Patient: {user_context.get('name','Patient')}
Age: {user_context.get('age')} |
BMI: {user_context.get('bmi')}
Condition: {disease}
Top foods: {ranked_foods}
Research insights:
{json.dumps(insights)[:1000]}

Write as plain paragraphs (not JSON):
1. What is happening biochemically
2. Why their values are concerning
3. For each top food — exact nutrient and mechanism
4. Foods to avoid and reasons
5. Monitoring plan

Cite PMIDs. Evidence-based. Clear English.
Do NOT return JSON. Return plain text report only.
"""
    response = safe_groq_call(
        prompt, max_tokens=2500, temperature=0.3
    )
    # Fix 15: Handle all possible return types
    if isinstance(response, str) and len(response) > 50:
        return response
    elif isinstance(response, dict):
        # Extract any text content from dict
        for key in [
            "report","content","text","response"
        ]:
            if key in response and response[key]:
                return str(response[key])
        # Last resort: convert dict to readable text
        parts = []
        for k, v in response.items():
            if v and k not in ["error"]:
                parts.append(f"**{k}:** {v}")
        if parts:
            return "\n\n".join(parts)
    return (
        f"Clinical Report for {disease}\n\n"
        f"Patient: {user_context.get('name','')}\n"
        f"Condition: {disease}\n"
        f"Top Recommended Foods: "
        f"{', '.join(str(f) for f in ranked_foods[:5])}\n\n"
        f"Please regenerate for full clinical report."
    )