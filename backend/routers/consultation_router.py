import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models import User, AssessmentRecord, SymptomSession, PatientProfile
from backend.schemas import ConsultationSummaryGenerateRequest
from backend.auth import get_current_user
from backend.clinical_nlp import clinical_extractor
from backend.emergency_triage import evaluate_emergency_triage
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list

router = APIRouter(prefix="/api/consultation", tags=["Doctor Consultation Summary"])

@router.post("/generate")
def generate_consultation_summary(
    req: ConsultationSummaryGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Feature 7: Generate structured SOAP clinical summary for doctor review.
    """
    chief_complaint = req.chief_complaint or "Routine clinical inquiry"
    symptoms_text = req.symptoms or chief_complaint
    history_text = req.history or "No significant past history reported."

    # If linked to a session
    if req.session_id:
        session = db.query(SymptomSession).filter(SymptomSession.id == req.session_id).first()
        if session:
            chief_complaint = session.chief_complaint
            symptoms_text = " ".join([m.get("content", "") for m in (session.conversation_history or []) if m.get("role") == "user"])

    # 1. MedSpaCy clinical entity extraction
    entities = clinical_extractor.extract_entities(f"{chief_complaint} {symptoms_text}")

    # 2. Emergency triage check
    triage = evaluate_emergency_triage(f"{chief_complaint} {symptoms_text}")

    # 3. Medical knowledge references
    sources = search_medical_knowledge(chief_complaint, max_results=2)
    citations = get_sources_citation_list(sources)

    # 4. Synthesize SOAP Note with syndromic analysis
    diff_considerations = []
    if entities.get("detected_syndromes"):
        for s in entities["detected_syndromes"]:
            diff_considerations.append(f"{s['syndrome']} (Constellation: {', '.join(s['constellation'])})")
    if not diff_considerations:
        diff_considerations = [
            f"Symptom complex consistent with: {chief_complaint}",
            "Self-limiting viral etiology vs acute inflammatory process (to be confirmed clinically)"
        ]

    # Condition-specific tests to consider
    tests_to_consider = ["Complete Blood Count (CBC) with differential"]
    if any("Arboviral" in c for c in diff_considerations):
        tests_to_consider = [
            "Complete Blood Count (CBC) with Platelet Count & Hematocrit (PCV)",
            "Dengue NS1 Antigen Test (Day 1-5)",
            "Dengue IgM / IgG Serology (Day 5+)",
            "Peripheral Blood Smear for Malaria Parasites"
        ]
    elif any("Cardiac" in c for c in diff_considerations):
        tests_to_consider = ["12-Lead Electrocardiogram (ECG)", "High-Sensitivity Cardiac Troponins (hs-cTnI/T)"]
    elif any("Meningeal" in c for c in diff_considerations):
        tests_to_consider = ["Emergency Lumbar Puncture / CSF Analysis", "Blood Cultures & CBC"]

    soap_note = {
        "format": "SOAP (Subjective, Objective, Assessment, Plan)",
        "subjective": {
            "chief_complaint": chief_complaint,
            "history_of_present_illness": symptoms_text,
            "active_symptoms": entities["active_symptoms"],
            "denied_symptoms (negated)": entities["negated_symptoms"],
            "patient_context": history_text
        },
        "objective": {
            "vital_signs_status": "Pending in-person measurement by physician",
            "laboratory_imaging_reviewed": entities["tests_mentioned"] or ["None currently attached"],
            "physical_exam_status": "Requires direct physical examination"
        },
        "assessment": {
            "triage_category": triage["triage_level"],
            "emergency_warning": triage["is_emergency"],
            "differential_considerations": diff_considerations,
            "clinical_notes": "Clinical entities and syndromic constellations extracted via NLP pipeline. Differential considerations provided for physician decision support only."
        },
        "plan": {
            "diagnostic_tests_to_consider": tests_to_consider,
            "non_pharmacological_support": [
                "Adequate rest and oral hydration",
                "Daily symptom and temperature monitoring log"
            ],
            "physician_actions_needed": [
                "Confirm physical examination and auscultation",
                "Verify medication history and drug-drug interactions before any prescription",
                "Sign and approve final treatment course"
            ]
        },
        "sources": citations,
        "disclaimer": "This structured summary is an AI-generated clinical pre-encounter note intended to assist licensed healthcare providers. It is not an independent diagnosis."
    }

    return soap_note
