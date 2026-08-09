# 🔬 NutriAI Pro — Personalised Nutrition Intelligence System



![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge)
![PubMed](https://img.shields.io/badge/PubMed-35M+_Papers-326599?style=for-the-badge)
![USDA](https://img.shields.io/badge/USDA-FoodData_Central-2E7D32?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)





---

## 📌 What Is NutriAI Pro?

NutriAI Pro is a **clinical-grade personalised nutrition system** built for the Indian population. It takes a patient's blood test report, extracts every value using OCR, calculates a 5–10 year health trajectory using published UKPDS research, selects the optimal evidence-based diet protocol, and prescribes exactly 3 foods with exact gram amounts and exact clock times — all sourced from PubMed clinical trials.

**Every recommendation traces back to a published PMID citation. No guesswork. No generic advice.**

---

## 🧑‍💻 Developer

| Field | Detail |
|---|---|
| **Name** | Janardhanan C (CJ) |
| **Degree** | B.Tech Food Technology + Data Science Minor |
| **Institution** | Anna University, Centre for Food Technology, Chennai |
| **CGPA** | 8.65 |
| **Batch** | R-2023 |
| **Specialisation** | AI in Food Science, Clinical Nutrition, Industry 4.0 |

---

## 🎯 The Core Vision

```
Blood Test Report Upload
        ↓
OCR Extraction of All Biomarkers
        ↓
Clinical Safety Check (hard thresholds)
        ↓
5-Year & 10-Year Trajectory (UKPDS PMID:10938048)
        ↓
15-Protocol Diet Selection (scored for this patient)
        ↓
3 Precise Foods from PubMed Clinical Trials
        ↓
Week 1 → Week 4 → Week 8 → Month 3 → Year 1 → Year 5 Predictions
        ↓
7-Day Meal Plan with Exact Quantities and Times
        ↓
Adaptive Trajectory — Updates from Real Patient Logged Data
```

---

## ✨ Features

### 🩸 Report Scanner
- Supports PDF, JPG, PNG, TIFF, WebP
- Multi-stage OCR — pdfplumber → Tesseract (PSM 3/4/6) → table extraction
- Recognises Indian hospital formats — GOD POD, HPLC, [H][L] markers
- Supports SRL, Thyrocare, Metropolis, Lal Path Labs, Apollo formats
- Calculates derived values — eGFR from creatinine, LDL via Friedewald equation
- Hard clinical safety thresholds before any advice is generated

### 🔮 Health Trajectory
- UKPDS 35 base rates — 5,102 patients, 20 years (PMID:10938048)
- Microvascular and cardiovascular 5-year and 10-year risk
- Compound risk detection — diabetes + hypertension = 4× cardiac risk
- Adaptive trajectory — updates when 3+ weeks of patient data are logged
- Side-by-side with vs without intervention comparison chart

### 💊 Precise Food Prescription
- 3 foods found from PubMed clinical trial protocols — not from memory
- Exact amounts in grams or millilitres
- Exact clock times based on chronobiology evidence
- Exact duration in weeks
- Clinical trial outcome with PMID citation for each food
- MAO inhibitor hardcoded safety check
- Drug depletion awareness for 12 common medications

### 🥗 Clinical Diet Protocol Selector
All 15 evidence-based protocols scored simultaneously:

| Protocol | Trigger | Evidence |
|---|---|---|
| Low Glycaemic Index | Glucose > 100 or HbA1c > 5.7 | Cochrane 27 RCTs PMID:19370592 |
| DASH | Systolic BP > 120 | NEJM PMID:9099299 |
| Mediterranean | Cholesterol > 200 or CVD | PREDIMED PMID:23432189 |
| MIND | Age > 55 | Alzheimers Dement PMID:25681666 |
| Renal Diet | Creatinine > 1.5 | KDOQI PMID:20463886 |
| Anti-Inflammatory | CRP > 1 or BMI > 27 | AJCN PMID:16762935 |
| Ketogenic | BMI > 32 or Glucose > 180 | DIRECT-PLUS PMID:32936771 |
| Therapeutic Carb Reduction | HbA1c > 7 and BMI > 25 | Virta PMID:29221526 |
| Plant-Based Whole Food | Cholesterol > 240 | Ornish PMID:9863851 |
| PCOD Protocol | PCOD/PCOS | PMID:30499787 |
| South Asian Heart | Age > 35 + cholesterol > 180 | PMID:26481006 |
| High Fibre | Cholesterol > 200 or IBS | BNF PMID:24982744 |
| Low FODMAP | IBS or bloating | Gastroenterology PMID:24906127 |
| VLCD | BMI > 35 | Look AHEAD PMID:17574999 |
| CRAN | Age > 40, healthy BMI | CALERIE PMID:25527358 |

Foods appearing in multiple applicable protocols are flagged as **priority foods** — they serve the most clinical goals simultaneously.

### 📈 Week-by-Week Improvement Timeline
- Week 1 — what changes in body
- Week 4 — measurable glucose and weight changes
- Week 8 — target values achievable
- Month 3 — HbA1c reassessment prediction
- Year 1 — permanent health changes
- Year 5 — quality of life and complication risk

### 💬 Enhanced AI Doctor Chatbot
- Real-time streaming responses — word by word like Claude
- Emotional state detection — frustrated, anxious, discouraged
- Proactive insights — mentions patterns without being asked
- Chain of thought reasoning for complex queries
- Differential clinical assessment — holds multiple hypotheses
- Natural language food logging — "I had idli" auto-logs to diary
- Goal tracking — "Am I on track?" pulls actual data and compares
- Tamil, Hindi, Telugu, and mixed language support
- Cross-session persistent memory via patient profile
- Trajectory-aware — references patient's 5-year risk in responses
- Prescription-aware — references prescribed foods by name

### 📸 Food Vision (Gemini Vision)
- General food photo analysis
- Indian thali analysis — total GL, K:Na ratio, protein adequacy of whole plate
- Packaged food label reader — daily budget impact per nutrient
- Condition compatibility check
- Swap suggestions with specific nutritional reasons

### ⌚ Wearable Integration
- Google Fit JSON export parsing
- Apple Health XML export parsing
- Fitbit CSV export parsing
- Manual daily entry — steps, sleep, resting heart rate, calories
- Automatic calorie target adjustment from step count
- Sleep deprivation protocol — adjusts evening meal and bedtime snack
- High resting HR alert with anti-inflammatory food response

### 🔬 Additional Clinical Modules
- Drug-food interaction checker — 12 medications hardcoded, FDA API for rest
- Supplement-supplement interaction matrix — calcium/iron, zinc/copper, etc.
- Microbiome analysis with Indian probiotic foods
- Bioavailability analyser — antinutrients, enhancers, synergies
- Symptom diary with food-symptom correlation detection
- Intermittent fasting protocol advisor
- Lab value predictor from trend data
- Medication scheduling with timing optimisation
- Supplement stack builder with budget filter
- Recipe modifier — healthifies traditional Indian recipes
- Shopping list generator — quantities and INR estimates for 7 days
- Report comparator — before and after blood test comparison
- Literature surveillance — weekly PubMed monitoring for condition
- Outcome tracker — prescription effectiveness against expected
- Nutrient density ranker
- Hydration tracker with personalised target
- Clinical PDF report generator

---

## 🏗️ Architecture

```
personalized_nutrition_ai_/
│
├── app.py                          # Main Streamlit app — 30 tabs
├── config.py                       # API keys, reference ranges, protocol definitions
├── utils.py                        # Rate limiters, safe_groq_call, safe_float
├── cache_manager.py                # Thread-safe JSON cache with atomic writes
│
├── CORE CLINICAL ENGINE
│   ├── report_scanner.py           # Multi-stage OCR — PDF and image
│   ├── report_analyser.py          # Biomarker extraction from OCR text
│   ├── health_trajectory.py        # UKPDS 5/10-year prediction + adaptive
│   ├── precise_prescription.py     # 3 foods from PubMed trial protocols
│   ├── clinical_rules.py           # Hard safety thresholds — override all AI
│   ├── diet_protocols.py           # 15 protocols — scored and blended
│   ├── meal_improvement_timeline.py# Week 1/4/8/Month3/Year1/Year5
│   └── meal_planner.py             # 7-day meal plan, day-by-day generation
│
├── PATIENT MANAGEMENT
│   ├── patient_profile.py          # Persistent cross-session profile
│   ├── progress_tracker.py         # Weekly biomarker logging and charts
│   ├── outcome_tracker.py          # Prescription effectiveness tracking
│   └── wearable_integration.py     # Google Fit, Apple Health, Fitbit
│
├── AI AND NLP
│   ├── chatbot.py                  # Enhanced clinical chatbot — streaming
│   ├── nlp_extractor.py            # PubMed insight extraction
│   └── metabolic_profiler.py       # Metabolic archetype classification
│
├── DATA SOURCES
│   ├── pubmed_fetcher.py           # NCBI E-utilities — 35M papers
│   ├── usda_fetcher.py             # USDA FoodData Central — 600K foods
│   ├── fda_fetcher.py              # FDA OpenFDA drug database
│   └── live_food_science.py        # PubChem, GI database
│
├── CLINICAL MODULES
│   ├── drug_nutrient.py            # Drug-food interactions
│   ├── disease_predictor.py        # Framingham CVD + FINDRISC diabetes
│   ├── validation.py               # WHO/ADA/ICMR alignment scoring
│   ├── supplement_interactions.py  # Supplement-supplement matrix
│   ├── shopping_list.py            # Automated 7-day shopping list
│   ├── report_comparator.py        # Before/after report comparison
│   ├── literature_surveillance.py  # PubMed weekly monitoring
│   ├── hydration_tracker.py        # Personalised water target
│   ├── recipe_modifier.py          # Recipe healthification
│   └── nutrient_density.py         # Nutrient density scoring
│
├── INTELLIGENCE LAYER
│   ├── intelligence/longitudinal.py   # Multi-week trend analysis
│   ├── intelligence/translator.py     # Multilingual report support
│   └── intelligence/preference_filter.py  # Food preference application
│
├── FOOD SCIENCE
│   ├── food_layer/bioavailability.py  # Absorption and antinutrient analysis
│   ├── food_layer/recipe_generator.py # Indian regional recipe generation
│   ├── food_layer/seasonal_foods.py   # Region and season aware foods
│   └── food_vision.py                 # Gemini Vision — thali, label, general
│
├── PATIENT TRACKING
│   ├── tracking/symptom_diary.py     # Food-symptom correlation
│   ├── tracking/fasting_advisor.py   # 16:8, 5:2 fasting protocols
│   └── tracking/lab_predictor.py     # Biomarker trend prediction
│
├── MEDICAL REPORTS
│   ├── medical/medication_scheduler.py   # Drug timing optimisation
│   ├── medical/guideline_comparator.py   # WHO/ADA/AHA/ICMR alignment
│   ├── medical/supplement_builder.py     # Evidence-based stack builder
│   └── medical/pdf_generator.py          # Clinical PDF with day-by-day meals
│
└── ML MODELS
    ├── ml_models/antioxidant_predictor.py # DPPH IC50 prediction
    ├── ml_models/meal_scorer.py            # Meal plan quality scoring
    ├── ml_models/absorption_model.py       # Nutrient absorption ML
    └── ml_models/shelf_life_predictor.py   # Food shelf life prediction
```

---

## 🔌 Data Sources

| Source | What It Provides | API |
|---|---|---|
| **PubMed NCBI** | 35 million biomedical papers — all recommendations | E-utilities (free) |
| **USDA FoodData Central** | 600,000 foods with complete nutrient profiles | FDC API (free key) |
| **FDA OpenFDA** | Drug-food interaction database | OpenFDA (free) |
| **PubChem** | 90 million chemical compounds — active ingredients | REST (free) |
| **Groq LLaMA 3.3 70B** | Clinical reasoning and response generation | Groq API (free tier) |
| **Gemini 1.5 Flash** | Food image and report vision analysis | Gemini API (free tier) |
| **UKPDS 35** | 5,102 patient, 20-year complication rates | Static — PMID:10938048 |

**No local nutrition database.** Every food recommendation is fetched live from USDA and validated against PubMed. Only UKPDS risk tables and 18-food GI database are static (justified — fixed historical data with no free live equivalent).

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- Tesseract OCR — required for report scanning
- pip

### Step 1 — Clone Repository
```bash
git clone https://github.com/yourusername/personalized_nutrition_ai_.git
cd personalized_nutrition_ai_
```

### Step 2 — Install Tesseract OCR

**Windows:**
Download installer from https://github.com/UB-Mannheim/tesseract/wiki
Install to default path: `C:\Program Files\Tesseract-OCR\`

**Linux / Mac:**
```bash
sudo apt-get install tesseract-ocr    # Ubuntu/Debian
brew install tesseract                 # macOS
```

### Step 3 — Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure API Keys
```bash
cp .env.example .env
```
Edit `.env` and add your API keys (see [API Keys](#api-keys) section below).

### Step 5 — Run
```bash
streamlit run app.py
```

Open browser at `http://localhost:8501`

Default password: `nutriai2024` (change in `.env`)

---

## 🔑 API Keys

All APIs have free tiers sufficient for development and personal use.

| Key | Where to Get | Free Tier |
|---|---|---|
| `GROQ_API_KEY` | https://console.groq.com | 14,400 req/day |
| `GEMINI_API_KEY` | https://aistudio.google.com | 1,500 req/day |
| `USDA_API_KEY` | https://fdc.nal.usda.gov/api-key-signup | Unlimited |
| `NCBI_API_KEY` | https://www.ncbi.nlm.nih.gov/account | 10 req/sec |

Create `.env` file:
```env
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
USDA_API_KEY=your_usda_key_here
NCBI_API_KEY=your_ncbi_key_here
APP_PASSWORD=nutriai2024

DEVELOPER_NAME=Janardhanan C (CJ)
DEVELOPER_COLLEGE=Anna University, Chennai
DEVELOPER_DEGREE=B.Tech Food Technology
DEVELOPER_CGPA=8.65
DEVELOPER_EMAIL=your_email@gmail.com
DEVELOPER_LINKEDIN=linkedin.com/in/yourprofile
DEVELOPER_GITHUB=github.com/yourusername
```

---

## ☁️ Deployment — Streamlit Cloud (Free)

1. Push repository to GitHub
2. Go to https://share.streamlit.io
3. Click **New app**
4. Select your repository, branch `main`, file `app.py`
5. Click **Advanced settings → Secrets**
6. Add all `.env` variables in TOML format:
```toml
GROQ_API_KEY = "your_key"
GEMINI_API_KEY = "your_key"
USDA_API_KEY = "your_key"
NCBI_API_KEY = "your_key"
APP_PASSWORD = "nutriai2024"
```
7. Click **Deploy**

Your app will be live at `https://yourapp.streamlit.app` within 5 minutes.

---

## 📱 Application Tabs

| Tab | Function |
|---|---|
| 💬 AI Doctor | Streaming clinical chatbot with emotional intelligence |
| 📋 Report Scanner | OCR + trajectory + prescription from blood test |
| 📊 Report Compare | Before/after blood test comparison |
| 📸 Food Vision | Thali analysis, label reader, general food analysis |
| ⚠️ Risk Predictor | Framingham CVD + FINDRISC diabetes scoring |
| 🧬 Metabolic | Metabolic archetype classification and BMR |
| 🌿 Indian Foods | Regional food alternatives by state |
| 📈 Progress | Weekly biomarker logging with adaptive trajectory |
| 📝 Manual Input | Full analysis without report upload |
| 🔄 Longitudinal | Multi-week trend analysis |
| 🌱 Seasonal | Season and region aware food recommendations |
| 👨‍🍳 Recipes | Indian regional recipe generation |
| 🔬 Bioavailability | Absorption, antinutrients, synergies |
| 📓 Symptom Diary | Food-symptom correlation detection |
| ⏰ Fasting | 16:8, 5:2, time-restricted eating protocols |
| 💊 Med Schedule | Medication timing with food interactions |
| 📊 Guidelines | WHO / ADA / AHA / ICMR alignment |
| 💊 Supplements | Evidence-based stack with budget filter |
| 🔗 Supp Interactions | Supplement-supplement interaction checker |
| 📄 PDF Report | Clinical PDF with day-by-day meals |
| ✅ Validation | API health check, biomarker validation, plan scoring |
| ⌚ Wearables | Google Fit, Apple Health, Fitbit integration |
| 🥗 Diet Protocol | All 15 protocols scored for this patient |
| 📚 Literature Watch | Automated PubMed monitoring for new trials |
| 🛒 Shopping List | 7-day automated shopping list with INR estimates |
| 📊 Outcomes | Prescription effectiveness tracking |
| 💧 Hydration | Personalised water target with logging |
| 🍲 Recipe Modifier | Healthifies traditional Indian recipes |
| 📊 Nutrient Density | Scores foods by nutrition per calorie |
| 🤖 ML Analysis | Antioxidant prediction, meal scoring |

---

## 🧪 Clinical Evidence Base

### Primary Citations

| Feature | Citation | Study Details |
|---|---|---|
| Health Trajectory | PMID:10938048 | UKPDS 35, BMJ 2000, 5,102 patients, 20 years |
| Low GI Diet | PMID:19370592 | Cochrane Review, 27 RCTs |
| DASH Diet | PMID:9099299 | NEJM 1997, 459 patients, 8 weeks |
| Mediterranean Diet | PMID:23432189 | PREDIMED, 7,447 patients, 5 years |
| MIND Diet | PMID:25681666 | Alzheimers Dement 2015, 923 participants |
| Ketogenic Diet | PMID:32936771 | DIRECT-PLUS trial |
| Plant-Based | PMID:9863851 | Ornish Reversal Program |
| PCOD Nutrition | PMID:30499787 | Inositol meta-analysis |
| South Asian CVD | PMID:26481006 | South Asian Heart Health Guidelines |
| Diabetes Risk | PMID:12709467 | FINDRISC validation study |
| CVD Risk | PMID:9486607 | Framingham Heart Study |

### Why Indian-Specific?
- Indian populations develop cardiovascular disease 10 years earlier than Western populations at the same BMI
- South Asian-specific CVD thresholds applied throughout (PMID:26481006)
- All food recommendations are foods available in Indian markets
- Regional variations by Tamil Nadu, Kerala, Karnataka, Maharashtra, and 6 other states
- All Indian hospital report formats supported — GOD POD glucose, HPLC HbA1c

---

## 🛡️ Clinical Safety

### Hard Safety Rules (Never Overridden by AI)
```
Glucose ≥ 400 mg/dL    → Emergency alert. Block all meal generation.
Glucose ≥ 300 mg/dL    → Critical alert. Block meal plan.
Systolic BP ≥ 180 mmHg → Emergency alert. Block all generation.
Potassium ≥ 5.5 mEq/L  → Critical. Block meal and prescription.
Haemoglobin < 7 g/dL   → Severe anaemia warning before advice.
Creatinine ≥ 3.0 mg/dL → Advanced CKD. Renal diet mandatory.
MAO Inhibitors          → Hardcoded food exclusion list.
```

### What This System Is Not
- Not a replacement for a qualified healthcare professional
- Not suitable for making medication dosage decisions
- All recommendations are for informational purposes
- Critical findings include instruction to consult a doctor

---

## 🤖 AI Architecture

```
User Input / Blood Test Report
         ↓
Clinical Safety Check (hardcoded rules)
         ↓
PubMed Search (condition-specific, max 40 papers)
         ↓
Groq LLaMA 3.3 70B — reads evidence, extracts insights
         ↓
USDA API — fetches exact nutrient profiles
         ↓
FDA API — checks drug-food interactions
         ↓
Groq — clinical reasoning over fetched evidence
         ↓
Output with PMID citations
```

**Groq is used as an interpreter of fetched evidence — not as a generator of nutritional facts from training memory.**

---

## 📊 Performance

| Metric | Value |
|---|---|
| Report scanning time | 8–15 seconds (PDF), 5–10 seconds (image) |
| PubMed fetch time | 3–8 seconds (40 papers) |
| Meal plan generation | 45–90 seconds (7 days, one call per day) |
| Trajectory calculation | 4–8 seconds |
| Cache hit (48-hour) | < 0.5 seconds |
| Chatbot response | Real-time streaming |

### Cache Strategy
- All PubMed, USDA, and trajectory results cached 48 hours
- Atomic writes with `.tmp` swap — no corruption on crash
- Cache auto-cleared from sidebar
- Cache invalidated by version key in cache name

---

## 🔧 Requirements

```
streamlit>=1.32.0
groq>=0.4.0
google-generativeai>=0.5.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
plotly>=5.18.0
requests>=2.31.0
pdfplumber>=0.10.0
pytesseract>=0.3.10
pillow>=10.0.0
pdf2image>=1.16.0
reportlab>=4.0.0
python-dotenv>=1.0.0
joblib>=1.3.0
```

---

## 📂 Key Design Decisions

**No local food database.** Every food value is fetched from USDA FoodData Central in real time. This ensures accuracy and eliminates maintenance burden.

**Day-by-day meal plan generation.** Generating 7 days as 7 separate Groq calls prevents request timeout. Each day generates in 8–12 seconds independently.

**UKPDS as trajectory foundation.** Machine learning on available data would be unreliable. UKPDS is a 20-year, 5,102-patient fixed historical dataset — the gold standard for diabetes complication prediction.

**AI reads evidence — AI does not invent evidence.** Every prescription prompt explicitly instructs the model to read the provided PubMed abstracts and find the best food from them. It is forbidden from suggesting foods from training memory.

**Adaptive trajectory over population average.** When a patient logs 3 or more weeks of actual glucose values, the system uses their personal weekly response rate — not population average — to predict future trajectory.

**Protocol scoring over protocol matching.** All 15 diet protocols are scored simultaneously against the patient's complete biomarker profile. Protocols are not matched one-to-one to conditions.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for details.

Clinical recommendations generated by this system are for informational purposes only. "!!Always consult a qualified healthcare professional before making dietary changes, especially if you have a medical condition or are taking medications!!".

---

## 🙏 Acknowledgements

- **UKPDS Study Group** — 20-year diabetes outcome data (PMID:10938048)
- **National Center for Biotechnology Information** — PubMed API
- **USDA Agricultural Research Service** — FoodData Central
- **Anthropic** — Claude AI platform used in development
- **Groq** — Ultra-fast LLaMA inference
- **Google** — Gemini Vision API
- **Streamlit** — Open source app framework
- **Anna University** — Academic foundation and support

---

<div align="center">

**Built with ❤️ for the Indian population**

*Connecting ancient Indian food wisdom with modern clinical evidence.*

*I am still developing this work using ai because I focus on delivering a personalised nutrition to everyone where our body upgrade ourself slowly based on food what we eat & continous intake of nutritient food is necessary along with better bioavailability of our body*



**Janardhanan C (CJ) · Anna University · B.Tech Food Technology**

</div>
