import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os

st.set_page_config(
    page_title="NutriAI Pro",
    page_icon="🔬",
    layout="wide"
)

# ── Password protection ──
def check_password():
    import config
    if not config.APP_PASSWORD:
        return True
    if st.session_state.get("authenticated"):
        return True
    st.markdown("""
    <div style='max-width:400px;margin:100px auto;
    text-align:center;padding:30px;
    background:#0d1a24;border-radius:16px;
    border:1px solid #1a3048'>
    <h2 style='color:#00ff88'>🔬 NutriAI Pro</h2>
    <p style='color:#aaa'>Enter access password</p>
    </div>
    """, unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password",
                        key="pwd_input")
    if st.button("Enter"):
        if pwd == config.APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# ── Import error boundary ──
IMPORT_ERRORS = []
try:
    from config import (MISSING_KEYS, normalise_condition,
                        REFERENCE_RANGES)
    from utils import (safe_groq_call, sanitise_input,
                       format_error, validate_number,
                       calculate_glycaemic_load,
                       calculate_kna_ratio, safe_float)
    from pubmed_fetcher import search_pubmed
    from usda_fetcher import (fetch_foods_for_nutrients,
                               rank_foods_by_nutrients)
    from symptom_mapper import (map_symptoms_to_medical,
                                 auto_collect_missing_data)
    from nlp_extractor import (extract_insights_from_papers,
                                generate_follow_up_questions,
                                generate_final_report)
    from metabolic_profiler import (classify_metabolic_type,
                                     calculate_personalised_bmr)
    from chatbot import get_chat_response, extract_profile_from_chat
    from disease_predictor import predict_disease_risk
    from meal_planner import generate_meal_plan, generate_meal_swap
    from drug_nutrient import check_drug_nutrient_interactions
    from microbiome import generate_microbiome_recommendations
    from report_scanner import extract_report_text
    from report_analyser import (extract_medical_values,
                                  generate_report_based_meal_plan,
                                  generate_foods_to_avoid,
                                  generate_health_benefits_timeline)
    from progress_tracker import (save_progress, load_progress,
                                   get_progress_charts)
    from live_food_science import (GI_DATABASE, SYNERGIES,
                                    PHYTOCHEMICALS,
                                    get_phytochemical)
    from food_layer.seasonal_foods import get_seasonal_foods
    from food_layer.recipe_generator import (generate_recipe,
                                              generate_leftover_meal)
    from food_layer.bioavailability import analyse_bioavailability
    from intelligence.preference_filter import filter_meal_plan
    from intelligence.longitudinal import (
        load_patient_history, save_week_entry,
        analyse_longitudinal_trend)
    from intelligence.translator import (translate_report,
                                          SUPPORTED_LANGUAGES)
    from tracking.symptom_diary import (save_diary_entry,
                                         load_diary,
                                         correlate_symptoms_with_food)
    from tracking.fasting_advisor import get_fasting_protocol
    from tracking.lab_predictor import predict_lab_values
    from medical.medication_scheduler import build_medication_schedule
    from medical.guideline_comparator import compare_guidelines
    from medical.supplement_builder import build_supplement_stack
    from medical.pdf_generator import generate_pdf_report
    from regional_foods import get_regional_alternatives
except ImportError as e:
    IMPORT_ERRORS.append(str(e))

# ── Styles ──
st.markdown("""
<style>
.main{background:#f0f2f6}
.chat-user{background:#0084ff;color:white;
  padding:12px 16px;border-radius:18px 18px 4px 18px;
  margin:6px 0;max-width:75%;margin-left:auto;
  font-size:15px}
.chat-ai{background:white;color:#1a1a1a;
  padding:12px 16px;border-radius:18px 18px 18px 4px;
  margin:6px 0;max-width:75%;
  box-shadow:0 1px 4px rgba(0,0,0,.1);font-size:15px}
.food-card{background:white;padding:14px;
  border-radius:12px;border-left:5px solid #28a745;
  margin:7px 0;box-shadow:0 2px 5px rgba(0,0,0,.07)}
.avoid-card{background:#fff5f5;padding:14px;
  border-radius:12px;border-left:5px solid #dc3545;margin:7px 0}
.science-box{background:#f0fff4;padding:12px;
  border-radius:8px;border-left:4px solid #20c997;
  margin:6px 0;font-size:0.85em}
</style>
""", unsafe_allow_html=True)

# ── Show warnings ──
if MISSING_KEYS:
    st.warning(
        f"⚠️ Missing API keys: {', '.join(MISSING_KEYS)}. "
        f"Add to .env file."
    )
if IMPORT_ERRORS:
    st.error(
        f"Import errors: {'; '.join(IMPORT_ERRORS)}. "
        f"Run: pip install -r requirements.txt"
    )
    st.stop()

# ── Session defaults ──
DEFAULTS = {
    "stage": "input", "context": {}, "insights": {},
    "questions": [], "ranked_foods": [],
    "chat_history": [], "food_logs": [],
    "meal_plan": {}, "metabolic_profile": {},
    "seasonal_foods": {}, "disliked_foods": []
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Cached API wrappers ──
@st.cache_data(ttl=3600, show_spinner=False)
def cached_pubmed(query, max_papers=30):
    return search_pubmed(query, max_papers)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_usda(nutrient_str):
    return fetch_foods_for_nutrients(json.loads(nutrient_str))

# ── Cross-tab helpers ──
def ctx(key, fallback=None):
    return st.session_state.context.get(key, fallback)

def validate_clinical(value, label, min_v, max_v):
    if value and value != 0:
        if not (min_v <= float(value) <= max_v):
            st.warning(
                f"⚠️ {label}={value} seems unusual "
                f"(expected {min_v}–{max_v}). Please verify."
            )

# ── Meal plan display ──
def show_meal_plan(meal_data, condition="", show_swap=False):
    if not meal_data or "error" in meal_data:
        st.warning(format_error("Meal plan unavailable"))
        return
    weekly = meal_data.get("weekly_plan",[])
    goals = meal_data.get("primary_goals",[])
    sci_notes = meal_data.get("food_science_notes",[])
    subs = meal_data.get("substitutions_made",[])

    if goals:
        st.info(f"🎯 **Goals:** {' | '.join(str(g) for g in goals)}")
    if subs:
        with st.expander("✅ Dietary Substitutions Made"):
            for s in subs:
                st.write(f"• {s}")
    if not weekly:
        return

    days = [d.get("day","Day") for d in weekly if isinstance(d,dict)]
    dtabs = st.tabs(days)
    meal_icons = {
        "breakfast":"🌅","lunch":"☀️","dinner":"🌙",
        "snack":"🥜","mid":"🍎"
    }

    for tab, day in zip(dtabs, weekly):
        if not isinstance(day, dict):
            continue
        with tab:
            total = day.get("total_calories","N/A")
            protein = day.get("total_protein_g","N/A")
            fiber = day.get("total_fiber_g","N/A")
            c1,c2,c3 = st.columns(3)
            c1.metric("🔥 Calories", f"{total} kcal")
            c2.metric("💪 Protein", f"{protein}g")
            c3.metric("🌾 Fiber", f"{fiber}g")

            kna = day.get("kna_ratio",{})
            if kna and isinstance(kna, dict):
                st.caption(
                    f"K:Na ratio: {kna.get('ratio','N/A')}:1 "
                    f"— {kna.get('status','')} "
                    f"(WHO target 4:1)"
                )
            if isinstance(total,(int,float)):
                st.progress(min(total/2000,1.0))

            for meal in day.get("meals",[]):
                if not isinstance(meal, dict):
                    continue
                mn = meal.get("meal","").lower()
                icon = next(
                    (v for k,v in meal_icons.items() if k in mn),
                    "🍽️"
                )
                mc = (meal.get("total_meal_calories") or
                      meal.get("meal_calories") or
                      meal.get("calories") or "N/A")

                with st.expander(
                    f"{icon} **{meal.get('meal','')}** "
                    f"({meal.get('time','')}) — {mc} kcal"
                ):
                    for item in meal.get("items",[]):
                        if isinstance(item, str):
                            st.markdown(
                                f"<div class='food-card'>"
                                f"🥗 {item}</div>",
                                unsafe_allow_html=True
                            )
                        elif isinstance(item, dict):
                            food = (item.get("food") or
                                    item.get("name") or "Food")
                            portion = item.get("portion","")
                            cals = item.get("calories","N/A")
                            prot = item.get("protein_g","N/A")
                            fib = item.get("fiber_g","N/A")
                            gi = item.get("gi","")
                            gi_cit = item.get("gi_citation","")
                            gl = item.get("glycaemic_load",{})
                            compound = (
                                item.get("active_compound") or
                                item.get("active_phytochemical","")
                            )
                            prep = item.get("preparation_note","")

                            gi_txt = ""
                            if gi:
                                gl_txt = ""
                                if gl and isinstance(gl,dict):
                                    gl_txt = (
                                        f" GL={gl.get('gl','')}"
                                        f"({gl.get('category','')})"
                                    )
                                gi_txt = (
                                    f"GI={gi}{gl_txt} "
                                    f"{gi_cit}"
                                )
                            st.markdown(f"""
<div class='food-card'>
<b>{food}</b> — {portion}<br>
🔥{cals} kcal | 💪{prot}g | 🌾{fib}g
{f'<br>📊 {gi_txt}' if gi_txt else ''}
{f'<br>🧪 {compound}' if compound else ''}
{f'<br>📝 {prep}' if prep else ''}
</div>
""", unsafe_allow_html=True)
                            # Show phytochemical from database
                            if compound:
                                phyto = get_phytochemical(compound)
                                if phyto and phyto.get("mechanism"):
                                    st.markdown(
                                        f"<div class='science-box'>"
                                        f"🔬 {phyto['mechanism']} | "
                                        f"{phyto.get('citation','')}"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )

                    why = meal.get("why_this_meal","")
                    if why:
                        st.success(f"💡 **Why:** {why}")
                    synergy = meal.get("synergistic_combination","")
                    if synergy:
                        st.info(f"🤝 **Synergy:** {synergy}")
                    body = meal.get("body_process_activated","")
                    if body:
                        st.write(f"🔬 **Body activates:** {body}")
                    act = meal.get("physical_activity","")
                    dur = meal.get("activity_duration","")
                    act_ben = meal.get("activity_benefit","")
                    if act:
                        st.warning(f"🏃 **Activity:** {act} — {dur}")
                        if act_ben:
                            st.caption(act_ben)
                    else:
                        if "breakfast" in mn:
                            st.warning(
                                "🏃 20-min walk activates "
                                "GLUT4 receptors — reduces "
                                "post-meal glucose 15-30%"
                            )
                        elif "dinner" in mn:
                            st.warning(
                                "🚶 15-min walk regulates "
                                "overnight blood sugar"
                            )
                    # Chronobiology
                    chrono = meal.get("chronobiology",{})
                    if chrono and isinstance(chrono, dict):
                        benefit = (chrono.get("benefit") or
                                   chrono.get("caution",""))
                        if benefit:
                            st.caption(
                                f"⏰ Circadian: {benefit}"
                            )
                    # Meal swap button
                    if show_swap:
                        swap_key = f"swap_{meal.get('meal','')}"
                        if st.button(
                            f"🔄 Swap this meal",
                            key=swap_key
                        ):
                            condition_ctx = (
                                condition or
                                st.session_state.context.get(
                                    "disease","general"
                                )
                            )
                            region = st.session_state.context.get(
                                "region","Tamil Nadu"
                            )
                            with st.spinner("Finding alternative..."):
                                swapped = generate_meal_swap(
                                    meal, condition_ctx,
                                    mc, region
                                )
                            if swapped:
                                st.json(swapped)

            # Calorie pie chart
            meal_names, meal_cals = [], []
            for m in day.get("meals",[]):
                if isinstance(m, dict):
                    mn2 = m.get("meal","")
                    mc2 = (m.get("total_meal_calories") or
                           m.get("meal_calories") or
                           m.get("calories",0))
                    if mn2 and isinstance(mc2,(int,float)):
                        meal_names.append(mn2)
                        meal_cals.append(mc2)
            if meal_names:
                fig = px.pie(
                    names=meal_names, values=meal_cals,
                    title="Calorie Distribution",
                    color_discrete_sequence=px.colors.sequential.Greens
                )
                fig.update_layout(height=280)
                st.plotly_chart(fig, use_container_width=True)

    if sci_notes:
        st.subheader("🔬 Food Science Notes")
        for note in sci_notes:
            if isinstance(note, str):
                st.markdown(
                    f"<div class='science-box'>• {note}</div>",
                    unsafe_allow_html=True
                )

# ── HEADER ──
st.markdown("""
<div style='text-align:center;padding:20px;
background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
border-radius:16px;margin-bottom:20px'>
<h1 style='color:#00ff88;font-size:2.4em;margin:0'>
🔬 NutriAI Pro
</h1>
<p style='color:#aaa;font-size:0.95em;margin:5px 0 0 0'>
Personalised Nutrition Intelligence |
PubMed · USDA · PubChem · FDA · NIH ODS · Groq AI
</p>
<p style='color:#555;font-size:0.8em;margin:3px 0 0 0'>
No hardcoded nutrition data — everything fetched live from
public research databases
</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ──
TAB_NAMES = [
    "💬 AI Doctor", "📋 Report Scanner",
    "📸 Food Vision", "⚠️ Risk Predictor",
    "🧬 Metabolic", "🌿 Indian Foods",
    "📈 Progress", "📝 Manual Input",
    "🔄 Longitudinal", "🌱 Seasonal",
    "👨‍🍳 Recipes", "🔬 Bioavailability",
    "📓 Symptom Diary", "⏰ Fasting",
    "💊 Med Schedule", "📊 Guidelines",
    "💊 Supplements", "📄 PDF Report"
]
tabs = st.tabs(TAB_NAMES)
tab = {name: tabs[i] for i, name in enumerate(TAB_NAMES)}

# ════════════════════════════════════════
# TAB: AI DOCTOR
# ════════════════════════════════════════
with tab["💬 AI Doctor"]:
    st.header("💬 AI Doctor Chat")
    st.caption(
        "Any language — English, Tamil, Hindi, mixed. "
        "Symptoms mapped to medical terms automatically."
    )
    if not st.session_state.chat_history:
        st.markdown("""
<div class='chat-ai'>
👋 Hello! I'm Dr. NutriAI.<br><br>
Tell me anything like:<br>
- "I have chest pain and feel tired"<br>
- "My sugar is 280, HbA1c 8.2"<br>
- "என் ரத்த அழுத்தம் அதிகம்" (Tamil OK)<br>
- "BP 160/100, cholesterol 240, age 45"<br><br>
I'll ask focused questions and build your complete plan.
</div>
""", unsafe_allow_html=True)

    for msg in st.session_state.chat_history:
        css = "chat-user" if msg["role"]=="user" else "chat-ai"
        prefix = "" if msg["role"]=="user" else "🤖 "
        st.markdown(
            f"<div class='{css}'>"
            f"{prefix}{msg['content']}</div>",
            unsafe_allow_html=True
        )

    ci, cs = st.columns([5,1])
    with ci:
        user_input = st.text_input(
            "Message", key="chat_in",
            label_visibility="collapsed",
            placeholder="Describe your health condition..."
        )
    with cs:
        send_btn = st.button("Send 💬", type="primary")

    if send_btn and user_input:
        clean = sanitise_input(user_input)
        with st.spinner("Analysing..."):
            sym = map_symptoms_to_medical(clean)
        if sym.get("is_emergency"):
            st.error(
                f"🚨 **EMERGENCY:** "
                f"{sym.get('emergency_message','')}\n\n"
                f"**Call 108 immediately!**"
            )
        ai_resp = get_chat_response(
            st.session_state.chat_history, clean
        )
        st.session_state.chat_history.append(
            {"role":"user","content":clean}
        )
        st.session_state.chat_history.append(
            {"role":"assistant","content":ai_resp}
        )
        st.rerun()

    with st.expander("🔍 Live Symptom Analysis"):
        if st.session_state.chat_history:
            last_user = next(
                (m["content"] for m in
                 reversed(st.session_state.chat_history)
                 if m["role"]=="user"), ""
            )
            if last_user:
                sm = map_symptoms_to_medical(last_user)
                for s in sm.get("identified_symptoms",[]):
                    if isinstance(s, dict):
                        u = s.get("urgency","low")
                        ic = ("🔴" if u in ["emergency","high"]
                              else "🟡" if u=="medium" else "🟢")
                        st.write(
                            f"{ic} **{s.get('patient_said','')}**"
                            f" → _{s.get('medical_term','')}_"
                        )

    if (len(st.session_state.chat_history) >= 4 and
            st.button("📊 Build Full Plan from Chat",
                      type="primary")):
        with st.spinner("Extracting profile..."):
            profile = extract_profile_from_chat(
                st.session_state.chat_history
            )
        disease = normalise_condition(
            profile.get("chief_complaint","")
        )
        if disease:
            st.session_state.context.update(profile)
            st.session_state.context["disease"] = disease
            prog = st.progress(0,"Fetching papers...")
            papers = cached_pubmed(disease, 30)
            prog.progress(40,"Reading papers...")
            insights = extract_insights_from_papers(disease, papers)
            st.session_state.insights = insights
            prog.progress(70,"Ranking foods...")
            nutrients = [
                n.get("nutrient","")
                for n in insights.get("beneficial_nutrients",[])
                if isinstance(n,dict)
            ]
            if nutrients:
                food_df = fetch_foods_for_nutrients(nutrients)
                ranked = rank_foods_by_nutrients(food_df, nutrients)
                if not ranked.empty:
                    st.session_state.ranked_foods = (
                        ranked["food_name"].head(10).tolist()
                    )
            prog.progress(90,"Generating plan...")
            mp = generate_meal_plan(
                disease,
                st.session_state.ranked_foods,
                1800, st.session_state.context
            )
            st.session_state.meal_plan = mp
            prog.progress(100)
            st.subheader("🍽️ Your Plan")
            show_meal_plan(mp, disease, show_swap=True)
        else:
            st.warning(
                "Please describe your condition more "
                "before generating a plan."
            )

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()
    # In the AI Doctor tab, replace the get_chat_response call with:
    ai_resp = get_chat_response(
        st.session_state.chat_history,
        clean,
        patient_context=st.session_state.context,
        trajectory=st.session_state.get("trajectory", {}),
        prescription=st.session_state.get("prescription", {})
        )
    ai_resp = get_chat_response(
        st.session_state.chat_history,
        qm,
        patient_context=st.session_state.context,
        trajectory=st.session_state.get("trajectory", {}),
        prescription=st.session_state.get("prescription", {})
    )

# ════════════════════════════════════════
# TAB: REPORT SCANNER
# ════════════════════════════════════════
with tab["📋 Report Scanner"]:
    st.header("📋 Medical Report Scanner")
    st.markdown(
        "Upload blood test or diagnostic report — "
        "AI reads every value and builds your nutrition plan"
    )
    uploaded = st.file_uploader(
        "Upload Report (PDF or Image)",
        type=["pdf","jpg","jpeg","png","tiff"]
    )
    c1,c2,c3 = st.columns(3)
    rs_w = c1.number_input("Weight kg",30.0,200.0,70.0,key="rw")
    rs_h = c2.number_input("Height cm",100.0,220.0,165.0,key="rh")
    rs_a = c3.number_input("Age",10,100,30,key="ra")
    rs_g = c1.selectbox("Gender",["Male","Female"],key="rg")
    rs_act = c2.selectbox(
        "Activity",
        ["Sedentary","Light","Moderate","Active"],key="ract"
    )
    rs_reg = c3.selectbox(
        "Region",
        ["Tamil Nadu","Kerala","North India",
         "Karnataka","Andhra Pradesh"],key="rreg"
    )
    rs_diet = c1.selectbox(
        "Diet Type",
        ["No restriction","Vegetarian","Vegan","Jain"],
        key="rdiet"
    )
    rs_allerg = c2.text_input(
        "Allergies", placeholder="peanuts, dairy", key="rallerg"
    )

    act_map = {
        "Sedentary":1.2,"Light":1.375,
        "Moderate":1.55,"Active":1.725
    }

    if uploaded and st.button("🔍 Scan & Analyse", type="primary"):
        prog = st.progress(0,"Reading report...")
        text = extract_report_text(uploaded)
        if not text or len(text.strip()) < 30:
            st.error(format_error(
                "Could not read report. "
                "Try higher quality scan"
            ))
            st.stop()
        if "TESSERACT" in text:
            st.error(
                "Tesseract OCR not found. Install from: "
                "github.com/UB-Mannheim/tesseract/wiki"
            )
            st.stop()
        with st.expander("📝 Extracted Text"):
            st.text(text[:2000])
        prog.progress(15,"Analysing values...")
        md = extract_medical_values(text)
        if not md or "error" in md:
            st.error(format_error("Analysis failed"))
            st.stop()
        # Store in session
        bmi_v = round(rs_w/((rs_h/100)**2),1)
        st.session_state.context.update({
            "name": md.get("patient_name","Patient"),
            "age": md.get("patient_age", rs_a),
            "gender": md.get("patient_gender", rs_g),
            "weight": rs_w, "height": rs_h, "bmi": bmi_v,
            "disease": normalise_condition(
                md.get("primary_concern","")
            ),
            "region": rs_reg,
            "report_data": md
        })
        st.subheader("👤 Summary")
        pc1,pc2,pc3 = st.columns(3)
        pc1.info(f"**Name:** {md.get('patient_name','N/A')}")
        pc2.info(f"**Primary:** {md.get('primary_concern','N/A')}")
        pc3.metric("BMI", bmi_v)
        urg = md.get("urgency","routine")
        if urg == "immediate":
            st.error("🚨 Seek immediate medical attention!")
        elif urg == "soon":
            st.warning("⚠️ See doctor within 1-2 weeks")
        st.subheader("🩺 Conditions")
        for cond in md.get("detected_conditions",[]):
            if isinstance(cond, dict):
                sev = cond.get("severity","moderate")
                fn = (st.error if sev=="severe"
                      else st.warning if sev=="moderate"
                      else st.info)
                fn(f"**{cond.get('condition','')}** — "
                   f"{cond.get('evidence','')}")
        prog.progress(30,"Biomarker table...")
        rows = []
        for bm in md.get("biomarkers",[]):
            if isinstance(bm, dict):
                rows.append({
                    "Parameter": bm.get("name",""),
                    "Value": bm.get("value",""),
                    "Normal": bm.get("normal_range",""),
                    "Status": str(bm.get("status","")).upper()
                })
        if rows:
            bm_df = pd.DataFrame(rows)
            st.dataframe(
                bm_df.style.applymap(
                    lambda x: (
                        "background-color:#ffcccc"
                        if x in ["HIGH","LOW"]
                        else "background-color:#ccffcc"
                        if x=="NORMAL" else ""
                    ),
                    subset=["Status"]
                ),
                use_container_width=True
            )
        prog.progress(45,"Calculating needs...")
        if rs_g == "Male":
            bmr = (10*rs_w)+(6.25*rs_h)-(5*rs_a)+5
        else:
            bmr = (10*rs_w)+(6.25*rs_h)-(5*rs_a)-161
        tdee = round(bmr * act_map[rs_act])
        cal_target = tdee - 400
        cc1,cc2,cc3 = st.columns(3)
        cc1.metric("BMR", f"{round(bmr)} kcal")
        cc2.metric("TDEE", f"{tdee} kcal")
        cc3.metric("Target", f"{cal_target} kcal/day")
        prog.progress(55,"Generating meal plan...")
        diet_type = (
            rs_diet.lower()
            if rs_diet != "No restriction" else None
        )
        allergy_list = [
            a.strip() for a in rs_allerg.split(",")
            if a.strip()
        ] if rs_allerg else []
        meal_data = generate_report_based_meal_plan(
            md, cal_target
        )
        if diet_type or allergy_list:
            with st.spinner("Applying dietary preferences..."):
                meal_data = filter_meal_plan(
                    meal_data,
                    diet_type or "no restriction",
                    allergy_list, None, rs_reg
                )
        st.session_state.meal_plan = meal_data
        st.subheader("🍽️ 7-Day Meal Plan")
        show_meal_plan(meal_data, show_swap=True)
        prog.progress(70,"Foods to avoid...")
        st.subheader("🚫 Foods to Avoid")
        avoid_data = generate_foods_to_avoid(md)
        if avoid_data and "error" not in avoid_data:
            for item in avoid_data.get("strict_avoid",[]):
                if isinstance(item, dict):
                    st.markdown(f"""
<div class='avoid-card'>
❌ <b>{item.get('food','')}</b> — {item.get('reason','')}<br>
✅ {item.get('alternative','')}
</div>
""", unsafe_allow_html=True)
        prog.progress(80,"Health timeline...")
        st.subheader("📈 Expected Improvements")
        benefits = generate_health_benefits_timeline(
            md, meal_data
        )
        if benefits and "error" not in benefits:
            for imp in benefits.get("improvements",[]):
                if isinstance(imp, dict):
                    with st.expander(
                        f"📊 {imp.get('biomarker','')} "
                        f"→ {imp.get('expected_timeline','')}"
                    ):
                        st.write(
                            f"**{imp.get('current_value','')}**"
                            f" → **{imp.get('target_value','')}**"
                        )
                        st.write(imp.get("mechanism",""))
                        st.success(imp.get("body_benefit",""))
        prog.progress(100,"Complete!")
        col_d1, col_d2 = st.columns(2)
        with col_d2:
            if st.button("📄 Generate PDF"):
                with st.spinner("Creating PDF..."):
                    try:
                        pdf_path = generate_pdf_report(
                            st.session_state.context,
                            {}, meal_data,
                            st.session_state.ranked_foods,
                            avoid_data, benefits
                        )
                        with open(pdf_path,"rb") as f:
                            st.download_button(
                                "⬇️ Download PDF",
                                data=f.read(),
                                file_name="NutriAI_Report.pdf",
                                mime="application/pdf"
                            )
                    except Exception as e:
                        st.error(format_error("PDF failed"))
    # After prescription display, add improvement timeline
st.subheader("📈 Week-by-Week Improvement Prediction")
st.caption(
    "If you follow this exact meal plan and prescription — "
    "what changes week by week"
)

from meal_improvement_timeline import (
    generate_improvement_timeline,
    display_improvement_timeline
)

# Generate meal plan from report first
prog.progress(88, "Predicting week-by-week improvements...")
with st.spinner("Calculating improvement timeline..."):
    # Generate report-based meal plan first
    report_meal_plan = generate_report_based_meal_plan(
        md,
        int(safe_float(bmi_v * 25, 1800))
    )
    # Then generate improvement timeline
    timeline = generate_improvement_timeline(
        biomarkers=traj_bm,
        meal_plan=report_meal_plan,
        condition=condition,
        prescription_foods=prescription.get("foods",[])
        if prescription else [],
        patient_info=patient_info
    )

display_improvement_timeline(
    timeline,
    patient_name=md.get("patient_name","")
) 


# ════════════════════════════════════════
# TAB: FOOD VISION
# ════════════════════════════════════════
with tab["📸 Food Vision"]:
    st.header("📸 Food Vision")
    fv_mode = st.selectbox(
        "Analysis type",
        [
            "🍽️ General Food Analysis",
            "🥘 Indian Thali Analysis",
            "📦 Food Label Reader"
        ],
        key="fv_mode"
    )
    fv_file = st.file_uploader(
        "Upload photo",
        type=["jpg","jpeg","png","webp"],
        key="fv_upload"
    )
    fv_conds = st.multiselect(
        "Your conditions",
        ["Type 2 Diabetes","Hypertension",
         "High Cholesterol","Obesity","Anaemia"],
        key="fv_cond"
    )

    if fv_file and st.button("🔍 Analyse", type="primary"):
        img_bytes = fv_file.getvalue()

        if "Thali" in fv_mode:
            with st.spinner("Analysing your thali..."):
                from food_vision import analyze_indian_thali
                result = analyze_indian_thali(
                    img_bytes,
                    patient_context=st.session_state.context
                )
            if "error" in result:
                st.error(result["error"])
            else:
                st.subheader(
                    f"🥘 {result.get('plate_type','')} Thali Analysis"
                )
                total = result.get("total_meal",{})
                tc1,tc2,tc3,tc4,tc5 = st.columns(5)
                tc1.metric("Calories",    total.get("total_calories",""))
                tc2.metric("Carbs",       f"{total.get('total_carbs_g','')}g")
                tc3.metric("Protein",     f"{total.get('total_protein_g','')}g")
                tc4.metric("Meal GL",     total.get("meal_glycaemic_load",""))
                tc5.metric("K:Na Ratio",  total.get("kna_ratio",""))

                cond_anal = result.get("condition_analysis",{})
                if cond_anal.get("biggest_issue"):
                    st.warning(
                        f"⚠️ Issue: {cond_anal['biggest_issue']}"
                    )
                if cond_anal.get("biggest_strength"):
                    st.success(
                        f"✅ Strength: "
                        f"{cond_anal['biggest_strength']}"
                    )

                swaps = result.get("swaps_to_improve",[])
                if swaps:
                    st.subheader("💡 Suggested Swaps")
                    for swap in swaps:
                        if isinstance(swap, dict):
                            st.info(
                                f"Replace **{swap.get('current_item','')}** "
                                f"with **{swap.get('swap_to','')}** — "
                                f"{swap.get('reason','')} → "
                                f"{swap.get('impact','')}"
                            )

                if result.get("what_to_add"):
                    st.success(
                        f"➕ Add: {result['what_to_add']}"
                    )

                score = result.get("overall_score",0)
                verdict = result.get("clinical_verdict","")
                verdict_color = (
                    "#28a745" if verdict == "suitable"
                    else "#ffc107" if verdict == "modify"
                    else "#dc3545"
                )
                st.markdown(
                    f"<div style='background:{verdict_color}15;"
                    f"border:2px solid {verdict_color};"
                    f"border-radius:10px;padding:16px;text-align:center'>"
                    f"<h3 style='color:{verdict_color}'>"
                    f"Score: {score}/10 — {verdict.upper()}</h3>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Offer to log to diary
                if st.button("📓 Log this meal to diary",
                              key="fv_log_thali"):
                    name = st.session_state.context.get("name","")
                    if name:
                        from tracking.symptom_diary import save_symptom_entry
                        save_symptom_entry(name, {
                            "foods": f"Thali: {result.get('plate_type','')} — "
                                     f"{total.get('total_calories','')} kcal",
                            "energy": 5,
                            "digestion": 5,
                            "mood": 5,
                            "symptoms": ""
                        })
                        st.success("✅ Meal logged to symptom diary!")
                    else:
                        st.warning("Enter your name in sidebar first.")

        elif "Label" in fv_mode:
            with st.spinner("Reading food label..."):
                from food_vision import analyze_food_label
                result = analyze_food_label(
                    img_bytes,
                    patient_context=st.session_state.context
                )
            if "error" in result:
                st.error(result["error"])
            else:
                st.subheader(
                    f"📦 {result.get('product_name','Product')}"
                )
                ps = result.get("per_serving",{})
                lc1,lc2,lc3,lc4 = st.columns(4)
                lc1.metric("Calories",   ps.get("calories",""))
                lc2.metric("Sugar",      f"{ps.get('sugar_g','')}g")
                lc3.metric("Sodium",     f"{ps.get('sodium_mg','')}mg")
                lc4.metric("Protein",    f"{ps.get('protein_g','')}g")

                verdict = result.get("verdict_for_condition","")
                reason  = result.get("reason","")
                if verdict == "suitable":
                    st.success(f"✅ Suitable — {reason}")
                elif verdict == "avoid":
                    st.error(f"❌ Avoid — {reason}")
                else:
                    st.warning(f"⚠️ Occasionally — {reason}")

                budget = result.get("daily_budget_impact",{})
                if budget:
                    st.subheader("📊 Daily Budget Impact")
                    bc1,bc2,bc3 = st.columns(3)
                    bc1.metric("Sodium used",
                               f"{budget.get('sodium_percent_of_daily_limit','')}%")
                    bc2.metric("Sugar used",
                               f"{budget.get('sugar_percent_of_daily_limit','')}%")
                    bc3.metric("Calories used",
                               f"{budget.get('calorie_percent_of_daily_target','')}%")

                concerns = result.get("ingredients_of_concern",[])
                if concerns:
                    st.warning(
                        f"⚠️ Ingredients of concern: "
                        f"{', '.join(concerns)}"
                    )

                better = result.get("better_alternative","")
                if better:
                    st.info(f"💡 Better option: {better}")

        else:
            # General food analysis
            with st.spinner("Analysing food..."):
                result = analyze_food_image(
                    img_bytes, fv_conds or None
                )
            if "error" in result:
                st.error(result["error"])
                if "API key" in result.get("error",""):
                    st.info("Add GEMINI_API_KEY to .env")
            elif result:
                st.subheader("🍽️ Analysis Results")
                foods = result.get("foods_detected",[])
                total_cal = result.get("total_calories",0)
                hr        = result.get("health_rating","")
                rc = {"excellent":"#28a745","good":"#17a2b8",
                      "moderate":"#ffc107","poor":"#dc3545"}.get(hr,"#ffc107")
                st.markdown(
                    f"<div style='background:{rc}15;"
                    f"border:2px solid {rc};"
                    f"border-radius:10px;padding:16px'>"
                    f"<h3 style='color:{rc}'>"
                    f"Total: {total_cal} kcal — "
                    f"Rating: {hr.upper()}</h3></div>",
                    unsafe_allow_html=True
                )
                for food in foods:
                    if isinstance(food, dict):
                        with st.expander(
                            f"🥘 {food.get('name','')} — "
                            f"{food.get('portion_estimate','')}"
                        ):
                            fc1,fc2,fc3,fc4 = st.columns(4)
                            fc1.metric("Calories",food.get("calories",0))
                            fc2.metric("Protein", f"{food.get('protein_g',0)}g")
                            fc3.metric("Carbs",   f"{food.get('carbs_g',0)}g")
                            fc4.metric("GI",      food.get("gi","—"))
                compat = result.get("condition_compatibility",{})
                if compat.get("good_for"):
                    st.success(f"✅ Good for: {', '.join(compat['good_for'])}")
                if compat.get("bad_for"):
                    st.error(f"⚠️ Avoid if: {', '.join(compat['bad_for'])}")
                for sug in result.get("improvement_suggestions",[]):
                    st.write(f"💡 {sug}")


# ════════════════════════════════════════
# TAB: RISK PREDICTOR
# ════════════════════════════════════════
with tab["⚠️ Risk Predictor"]:
    st.header("⚠️ Disease Risk Predictor")
    st.markdown(
        "Validated clinical scoring: Framingham (CVD) · "
        "FINDRISC (Diabetes) · ACC/AHA (BP) · KDIGO (Kidney)"
    )
    rc1,rc2,rc3 = st.columns(3)
    with rc1:
        dp_age = st.number_input(
            "Age",10,100,
            int(ctx("age",35)),key="dpa"
        )
        dp_g = st.selectbox("Gender",["Male","Female"],key="dpg")
        dp_w = st.number_input(
            "Weight kg",30.0,200.0,
            float(ctx("weight",75.0)),key="dpw"
        )
        dp_h = st.number_input(
            "Height cm",100.0,220.0,
            float(ctx("height",170.0)),key="dph"
        )
        dp_bmi = round(dp_w/((dp_h/100)**2),1)
        st.metric("BMI", dp_bmi)
    with rc2:
        dp_sys = st.number_input("Systolic BP",80,220,125,key="dpsys")
        dp_dia = st.number_input("Diastolic BP",40,140,82,key="dpdia")
        dp_chol = st.number_input("Total Cholesterol",100,600,190,key="dpc")
        dp_hdl = st.number_input("HDL",20,100,50,key="dph2")
        dp_gluc = st.number_input("Fasting Glucose",50,400,95,key="dpg2")
        dp_hba1c = st.number_input("HbA1c %",3.0,15.0,5.4,key="dpha")
        dp_waist = st.number_input("Waist cm (0=unknown)",0,200,0,key="dpw2")
        validate_clinical(dp_sys,"Systolic BP",70,220)
        validate_clinical(dp_gluc,"Glucose",50,600)
    with rc3:
        dp_smoke = st.checkbox("Smoker",key="dpsm")
        dp_bp_med = st.checkbox("On BP Medication",key="dpbpmed")
        dp_fam_d = st.checkbox("Family: Diabetes",key="dpfd")
        dp_fam_c = st.checkbox("Family: Heart Disease",key="dpfc")
        dp_stress = st.checkbox("High Stress",key="dpst")
        dp_salt = st.checkbox("High Salt Diet",key="dpsa")
        dp_act = st.selectbox(
            "Activity",
            ["sedentary","light","moderate","active"],
            key="dpact"
        )

    if st.button("🔮 Calculate Risk", type="primary"):
        biomarkers = {
            "systolic_bp":dp_sys,"diastolic_bp":dp_dia,
            "total_cholesterol":dp_chol,"hdl":dp_hdl,
            "fasting_glucose":dp_gluc,"hba1c":dp_hba1c
        }
        lifestyle = {
            "smoker":dp_smoke,"on_bp_medication":dp_bp_med,
            "family_diabetes":("first_degree" if dp_fam_d else "none"),
            "family_cvd":dp_fam_c,
            "high_stress":dp_stress,"high_sodium_diet":dp_salt,
            "activity_level":dp_act,
            "waist_cm":dp_waist if dp_waist>0 else None
        }
        with st.spinner("Calculating with validated scores..."):
            result = predict_disease_risk(
                biomarkers, dp_age, dp_g, dp_bmi, lifestyle
            )
        risks = result.get("risks",{})
        ai_exp = result.get("ai_explanation",{})
        st.subheader("📊 10-Year Risk Profile")
        gcols = st.columns(4)
        disease_info = {
            "cvd":("❤️ Heart","Framingham PMID:9486607"),
            "diabetes":("🩸 Diabetes","FINDRISC PMID:12709467"),
            "hypertension":("💧 BP","ACC/AHA PMID:29133354"),
        }
        for i,(dk,(dn,guide)) in enumerate(disease_info.items()):
            rd = risks.get(dk,{})
            pct = rd.get("risk_percent",0)
            lv = rd.get("level","Low")
            with gcols[i]:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    number={"suffix":"%"},
                    title={"text":dn,"font":{"size":12}},
                    gauge={
                        "axis":{"range":[0,50]},
                        "bar":{"color":(
                            "#dc3545" if lv=="High"
                            else "#ffc107" if lv=="Moderate"
                            else "#28a745"
                        )},
                        "steps":[
                            {"range":[0,10],"color":"#d4edda"},
                            {"range":[10,20],"color":"#fff3cd"},
                            {"range":[20,50],"color":"#f8d7da"}
                        ]
                    }
                ))
                fig_g.update_layout(height=220,margin=dict(t=50))
                st.plotly_chart(fig_g,use_container_width=True)
                st.caption(guide)
        rexp = ai_exp.get("risk_explanations",{})
        st.subheader("🔍 Detailed Breakdown")
        for dk,(dn,_) in disease_info.items():
            rd = risks.get(dk,{})
            lv = rd.get("level","Low")
            exp = rexp.get(dk,{})
            pct = rd.get("risk_percent",0)
            ic = "🔴" if lv=="High" else "🟡" if lv=="Moderate" else "🟢"
            with st.expander(f"{ic} {dn} — {lv} ({pct}%)"):
                why = exp.get("why_this_patient","")
                if why:
                    st.write(f"**Why:** {why}")
                for f in exp.get("top_foods",[]):
                    if isinstance(f, dict):
                        mech = f.get("mechanism","")
                        cit = f.get("citation","")
                        st.success(
                            f"✅ **{f.get('food','')}** — "
                            f"{mech} {cit}"
                        )
                    elif isinstance(f,str):
                        st.success(f"✅ {f}")
                change = exp.get("key_lifestyle_change","")
                if change:
                    st.info(f"💪 **Key change:** {change}")
        bio_age = ai_exp.get("biological_age_estimate","")
        urgent = ai_exp.get("most_urgent","")
        if bio_age:
            st.info(f"🧬 **Biological Age:** {bio_age}")
        if urgent:
            st.warning(f"🎯 **Most Urgent:** {urgent}")


# ════════════════════════════════════════
# TABS: METABOLIC, INDIAN FOODS,
# PROGRESS, MANUAL INPUT, LONGITUDINAL,
# SEASONAL, RECIPES, BIOAVAILABILITY,
# SYMPTOM DIARY, FASTING, MED SCHEDULE,
# GUIDELINES, SUPPLEMENTS, PDF
# ════════════════════════════════════════

with tab["🧬 Metabolic"]:
    st.header("🧬 Metabolic Profile")
    st.markdown(
        "Phenotypic proxy method — classifies your "
        "metabolic type from blood values. No DNA needed."
    )
    mp_tsh = st.number_input("TSH (0=unknown)",0.0,20.0,0.0,key="mptsh")
    mp_crp = st.number_input("CRP mg/L (0=unknown)",0.0,50.0,0.0,key="mpcrp")
    mp_syms = st.text_area(
        "Symptoms",
        placeholder="fatigue, cold intolerance, brain fog",
        key="mpsyms"
    )
    mp_sleep = st.selectbox(
        "Sleep pattern",
        ["Normal","Night owl","Early bird"],key="mpslp"
    )
    if st.button("🧬 Analyse", type="primary"):
        bm = {
            "tsh": mp_tsh if mp_tsh>0 else None,
            "crp": mp_crp if mp_crp>0 else None,
            "bmi": ctx("bmi",25)
        }
        ls = {"sleep_pattern":mp_sleep}
        with st.spinner("Classifying from PubMed research..."):
            profile = classify_metabolic_type(bm, mp_syms, ls)
        if profile and "error" not in profile:
            st.session_state.metabolic_profile = profile
            st.subheader(profile.get("metabolic_archetype",""))
            st.write(profile.get("archetype_description",""))
            st.info(f"**Confidence:** {profile.get('confidence','')}")
            w = float(ctx("weight",70))
            h = float(ctx("height",165))
            a = int(ctx("age",30))
            g = ctx("gender","Male")
            bmr_data = calculate_personalised_bmr(w,h,a,g,profile,bm)
            b1,b2,b3 = st.columns(3)
            b1.metric("Standard BMR",f"{bmr_data.get('base_bmr',0)} kcal")
            b2.metric("Your BMR",f"{bmr_data.get('personalised_bmr',0)} kcal")
            b3.metric("Adjustment",f"{bmr_data.get('total_adjustment_percent',0):+.0f}%")
            st.info(bmr_data.get("explanation",""))
            macro = profile.get("macro_ratios",{})
            if macro:
                fig = px.pie(
                    names=["Protein","Carbs","Fat"],
                    values=[
                        macro.get("protein_percent",30),
                        macro.get("carb_percent",40),
                        macro.get("fat_percent",30)
                    ],
                    title="Your Optimal Macros",
                    color_discrete_sequence=["#28a745","#ffc107","#dc3545"]
                )
                st.plotly_chart(fig,use_container_width=True)
            ec1,ec2 = st.columns(2)
            with ec1:
                for f in profile.get("foods_uniquely_beneficial",[])[:4]:
                    st.success(f"✅ {f}")
            with ec2:
                for f in profile.get("foods_uniquely_harmful",[])[:4]:
                    st.error(f"❌ {f}")
            st.success(
                "✅ Profile saved. Go to Manual Input to "
                "generate your personalised meal plan."
            )


with tab["🌿 Indian Foods"]:
    st.header("🌿 Regional Indian Food Advisor")
    ir = st.selectbox(
        "State/Region",
        ["Tamil Nadu","Kerala","Karnataka",
         "Andhra Pradesh","North India",
         "Maharashtra","Bengal","Punjab"],
        key="ireg"
    )
    ic = st.text_area(
        "Conditions",
        value=", ".join(
            c for c in [ctx("disease","")] if c
        ),
        key="icond"
    )
    iw = st.text_area(
        "Western foods recommended (optional)",
        placeholder="kale, quinoa, salmon",
        key="iwest"
    )
    if st.button("🌿 Get Regional Plan", type="primary"):
        cl = [c.strip() for c in ic.split(",") if c.strip()]
        wl = [f.strip() for f in iw.split(",") if f.strip()]
        rk = ir.lower().replace(" ","_")
        with st.spinner("Fetching traditional food research..."):
            reg = get_regional_alternatives(wl, cl, rk)
        if reg and "error" not in reg:
            rmp = reg.get("regional_meal_plan",{})
            rituals = (rmp.get("morning_rituals") or
                       rmp.get("morning_ritual",[]))
            if rituals:
                st.subheader("☀️ Morning Rituals")
                for r in rituals:
                    if isinstance(r,dict):
                        ev = r.get("pubmed_evidence","traditional")
                        ic2 = ("🟢" if ev=="strong"
                               else "🟡" if ev=="moderate" else "🔵")
                        st.success(
                            f"{ic2} **{r.get('item','')}** — "
                            f"{r.get('preparation','')} | "
                            f"{r.get('benefit','')} | "
                            f"{r.get('citation','')}"
                        )
            for mk,mn,me in [
                ("breakfast","Breakfast","🌅"),
                ("lunch","Lunch","☀️"),
                ("dinner","Dinner","🌙"),
                ("snacks","Snacks","🥜")
            ]:
                items = rmp.get(mk,[])
                if items:
                    st.subheader(f"{me} {mn}")
                    for item in items:
                        if isinstance(item,dict):
                            st.markdown(f"""
<div class='food-card'>
🍛 <b>{item.get('indian_alternative','')}</b>
(replaces: {item.get('western_equivalent','')})<br>
📝 {item.get('preparation','')} | ⚖️ {item.get('portion','')}<br>
🧪 {', '.join(item.get('key_nutrients',[]))} |
✅ {item.get('why_better_locally','')}
{f"<br>⚠️ {item.get('antinutrient_note','')}" if item.get('antinutrient_note') else ''}
</div>
""", unsafe_allow_html=True)
            supers = rmp.get("traditional_superfoods",[])
            if supers:
                st.subheader("🌿 Traditional Superfoods")
                for s in supers:
                    if isinstance(s,dict):
                        ev = s.get("evidence_level","traditional")
                        ei = ("🟢" if ev=="strong"
                              else "🟡" if ev=="moderate" else "🔵")
                        st.info(
                            f"{ei} **{s.get('item','')}** "
                            f"({s.get('local_name','')}) — "
                            f"{s.get('form','')} | "
                            f"Dose: {s.get('dose','')} | "
                            f"{s.get('benefit','')} | "
                            f"{s.get('citation','')}"
                        )
            spices = rmp.get("spices_as_medicine",[])
            if spices:
                st.subheader("🌶️ Medicinal Spices")
                scols = st.columns(min(len(spices),3))
                for i,s in enumerate(spices):
                    if isinstance(s,dict):
                        with scols[i%3]:
                            st.success(
                                f"**{s.get('spice','')}**\n"
                                f"For: {s.get('condition','')}\n"
                                f"Amount: {s.get('daily_amount','')}\n"
                                f"How: {s.get('how_to_use','')}\n"
                                f"{s.get('citation','')}"
                            )


with tab["📈 Progress"]:
    st.header("📈 Progress Tracker")
    pt_name = st.text_input("Your Name", key="ptname")
    if pt_name:
        st.subheader("📝 Log Today")
        pc1,pc2,pc3 = st.columns(3)
        pt_w = pc1.number_input("Weight kg",30.0,200.0,70.0,key="ptw")
        pt_sys = pc2.number_input("Systolic BP",80,220,120,key="ptsys")
        pt_gluc = pc3.number_input("Glucose",50,400,90,key="ptgluc")
        pt_chol = pc1.number_input("Cholesterol",100,600,190,key="ptchol")
        pt_meals = pc2.slider("Meal plan followed (of 5)",0,5,3)
        pt_ex = pc3.number_input("Exercise min",0,300,30,key="ptex")
        pt_water = pc1.number_input("Water litres",0.0,6.0,2.0,key="ptwater")
        pt_sleep = pc2.slider("Sleep hours",4,12,7)
        pt_mood = st.select_slider(
            "How do you feel?",
            options=["😞","😐","🙂","😊","😁"]
        )
        hs = 4.0
        if pt_sys < 130: hs += 0.8
        if pt_gluc < 100: hs += 0.8
        if pt_meals >= 4: hs += 1.0
        if pt_ex >= 30: hs += 1.2
        if pt_water >= 2: hs += 0.7
        if pt_sleep >= 7: hs += 0.7
        if pt_mood in ["😊","😁"]: hs += 0.5
        hs = min(round(hs,1),10.0)
        st.metric("Today's Health Score", f"{hs}/10")
        if st.button("💾 Save", type="primary"):
            save_progress(pt_name,{
                "weight":pt_w,"systolic_bp":pt_sys,
                "glucose":pt_gluc,"cholesterol":pt_chol,
                "meals_followed":pt_meals,"exercise_min":pt_ex,
                "water_litres":pt_water,"sleep_hours":pt_sleep,
                "mood":pt_mood,"health_score":hs
            })
            st.success("✅ Saved!")
            st.balloons()
        charts, preds = get_progress_charts(pt_name)
        if charts:
            for _, fig in charts.items():
                st.plotly_chart(fig, use_container_width=True)
            if isinstance(preds, dict):
                for _, p in preds.items():
                    st.info(f"🔮 {p}")
            entries = load_progress(pt_name).get("entries",[])
            if len(entries) >= 3 and st.button("🔮 Predict Next Month"):
                disease_ctx = ctx("disease","general health")
                with st.spinner("Calculating..."):
                    preds2 = predict_lab_values(
                        pt_name, entries, disease_ctx
                    )
                if preds2.get("message"):
                    st.info(preds2["message"])
                else:
                    ai_p = preds2.get("ai_predictions",{})
                    for mk, data in ai_p.get("predictions",{}).items():
                        if isinstance(data,dict):
                            st.write(
                                f"**{mk.replace('_',' ').title()}:** "
                                f"{data.get('current','N/A')} → "
                                f"{data.get('predicted_1_month','N/A')} "
                                f"(1 month)"
                            )
                            action = data.get("dietary_action","")
                            if action:
                                st.info(f"💡 {action}")
        else:
            st.info("Log 2+ entries to see trends.")

    # In Progress tab, after existing charts
    if pg_name and len(entries) >= 3:
        st.subheader("🔮 Adaptive Health Trajectory")
        st.caption(
            f"Recalculated using YOUR actual "
            f"{len(entries)} weeks of data — "
            f"not population averages"
        )
        with st.spinner(
            "Recalculating trajectory from your actual data..."
        ):
            from health_trajectory import (
                generate_adaptive_trajectory
            )
            adaptive = generate_adaptive_trajectory(
                biomarkers=st.session_state.context,
                patient_info=st.session_state.context,
                condition=ctx("disease","diabetes"),
                logged_progress_entries=entries
            )
        if adaptive and isinstance(adaptive, dict):
            trend = adaptive.get("trend_status","")
            trend_msg = adaptive.get("trend_message","")
            trend_colors = {
                "faster_than_expected":"#28a745",
                "on_track":"#17a2b8",
                "stable_not_improving":"#ffc107",
                "worsening":"#dc3545"
            }
            tc = trend_colors.get(trend,"#ffc107")
            st.markdown(f"""
    <div style='background:{tc}15;border:2px solid {tc};
    border-radius:12px;padding:20px;margin:12px 0'>
    <h4 style='color:{tc};margin:0 0 8px'>
    {trend.replace('_',' ').title()}
    </h4>
    <p style='color:#e8f5ee;margin:0'>{trend_msg}</p>
    </div>""", unsafe_allow_html=True)

            revised = adaptive.get("revised_5yr_risks",{})
            motivation = adaptive.get("motivation","")
            next_adj   = adaptive.get("next_adjustment","")
            weeks_left = adaptive.get(
                "weeks_to_normal_glucose",0
            )

            ac1,ac2,ac3 = st.columns(3)
            ac1.metric(
                "Revised 5yr CV Risk",
                f"{revised.get('cardiovascular_percent','?')}%"
            )
            ac2.metric(
                "Revised 5yr Complication Risk",
                f"{revised.get('microvascular_percent','?')}%"
            )
            if weeks_left and weeks_left > 0:
                ac3.metric(
                    "Weeks to Normal Glucose",
                    f"{weeks_left} weeks"
                )

            if motivation:
                st.success(f"💪 {motivation}")
            if next_adj:
                st.info(f"🎯 Next adjustment: {next_adj}")

            adh = adaptive.get("adherence_assessment","")
            if adh:
                st.write(f"📋 **Adherence:** {adh}")

            actual_vs = adaptive.get("actual_vs_expected",{})
            if actual_vs:
                expected = actual_vs.get(
                    "expected_weekly_change_mg_dl",""
                )
                actual   = actual_vs.get(
                    "actual_weekly_change_mg_dl",""
                )
                performing = actual_vs.get("performing","")
                st.caption(
                    f"Expected: {expected} mg/dL/week | "
                    f"Your actual: {actual} mg/dL/week | "
                    f"Status: {performing}"
                )

        elif adaptive and adaptive.get("note"):
            st.info(adaptive["note"])    


with tab["🥗 Diet Protocol"]:
    st.header("🥗 Clinical Diet Protocol Selector")
    st.caption(
        "All 15 evidence-based protocols scored "
        "against your complete profile — not one condition, "
        "one diet. Your full picture drives the selection."
    )

    dp1, dp2, dp3 = st.columns(3)
    dp_glucose = dp1.number_input("Fasting Glucose",  0, 500,
        int(safe_float(ctx("glucose"), 0)), key="dp_gl")
    dp_bp      = dp2.number_input("Systolic BP",      0, 300,
        int(safe_float(ctx("systolic_bp"), 0)), key="dp_bp")
    dp_chol    = dp3.number_input("Cholesterol",      0, 500, 0,
        key="dp_chol")
    dp4, dp5   = st.columns(2)
    dp_creat   = dp4.number_input("Creatinine", 0.0, 10.0, 0.0,
        key="dp_creat")
    dp_hba1c   = dp5.number_input("HbA1c %",   0.0, 15.0, 0.0,
        key="dp_hba1c")
    dp_age  = st.number_input("Age",  1, 100,
        int(ctx("age", 40) or 40), key="dp_age")
    dp_bmi  = st.number_input("BMI",  10.0, 60.0,
        float(ctx("bmi", 25) or 25), key="dp_bmi")

    if st.button("🔬 Score All Protocols for Me",
                 type="primary"):
        bm_dp = {
            "fasting_glucose":   dp_glucose,
            "systolic_bp":       dp_bp,
            "total_cholesterol": dp_chol,
            "creatinine":        dp_creat,
            "hba1c":             dp_hba1c
        }
        pi_dp  = {
            "age": dp_age, "bmi": dp_bmi,
            "gender": ctx("gender",""),
            "diet_type": ctx("diet_type",""),
            "region": ctx("region","Tamil Nadu")
        }
        conds = (
            [ctx("disease","")]
            if ctx("disease","") else []
        )

        with st.spinner(
            "Scoring all 15 protocols against your profile..."
        ):
            result = select_diet_protocol(
                bm_dp, conds, pi_dp
            )
            st.session_state.diet_protocol = result
            st.session_state.context["diet_protocol"] = (
                result.get("primary",{}).get("name","")
            )

        if result.get("renal_override"):
            st.error(
                "🚨 Renal Diet is mandatory. "
                "Your creatinine requires protein restriction. "
                "All other protocols are secondary."
            )

        # Patient explanation
        exp = result.get("patient_explanation","")
        if exp:
            st.info(f"🔬 **Why these protocols for you:** {exp}")

        # Primary protocol
        primary = result.get("primary",{})
        if primary:
            st.subheader(
                f"🥇 Primary: {primary.get('name','')}"
            )
            st.success(primary.get("evidence",""))
            st.caption(primary.get("citation",""))
            if primary.get("indian_adaptation"):
                st.info(
                    f"🇮🇳 Indian adaptation: "
                    f"{primary['indian_adaptation']}"
                )
            if primary.get("caution"):
                st.warning(
                    f"⚠️ {primary['caution']}"
                )

        # Priority foods (appear in multiple protocols)
        priority_foods = result.get(
            "blended_priority_foods", []
        )
        if priority_foods:
            st.subheader(
                "⭐ Priority Foods — "
                "Serve Multiple Protocol Goals"
            )
            st.caption(
                "These foods appear in multiple applicable "
                "protocols — eat these first every day"
            )
            cols = st.columns(min(len(priority_foods), 4))
            for i, food in enumerate(
                priority_foods[:8]
            ):
                cols[i % 4].success(f"✅ {food}")

        # Adjunct protocols
        adjuncts = result.get("adjuncts",[])
        if adjuncts:
            st.subheader("➕ Supporting Protocols")
            for adj in adjuncts:
                with st.expander(
                    f"➕ {adj.get('name','')} — "
                    f"Score: {adj.get('score','')}"
                ):
                    st.write(adj.get("evidence",""))
                    st.write(
                        f"**Indian adaptation:** "
                        f"{adj.get('indian_adaptation','')}"
                    )
                    st.caption(adj.get("citation",""))

        # All scored protocols
        all_scored = result.get("ranked_protocols",[])
        if len(all_scored) > 3:
            with st.expander(
                f"📊 All {len(all_scored)} applicable "
                f"protocols (ranked)"
            ):
                for p in all_scored:
                    score = p.get("score",0)
                    pname = p.get("name","")
                    sc = (
                        "#28a745" if score >= 80
                        else "#ffc107" if score >= 65
                        else "#6c757d"
                    )
                    st.markdown(
                        f"<span style='color:{sc}'>"
                        f"**Score {score}** — {pname}"
                        f"</span>",
                        unsafe_allow_html=True
                    )
                    st.caption(
                        p.get("citation","")
                    )

        # Avoid list
        avoid_list = result.get("blended_avoid",[])
        if avoid_list:
            with st.expander("❌ Foods to Avoid"):
                for food in avoid_list:
                    st.write(f"• {food}")

        # Generate blended meal plan
        if st.button(
            "🍽️ Generate Blended Protocol Meal Plan",
            key="gen_blended_plan"
        ):
            cal_t = int(
                safe_float(ctx("tdee"), 1800) or 1800
            )
            with st.spinner(
                "Generating meal plan serving "
                "all your protocol goals..."
            ):
                mp_b = generate_protocol_meal_plan(
                    result, cal_t,
                    st.session_state.context,
                    bm_dp
                )
            if mp_b:
                st.session_state.meal_plan = mp_b
                st.success(
                    "✅ Blended protocol meal plan generated! "
                    "View in Manual Input tab."
                )
            else:
                st.error("Generation failed. Try again.")


with tab["📝 Manual Input"]:
    if st.session_state.stage == "input":
        st.header("Step 1 — Health Profile")
        mc1,mc2 = st.columns(2)
        with mc1:
            mi_name = st.text_input("Name",key="miname")
            mi_age = st.number_input("Age",10,100,30,key="miage")
            mi_g = st.selectbox("Gender",["Male","Female","Other"],key="mig")
            mi_w = st.number_input("Weight kg",30.0,200.0,70.0,key="miw")
            mi_h = st.number_input("Height cm",100.0,220.0,165.0,key="mih")
            mi_act = st.selectbox(
                "Activity",
                ["Sedentary","Light","Moderate","Active"],key="miact"
            )
            mi_reg = st.selectbox(
                "Region",
                ["Tamil Nadu","Kerala","North India",
                 "Karnataka","Other"],key="mireg"
            )
            mi_diet = st.selectbox(
                "Diet Type",
                ["No restriction","Vegetarian","Vegan","Jain"],
                key="midiet"
            )
            mi_allerg = st.text_input(
                "Allergies",placeholder="peanuts, dairy",key="miallerg"
            )
        with mc2:
            mi_disease = st.text_area(
                "Describe your condition (any language)",
                placeholder=(
                    "e.g. I have high BP and diabetes\n"
                    "or: PCOS with weight gain\n"
                    "or: ரத்த சர்க்கரை அதிகம்"
                ),
                height=120,key="midis"
            )
            mi_bp = st.text_input("BP",placeholder="140/90",key="mibp")
            mi_gluc = st.number_input("Glucose (0=unknown)",0,400,0,key="migluc")
            mi_chol = st.number_input("Cholesterol (0=unknown)",0,600,0,key="michol")
            mi_meds = st.text_area("Medications (one per line)",height=60,key="mimeds")
            validate_clinical(mi_gluc,"Glucose",50,600)

        if st.button("🔍 Analyse",type="primary",key="migo"):
            if not mi_disease.strip():
                st.error("Please describe your condition")
            else:
                bmi = round(mi_w/((mi_h/100)**2),1)
                act_m = {
                    "Sedentary":1.2,"Light":1.375,
                    "Moderate":1.55,"Active":1.725
                }
                bmr = (
                    (10*mi_w)+(6.25*mi_h)-(5*mi_age)+5
                    if mi_g=="Male"
                    else (10*mi_w)+(6.25*mi_h)-(5*mi_age)-161
                )
                tdee = round(bmr * act_m[mi_act])
                med_list = [
                    m.strip() for m in mi_meds.split("\n") if m.strip()
                ]
                allergy_list = [
                    a.strip() for a in mi_allerg.split(",") if a.strip()
                ]
                clean_dis = sanitise_input(mi_disease)
                prog = st.progress(0,"Mapping symptoms...")
                sym = map_symptoms_to_medical(clean_dis)
                if sym.get("is_emergency"):
                    st.error(
                        f"🚨 EMERGENCY: "
                        f"{sym.get('emergency_message','')}"
                    )
                search_q = normalise_condition(
                    sym.get("primary_condition_guess",clean_dis)
                )
                st.session_state.context = {
                    "name":mi_name,"age":mi_age,"gender":mi_g,
                    "weight":mi_w,"height":mi_h,"bmi":bmi,
                    "bmr":round(bmr),"tdee":tdee,
                    "disease":search_q,
                    "original_complaint":mi_disease,"bp":mi_bp,
                    "glucose":mi_gluc if mi_gluc>0 else None,
                    "cholesterol":mi_chol if mi_chol>0 else None,
                    "medications":med_list,
                    "allergies":allergy_list,
                    "diet_type":mi_diet,"region":mi_reg,
                    "symptom_map":sym
                }
                prog.progress(25,"Fetching papers...")
                papers = cached_pubmed(search_q, 40)
                st.session_state.context["paper_count"] = len(papers)
                prog.progress(55,"Reading papers...")
                insights = extract_insights_from_papers(search_q, papers)
                st.session_state.insights = insights
                prog.progress(80,"Generating questions...")
                questions = generate_follow_up_questions(
                    search_q, st.session_state.context
                )
                smart_qs = auto_collect_missing_data(sym)
                all_qs = questions + [
                    {"question":q.get("question",""),
                     "purpose":q.get("purpose","")}
                    for q in smart_qs if isinstance(q,dict)
                ]
                st.session_state.questions = all_qs[:5]
                prog.progress(100)
                st.session_state.stage = "questions"
                st.rerun()

    elif st.session_state.stage == "questions":
        st.header("Step 2 — Clinical Follow-Up")
        cnt = st.session_state.context.get("paper_count",0)
        dis = st.session_state.context.get("disease","")
        if cnt > 0:
            st.success(f"✅ Found **{cnt}** papers on: *{dis}*")
        else:
            st.info("Using AI clinical knowledge.")
        sym = st.session_state.context.get("symptom_map",{})
        if sym.get("identified_symptoms"):
            with st.expander("🔍 Symptom Mapping"):
                for s in sym.get("identified_symptoms",[]):
                    if isinstance(s,dict):
                        u = s.get("urgency","low")
                        ic = ("🔴" if u in ["emergency","high"]
                              else "🟡" if u=="medium" else "🟢")
                        st.write(
                            f"{ic} **{s.get('patient_said','')}**"
                            f" → _{s.get('medical_term','')}_"
                        )
        answers = {}
        for i,q in enumerate(st.session_state.questions):
            if not isinstance(q,dict): continue
            st.markdown(f"**Q{i+1}: {q.get('question','')}**")
            st.caption(f"*{q.get('purpose','')}*")
            answers[q.get("question",f"q{i}")] = st.text_input(
                "Answer",key=f"miq{i}",
                label_visibility="collapsed"
            )
        if st.button("📊 Generate Report",type="primary",key="migen"):
            st.session_state.context["followup_answers"] = answers
            st.session_state.stage = "results"
            st.rerun()

    elif st.session_state.stage == "results":
        insights = st.session_state.insights
        context = st.session_state.context
        disease = context.get("disease","")
        st.subheader(f"📋 Report: {context.get('name','Patient')}")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("BMI",context.get("bmi","N/A"))
        m2.metric("BMR",f"{context.get('bmr','N/A')} kcal")
        m3.metric("TDEE",f"{context.get('tdee','N/A')} kcal")
        m4.metric("Papers",context.get("paper_count",0))
        with st.expander("🔍 Condition",expanded=True):
            st.write(insights.get("condition_explanation",""))
            if insights.get("normal_ranges"):
                st.info(f"**Ranges:** {insights['normal_ranges']}")
        nutrients = [
            n.get("nutrient","")
            for n in insights.get("beneficial_nutrients",[])
            if isinstance(n,dict)
        ]
        ranked = pd.DataFrame()
        if nutrients:
            with st.spinner("Fetching USDA data..."):
                food_df = fetch_foods_for_nutrients(nutrients)
                ranked = rank_foods_by_nutrients(food_df, nutrients)
                if not ranked.empty:
                    st.session_state.ranked_foods = (
                        ranked["food_name"].head(10).tolist()
                    )
        st.subheader("🧪 Evidence Nutrients")
        si = {"strong":"🟢","moderate":"🟡","limited":"🔴"}
        for item in insights.get("beneficial_nutrients",[]):
            if isinstance(item,dict):
                s = item.get("evidence_strength","moderate")
                nc1,nc2,nc3,nc4 = st.columns([2,4,1,2])
                nc1.markdown(f"**{item.get('nutrient','')}**")
                nc2.write(item.get("mechanism",""))
                nc3.write(f"{si.get(s,'🟡')} {s}")
                nc4.caption(f"PMID:{item.get('pmid_source','')}")
        if not ranked.empty:
            st.subheader("🏆 Top Foods")
            fig = px.bar(
                ranked.head(12),x="composite_score",y="food_name",
                orientation="h",color="composite_score",
                color_continuous_scale="Greens",
                title=f"Foods for {disease}"
            )
            fig.update_layout(
                yaxis={"categoryorder":"total ascending"},height=450
            )
            st.plotly_chart(fig,use_container_width=True)
        # Bioavailability
        if st.session_state.ranked_foods:
            with st.spinner("Analysing absorption..."):
                bio = analyse_bioavailability(
                    st.session_state.ranked_foods[:5],[disease]
                )
            if bio and "error" not in bio:
                with st.expander("🔬 Nutrient Absorption Guide"):
                    for item in bio.get("bioavailability_analysis",[])[:4]:
                        if isinstance(item,dict):
                            st.write(
                                f"**{item.get('food','')}** — "
                                f"Label: {item.get('label_content','')} | "
                                f"Absorbed: {item.get('actual_absorbed','')}"
                            )
                            for enh in item.get("enhancement_strategies",[])[:2]:
                                if isinstance(enh,dict):
                                    st.success(
                                        f"↑ {enh.get('strategy','')} — "
                                        f"{enh.get('mechanism','')} "
                                        f"({enh.get('citation','')})"
                                    )
                    kkadai = bio.get("cast_iron_kadai_tip",{})
                    if kkadai:
                        st.markdown(
                            f"<div class='science-box'>"
                            f"🍳 {kkadai.get('advice','')} — "
                            f"{kkadai.get('science','')} "
                            f"({kkadai.get('citation','')})"
                            f"</div>",
                            unsafe_allow_html=True
                        )
        # Calorie target
        tdee = context.get("tdee",1800)
        mp = st.session_state.get("metabolic_profile",{})
        effective_cal = (
            mp.get("personalised_bmr") or tdee
        ) - 300
        # Seasonal
        region = context.get("region","Tamil Nadu")
        if not st.session_state.seasonal_foods:
            with st.spinner("Checking seasonal foods..."):
                seasonal = get_seasonal_foods(
                    region.lower().replace(" ","_"),
                    [disease]
                )
                st.session_state.seasonal_foods = seasonal
        # Diet filter
        diet_type = context.get("diet_type","")
        allergy_list = context.get("allergies",[])
        disliked = st.session_state.get("disliked_foods",[])
        with st.spinner("Generating meal plan..."):
            mp_data = generate_meal_plan(
                disease,
                st.session_state.ranked_foods,
                effective_cal,
                context,
                metabolic_profile=mp,
                seasonal_foods=st.session_state.seasonal_foods,
                diet_restrictions=(
                    {"exclude":allergy_list} if allergy_list else None
                ),
                disliked_foods=disliked if disliked else None
            )
        if diet_type and diet_type != "No restriction":
            with st.spinner("Applying preferences..."):
                mp_data = filter_meal_plan(
                    mp_data, diet_type.lower(),
                    allergy_list, None, region
                )
        st.session_state.meal_plan = mp_data
        st.subheader("🍽️ 7-Day Meal Plan")
        show_meal_plan(mp_data, disease, show_swap=True)
        # Disliked foods
        dislike_input = st.text_input(
            "Mark foods you dislike (comma separated):",
            placeholder="bitter gourd, horsegram",
            key="dislike_input"
        )
        if dislike_input and st.button("🚫 Exclude These Foods"):
            new_dislikes = [
                f.strip() for f in dislike_input.split(",")
                if f.strip()
            ]
            st.session_state.disliked_foods.extend(new_dislikes)
            st.success(
                f"Will exclude: {', '.join(new_dislikes)} "
                f"from future plans."
            )
            st.rerun()
        # Drug interactions
        meds = context.get("medications",[])
        if meds:
            st.subheader("💊 Drug-Nutrient Interactions")
            with st.spinner("Checking FDA + depletions..."):
                drug_data = check_drug_nutrient_interactions(
                    meds,
                    st.session_state.ranked_foods,
                    nutrients
                )
            if drug_data and "error" not in drug_data:
                for item in drug_data.get("interactions",[]):
                    if isinstance(item,dict):
                        sev = item.get("severity","minor")
                        msg = (
                            f"**{item.get('drug','')}** + "
                            f"{item.get('food_or_nutrient','')} — "
                            f"{item.get('mechanism','')}"
                        )
                        if sev=="critical": st.error(f"⚠️ {msg}")
                        elif sev=="moderate": st.warning(f"⚡ {msg}")
                        else: st.info(f"ℹ️ {msg}")
                for dep in drug_data.get("nutrient_depletions",[]):
                    if isinstance(dep,dict):
                        st.warning(
                            f"⚠️ **{dep.get('drug','')}** depletes "
                            f"**{dep.get('depletes','')}** — "
                            f"{dep.get('supplement_recommendation','')} "
                            f"({dep.get('citation','')})"
                        )
        # Microbiome
        st.subheader("🦠 Microbiome")
        with st.spinner("Fetching microbiome research..."):
            mb = generate_microbiome_recommendations(
                disease, st.session_state.ranked_foods
            )
        if mb and "error" not in mb:
            st.info(mb.get("gut_condition_connection",""))
            for b in mb.get("beneficial_bacteria",[])[:3]:
                if isinstance(b,dict):
                    with st.expander(f"🦠 {b.get('bacteria','')}"):
                        st.write(b.get("mechanism",""))
                        foods_in = b.get("found_in_foods",[])
                        if foods_in:
                            st.write(f"Found in: {', '.join(str(f) for f in foods_in)}")
        # Final report
        st.subheader("📄 Clinical Report")
        with st.spinner("Writing report..."):
            report = generate_final_report(
                disease, insights, context,
                st.session_state.ranked_foods
            )
        st.markdown(report)
        # Translation
        lang = st.selectbox(
            "Translate report to:",
            list(SUPPORTED_LANGUAGES.keys()),
            key="rpt_lang"
        )
        if lang != "English" and st.button(f"🌐 Translate to {lang}"):
            with st.spinner(f"Translating to {lang}..."):
                translated = translate_report(report, lang)
            st.markdown(translated)
        refs = insights.get("key_references",[])
        if refs:
            st.subheader("📚 References")
            for pmid in refs:
                st.markdown(
                    f"- [PMID {pmid}]"
                    f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                )
        col_d1,col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "⬇️ Download Report (Text)",
                data=report,
                file_name=f"NutriAI_{context.get('name','patient')}.txt",
                mime="text/plain"
            )
        with col_d2:
            if st.button("📄 Generate PDF",key="mi_pdf"):
                with st.spinner("Creating PDF..."):
                    try:
                        pdf_path = generate_pdf_report(
                            context, insights, mp_data,
                            st.session_state.ranked_foods,
                            insights.get("foods_to_avoid",[]),
                            {}
                        )
                        with open(pdf_path,"rb") as f:
                            st.download_button(
                                "⬇️ Download PDF",
                                data=f.read(),
                                file_name="NutriAI_Report.pdf",
                                mime="application/pdf"
                            )
                    except Exception:
                        st.error(format_error("PDF failed"))
        if st.button("🔄 New Assessment",key="mireset"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# Remaining tabs — brief implementations
with tab["🔄 Longitudinal"]:
    st.header("🔄 Longitudinal Learning")
    ln = st.text_input("Patient Name",key="lnname")
    ld = st.text_input("Condition",key="lndis")
    if ln:
        lc1,lc2,lc3 = st.columns(3)
        lw = lc1.number_input("Weight kg",30.0,200.0,75.0,key="lw")
        lg = lc2.number_input("Glucose",50,400,120,key="lg")
        lb = lc3.number_input("Systolic BP",80,220,140,key="lb")
        lm = lc1.slider("Meal plan days followed",0,7,5)
        le = lc2.number_input("Exercise days",0,7,4,key="le")
        if st.button("💾 Log Week",type="primary"):
            save_week_entry(ln,{
                "weight":lw,"glucose":lg,"systolic_bp":lb,
                "meal_compliance":lm,"exercise_days":le
            })
            st.success("Week logged!")
        if st.button("📊 Analyse Trend"):
            with st.spinner("Analysing..."):
                trend = analyse_longitudinal_trend(ln, ld)
            if trend.get("message"):
                st.info(trend["message"])
            else:
                st.metric("Trend",trend.get("overall_trend","").upper())
                for adj in trend.get("next_week_adjustments",[]):
                    if isinstance(adj,dict):
                        st.info(
                            f"🔄 **{adj.get('change','')}** — "
                            f"{adj.get('reason','')} | "
                            f"Expected: {adj.get('expected_impact','')}"
                        )
                pred = trend.get("predicted_next_week",{})
                if pred:
                    pp1,pp2,pp3 = st.columns(3)
                    pp1.metric("Weight",f"{pred.get('weight','N/A')} kg")
                    pp2.metric("Glucose",f"{pred.get('glucose','N/A')} mg/dL")
                    pp3.metric("BP",f"{pred.get('systolic_bp','N/A')} mmHg")
                st.info(trend.get("motivational_message",""))


with tab["🌱 Seasonal"]:
    st.header("🌱 Seasonal Food Calendar")
    sea_reg = st.selectbox(
        "Region",
        ["Tamil Nadu","Kerala","North India","Karnataka"],key="seareg"
    )
    sea_cond = st.text_input(
        "Conditions",
        value=ctx("disease",""),
        placeholder="diabetes, hypertension",key="seacond"
    )
    if st.button("🌱 Show Seasonal Foods",type="primary"):
        cond_list = [c.strip() for c in sea_cond.split(",") if c.strip()]
        with st.spinner("Finding seasonal foods..."):
            seasonal = get_seasonal_foods(
                sea_reg.lower().replace(" ","_"),
                cond_list
            )
        if seasonal and "error" not in seasonal:
            st.info(f"🌤️ **Season:** {seasonal.get('season','').title()}")
            for food in seasonal.get("available_now",[]):
                if isinstance(food,dict):
                    with st.expander(
                        f"🥬 {food.get('food','')} "
                        f"({food.get('local_name','')}) — "
                        f"₹{food.get('approximate_cost_per_kg_inr','N/A')}/kg"
                    ):
                        st.write(f"**Why now:** {food.get('why_good_now','')}")
                        st.success(f"**For condition:** {food.get('condition_benefit','')}")
                        st.info(f"**Active compound:** {food.get('active_compound','')}")
                        st.write(f"**Prep tip:** {food.get('preparation_tip','')}")
            for a in seasonal.get("avoid_this_season",[]):
                if isinstance(a,dict):
                    st.warning(
                        f"⚠️ **{a.get('food','')}** — "
                        f"{a.get('reason','')} | "
                        f"Instead: {a.get('alternative','')}"
                    )


with tab["👨‍🍳 Recipes"]:
    st.header("👨‍🍳 Recipe Generator")
    rc1,rc2 = st.columns(2)
    with rc1:
        rec_food = st.text_input(
            "Food to cook",
            placeholder="ragi kanji, horsegram soup",key="recfood"
        )
        rec_cond = st.text_input(
            "Condition",
            value=ctx("disease",""),
            placeholder="diabetes",key="reccond"
        )
        rec_reg = st.selectbox(
            "Region",
            ["Tamil Nadu","Kerala","North India"],key="recreg"
        )
    with rc2:
        leftovers = st.text_area(
            "Or — What's in your kitchen?",
            placeholder="rice, dal, onion, tomato, egg",
            height=100,key="left"
        )
    cc1,cc2 = st.columns(2)
    if cc1.button("👨‍🍳 Generate Recipe",type="primary"):
        if rec_food:
            with st.spinner("Generating recipe..."):
                recipe = generate_recipe(rec_food, rec_cond, rec_reg)
            if recipe and "error" not in recipe:
                st.subheader(
                    f"🍽️ {recipe.get('recipe_name','')} "
                    f"({recipe.get('local_name','')})"
                )
                tc1,tc2,tc3 = st.columns(3)
                tc1.metric("Prep",f"{recipe.get('prep_time_minutes',0)}min")
                tc2.metric("Cook",f"{recipe.get('cook_time_minutes',0)}min")
                tc3.metric("Difficulty",recipe.get("difficulty",""))
                n = recipe.get("nutrition_per_serving",{})
                nc1,nc2,nc3 = st.columns(3)
                nc1.metric("Calories",f"{n.get('calories',0)} kcal")
                nc2.metric("Protein",f"{n.get('protein_g',0)}g")
                nc3.metric("GI",n.get("gi","N/A"))
                adps = recipe.get("condition_adaptations",[])
                if adps:
                    st.info("**Adapted:** " + " · ".join(str(a) for a in adps))
                anti = recipe.get("antinutrient_reduction","")
                if anti:
                    st.markdown(
                        f"<div class='science-box'>🧪 {anti}</div>",
                        unsafe_allow_html=True
                    )
                st.subheader("🧺 Ingredients")
                for ing in recipe.get("ingredients",[]):
                    if isinstance(ing,dict):
                        note = ing.get("food_tech_note","")
                        st.write(
                            f"• **{ing.get('item','')}** — "
                            f"{ing.get('amount','')} "
                            f"_{f'({note})' if note else ''}_"
                        )
                st.subheader("📝 Instructions")
                for step in recipe.get("instructions",[]):
                    if isinstance(step,dict):
                        with st.expander(
                            f"Step {step.get('step','')} — "
                            f"{step.get('action','')[:40]}"
                        ):
                            st.write(step.get("action",""))
                            tip = step.get("chef_tip","")
                            if tip:
                                st.success(f"💡 {tip}")
                            maillard = step.get("maillard_warning","")
                            if maillard:
                                st.error(f"⚠️ Maillard/AGE warning: {maillard}")
                why = recipe.get("why_this_heals","")
                if why:
                    st.success(f"🔬 **Why this heals:** {why}")
    if cc2.button("🥘 Leftover Meals"):
        if leftovers:
            cond = rec_cond or ctx("disease","general")
            with st.spinner("Planning meals..."):
                lm = generate_leftover_meal(leftovers, cond, rec_reg)
            if lm and "error" not in lm:
                for meal in lm.get("meals",[]):
                    if isinstance(meal,dict):
                        fn = (st.success if meal.get("condition_suitability")=="good"
                              else st.warning)
                        fn(f"**{meal.get('name','')}** — "
                           f"{meal.get('ready_in_minutes',0)} min")
                        st.write(meal.get("quick_instructions",""))
                shop = lm.get("shopping_suggestion","")
                if shop:
                    st.info(f"🛒 Buy: {shop}")


with tab["🔬 Bioavailability"]:
    st.header("🔬 Bioavailability Engine")
    st.markdown(
        "Food technologist insight: label content ≠ "
        "what your body absorbs. This shows the real picture."
    )
    bio_foods = st.text_area(
        "Foods you eat regularly",
        placeholder="spinach, ragi, turmeric, dal",
        key="biofoods"
    )
    bio_cond = st.text_input(
        "Condition",
        value=ctx("disease",""),
        placeholder="diabetes",key="biocond"
    )
    if st.button("🔬 Analyse Bioavailability",type="primary"):
        fl = [f.strip() for f in bio_foods.split(",") if f.strip()]
        cl = [c.strip() for c in bio_cond.split(",") if c.strip()]
        with st.spinner("Analysing food matrix effects..."):
            bio = analyse_bioavailability(fl, cl)
        if bio and "error" not in bio:
            for item in bio.get("bioavailability_analysis",[]):
                if isinstance(item,dict):
                    with st.expander(
                        f"🥬 {item.get('food','')} — "
                        f"{item.get('key_nutrient','')}"
                    ):
                        bc1,bc2 = st.columns(2)
                        bc1.metric("Label",item.get("label_content",""))
                        bc2.metric("Actually Absorbed",
                                   item.get("actual_absorbed",""))
                        st.warning(f"**Limiting:** {item.get('limiting_factor','')}")
                        for enh in item.get("enhancement_strategies",[])[:2]:
                            if isinstance(enh,dict):
                                st.success(
                                    f"↑ {enh.get('strategy','')} — "
                                    f"{enh.get('mechanism','')} "
                                    f"({enh.get('citation','')})"
                                )
                        ci = item.get("cast_iron_benefit","")
                        if ci:
                            st.markdown(
                                f"<div class='science-box'>"
                                f"🍳 {ci}</div>",
                                unsafe_allow_html=True
                            )
            iron_tip = bio.get("iron_absorption_strategy","")
            if iron_tip:
                st.subheader("🩸 Iron Absorption Strategy")
                st.info(iron_tip)
            tea_tip = bio.get("tea_coffee_timing","")
            if tea_tip:
                st.warning(f"☕ Tea/Coffee timing: {tea_tip}")
            kadai = bio.get("cast_iron_kadai_tip",{})
            if kadai and isinstance(kadai,dict):
                st.markdown(
                    f"<div class='science-box'>"
                    f"🍳 <b>{kadai.get('advice','')}</b> — "
                    f"{kadai.get('science','')} "
                    f"({kadai.get('citation','')})"
                    f"</div>",
                    unsafe_allow_html=True
                )
            for s in bio.get("synergistic_combinations",[]):
                if isinstance(s,dict):
                    st.success(
                        f"🤝 **{s.get('food1','')} + "
                        f"{s.get('food2','')}** — "
                        f"{s.get('synergy','')} "
                        f"({s.get('citation','')})"
                    )
            for a in bio.get("antinutrient_warnings",[]):
                if isinstance(a,dict):
                    st.error(
                        f"⚠️ **{a.get('food','')}** — "
                        f"{a.get('antinutrient','')} — "
                        f"{a.get('impact','')} | "
                        f"Solution: {a.get('reduction_method','')}"
                    )


with tab["📓 Symptom Diary"]:
    st.header("📓 Symptom Diary")
    st.info(
        "Log daily food and symptoms — AI finds correlations "
        "after 7 entries."
    )
    sd_name = st.text_input("Name",key="sdname")
    sd_dis = st.text_input(
        "Condition",value=ctx("disease",""),key="sddis"
    )
    if sd_name:
        sd1,sd2 = st.columns(2)
        with sd1:
            sd_en = st.slider("Energy",1,10,6)
            sd_sl = st.slider("Sleep quality",1,10,6)
            sd_di = st.select_slider(
                "Digestion",
                ["Very Poor","Poor","Normal","Good","Excellent"]
            )
            sd_mo = st.select_slider(
                "Mood",["Very Low","Low","Neutral","Good","Great"]
            )
        with sd2:
            sd_foods = st.text_area(
                "Foods eaten today",
                placeholder="ragi kanji, dal rice, amla juice",
                height=80,key="sdfoods"
            )
            sd_syms = st.text_area(
                "Symptoms today",
                placeholder="bloating, fatigue, headache",
                height=60,key="sdsyms"
            )
            sd_water = st.number_input("Water litres",0.0,6.0,2.0,key="sdwater")
        if st.button("📝 Save Entry",type="primary"):
            save_diary_entry(sd_name,{
                "energy":sd_en,"sleep_quality":sd_sl,
                "digestion":sd_di,"mood":sd_mo,
                "foods_eaten":sd_foods,"symptoms":sd_syms,
                "water_litres":sd_water
            })
            st.success("✅ Entry saved!")
        if st.button("🔍 Find Correlations"):
            with st.spinner("Analysing diary..."):
                corr = correlate_symptoms_with_food(sd_name, sd_dis)
            if corr.get("message"):
                st.info(corr["message"])
            else:
                for c in corr.get("positive_correlations",[]):
                    if isinstance(c,dict):
                        st.success(
                            f"🌟 **{c.get('food_or_pattern','')}** → "
                            f"improves **{c.get('symptom_improved','')}** "
                            f"({c.get('strength','')})"
                        )
                for c in corr.get("negative_correlations",[]):
                    if isinstance(c,dict):
                        st.warning(
                            f"⚠️ **{c.get('food_or_pattern','')}** → "
                            f"worsens **{c.get('symptom_worsened','')}**"
                        )
                exp = corr.get("recommended_experiment","")
                if exp:
                    st.info(f"🧪 **Try this week:** {exp}")


with tab["⏰ Fasting"]:
    st.header("⏰ Intermittent Fasting Advisor")
    st.markdown(
        "Personalised fasting protocol based on your "
        "metabolic type — not one-size-fits-all."
    )
    fa_cond = st.text_input(
        "Conditions",value=ctx("disease",""),key="facond"
    )
    fa_gluc = st.number_input("Fasting Glucose",50,400,110,key="fagluc")
    fa_hba1c = st.number_input("HbA1c %",3.0,15.0,6.5,key="fahba")
    fa_meds = st.text_input(
        "Medications",
        value=", ".join(ctx("medications",[])),
        key="fameds"
    )
    fa_act = st.selectbox(
        "Activity",["sedentary","light","moderate","active"],key="faact"
    )
    if st.button("⏰ Get Protocol",type="primary"):
        cl = [c.strip() for c in fa_cond.split(",") if c.strip()]
        bm = {"fasting_glucose":fa_gluc,"hba1c":fa_hba1c}
        ls = {"activity_level":fa_act,"medications":fa_meds}
        mp = st.session_state.get("metabolic_profile",{})
        with st.spinner("Fetching fasting research..."):
            fasting = get_fasting_protocol(mp, cl, ls, bm)
        if fasting and "error" not in fasting:
            if not fasting.get("fasting_recommended"):
                st.warning(f"⚠️ Not recommended: {fasting.get('reason','')}")
                for c in fasting.get("contraindications",[]):
                    st.error(f"❌ {c}")
            else:
                st.success("✅ Fasting is beneficial for you!")
                proto = fasting.get("recommended_protocol",{})
                if proto:
                    fp1,fp2,fp3 = st.columns(3)
                    fp1.metric("Protocol",proto.get("name",""))
                    fp2.metric("Eating Window",proto.get("eating_window",""))
                    fp3.metric("Timeline",proto.get("timeline_to_results",""))
                    st.info(proto.get("rationale",""))
                for step in fasting.get("implementation_guide",[]):
                    if isinstance(step,dict):
                        st.write(
                            f"**{step.get('week','')}:** "
                            f"{step.get('action','')} — "
                            f"_{step.get('reason','')}_"
                        )
                for w in fasting.get("warning_signs_to_stop",[]):
                    st.error(f"🛑 Stop if: {w}")


with tab["💊 Med Schedule"]:
    st.header("💊 Medication-Meal Scheduler")
    ms_meds = st.text_area(
        "Medications (one per line)",
        value="\n".join(ctx("medications",[])),
        height=100,key="msmeds"
    )
    ms_wake = st.text_input("Wake time","6:30 AM",key="mswake")
    ms_sleep = st.text_input("Sleep time","10:30 PM",key="mssleep")
    if st.button("⏰ Build Schedule",type="primary"):
        med_list = [m.strip() for m in ms_meds.split("\n") if m.strip()]
        if med_list:
            with st.spinner("Checking FDA drug database..."):
                schedule = build_medication_schedule(
                    med_list,
                    st.session_state.get("meal_plan",{}),
                    ms_wake, ms_sleep
                )
            if schedule and "error" not in schedule:
                st.subheader("📅 Your Daily Schedule")
                for event in schedule.get("daily_schedule",[]):
                    if isinstance(event,dict):
                        etype = event.get("action_type","")
                        icon = ("💊" if etype=="medication"
                                else "🍽️" if etype=="meal"
                                else "💧")
                        fn = (st.error if etype=="medication"
                              else st.info if etype=="meal"
                              else st.write)
                        fn(
                            f"{icon} **{event.get('time','')}** — "
                            f"{event.get('action','')} | "
                            f"_{event.get('reason','')}_"
                        )
                for c in schedule.get("food_drug_conflicts",[]):
                    if isinstance(c,dict):
                        st.error(
                            f"⚠️ **{c.get('medication','')}** + "
                            f"{c.get('avoid_food','')} — "
                            f"{c.get('reason','')}"
                        )
        else:
            st.error("Please enter at least one medication")


with tab["📊 Guidelines"]:
    st.header("📊 Medical Guideline Comparator")
    gc_cond = st.text_input(
        "Condition",
        value=ctx("disease",""),
        placeholder="Type 2 Diabetes",key="gccond"
    )
    gc_recs = st.text_area(
        "Current recommendations",
        placeholder="eat low GI foods, reduce sodium",
        height=80,key="gcrecs"
    )
    if st.button("📊 Compare WHO vs AHA vs ICMR",type="primary"):
        with st.spinner("Fetching guidelines research..."):
            comp = compare_guidelines(gc_cond, gc_recs)
        if comp and "error" not in comp:
            st.subheader("✅ All Guidelines Agree")
            for c in comp.get("consensus_recommendations",[]):
                if isinstance(c,dict):
                    st.success(
                        f"✅ **{c.get('recommendation','')}** — "
                        f"Agreed by: {', '.join(c.get('agreed_by',[]))}"
                    )
            conflicts = comp.get("conflicting_recommendations",[])
            if conflicts:
                st.subheader("⚡ Guidelines Disagree")
                for c in conflicts:
                    if isinstance(c,dict):
                        with st.expander(f"⚡ {c.get('topic','')}"):
                            cc1,cc2,cc3 = st.columns(3)
                            cc1.info(f"**WHO:** {c.get('who_says','')}")
                            cc2.warning(f"**AHA:** {c.get('aha_says','')}")
                            cc3.success(f"**ICMR:** {c.get('icmr_says','')}")
                            st.write(
                                f"**For India:** "
                                f"{c.get('practical_advice_india','')}"
                            )
            for i in comp.get("india_specific_considerations",[]):
                st.info(f"🇮🇳 {i}")


with tab["💊 Supplements"]:
    st.header("💊 Supplement Stack Builder")
    sb_cond = st.text_input(
        "Conditions",value=ctx("disease",""),key="sbcond"
    )
    sb_meds = st.text_input(
        "Medications",
        value=", ".join(ctx("medications",[])),
        key="sbmeds"
    )
    sb_diet = st.selectbox(
        "Diet Type",
        ["vegetarian","vegan","non-vegetarian","jain"],key="sbdiet"
    )
    sb_budget = st.number_input(
        "Monthly budget ₹ (0=no limit)",0,5000,0,key="sbbudget"
    )
    if st.button("💊 Build Stack",type="primary"):
        cl = [c.strip() for c in sb_cond.split(",") if c.strip()]
        ml = [m.strip() for m in sb_meds.split(",") if m.strip()]
        with st.spinner("Searching PubMed for evidence..."):
            stack = build_supplement_stack(
                cl, {}, ml, sb_diet,
                sb_budget if sb_budget>0 else None
            )
        if stack and "error" not in stack:
            total = stack.get("total_monthly_cost_inr",0)
            st.info(f"**Estimated monthly cost:** ₹{total}")
            for supp in stack.get("supplement_stack",[]):
                if isinstance(supp,dict):
                    ev = supp.get("evidence_grade","C")
                    ev_ic = ("🟢" if ev in ["A","B"]
                             else "🟡" if ev=="C" else "🔴")
                    with st.expander(
                        f"{ev_ic} {supp.get('supplement','')} — "
                        f"{supp.get('dose','')} | "
                        f"₹{supp.get('monthly_cost_inr',0)}/month"
                    ):
                        st.write(f"**When:** {supp.get('timing','')}")
                        st.write(f"**Form:** {supp.get('form','')}")
                        st.success(f"**Why:** {supp.get('why','')}")
                        di = supp.get("drug_interaction","")
                        if di in ["caution","avoid"]:
                            st.warning(
                                f"⚡ {di}: "
                                f"{supp.get('interaction_detail','')}"
                            )
                        alt = supp.get("food_alternative","")
                        if alt:
                            st.info(f"🌿 Food alternative: {alt}")
            mao = stack.get("mao_warning","")
            if mao:
                st.error(f"🚨 MAO Warning: {mao}")
            for d in stack.get("do_not_take",[]):
                if isinstance(d,dict):
                    st.error(
                        f"❌ **Do NOT take:** "
                        f"{d.get('supplement','')} — "
                        f"{d.get('reason','')}"
                    )


with tab["📄 PDF Report"]:
    st.header("📄 PDF Clinical Report")
    st.info(
        "Complete Manual Input or Report Scanner first, "
        "then generate your PDF here."
    )
    pdf_name = st.text_input(
        "Patient Name",
        value=ctx("name",""),key="pdfname"
    )
    # After the IMPORT_ERRORS try/except block, add:
    # Fix 2: Safe fallback if translator import failed
    if 'SUPPORTED_LANGUAGES' not in dir():
        SUPPORTED_LANGUAGES = {
            "English": "en",
            "Tamil": "ta",
            "Hindi": "hi",
            "Telugu": "te"
    }
    lang_choice = st.selectbox(
        "Report language",
        list(SUPPORTED_LANGUAGES.keys()),key="pdflang"
    )
    if st.button("📄 Generate PDF",type="primary"):
        context = st.session_state.context
        if not context:
            st.error(
                "No data found. Complete Manual Input first."
            )
        else:
            context["name"] = pdf_name
            with st.spinner("Generating clinical PDF..."):
                try:
                    report_text = generate_final_report(
                        context.get("disease",""),
                        st.session_state.insights,
                        context,
                        st.session_state.ranked_foods
                    )
                    if lang_choice != "English":
                        with st.spinner(f"Translating to {lang_choice}..."):
                            report_text = translate_report(
                                report_text, lang_choice
                            )
                    pdf_path = generate_pdf_report(
                        context,
                        st.session_state.insights,
                        st.session_state.get("meal_plan",{}),
                        st.session_state.ranked_foods,
                        st.session_state.insights.get(
                            "foods_to_avoid",[]
                        ),
                        {},
                        output_path=f"cache/report_{pdf_name}.pdf"
                    )
                    with open(pdf_path,"rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            data=f.read(),
                            file_name=f"NutriAI_{pdf_name}.pdf",
                            mime="application/pdf"
                        )
                    st.success("✅ PDF generated!")
                except Exception as e:
                    st.error(format_error(
                        f"PDF failed. "
                        f"Ensure reportlab is installed."
                    ))
# ════════════════════════════════════════
# TABS: ML ANALYSIS
# ════════════════════════════════════════
# Replace direct imports inside ML tabs with:
try:
    from ml_models.antioxidant_predictor import (
        AntioxidantPredictor
    )
    ap = AntioxidantPredictor()
except ImportError:
    st.error(
        "ML models not found. "
        "Ensure ml_models/ folder exists with "
        "__init__.py file."
    )
    st.stop()

    ml_tabs = st.tabs([
        "🧪 Antioxidant Predictor",
        "📦 Shelf Life Predictor",
        "📊 Plan Effectiveness Score",
        "🔬 Personal Absorption Model"
    ])

    with ml_tabs[0]:
        st.subheader("🧪 Antioxidant Efficacy Predictor")
        st.markdown(
            "Predicts DPPH radical scavenging activity. "
            "Used in ingredient R&D by Kemin, Symrise, IFF."
        )
        from ml_models.antioxidant_predictor import (
            AntioxidantPredictor
        )
        ap = AntioxidantPredictor()

        a1,a2 = st.columns(2)
        with a1:
            a_poly = st.number_input(
                "Polyphenol mg/100g",0,10000,500
            )
            a_flav = st.number_input(
                "Flavonoid mg/100g",0,5000,200
            )
            a_vitc = st.number_input(
                "Vitamin C mg/100g",0,800,50
            )
            a_vite = st.number_input(
                "Vitamin E mg/100g",0.0,50.0,1.0
            )
            a_bc = st.number_input(
                "Beta-carotene ug/100g",0,10000,0
            )
        with a2:
            a_lyc = st.number_input(
                "Lycopene ug/100g",0,10000,0
            )
            a_anth = st.number_input(
                "Anthocyanin mg/100g",0,1000,0
            )
            a_tan = st.number_input(
                "Tannin mg/100g",0,2000,50
            )
            a_ph = st.number_input("pH",1.0,8.0,6.5)
            a_moist = st.number_input(
                "Moisture %",0.0,100.0,80.0
            )

        if st.button(
            "🧪 Predict Antioxidant Activity",
            type="primary"
        ):
            composition = {
                "polyphenol_mg_per_100g": a_poly,
                "flavonoid_mg_per_100g": a_flav,
                "vitamin_c_mg_per_100g": a_vitc,
                "vitamin_e_mg_per_100g": a_vite,
                "beta_carotene_ug_per_100g": a_bc,
                "lycopene_ug_per_100g": a_lyc,
                "anthocyanin_mg_per_100g": a_anth,
                "tannin_mg_per_100g": a_tan,
                "ph_level": a_ph,
                "moisture_percent": a_moist
            }
            with st.spinner("Running ML model..."):
                pred = ap.predict(composition)

            st.metric(
                "DPPH IC50 (ug/ml)",
                pred["predicted_dpph_ic50_ug_ml"],
                help="Lower = stronger antioxidant"
            )
            ac = pred["antioxidant_activity"]
            col = ("success" if "Strong" in ac
                   else "warning" if "Moderate" in ac
                   else "error")
            getattr(st, col)(
                f"**Activity: {ac}** — "
                f"{pred['commercial_category']}"
            )
            for cv, comp in pred.get(
                "comparison",{}
            ).items():
                st.write(f"• {comp}")
            contribs = pred.get("key_contributors",{})
            if contribs:
                st.write("**Key contributors:**")
                for k,v in sorted(
                    contribs.items(),
                    key=lambda x: x[1], reverse=True
                ):
                    st.progress(
                        v,
                        text=f"{k.replace('_',' ')}: "
                             f"{round(v*100)}%"
                    )

    with ml_tabs[1]:
        st.subheader("📦 Shelf Life Predictor")
        st.markdown(
            "Predicts functional food product stability. "
            "Encapsulation technology application."
        )
        from ml_models.shelf_life_predictor import (
            ShelfLifePredictor
        )
        slp = ShelfLifePredictor()

        sl1,sl2 = st.columns(2)
        with sl1:
            sl_wa = st.slider("Water Activity",0.0,1.0,0.25)
            sl_ph = st.number_input("pH",1.0,8.0,6.5,key="slph")
            sl_temp = st.number_input(
                "Storage Temp °C",-20,40,25
            )
            sl_o2 = st.slider("Oxygen %",0.0,21.0,2.0)
            sl_anx = st.number_input(
                "Initial Antioxidant mg/kg",0,2000,500
            )
        with sl2:
            sl_enc = st.checkbox("Encapsulated")
            sl_ee = st.slider(
                "Encapsulation Efficiency %",0,100,88
            ) if sl_enc else 0
            sl_perm = st.slider(
                "Wall Material Permeability",0.0,1.0,0.15
            ) if sl_enc else 0.8
            sl_moist = st.slider("Moisture %",0.0,20.0,3.0)
            sl_fat = st.slider("Fat %",0.0,50.0,5.0)
            sl_light = st.checkbox("Light Exposure")

        if st.button(
            "📦 Predict Shelf Life", type="primary"
        ):
            formulation = {
                "water_activity": sl_wa,
                "ph": sl_ph,
                "temperature_storage_celsius": sl_temp,
                "oxygen_percentage": sl_o2,
                "initial_antioxidant_mg_per_kg": sl_anx,
                "encapsulated": 1 if sl_enc else 0,
                "encapsulation_efficiency_percent": sl_ee,
                "wall_material_permeability": sl_perm,
                "moisture_percent": sl_moist,
                "fat_percent": sl_fat,
                "light_exposure": 1 if sl_light else 0
            }
            with st.spinner("Running shelf life model..."):
                result = slp.predict_shelf_life(formulation)

            sm1,sm2,sm3 = st.columns(3)
            sm1.metric(
                "Shelf Life",
                f"{result['predicted_shelf_life_days']} days"
            )
            sm2.metric(
                "Months",
                f"{result['shelf_life_months']} months"
            )
            sm3.metric(
                "Encapsulation Benefit",
                str(result["encapsulation_benefit"])
            )
            if result.get("arrhenius_note"):
                st.info(result["arrhenius_note"])
            for factor in result.get("critical_factors",[]):
                st.error(f"⚠️ {factor}")
            for rec in result.get(
                "storage_recommendations",[]
            ):
                st.info(f"📦 {rec}")

    with ml_tabs[2]:
        st.subheader("📊 Plan Effectiveness Score")
        st.markdown(
            "Scores your current meal plan against "
            "clinical evidence for your condition."
        )
        from ml_models.meal_scorer import MealPlanScorer
        scorer = MealPlanScorer()

        plan = st.session_state.get("meal_plan",{})
        condition = ctx("disease","")
        if plan and condition:
            with st.spinner("Scoring plan..."):
                score_result = scorer.score_meal_plan(
                    plan, condition
                )
            sc = score_result.get("overall_score",0)
            grade = score_result.get("grade","N/A")
            sc_color = (
                "#28a745" if sc >= 85
                else "#ffc107" if sc >= 70
                else "#dc3545"
            )
            st.markdown(f"""
<div style='text-align:center;padding:20px;
background:{sc_color}20;border-radius:12px;
border:2px solid {sc_color}'>
<h1 style='color:{sc_color}'>{sc}/100</h1>
<h3>Grade: {grade}</h3>
</div>
""", unsafe_allow_html=True)
            st.write(score_result.get("interpretation",""))
            daily = score_result.get("daily_scores",[])
            if daily:
                import plotly.graph_objects as go
                fig = go.Figure(go.Bar(
                    x=[f"Day {i+1}" for i in range(len(daily))],
                    y=daily,
                    marker_color=[
                        "#28a745" if d >= 85
                        else "#ffc107" if d >= 70
                        else "#dc3545"
                        for d in daily
                    ]
                ))
                fig.update_layout(
                    title="Daily Plan Scores",
                    yaxis={"range":[0,100]},
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            for gap in score_result.get(
                "improvement_areas",[]
            ):
                st.warning(f"💡 {gap}")
        else:
            st.info(
                "Generate a meal plan in Manual Input "
                "or Report Scanner first."
            )

    with ml_tabs[3]:
        st.subheader("🔬 Personal Absorption Model")
        st.markdown(
            "Trains on YOUR diary data to predict which "
            "meal context maximises YOUR nutrient absorption. "
            "Requires 7+ diary entries."
        )
        pm_name = st.text_input(
            "Your Name",
            value=ctx("name",""),key="pmname"
        )
        if pm_name:
            diary = load_diary(pm_name)
            entries = diary.get("entries",[])
            st.info(
                f"You have {len(entries)} diary entries. "
                f"Need 7 minimum."
            )
            if len(entries) >= 3:
                if st.button(
                    "🔬 Train Personal Model",
                    type="primary"
                ):
                    from ml_models.absorption_model import (
                        load_or_create_model
                    )
                    with st.spinner("Training on your data..."):
                        model, result = load_or_create_model(
                            pm_name, entries
                        )
                    if result.get("status") == "trained":
                        st.success(result["message"])
                        best = model.predict_best_meal_timing({})
                        if best.get("best_context"):
                            st.subheader("🏆 For You Specifically")
                            bc = best["best_context"]
                            st.success(
                                f"**Best context:** "
                                f"{bc['context']} "
                                f"(score: {bc['predicted_absorption_score']})"
                            )
                            st.info(best.get("personalised_tip",""))
                    else:
                        st.info(result.get("message",""))
            else:
                st.warning(
                    f"Log {7-len(entries)} more diary "
                    f"entries to enable personal model."
                )                    