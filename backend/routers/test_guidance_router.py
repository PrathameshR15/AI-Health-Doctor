from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from backend.schemas import TestGuidanceRequest
from backend.auth import get_current_user
from backend.models import User
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list

router = APIRouter(prefix="/api/tests", tags=["Medical Test Guidance"])

# Common Medical Test Knowledge Catalog
TEST_CATALOG = {
    "cbc": {
        "test_name": "Complete Blood Count (CBC)",
        "sample_type": "Venous Blood Draw",
        "purpose": "Evaluates red blood cells (anemia), white blood cells (infection/inflammation), and platelets (clotting ability).",
        "preparation": "No special fasting required unless combined with metabolic tests.",
        "what_doctors_look_for": "Elevated WBC suggests bacterial or severe viral infection; low hemoglobin indicates anemia; low platelets may suggest viral suppression like dengue."
    },
    "chest_xray": {
        "test_name": "Chest X-Ray (PA View)",
        "sample_type": "Radiographic Imaging",
        "purpose": "Produces images of heart, lungs, airways, blood vessels, and the bones of the spine and chest.",
        "preparation": "Remove jewelry, eyeglasses, and metal objects. Inform radiology staff if pregnant.",
        "what_doctors_look_for": "Infiltrates or consolidation (pneumonia), pleural effusion (fluid), cardiomegaly (enlarged heart), or pneumothorax."
    },
    "ecg": {
        "test_name": "12-Lead Electrocardiogram (ECG / EKG)",
        "sample_type": "Electrophysiological Recording",
        "purpose": "Measures electrical activity and rhythm of the heart to evaluate cardiac events or arrhythmias.",
        "preparation": "Avoid oily lotions on chest before the test; rest quietly during recording.",
        "what_doctors_look_for": "ST-segment elevation or depression (ischemia/infarction), arrhythmias, bundle branch blocks."
    },
    "blood_glucose": {
        "test_name": "Fasting Blood Sugar (FBS) & HbA1c",
        "sample_type": "Venous Blood Draw",
        "purpose": "Measures acute glucose levels and 3-month glycemic control for diabetes screening and monitoring.",
        "preparation": "Fasting for 8-10 hours prior to the fasting glucose test (water is permitted). HbA1c does not require fasting.",
        "what_doctors_look_for": "Fasting glucose >126 mg/dL or HbA1c >= 6.5% indicates hyperglycemia / diabetes mellitus."
    },
    "lipid_panel": {
        "test_name": "Lipid Profile (Cholesterol Panel)",
        "sample_type": "Venous Blood Draw",
        "purpose": "Measures Total Cholesterol, LDL ('bad'), HDL ('good'), and Triglycerides to evaluate cardiovascular risk.",
        "preparation": "Fasting for 9-12 hours is recommended for accurate triglyceride measurement.",
        "what_doctors_look_for": "Elevated LDL (>100-130 mg/dL) or low HDL (<40 mg/dL) indicating atherosclerotic risk."
    },
    "lft_kft": {
        "test_name": "Liver & Kidney Function Panels (LFT / KFT)",
        "sample_type": "Venous Blood Draw",
        "purpose": "Evaluates hepatic enzymes (ALT, AST, Bilirubin) and renal filtration (Creatinine, BUN, eGFR, Electrolytes).",
        "preparation": "Avoid heavy alcohol consumption or intense strenuous workouts 24 hours prior.",
        "what_doctors_look_for": "Elevated ALT/AST points to liver stress; elevated creatinine indicates decreased glomerular filtration."
    },
    "crp_esr": {
        "test_name": "Inflammatory Markers (CRP & ESR)",
        "sample_type": "Venous Blood Draw",
        "purpose": "Non-specific markers indicating active acute or chronic inflammation in the body.",
        "preparation": "Standard blood draw; no special fasting.",
        "what_doctors_look_for": "Elevated CRP (>5-10 mg/L) indicates active systemic inflammatory or infectious response."
    }
}

@router.post("/guidance")
def get_medical_test_guidance(req: TestGuidanceRequest, current_user: User = Depends(get_current_user)):
    """
    Feature 5: Explain tests doctors may consider and their purposes.
    """
    symptoms = req.symptoms_or_condition.lower()
    sources = search_medical_knowledge(symptoms, max_results=3)
    citations = get_sources_citation_list(sources)

    recommended_tests = []
    
    # Check relevant tests based on symptoms
    if any(w in symptoms for w in ["cough", "chest", "fever", "phlegm", "breath", "lung"]):
        recommended_tests.extend([TEST_CATALOG["cbc"], TEST_CATALOG["chest_xray"], TEST_CATALOG["crp_esr"]])
    elif any(w in symptoms for w in ["heart", "palpitation", "bp", "blood pressure", "chest pain", "dizzy"]):
        recommended_tests.extend([TEST_CATALOG["ecg"], TEST_CATALOG["lipid_panel"], TEST_CATALOG["cbc"]])
    elif any(w in symptoms for w in ["sugar", "diabetes", "thirst", "urine", "weight"]):
        recommended_tests.extend([TEST_CATALOG["blood_glucose"], TEST_CATALOG["lft_kft"], TEST_CATALOG["lipid_panel"]])
    elif any(w in symptoms for w in ["stomach", "vomit", "liver", "abdomen", "jaundice"]):
        recommended_tests.extend([TEST_CATALOG["lft_kft"], TEST_CATALOG["cbc"]])
    else:
        recommended_tests.extend([TEST_CATALOG["cbc"], TEST_CATALOG["crp_esr"]])

    # Remove duplicates
    unique_tests = []
    seen = set()
    for t in recommended_tests:
        if t["test_name"] not in seen:
            seen.add(t["test_name"])
            unique_tests.append(t)

    return {
        "query": req.symptoms_or_condition,
        "tests_considered": unique_tests,
        "clinical_sources": citations,
        "disclaimer": "Diagnostic tests must be ordered, interpreted, and correlated with physical examination by a licensed medical physician."
    }
