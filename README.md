# Smart Health AI – LLM-Powered Medical Assistant

**Smart Health AI** is a complete, production-grade healthcare decision-support and patient health education platform powered by **OpenRouter LLM**, **MedSpaCy-compatible clinical NLP**, **HL7 FHIR R4 interoperability**, and deterministic emergency triage rules.

Built from scratch with **Python 3.11/3.14 + FastAPI**, **React + Vite**, and **SQLite**.

---

## 🌟 Key Technology Stack

- **Backend:** FastAPI, Python 3.11 / 3.14, SQLAlchemy, SQLite, Pydantic V2, Starlette
- **AI / LLM Engine:** OpenRouter API (`https://openrouter.ai/api/v1`) with online medical retrieval and fallback clinical reasoning
- **Medical Text NLP:** MedSpaCy & spaCy ConText linguistic pipeline (entity extraction, negation detection, temporality, experiencer)
- **Healthcare Standard:** HL7 FHIR R4 Interoperability (Patient, Condition, Observation, DiagnosticReport, AllergyIntolerance, Bundle)
- **Frontend:** React, Vite, Lucide Icons, Modern Clinical CSS
- **Authentication & Security:** JWT (JSON Web Tokens), bcrypt password hashing, Role-Based Access Control (`patient` vs `doctor`)

---

## 🩺 8 Core AI Features Implemented

1. **Interactive Symptom Checker:** Step-by-step clinical questions (one-by-one) tailored to user responses, concluding with a comprehensive explanation of possible conditions.
2. **Medical Report Analysis:** Upload PDF, scans/images, or FHIR JSON lab reports. Extracts text, identifies abnormal/normal parameters, and generates HL7 FHIR `DiagnosticReport` resources.
3. **Medical History Summary:** Aggregates symptoms, diagnoses, medications, and clinical events into a chronological timeline with full **HL7 FHIR R4 Bundle JSON export**.
4. **Health Precautions:** Evidence-based, non-drug home precautions, lifestyle guidance, and home self-monitoring metrics (SpO2, body temperature, pulse).
5. **Medical Test Guidance:** Explains diagnostic tests physicians may consider (CBC, Chest X-Ray, ECG, HbA1c, Lipid profile, etc.), their clinical purpose, and preparation steps.
6. **Allergy & Diet Assistant:** Identifies allergen cross-reactivities, specifies foods to strictly avoid, provides safe nutritional replacements, and enables doctor sign-off.
7. **Doctor Consultation Summary:** Generates structured pre-encounter clinical summaries in standard **SOAP note format** (Subjective, Objective, Assessment, Plan) for doctor review.
8. **Symptom-Based Medication Information:** Educational guidance on therapeutic classes, mechanisms, precautions, side effects, and drug-food interactions. **Strict safety rule: Never prescribes medications or dosages.**

---

## 🛡️ Medical Safety & Ethical Guardrails

- **Independent Emergency Triage:** Deterministic rule engine triggers immediate red-flag warnings for acute cardiac symptoms, stroke FAST signs, anaphylaxis, and severe respiratory distress, directing the user to 911 / 112 emergency services.
- **No Confirmed Diagnoses:** The system always frames findings as differential considerations to discuss with a licensed physician.
- **No Prescriptions or Dosages:** Medication information is strictly educational.
- **Patient Privacy & Isolation:** Patient records are cryptographically secured; patients can only query their own records.
- **AI Service Consent:** Tracks explicit patient consent before transmitting clinical text to external LLMs.
- **Verified References:** Integrates authentic medical knowledge citing **WHO**, **NHS (UK)**, **MedlinePlus (NLM)**, **ICMR (India)**, and **NCDC India** with live reference URLs.

---

## 👥 Two Dedicated Portals

### 1. Patient Portal
- **Dashboard:** Vitals overview, active allergies, chronic conditions, and recent assessments.
- **Analyze My Health:** Unified AI symptom evaluation generating all 8 clinical features.
- **Symptom Checker:** Interactive conversational questionnaire with quick-reply buttons.
- **Upload Medical Reports:** PDF, Image, and FHIR JSON upload with parameter analysis.
- **Medical History:** Interactive timeline and 1-click **Download HL7 FHIR Bundle** button.
- **Allergies & Diet:** Recorded allergies, foods to avoid, and safe dietary substitutes.
- **Previous AI Assessments:** History of all past assessments and doctor feedback.

### 2. Doctor Portal
- **Dashboard:** Metrics on registered patients, pending reviews, and emergency alerts.
- **Patient Management:** Searchable patient roster and deep-dive patient EHR charts.
- **Medical Record Analysis:** Review uploaded reports and FHIR resources across patients.
- **AI Assessment Reviews:** Review queue to inspect differential conditions and sign off on assessments.
- **Allergy & Diet Management:** Doctor clinical review and sign-off on dietary plans.
- **Medication Information Review:** Clinical review of educational drug monographs.
- **Doctor Notes:** Create and save clinical notes directly into patient records.

---

## ⚡ Quick 1-Click Demo Credentials

On the login page, you can use the **Quick Demo Buttons** or type:

| Role | Email | Password | Full Name |
| :--- | :--- | :--- | :--- |
| **Doctor** | `doctor@smarthealth.ai` | `Doctor@123` | Dr. Sarah Chen, MD |
| **Patient** | `patient@smarthealth.ai` | `Patient@123` | John Doe |
| **Patient 2** | `patient2@smarthealth.ai` | `Patient@123` | Priya Sharma |

---

## 🚀 Windows Setup & Running Instructions

### Prerequisites
- Python 3.11+ (Python 3.14 supported)
- Node.js 18+ and npm

### Step 1: Clone / Open Repository
```powershell
cd "c:\Users\Masterstroke\Desktop\Smart Health AI LLM"
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `backend/.env`:
```powershell
Copy-Item backend/.env.example backend/.env
```
*(Optional)* Add your **OpenRouter API Key** in `backend/.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_MODEL=meta-llama/llama-3.3-70b-instruct:free
```
*Note: If no API key is provided, the platform automatically utilizes its high-grade clinical knowledge engine and verified guideline database.*

### Step 3: Run the Backend
Using the prepared virtual environment:
```powershell
.\venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend starts at `http://localhost:8000`. Database tables and synthetic demo data are seeded automatically on first startup.

### Step 4: Run the Frontend

#### Option A: Built Production App (Served Directly by FastAPI)
The React app has already been pre-built into `frontend/dist`. You can directly open:
👉 **`http://localhost:8000`** in your browser!

#### Option B: Vite Development Server (Hot Reload)
To run the React development server:
```powershell
cd frontend
npm run dev
```
👉 Open **`http://localhost:5173`** in your browser.

---

## 🧪 Running Automated Tests

A comprehensive test suite covering all 8 features, authentication, emergency triage, and FHIR export is included:
```powershell
.\venv\Scripts\python test_backend.py
```
**Test Results:**
- `[PASS] 1. Root & Health Check OK`
- `[PASS] 2. Doctor Login OK`
- `[PASS] 3. Patient Login OK`
- `[PASS] 4a/b/c. Feature 1: Interactive Symptom Checker`
- `[PASS] 5. Feature 2: Medical Report Analysis & FHIR DiagnosticReport`
- `[PASS] 6a/b. Feature 3: Medical History Summary & HL7 FHIR Bundle Export`
- `[PASS] 7. Feature 4: Non-Drug Precautions & Monitoring Guidance`
- `[PASS] 8. Feature 5: Medical Test Guidance`
- `[PASS] 9a/b. Feature 6: Allergy & Diet Assistant`
- `[PASS] 10. Feature 7: Doctor Consultation Summary (SOAP Note)`
- `[PASS] 11. Feature 8: Symptom-Based Medication Education (NO Prescriptions)`
- `[PASS] 12. Independent Emergency Triage Red-Flag Rules`
- `[PASS] 13a/b/c. Doctor Portal Dashboard, Patient Management & Review Queue`
- `[PASS] 14. Verified Medical Knowledge Retrieval from WHO/NHS/ICMR/MedlinePlus`

---

## 📁 Project File Structure

```
Smart Health AI LLM/
├── backend/
│   ├── .env                      # OpenRouter API key & app configuration
│   ├── .env.example              # Environment template
│   ├── main.py                   # FastAPI entry point & CORS
│   ├── config.py                 # App settings & env loading
│   ├── database.py               # SQLite engine & session management
│   ├── models.py                 # SQLAlchemy relational data models
│   ├── schemas.py                # Pydantic validation schemas
│   ├── auth.py                   # JWT tokens & bcrypt password hashing
│   ├── openrouter_client.py      # OpenRouter API client & clinical generator
│   ├── clinical_nlp.py           # MedSpaCy / ConText clinical entity extractor
│   ├── fhir_service.py           # HL7 FHIR R4 parser & bundle generator
│   ├── medical_knowledge.py      # WHO, NHS, MedlinePlus, ICMR, NCDC database
│   ├── emergency_triage.py       # Independent red-flag emergency rule engine
│   ├── seed_data.py              # Synthetic patient & clinical demo seed data
│   └── routers/
│       ├── auth_router.py        # /api/auth
│       ├── symptom_router.py     # /api/symptom-checker (Feature 1)
│       ├── report_router.py      # /api/reports (Feature 2)
│       ├── history_router.py     # /api/history (Feature 3)
│       ├── precautions_router.py # /api/precautions (Feature 4)
│       ├── test_guidance_router.py # /api/tests (Feature 5)
│       ├── allergy_diet_router.py  # /api/allergy-diet (Feature 6)
│       ├── consultation_router.py # /api/consultation (Feature 7)
│       ├── medication_router.py  # /api/medication (Feature 8)
│       ├── doctor_router.py      # /api/doctor
│       ├── knowledge_router.py   # /api/knowledge
│       └── analysis_router.py    # /api/analyze
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── dist/                     # Pre-built production assets
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css             # Healthcare clinical design system
│       ├── api.js                # Unified API client
│       ├── components/
│       │   ├── Navbar.jsx
│       │   ├── DisclaimerBanner.jsx
│       │   ├── EmergencyAlert.jsx
│       │   ├── ConsentModal.jsx
│       │   └── SourceBadge.jsx
│       ├── portals/
│       │   ├── patient/          # Patient Portal (7 Views)
│       │   └── doctor/           # Doctor Portal (8 Views)
│       └── views/
│           └── LoginView.jsx     # 1-Click Demo Login
└── test_backend.py               # Automated 14-point test suite
```
#   A I - H e a l t h - D o c t o r  
 