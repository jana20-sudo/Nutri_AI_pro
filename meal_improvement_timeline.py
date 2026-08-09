"""
meal_improvement_timeline.py — NEW FILE
Predicts Week 1, Week 4, Week 8 health improvements
from following the specific meal plan.
Connected to actual biomarker values, not generic.
"""
from utils import safe_groq_call, safe_float
from pubmed_fetcher import search_pubmed
from cache_manager import cache_get, cache_set
import json


def generate_improvement_timeline(
    biomarkers, meal_plan, condition,
    prescription_foods=None, patient_info=None
):
    """
    Generates precise week-by-week improvement predictions
    tied to the specific meal plan and patient values.

    This is the core of the personalisation vision:
    - Week 1: what changes in body
    - Week 4: measurable values expected
    - Week 8: target achievable
    - Following full protocol: 5-year impact
    """
    fasting  = safe_float(biomarkers.get("fasting_glucose"), 0)
    hba1c    = safe_float(biomarkers.get("hba1c"), 0)
    sys_bp   = safe_float(biomarkers.get("systolic_bp"), 0)
    weight   = safe_float(
        (patient_info or {}).get("weight_kg"), 0
    )
    bmi      = safe_float(
        (patient_info or {}).get("bmi"), 0
    )
    age      = safe_float(
        (patient_info or {}).get("age"), 40
    )

    # Extract key foods from meal plan
    plan_foods = []
    for day in (meal_plan or {}).get("weekly_plan", [])[:3]:
        if not isinstance(day, dict): continue
        for meal in day.get("meals", []):
            if not isinstance(meal, dict): continue
            for item in meal.get("items", [])[:2]:
                if isinstance(item, dict):
                    food = item.get("food", "")
                    if food:
                        plan_foods.append(food)

    prescription_list = []
    if prescription_foods:
        for f in prescription_foods[:3]:
            if isinstance(f, dict) and f.get("food"):
                prescription_list.append(
                    f"{f['food']} — "
                    f"{f.get('exact_amount','')} at "
                    f"{f.get('exact_time','')}"
                )

    cache_key = (
        f"timeline_{condition[:20]}_"
        f"{fasting}_{hba1c}_{sys_bp}_{bmi}"
    )
    cached = cache_get(cache_key)
    if cached: return cached

    # Fetch intervention evidence
    papers = search_pubmed(
        f"{condition} dietary intervention "
        f"week improvement randomised clinical trial",
        max_papers=8
    )
    evidence = "\n".join([
        f"PMID:{p.get('pmid','')}: "
        f"{p.get('abstract','')[:200]}"
        for p in papers[:4]
    ])

    prompt = f"""
Clinical dietitian predicting week-by-week improvements.

Patient's CURRENT VALUES:
- Fasting glucose: {fasting} mg/dL
- HbA1c: {hba1c}%
- Systolic BP: {sys_bp} mmHg
- Weight: {weight} kg | BMI: {bmi}
- Age: {age}
- Condition: {condition}

Meal plan key foods (7-day plan):
{', '.join(plan_foods[:10])}

Precise prescription (3 foods with exact doses):
{chr(10).join(prescription_list)}

Published evidence:
{evidence[:1500]}

Based on THIS patient's SPECIFIC VALUES and
THESE specific foods, predict improvements.
Use actual numbers — not ranges.
Be realistic and specific.

Return JSON only:
{{
  "baseline_values": {{
    "fasting_glucose": {fasting},
    "hba1c": {hba1c},
    "systolic_bp": {sys_bp},
    "weight_kg": {weight},
    "bmi": {bmi}
  }},
  "week_1": {{
    "what_is_happening_in_body": "biochemical explanation",
    "visible_changes": ["symptom 1","symptom 2"],
    "expected_glucose": 0,
    "expected_bp": 0,
    "expected_weight": 0,
    "energy_change": "how energy levels shift",
    "digestive_change": "how gut responds",
    "key_mechanism": "why this happens",
    "patient_experience": "what patient will feel"
  }},
  "week_4": {{
    "expected_fasting_glucose": 0,
    "glucose_reduction_percent": 0,
    "expected_hba1c": 0,
    "expected_weight": 0,
    "weight_loss_kg": 0,
    "expected_bp": 0,
    "measurable_improvements": ["specific improvement 1"],
    "lab_test_to_confirm": "which test to do",
    "what_doctor_will_notice": "",
    "pmid_basis": ""
  }},
  "week_8": {{
    "expected_fasting_glucose": 0,
    "glucose_reduction_total_percent": 0,
    "expected_hba1c": 0,
    "expected_weight": 0,
    "total_weight_loss_kg": 0,
    "expected_bp": 0,
    "clinical_milestone": "what clinical milestone achieved",
    "risk_reduction_percent": 0,
    "should_retest": true,
    "recommended_tests": ["test 1","test 2"]
  }},
  "month_3": {{
    "expected_fasting_glucose": 0,
    "expected_hba1c": 0,
    "expected_weight": 0,
    "expected_bp": 0,
    "quality_of_life_improvement": "",
    "medication_review_needed": true,
    "pmid_basis": ""
  }},
  "year_1": {{
    "expected_fasting_glucose": 0,
    "expected_hba1c": 0,
    "expected_weight": 0,
    "complication_risk_reduction_percent": 0,
    "what_changes_permanently": "",
    "adherence_note": "what happens if adherence drops"
  }},
  "year_5_summary": {{
    "expected_health_status": "",
    "complication_probability_vs_no_intervention": "",
    "quality_of_life_score": "8/10 estimated",
    "key_message": "one sentence for the patient"
  }},
  "motivation_message": "personal message to patient",
  "critical_first_step": "single most important action this week",
  "if_patient_stops_at_week_4": "what happens to health",
  "confidence_basis": "which study this is based on",
  "pmid_citation": ""
}}
"""
    result = safe_groq_call(
        prompt, max_tokens=2500, temperature=0.1
    )
    if result and isinstance(result, dict):
        cache_set(cache_key, result)
    return result if isinstance(result, dict) else {}


def display_improvement_timeline(timeline, patient_name=""):
    """
    Call this from app.py after meal plan is generated.
    Shows the complete improvement journey in one view.
    """
    import streamlit as st

    if not timeline or "error" in timeline:
        st.warning("Improvement timeline not available.")
        return

    baseline = timeline.get("baseline_values", {})
    name_str = f"for {patient_name}" if patient_name else ""

    st.subheader(f"📈 Your Improvement Journey {name_str}")
    st.caption(
        "Predictions based on published clinical trials. "
        "Individual results vary. Monitor weekly."
    )

    # Baseline vs targets
    fasting_now = safe_float(
        baseline.get("fasting_glucose"), 0
    )
    w8 = timeline.get("week_8", {})
    m3 = timeline.get("month_3", {})
    y1 = timeline.get("year_1", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Now",
        f"{fasting_now} mg/dL",
        "Baseline glucose"
    )
    col2.metric(
        "Week 8",
        f"{w8.get('expected_fasting_glucose','?')} mg/dL",
        delta=f"-{w8.get('glucose_reduction_total_percent','?')}%"
    )
    col3.metric(
        "Month 3",
        f"{m3.get('expected_hba1c','?')}% HbA1c",
        "Target range"
    )
    col4.metric(
        "Year 1",
        f"{y1.get('complication_risk_reduction_percent','?')}%",
        "Risk reduction"
    )

    # Motivation message
    motivation = timeline.get("motivation_message", "")
    if motivation:
        st.success(f"💪 {motivation}")

    # Critical first step
    first_step = timeline.get("critical_first_step", "")
    if first_step:
        st.info(f"🎯 Start here: **{first_step}**")

    # Week-by-week detail
    week_tabs = st.tabs([
        "Week 1", "Week 4", "Week 8",
        "Month 3", "Year 1", "5 Years"
    ])

    # Week 1
    with week_tabs[0]:
        w1 = timeline.get("week_1", {})
        if w1:
            st.markdown(
                f"**🔬 What is happening in your body:**\n\n"
                f"{w1.get('what_is_happening_in_body','')}"
            )
            visible = w1.get("visible_changes", [])
            if visible:
                st.subheader("What you will notice:")
                for v in visible:
                    st.write(f"• {v}")
            wc1, wc2, wc3 = st.columns(3)
            wc1.metric(
                "Expected Glucose",
                f"{w1.get('expected_glucose','?')} mg/dL"
            )
            wc2.metric(
                "Expected BP",
                f"{w1.get('expected_bp','?')} mmHg"
            )
            wc3.metric(
                "Expected Weight",
                f"{w1.get('expected_weight','?')} kg"
            )
            if w1.get("energy_change"):
                st.write(
                    f"⚡ **Energy:** {w1['energy_change']}"
                )
            if w1.get("patient_experience"):
                st.info(
                    f"💭 {w1['patient_experience']}"
                )

    # Week 4
    with week_tabs[1]:
        w4 = timeline.get("week_4", {})
        if w4:
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric(
                "Glucose",
                f"{w4.get('expected_fasting_glucose','?')} mg/dL",
                delta=f"-{w4.get('glucose_reduction_percent','?')}%"
            )
            wc2.metric(
                "HbA1c",
                f"{w4.get('expected_hba1c','?')}%"
            )
            wc3.metric(
                "Weight",
                f"{w4.get('expected_weight','?')} kg",
                delta=f"-{w4.get('weight_loss_kg','?')} kg"
            )
            wc4.metric(
                "BP",
                f"{w4.get('expected_bp','?')} mmHg"
            )
            for imp in w4.get("measurable_improvements", []):
                st.success(f"✅ {imp}")
            if w4.get("lab_test_to_confirm"):
                st.info(
                    f"🧪 Test to confirm: "
                    f"{w4['lab_test_to_confirm']}"
                )
            if w4.get("pmid_basis"):
                st.caption(
                    f"Evidence: {w4['pmid_basis']}"
                )

    # Week 8
    with week_tabs[2]:
        w8_data = timeline.get("week_8", {})
        if w8_data:
            wc1, wc2, wc3 = st.columns(3)
            wc1.metric(
                "Glucose",
                f"{w8_data.get('expected_fasting_glucose','?')} mg/dL"
            )
            wc2.metric(
                "HbA1c",
                f"{w8_data.get('expected_hba1c','?')}%"
            )
            wc3.metric(
                "Weight Loss",
                f"{w8_data.get('total_weight_loss_kg','?')} kg total"
            )
            milestone = w8_data.get("clinical_milestone","")
            if milestone:
                st.success(f"🏆 Milestone: {milestone}")
            risk_r = w8_data.get("risk_reduction_percent","")
            if risk_r:
                st.info(
                    f"📉 Risk reduction: {risk_r}% lower "
                    f"than without intervention"
                )
            if w8_data.get("should_retest"):
                tests = w8_data.get("recommended_tests",[])
                if tests:
                    st.warning(
                        f"🧪 Get retested at Week 8: "
                        f"{', '.join(tests)}"
                    )

    # Month 3
    with week_tabs[3]:
        m3_data = timeline.get("month_3", {})
        if m3_data:
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Glucose",
                       f"{m3_data.get('expected_fasting_glucose','?')} mg/dL")
            mc2.metric("HbA1c",
                       f"{m3_data.get('expected_hba1c','?')}%")
            mc3.metric("Weight",
                       f"{m3_data.get('expected_weight','?')} kg")
            qol = m3_data.get("quality_of_life_improvement","")
            if qol:
                st.success(f"✅ {qol}")
            if m3_data.get("medication_review_needed"):
                st.warning(
                    "⚕️ Medication review recommended at 3 months — "
                    "dose may need to be adjusted based on improvement"
                )

    # Year 1
    with week_tabs[4]:
        y1_data = timeline.get("year_1", {})
        if y1_data:
            yc1, yc2, yc3 = st.columns(3)
            yc1.metric("Glucose",
                       f"{y1_data.get('expected_fasting_glucose','?')} mg/dL")
            yc2.metric("HbA1c",
                       f"{y1_data.get('expected_hba1c','?')}%")
            yc3.metric("Risk Reduction",
                       f"{y1_data.get('complication_risk_reduction_percent','?')}%")
            permanent = y1_data.get("what_changes_permanently","")
            if permanent:
                st.success(f"🏆 Permanent change: {permanent}")
            adherence = y1_data.get("adherence_note","")
            if adherence:
                st.warning(f"⚠️ If adherence drops: {adherence}")

    # 5 Years
    with week_tabs[5]:
        y5_data = timeline.get("year_5_summary", {})
        if y5_data:
            st.subheader(
                f"🔮 Your health at Year 5: "
                f"{y5_data.get('expected_health_status','')}"
            )
            st.info(
                f"Complication risk vs no intervention: "
                f"{y5_data.get('complication_probability_vs_no_intervention','')}"
            )
            st.success(
                f"Quality of life: "
                f"{y5_data.get('quality_of_life_score','')}"
            )
            key_msg = y5_data.get("key_message","")
            if key_msg:
                st.markdown(
                    f"<div style='background:#00e87a15;"
                    f"border:2px solid #00e87a;"
                    f"border-radius:12px;padding:20px;"
                    f"text-align:center'>"
                    f"<h3 style='color:#00e87a'>"
                    f"💚 {key_msg}</h3></div>",
                    unsafe_allow_html=True
                )

    # What happens if patient stops
    stop_note = timeline.get("if_patient_stops_at_week_4","")
    if stop_note:
        with st.expander("⚠️ What happens if I stop at Week 4?"):
            st.error(stop_note)

    confidence = timeline.get("confidence_basis","")
    pmid       = timeline.get("pmid_citation","")
    if confidence:
        st.caption(
            f"Based on: {confidence} "
            f"{'(' + pmid + ')' if pmid else ''}"
        )