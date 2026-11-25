import re
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.database import get_db
from backend.models import User, PatientProfile, SymptomSession, MedicalReport, AssessmentRecord, AllergyDiet, DoctorNote
from backend.auth import get_current_user
from backend.fhir_service import fhir_service

router = APIRouter(prefix="/api/history", tags=["Medical History Summary"])

def summarize_assessment_2_words(a: AssessmentRecord) -> str:
    """Extracts exactly a concise 2-word summary of what was assessed."""
    if a.possible_conditions:
        first = a.possible_conditions[0]
        c = first.get("condition") or first.get("name") if isinstance(first, dict) else str(first)
        if c:
            clean = re.sub(r"\(.*?\)", "", c)
            clean = re.sub(r"^(suspected|acute|mild|chronic)\s+", "", clean, flags=re.IGNORECASE).strip()
            words = [w for w in re.split(r"[\s/,-]+", clean) if len(w) > 1]
            if len(words) >= 2:
                return f"{words[0].capitalize()} {words[1].capitalize()}"
            elif len(words) == 1:
                return f"{words[0].capitalize()} Condition"

    comp = (a.chief_complaint or a.title or "Health Consultation").lower()
    if any(w in comp for w in ["sinus", "cheek", "nasal"]): return "Sinusitis Evaluation"
    if any(w in comp for w in ["headache", "migraine", "head pain"]): return "Headache Evaluation"
    if any(w in comp for w in ["cough", "throat", "bronchitis"]): return "Respiratory Evaluation"
    if any(w in comp for w in ["stomach", "gastric", "acidity", "nausea"]): return "Gastric Evaluation"
    if any(w in comp for w in ["fever", "chills"]): return "Febrile Evaluation"
    if any(w in comp for w in ["fatigue", "tired", "weakness"]): return "Fatigue Evaluation"
    
    words = [w for w in re.split(r"[\s/,-]+", a.chief_complaint or a.title or "") if len(w) > 2]
    if len(words) >= 2:
        return f"{words[0].capitalize()} {words[1].capitalize()}"
    return "Health Assessment"

def summarize_report_conclusion_3_words(r: MedicalReport) -> str:
    """Extracts exactly a concise 3-word conclusion of what the report analysis showed."""
    ext = r.extracted_entities or {}
    abnormal = ext.get("abnormal_findings", [])
    if not abnormal and r.clinical_findings:
        abnormal = [f for f in r.clinical_findings if isinstance(f, dict) and f.get("status") in ["High", "Low", "Abnormal"]]
    
    if abnormal:
        abn_text = " ".join([str(a.get("finding", "")).lower() for a in abnormal])
        has_platelet = "platelet" in abn_text
        has_hb = "hemoglobin" in abn_text or "hgb" in abn_text or "anemia" in abn_text
        has_wbc = "wbc" in abn_text or "white" in abn_text
        has_glucose = "glucose" in abn_text or "sugar" in abn_text
        has_creat = "creatinine" in abn_text

        if has_platelet and has_hb:
            return "Thrombocytopenia Anemia Detected"
        elif has_platelet:
            return "Low Platelets Detected"
        elif has_wbc:
            return "High WBC Count"
        elif has_glucose:
            return "Elevated Blood Glucose"
        elif has_creat:
            return "Elevated Serum Creatinine"
        elif has_hb:
            return "Low Hemoglobin Anemia"
        else:
            first_param = abnormal[0].get("finding", "Parameter").split()[0]
            first_status = abnormal[0].get("status", "Abnormal")
            return f"{first_param} {first_status} Detected"
    return "Normal Blood Indices"

def build_health_timeline(assessments, reports, doctor_notes):
    """Constructs the comprehensive chronological health timeline with 2-word assessment and 3-word report summaries."""
    timeline = []

    # 1. AI Assessments Done (What in 2 words)
    for a in assessments:
        two_words = summarize_assessment_2_words(a)
        dt_str = a.created_at.strftime("%b %d, %Y • %I:%M %p")
        timeline.append({
            "id": f"assess-{a.id}",
            "type": "ai_assessment",
            "event_label": "AI Assessment Done",
            "highlight": two_words,  # 2 words summary
            "two_word_summary": two_words,
            "date": a.created_at.isoformat(),
            "date_time": dt_str,
            "title": a.title or a.chief_complaint,
            "summary": a.chief_complaint,
            "badge": a.triage_level,
            "doctor_review_status": a.doctor_review_status,
            "possible_conditions": [c.get("condition") or c for c in (a.possible_conditions or [])][:2]
        })

        # Treatment Plan Approved by Doctor
        if a.doctor_review_status == "approved" and a.reviewed_at:
            rev_dt = a.reviewed_at.strftime("%b %d, %Y • %I:%M %p")
            timeline.append({
                "id": f"approve-{a.id}",
                "type": "treatment_start",
                "event_label": "Treatment Plan Approved",
                "highlight": "Treatment Plan Approved",
                "summary_3_words": "Treatment Plan Approved",
                "date": a.reviewed_at.isoformat(),
                "date_time": rev_dt,
                "title": f"Physician Approval: {two_words}",
                "summary": a.doctor_notes or "Physician verified and approved clinical care plan.",
                "badge": "Approved",
                "doctor_review_status": "approved"
            })

    # 2. Medical Reports Analyzed (What concluded in 3 words)
    for r in reports:
        three_words = summarize_report_conclusion_3_words(r)
        dt_str = r.uploaded_at.strftime("%b %d, %Y • %I:%M %p")
        has_abn = (r.extracted_entities or {}).get("has_abnormalities", False)
        timeline.append({
            "id": f"report-{r.id}",
            "type": "report_analyzed",
            "event_label": "Report Analyzed",
            "highlight": three_words,  # 3 words conclusion
            "three_word_conclusion": three_words,
            "date": r.uploaded_at.isoformat(),
            "date_time": dt_str,
            "title": f"Report: {r.file_name}",
            "summary": (r.extracted_entities or {}).get("relevant_conclusion") or r.key_observations or "Clinical diagnostic report evaluated.",
            "badge": r.file_type.upper(),
            "has_abnormalities": has_abn
        })

    # 3. Treatment Started (Clinical Notes & Prescriptions)
    for n in doctor_notes:
        dt_str = n.created_at.strftime("%b %d, %Y • %I:%M %p")
        is_rx = n.note_type in ["prescription", "medication"]
        timeline.append({
            "id": f"treatment-{n.id}",
            "type": "treatment_start",
            "event_label": "Treatment Started" if is_rx else "Clinical Treatment Plan",
            "highlight": "Prescription Treatment Started" if is_rx else "Clinical Care Initiated",
            "summary_3_words": "Prescription Therapy Initiated" if is_rx else "Clinical Treatment Started",
            "date": n.created_at.isoformat(),
            "date_time": dt_str,
            "title": n.title,
            "summary": n.content,
            "badge": n.note_type.capitalize()
        })

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline

@router.get("/summary")
def get_patient_history_summary(
    patient_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Feature 3: Organize patient symptoms, diagnoses, medications, and medical history.
    Includes chronological health timeline with 2-word AI assessment and 3-word report summaries.
    """
    # If patient, strictly their own id
    target_id = current_user.id
    if current_user.role == "doctor" and patient_id is not None:
        target_id = patient_id

    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found.")

    profile = db.query(PatientProfile).filter(PatientProfile.user_id == target_id).first()
    assessments = db.query(AssessmentRecord).filter(AssessmentRecord.patient_id == target_id).order_by(AssessmentRecord.created_at.desc()).all()
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == target_id).order_by(MedicalReport.uploaded_at.desc()).all()
    allergies = db.query(AllergyDiet).filter(AllergyDiet.patient_id == target_id).all()
    doctor_notes = db.query(DoctorNote).filter(DoctorNote.patient_id == target_id).order_by(DoctorNote.created_at.desc()).all()

    # Aggregate active symptoms from recent assessments
    recent_symptoms = []
    conditions_list = []
    seen_cond = set()
    for a in assessments:
        if a.possible_conditions:
            for c in a.possible_conditions:
                c_name = c.get("condition")
                if c_name and c_name not in seen_cond:
                    seen_cond.add(c_name)
                    conditions_list.append({
                        "name": c_name,
                        "likelihood": c.get("likelihood", "Assessed"),
                        "date": a.created_at.strftime("%Y-%m-%d"),
                        "status": a.doctor_review_status
                    })
        if a.chief_complaint:
            recent_symptoms.append({
                "complaint": a.chief_complaint,
                "date": a.created_at.strftime("%Y-%m-%d"),
                "triage": a.triage_level
            })

    # Build chronological health timeline
    timeline = build_health_timeline(assessments, reports, doctor_notes)

    return {
        "patient": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "dob": profile.date_of_birth if profile else None,
            "gender": profile.gender if profile else None,
            "blood_group": profile.blood_group if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "chronic_conditions": profile.chronic_conditions if profile else None,
            "current_medications": profile.current_medications if profile else None,
            "emergency_contact": profile.emergency_contact if profile else None
        },
        "recent_symptoms": recent_symptoms,
        "diagnoses_and_assessments": conditions_list,
        "allergies": [
            {
                "allergen": al.allergen,
                "reaction": al.reaction,
                "severity": al.severity,
                "doctor_approved": al.doctor_approved
            }
            for al in allergies
        ],
        "timeline": timeline,
        "total_assessments": len(assessments),
        "total_reports": len(reports),
        "total_notes": len(doctor_notes)
    }

@router.get("/fhir-export")
def export_patient_fhir_bundle(
    patient_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports complete patient history as a standardized HL7 FHIR R4 Bundle.
    """
    target_id = current_user.id
    if current_user.role == "doctor" and patient_id is not None:
        target_id = patient_id

    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found.")

    profile = db.query(PatientProfile).filter(PatientProfile.user_id == target_id).first()
    assessments = db.query(AssessmentRecord).filter(AssessmentRecord.patient_id == target_id).all()
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == target_id).all()
    allergies = db.query(AllergyDiet).filter(AllergyDiet.patient_id == target_id).all()

    resources = []

    # 1. Patient Resource
    patient_res = fhir_service.create_patient_resource(
        user_id=user.id,
        full_name=user.full_name,
        dob=profile.date_of_birth if profile else None,
        gender=profile.gender if profile else None,
        phone=user.phone
    )
    resources.append(patient_res)

    # 2. Condition Resources
    for a in assessments:
        for c in (a.possible_conditions or []):
            if isinstance(c, dict) and "condition" in c:
                cond_res = fhir_service.create_condition_resource(
                    patient_id=user.id,
                    condition_name=c["condition"],
                    verification_status="provisional" if a.doctor_review_status != "approved" else "confirmed"
                )
                resources.append(cond_res)

    # 3. AllergyIntolerance Resources
    for al in allergies:
        al_res = fhir_service.create_allergy_intolerance_resource(
            patient_id=user.id,
            allergen=al.allergen,
            reaction=al.reaction,
            severity=al.severity
        )
        resources.append(al_res)

    # 4. DiagnosticReport Resources
    for r in reports:
        diag_res = fhir_service.create_diagnostic_report_resource(
            patient_id=user.id,
            title=r.file_name,
            conclusion=r.key_observations or "Clinical document record.",
            findings=r.clinical_findings or []
        )
        resources.append(diag_res)

    bundle = fhir_service.create_bundle(resources, bundle_type="document")
    return bundle
