def generate_adaptive_trajectory(
    biomarkers, patient_info, condition,
    logged_progress_entries, intervention_foods=None
):
    """
    Adaptive version of trajectory that uses
    ACTUAL logged patient data instead of
    population average when 3+ weeks are available.

    This is the key personalisation upgrade:
    - With fewer than 3 entries: use UKPDS population average
    - With 3+ entries: calculate patient's PERSONAL response rate
    - Show how their actual trend compares to expected
    """
    import numpy as np

    # Extract actual glucose trend from logged data
    actual_glucose_values = []
    actual_bp_values      = []
    actual_weight_values  = []

    for entry in logged_progress_entries:
        if not isinstance(entry, dict):
            continue
        g = safe_float(entry.get("glucose"), 0)
        b = safe_float(entry.get("systolic_bp"), 0)
        w = safe_float(entry.get("weight"), 0)
        if g > 0: actual_glucose_values.append(g)
        if b > 0: actual_bp_values.append(b)
        if w > 0: actual_weight_values.append(w)

    # Need at least 3 data points for trend
    use_actual_trend = len(actual_glucose_values) >= 3

    if use_actual_trend:
        # Calculate actual weekly rate of change
        # using linear regression (degree 1)
        x = np.array(range(len(actual_glucose_values)))
        y = np.array(actual_glucose_values)
        slope = float(np.polyfit(x, y, 1)[0])

        # slope is weekly change in mg/dL
        weekly_glucose_change = round(slope, 2)
        current_glucose       = actual_glucose_values[-1]
        starting_glucose      = actual_glucose_values[0]
        total_weeks           = len(actual_glucose_values)
        actual_reduction_pct  = round(
            (starting_glucose - current_glucose) /
            starting_glucose * 100, 1
        )

        # Weight trend
        weekly_weight_change = 0
        if len(actual_weight_values) >= 3:
            xw = np.array(range(len(actual_weight_values)))
            yw = np.array(actual_weight_values)
            weekly_weight_change = round(
                float(np.polyfit(xw, yw, 1)[0]), 2
            )

        # Compare to UKPDS expected
        hba1c   = safe_float(biomarkers.get("hba1c"), 0)
        fasting = safe_float(
            biomarkers.get("fasting_glucose"), 0
        )
        if hba1c == 0 and fasting > 0:
            hba1c = _estimate_hba1c(fasting)
        rates    = _get_rates(hba1c) if hba1c > 0 else {"micro":2.5,"cardio":1.8}

        # Recalculate trajectory using patient's ACTUAL rate
        # If they are improving faster, risk reduces faster
        if weekly_glucose_change < -2:
            # Faster than expected — reduce complication rates
            improvement_multiplier = 0.65
            trend_status = "faster_than_expected"
            trend_message = (
                f"Your glucose is dropping "
                f"{abs(weekly_glucose_change)} mg/dL per week. "
                f"This is FASTER than the clinical trial average. "
                f"Your 5-year risk is lower than initial estimate."
            )
        elif weekly_glucose_change < 0:
            # Improving at expected rate
            improvement_multiplier = 0.75
            trend_status = "on_track"
            trend_message = (
                f"Your glucose is dropping "
                f"{abs(weekly_glucose_change)} mg/dL per week. "
                f"You are on track with expected clinical progress."
            )
        elif weekly_glucose_change < 1:
            # Stable — not improving
            improvement_multiplier = 0.9
            trend_status = "stable_not_improving"
            trend_message = (
                f"Your glucose is stable but not yet dropping. "
                f"This can be normal in weeks 1-3 as the body adjusts. "
                f"Continue the prescription for 4 more weeks."
            )
        else:
            # Worsening
            improvement_multiplier = 1.1
            trend_status = "worsening"
            trend_message = (
                f"Your glucose has increased "
                f"{weekly_glucose_change} mg/dL per week. "
                f"Review your adherence to the meal plan. "
                f"Consider consulting your doctor."
            )

        adjusted_micro_5yr  = round(
            _cumulative_risk(
                rates["micro"] * improvement_multiplier, 5
            ), 1
        )
        adjusted_cardio_5yr = round(
            _cumulative_risk(
                rates["cardio"] * improvement_multiplier, 5
            ), 1
        )
        adjusted_micro_10yr = round(
            _cumulative_risk(
                rates["micro"] * improvement_multiplier, 10
            ), 1
        )
        adjusted_cardio_10yr= round(
            _cumulative_risk(
                rates["cardio"] * improvement_multiplier, 10
            ), 1
        )

        # Project future values using actual trend
        weeks_remaining_to_normal = None
        if weekly_glucose_change < 0 and current_glucose > 100:
            weeks_remaining_to_normal = round(
                (current_glucose - 100) /
                abs(weekly_glucose_change)
            )

        cache_key = (
            f"adapt_traj_{str(biomarkers)[:40]}_"
            f"{total_weeks}_{current_glucose}"
        )
        cached = cache_get(cache_key)
        if cached: return cached

        # Fetch intervention evidence for context
        papers = search_pubmed(
            f"{condition} dietary intervention "
            f"clinical trial longitudinal progress",
            max_papers=5
        )
        evidence = " ".join([
            p.get("abstract","")[:150]
            for p in papers[:3]
        ])

        prompt = f"""
Clinical endocrinologist reviewing ACTUAL patient progress data.

This patient has been following the prescribed plan for {total_weeks} weeks.

ACTUAL LOGGED VALUES (real data, not estimates):
Glucose readings: {actual_glucose_values}
Weekly glucose change: {weekly_glucose_change} mg/dL per week
Total glucose reduction so far: {actual_reduction_pct}%
Current glucose: {current_glucose} mg/dL
Weight change per week: {weekly_weight_change} kg

Trend status: {trend_status}
{trend_message}

Adjusted 5-year risks based on ACTUAL trend:
Microvascular 5yr: {adjusted_micro_5yr}%
Cardiovascular 5yr: {adjusted_cardio_5yr}%

Published evidence: {evidence[:500]}

Write a personalised progress assessment using these
ACTUAL numbers, not population averages.

Return JSON only:
{{
  "trend_status": "{trend_status}",
  "trend_message": "{trend_message}",
  "actual_progress_assessment": "clinical interpretation",
  "weeks_data_used": {total_weeks},
  "actual_vs_expected": {{
    "expected_weekly_change_mg_dl": -1.5,
    "actual_weekly_change_mg_dl": {weekly_glucose_change},
    "performing": "better_than/as_expected/below_expected"
  }},
  "revised_5yr_risks": {{
    "microvascular_percent": {adjusted_micro_5yr},
    "cardiovascular_percent": {adjusted_cardio_5yr}
  }},
  "revised_10yr_risks": {{
    "microvascular_percent": {adjusted_micro_10yr},
    "cardiovascular_percent": {adjusted_cardio_10yr}
  }},
  "weeks_to_normal_glucose": {weeks_remaining_to_normal or 0},
  "motivation": "personalised message based on actual progress",
  "next_adjustment": "specific change to make based on trend",
  "adherence_assessment": "how well patient appears to be following plan",
  "confidence_improvement": "trajectory is now X% more accurate",
  "pmid_basis": ""
}}
"""
        result = safe_groq_call(
            prompt, max_tokens=1500, temperature=0.1
        )
        if result and isinstance(result, dict):
            result["data_source"]  = "actual_patient_logs"
            result["weeks_logged"] = total_weeks
            result["is_adaptive"]  = True
            cache_set(cache_key, result)
        return result if isinstance(result, dict) else {}

    else:
        # Fewer than 3 entries — use standard population-based trajectory
        standard = generate_health_trajectory(
            biomarkers, patient_info,
            condition, intervention_foods
        )
        if standard:
            standard["data_source"] = "population_average_ukpds"
            standard["weeks_logged"] = len(actual_glucose_values)
            standard["is_adaptive"]  = False
            standard["note"] = (
                f"You have {len(actual_glucose_values)} week(s) "
                f"of logged data. Log {3 - len(actual_glucose_values)} "
                f"more week(s) to get a personalised trajectory "
                f"based on your actual response."
            )
        return standard or {} 