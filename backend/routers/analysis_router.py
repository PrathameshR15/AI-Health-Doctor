import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, AssessmentRecord, PatientProfile
from backend.schemas import FullHealthAnalysisRequest
from backend.auth import require_patient, get_current_user
from backend.clinical_nlp import clinical_extractor
from backend.emergency_triage import evaluate_emergency_triage
from backend.openrouter_client import openrouter_client

router = APIRouter(prefix="/api/analyze", tags=["Analyze My Health"])

@router.post("/full-assessment")
async def perform_full_health_analysis(
    req: FullHealthAnalysisRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Patient Portal: 'Analyze My Health'
    Unified multi-feature AI health assessment generating:
    - Possible conditions (with likelihood and rationale)
    - Health precautions (non-drug)
    - Medical test guidance
    - Allergy & diet guidance
    - Medication education (NO dosages)
    - Doctor consultation SOAP summary
    - Verified citations from WHO, NHS, MedlinePlus, ICMR, NCDC India
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    
    print("\n======================================================================")
    print("[PIPELINE STEP 1: FRONTEND INPUT RECEIVED]")
    print(f"Chief Complaint       : {req.chief_complaint}")
    print(f"Duration Field        : {req.duration}")
    print(f"Severity Field        : {req.severity_1_10}/10")
    print(f"Accompanying Symptoms : {req.accompanying_symptoms}")
    print(f"Known Chronic Conds   : {req.known_conditions}")
    print(f"Known Allergies       : {req.known_allergies}")
    print("======================================================================")

    # 1. Combine patient narrative strictly for current on-time presentation (isolate from past/background conditions)
    full_narrative = (
        f"{req.chief_complaint}. Duration: {req.duration or 'Not specified'}. "
        f"Severity: {req.severity_1_10}/10. "
        f"Accompanying symptoms: {', '.join(req.accompanying_symptoms) if req.accompanying_symptoms else 'None reported'}."
    )

    # 2. Independent emergency rule engine on current presentation
    emergency_triage = evaluate_emergency_triage(full_narrative)

    # 3. Clinical entity extraction strictly on current presentation
    entities = clinical_extractor.extract_entities(
        text=full_narrative,
        accompanying_symptoms=req.accompanying_symptoms,
        explicit_duration=req.duration,
        explicit_severity=req.severity_1_10
    )

    print("\n======================================================================")
    print("[PIPELINE STEP 2: EXTRACTED SYMPTOMS & CLINICAL ENTITIES]")
    print(f"Active Symptoms       : {entities['active_symptoms']}")
    print(f"Negated Symptoms      : {entities['negated_symptoms']}")
    print(f"Warning Signs         : {entities['warning_signs']}")
    print(f"Duration Extracted    : {entities['duration_info']}")
    print(f"Severity Extracted    : {entities['severity_info']}")
    print(f"Detected Syndromes    : {[s['syndrome'] for s in entities['detected_syndromes']]}")
    print("======================================================================\n")

    # 4. Context for LLM
    patient_context = {
        "gender": profile.gender if profile else "Unspecified",
        "chronic_conditions": profile.chronic_conditions if profile else None,
        "current_medications": profile.current_medications if profile else None
    }

    # 5. OpenRouter / Clinical Engine generation
    assessment_data = await openrouter_client.generate_health_assessment(
        chief_complaint=req.chief_complaint,
        conversation_text=full_narrative,
        patient_context=patient_context,
        extracted_entities=entities
    )

    # 6. Save AssessmentRecord in database
    record = AssessmentRecord(
        patient_id=current_user.id,
        title=f"Health Analysis: {req.chief_complaint[:50]}",
        chief_complaint=req.chief_complaint,
        symptoms_summary=full_narrative,
        extracted_entities=entities,
        possible_conditions=assessment_data.get("possible_conditions", []),
        precautions=assessment_data.get("precautions", []),
        test_guidance=assessment_data.get("test_guidance", []),
        diet_guidance=assessment_data.get("diet_guidance", {}),
        medication_info=assessment_data.get("medication_info", []),
        consultation_summary=assessment_data.get("consultation_summary", {}),
        sources=assessment_data.get("sources", []),
        triage_level=emergency_triage["triage_level"],
        emergency_warning=emergency_triage["is_emergency"],
        doctor_review_status="pending"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "success",
        "assessment_id": record.id,
        "emergency_triage": emergency_triage,
        "extracted_entities": entities,
        "assessment": assessment_data,
        "review_status": "Queued for Doctor Review",
        "created_at": record.created_at.isoformat()
    }

@router.get("/previous")
def get_previous_assessments(current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """Retrieve all previously generated AI assessments for the patient."""
    assessments = db.query(AssessmentRecord).filter(
        AssessmentRecord.patient_id == current_user.id
    ).order_by(AssessmentRecord.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "chief_complaint": a.chief_complaint,
            "triage_level": a.triage_level,
            "emergency_warning": a.emergency_warning,
            "doctor_review_status": a.doctor_review_status,
            "doctor_notes": a.doctor_notes,
            "possible_conditions_count": len(a.possible_conditions or []),
            "created_at": a.created_at.isoformat()
        }
        for a in assessments
    ]

@router.get("/detail/{assessment_id}")
def get_assessment_detail(assessment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve full details of a specific AI assessment (accessible by the patient or reviewing doctor)."""
    query = db.query(AssessmentRecord).filter(AssessmentRecord.id == assessment_id)
    if current_user.role == "patient":
        query = query.filter(AssessmentRecord.patient_id == current_user.id)
        
    a = query.first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    return {
        "id": a.id,
        "title": a.title,
        "chief_complaint": a.chief_complaint,
        "symptoms_summary": a.symptoms_summary,
        "extracted_entities": a.extracted_entities,
        "possible_conditions": a.possible_conditions,
        "precautions": a.precautions,
        "test_guidance": a.test_guidance,
        "diet_guidance": a.diet_guidance,
        "medication_info": a.medication_info,
        "consultation_summary": a.consultation_summary,
        "sources": a.sources,
        "triage_level": a.triage_level,
        "emergency_warning": a.emergency_warning,
        "doctor_review_status": a.doctor_review_status,
        "doctor_notes": a.doctor_notes,
        "created_at": a.created_at.isoformat()
    }
