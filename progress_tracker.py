import json
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROGRESS_FILE = "cache/progress_data.json"
os.makedirs("cache", exist_ok=True)

def load_progress(name):
    if not os.path.exists(PROGRESS_FILE):
        return {"entries":[]}
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(name, {"entries":[]})
    except Exception:
        return {"entries":[]}

def save_progress(name, entry):
    all_data = {}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                all_data = json.load(f)
        except Exception:
            all_data = {}
    if name not in all_data:
        all_data[name] = {"entries":[]}
    today = datetime.now().strftime("%Y-%m-%d")
    # Fix: deduplication — remove existing entry for today
    all_data[name]["entries"] = [
        e for e in all_data[name]["entries"]
        if e.get("date") != today
    ]
    entry["date"] = today
    entry["timestamp"] = datetime.now().isoformat()
    all_data[name]["entries"].append(entry)
    tmp = PROGRESS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, PROGRESS_FILE)

def get_progress_charts(name):
    data = load_progress(name)
    entries = data.get("entries",[])
    if len(entries) < 2:
        return {}, {}
    df = pd.DataFrame(entries)
    charts = {}
    predictions = {}
    bio_cols = ["weight","systolic_bp","diastolic_bp",
                "glucose","cholesterol","hba1c"]
    avail = [c for c in bio_cols
             if c in df.columns and
             df[c].notna().sum() > 1]
    if avail:
        fig = go.Figure()
        for col in avail:
            series = pd.to_numeric(df[col], errors="coerce")
            if series.notna().sum() > 1:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=series,
                    mode="lines+markers",
                    name=col.replace("_"," ").title()
                ))
        fig.update_layout(
            title="📈 Biomarker Trends",
            hovermode="x unified", height=400
        )
        charts["biomarkers"] = fig
    if "health_score" in df.columns:
        scores = pd.to_numeric(
            df["health_score"], errors="coerce"
        ).dropna()
        if len(scores) > 0:
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=float(scores.iloc[-1]),
                delta={"reference": float(scores.iloc[0])
                       if len(scores)>1 else float(scores.iloc[-1])},
                title={"text":"Health Score /10"},
                gauge={
                    "axis":{"range":[0,10]},
                    "bar":{"color":"#28a745"},
                    "steps":[
                        {"range":[0,4],"color":"#f8d7da"},
                        {"range":[4,7],"color":"#fff3cd"},
                        {"range":[7,10],"color":"#d4edda"}
                    ]
                }
            ))
            fig_g.update_layout(height=280)
            charts["health_score"] = fig_g
    if "weight" in df.columns:
        wt = pd.to_numeric(df["weight"], errors="coerce").dropna()
        if len(wt) >= 3:
            import numpy as np
            slope = float(np.polyfit(range(len(wt)), wt.values, 1)[0])
            if slope < 0:
                weeks = abs(float(wt.iloc[-1])*0.1 / slope)
                predictions["weight"] = (
                    f"At current rate, lose 10% body weight "
                    f"in ~{round(weeks)} weeks"
                )
    return charts, predictions