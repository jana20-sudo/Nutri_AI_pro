import json
from utils import safe_groq_call, sanitise_input
from config import GROQ_MODEL, GROQ_API_KEY

MAX_HISTORY = 20  # messages before summarising

SYSTEM_PROMPT = """
You are Dr. NutriAI — warm, intelligent clinical nutritionist for India.

Rules:
- Understand English, Tamil, Hindi, mixed language
- Explain medical terms in simple brackets
- Ask ONE focused question at a time
- Never diagnose definitively — say "this may suggest"
- Always end with a specific food recommendation
- Keep responses under 130 words unless explaining
- Emergency: chest pain + breathlessness → call 108 immediately
- Glucose > 400 or < 60 → emergency, call doctor now
"""

def _trim_history(messages):
    if len(messages) <= MAX_HISTORY:
        return messages
    # Keep first 2 (context) and last 10 (recent)
    return messages[:2] + messages[-10:]

def get_chat_response(messages, user_input,
                      patient_context=None,
                      trajectory=None,
                      prescription=None):
    """
    Enhanced: Now references trajectory risk data
    and prescription in responses.
    Patient-specific clinical responses.
    """
    clean = sanitise_input(user_input)
    if not clean:
        return "Please tell me your health concern."
    if not groq_client:
        return "AI unavailable. Add GROQ_API_KEY to .env."

    is_emergency, emergency_msg = _check_emergency(clean)
    if is_emergency:
        return emergency_msg

    system = DOCTOR_SYSTEM_PROMPT

    # Build rich patient context
    if patient_context and isinstance(patient_context, dict):
        ctx_parts = []
        fields = [
            ("name","Patient"),("age","Age"),
            ("gender","Gender"),("bmi","BMI"),
            ("disease","Condition"),
            ("glucose","Fasting glucose mg/dL"),
            ("hba1c","HbA1c %"),
            ("systolic_bp","Systolic BP mmHg"),
        ]
        for field, label in fields:
            if patient_context.get(field):
                ctx_parts.append(
                    f"{label}: {patient_context[field]}"
                )
        meds = patient_context.get("medications",[])
        if meds and isinstance(meds, list):
            ctx_parts.append(f"Medications: {', '.join(meds)}")
        if patient_context.get("diet_protocol"):
            ctx_parts.append(
                f"Prescribed diet: "
                f"{patient_context['diet_protocol']}"
            )
        if ctx_parts:
            system += (
                "\n\nCURRENT PATIENT (from uploaded report):\n"
                + "\n".join(ctx_parts)
                + "\n\nAlways reference these SPECIFIC VALUES "
                  "not generic advice."
            )

    # Inject trajectory risk if available
    if trajectory and isinstance(trajectory, dict):
        base = trajectory.get("ukpds_base_rates", {})
        stage = trajectory.get("current_disease_stage",{})
        if base or stage:
            traj_context = []
            if stage.get("severity"):
                traj_context.append(
                    f"Disease severity: {stage['severity']}"
                )
            if base.get("cardiovascular_5yr"):
                traj_context.append(
                    f"5-year cardiovascular risk: "
                    f"{base['cardiovascular_5yr']}%"
                )
            if base.get("microvascular_5yr"):
                traj_context.append(
                    f"5-year complication risk: "
                    f"{base['microvascular_5yr']}%"
                )
            if traj_context:
                system += (
                    "\n\nPATIENT HEALTH TRAJECTORY:\n"
                    + "\n".join(traj_context)
                    + "\n\nWhen patient asks about severity "
                      "or future health, reference these numbers."
                )

    # Inject prescription foods if available
    if prescription and isinstance(prescription, dict):
        pfoods = prescription.get("foods",[])
        if pfoods:
            food_names = [
                f"{f.get('food','')} "
                f"({f.get('exact_amount','')} "
                f"at {f.get('exact_time','')})"
                for f in pfoods
                if isinstance(f, dict) and f.get("food")
            ]
            if food_names:
                system += (
                    "\n\nPRESCRIBED FOODS FOR THIS PATIENT:\n"
                    + "\n".join(food_names)
                    + "\n\nWhen asked about what to eat, "
                      "reference these prescribed foods specifically. "
                      "These were chosen from clinical trial data."
                )

    trimmed = (
        _summarise_history(messages)
        if len(messages) > MAX_HISTORY
        else messages
    )

    msgs = [{"role":"system","content":system}]
    msgs += trimmed
    msgs.append({"role":"user","content":clean})

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=600,
            messages=msgs,
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        err = str(e)
        if "429" in err:
            return (
                "Too many messages. "
                "Please wait 30 seconds."
            )
        return "Connection issue. Please try again."