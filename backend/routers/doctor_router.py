import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database import get_db
from backend.models import User, PatientProfile, AssessmentRecord, MedicalReport, AllergyDiet, DoctorNote
from backend.schemas import AssessmentReviewRequest, DoctorNoteCreate
from backend.auth import require_doctor
from backend.routers.history_router import build_health_timeline

router = APIRouter(prefix="/api/doctor", tags=["Doctor Portal Management"])

@router.get("/dashboard-stats")
def get_doctor_dashboard_stats(current_user: User = Depends(require_doctor), db: Session = Depends(get_db)):
    """Summary metrics for Doctor Dashboard."""
    total_patients = db.query(User).filter(User.role == "patient").count()
    pending_reviews = db.query(AssessmentRecord).filter(AssessmentRecord.doctor_review_status == "pending").count()
    emergency_alerts = db.query(AssessmentRecord).filter(AssessmentRecord.emergency_warning == True).count()
    total_reports = db.query(MedicalReport).count()
    notes_written = db.query(DoctorNote).filter(DoctorNote.doctor_id == current_user.id).count()

    recent_assessments = db.query(AssessmentRecord).order_by(AssessmentRecord.created_at.desc()).limit(5).all()

    return {
        "doctor_name": current_user.full_name,
        "total_patients": total_patients,
        "pending_assessments_count": pending_reviews,
        "emergency_alerts_count": emergency_alerts,
        "total_reports_uploaded": total_reports,
        "notes_written_count": notes_written,
        "recent_activity": [
            {
                "id": a.id,
                "patient_id": a.patient_id,
                "title": a.title,
                "chief_complaint": a.chief_complaint,
                "triage_level": a.triage_level,
                "emergency_warning": a.emergency_warning,
                "review_status": a.doctor_review_status,
                "created_at": a.created_at.isoformat()
            }
            for a in recent_assessments
        ]
    }

@router.get("/patients")
def list_patients(search: Optional[str] = None, current_user: User = Depends(require_doctor), db: Session = Depends(get_db)):
    """List all registered patients with their profile summaries."""
    query = db.query(User).filter(User.role == "patient")
    if search:
        query = query.filter(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    
    patients = query.order_by(User.full_name.asc()).all()
    results = []
    for p in patients:
        profile = p.patient_profile
        assessments_count = len(p.assessments or [])
        reports_count = len(p.medical_reports or [])
        results.append({
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone,
            "dob": profile.date_of_birth if profile else None,
            "gender": profile.gender if profile else None,
            "blood_group": profile.blood_group if profile else None,
            "chronic_conditions": profile.chronic_conditions if profile else None,
            "current_medications": profile.current_medications if profile else None,
            "assessments_count": assessments_count,
            "reports_count": reports_count,
            "created_at": p.created_at.isoformat()
        })
    return results

@router.get("/patient/{patient_id}")
def get_patient_detail(patient_id: int, current_user: User = Depends(require_doctor), db: Session = Depends(get_db)):
    """Deep dive into a specific patient's complete clinical chart."""
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    profile = patient.patient_profile
    assessments = db.query(AssessmentRecord).filter(AssessmentRecord.patient_id == patient_id).order_by(AssessmentRecord.created_at.desc()).all()
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id).order_by(MedicalReport.uploaded_at.desc()).all()
    allergies = db.query(AllergyDiet).filter(AllergyDiet.patient_id == patient_id).all()
    notes = db.query(DoctorNote).filter(DoctorNote.patient_id == patient_id).order_by(DoctorNote.created_at.desc()).all()

    # Build rich reports list with review status
    rep_list = []
    for r in reports:
        linked_ass = db.query(AssessmentRecord).filter(AssessmentRecord.report_id == r.id).first()
        ext = r.extracted_entities or {}
        rep_list.append({
            "id": r.id,
            "assessment_id": linked_ass.id if linked_ass else None,
            "file_name": r.file_name,
            "file_type": r.file_type,
            "key_observations": r.key_observations,
            "clinical_findings": r.clinical_findings,
            "abnormal_findings": ext.get("abnormal_findings", []),
            "has_abnormalities": ext.get("has_abnormalities", False),
            "is_prescription": ext.get("is_prescription", False),
            "medications": ext.get("medications", []),
            "relevant_conclusion": ext.get("relevant_conclusion", ""),
            "short_analysis": ext.get("short_analysis", ""),
            "doctor_review_status": linked_ass.doctor_review_status if linked_ass else "pending",
            "doctor_notes": linked_ass.doctor_notes if linked_ass else None,
            "uploaded_at": r.uploaded_at.isoformat()
        })

    return {
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "email": patient.email,
            "phone": patient.phone,
            "dob": profile.date_of_birth if profile else None,
            "gender": profile.gender if profile else None,
            "blood_group": profile.blood_group if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "chronic_conditions": profile.chronic_conditions if profile else None,
            "current_medications": profile.current_medications if profile else None,
            "emergency_contact": profile.emergency_contact if profile else None,
            "ai_consent_given": profile.ai_consent_given if profile else True
        },
        "assessments": [
            {
                "id": a.id,
                "title": a.title,
                "chief_complaint": a.chief_complaint,
                "symptoms_summary": a.symptoms_summary,
                "extracted_entities": a.extracted_entities,
                "triage_level": a.triage_level,
                "emergency_warning": a.emergency_warning,
                "doctor_review_status": a.doctor_review_status,
                "doctor_notes": a.doctor_notes,
                "possible_conditions": a.possible_conditions,
                "precautions": a.precautions,
                "test_guidance": a.test_guidance,
                "consultation_summary": a.consultation_summary,
                "created_at": a.created_at.isoformat()
            }
            for a in assessments
        ],
        "reports": rep_list,
        "allergies": [
            {
                "id": al.id,
                "allergen": al.allergen,
                "reaction": al.reaction,
                "severity": al.severity,
                "foods_to_avoid": al.foods_to_avoid,
                "recommended_foods": al.recommended_foods,
                "doctor_approved": al.doctor_approved,
                "doctor_notes": al.doctor_notes
            }
            for al in allergies
        ],
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "note_type": n.note_type,
                "doctor_id": n.doctor_id,
                "created_at": n.created_at.isoformat()
            }
            for n in notes
        ],
        "timeline": build_health_timeline(assessments, reports, notes)
    }

@router.get("/assessments")
def get_all_assessments(status_filter: Optional[str] = None, current_user: User = Depends(require_doctor), db: Session = Depends(get_db)):
    """List AI assessments for doctor review queue."""
    query = db.query(AssessmentRecord)
    if status_filter:
        query = query.filter(AssessmentRecord.doctor_review_status == status_filter)
    
    assessments = query.order_by(AssessmentRecord.created_at.desc()).all()
    results = []
    for a in assessments:
        patient = a.patient
        results.append({
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": patient.full_name if patient else "Unknown",
            "title": a.title,
            "chief_complaint": a.chief_complaint,
            "symptoms_summary": a.symptoms_summary,
            "extracted_symptoms": (a.extracted_entities or {}).get("active_symptoms", []),
            "triage_level": a.triage_level,
            "emergency_warning": a.emergency_warning,
            "doctor_review_status": a.doctor_review_status,
            "doctor_notes": a.doctor_notes,
            "possible_conditions_count": len(a.possible_conditions or []),
            "created_at": a.created_at.isoformat()
        })
    return results

@router.post("/assessment-review/{assessment_id}")
def review_assessment(
    assessment_id: int,
    review_in: AssessmentReviewRequest,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Doctor reviews, annotates, and approves an AI assessment."""
    assessment = db.query(AssessmentRecord).filter(AssessmentRecord.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    assessment.doctor_review_status = review_in.status
    assessment.doctor_notes = review_in.doctor_notes
    assessment.reviewed_by_id = current_user.id
    assessment.reviewed_at = datetime.datetime.utcnow()

    # Automatically add a doctor note to the patient chart
    note = DoctorNote(
        patient_id=assessment.patient_id,
        doctor_id=current_user.id,
        title=f"Review of Assessment: {assessment.chief_complaint[:50]}",
        content=review_in.doctor_notes,
        note_type="clinical"
    )
    db.add(note)
    db.commit()

    return {
        "status": "success",
        "assessment_id": assessment.id,
        "doctor_review_status": assessment.doctor_review_status,
        "reviewed_by": current_user.full_name,
        "reviewed_at": assessment.reviewed_at.isoformat(),
        "message": "Assessment signed off and recorded in patient chart."
    }

@router.post("/notes")
def create_doctor_note(
    note_in: DoctorNoteCreate,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Doctor writes clinical notes for a patient."""
    patient = db.query(User).filter(User.id == note_in.patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    note = DoctorNote(
        patient_id=note_in.patient_id,
        doctor_id=current_user.id,
        title=note_in.title,
        content=note_in.content,
        note_type=note_in.note_type
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return {
        "status": "success",
        "note_id": note.id,
        "title": note.title,
        "created_at": note.created_at.isoformat()
    }
