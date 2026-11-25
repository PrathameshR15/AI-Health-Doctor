import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.models import User, SymptomSession, AssessmentRecord, PatientProfile, AllergyDiet
from backend.schemas import SymptomInitRequest, SymptomAnswerRequest, SymptomFollowUpQuestion
from backend.auth import get_current_user, require_patient
from backend.clinical_nlp import clinical_extractor
from backend.emergency_triage import evaluate_emergency_triage
from backend.openrouter_client import openrouter_client

router = APIRouter(prefix="/api/symptom-checker", tags=["AI Virtual Doctor"])

class VirtualDoctorFollowUpStartRequest(BaseModel):
    previous_session_id: int
    progress_update: Optional[str] = None
    update_note: Optional[str] = None

@router.post("/start", response_model=SymptomFollowUpQuestion)
async def start_symptom_session(req: SymptomInitRequest, current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """
    Step 1: Patient initiates AI Virtual Doctor consultation with natural language symptoms.
    Extracts entities via MedSpaCy, assesses allergies/profile context, runs emergency triage check, generates follow-up question 1.
    """
    # 1. Evaluate emergency red-flag rules
    triage = evaluate_emergency_triage(req.chief_complaint)
    
    # 2. Extract medical entities with MedSpaCy / ConText
    entities = clinical_extractor.extract_entities(req.chief_complaint)

    # 3. Fetch patient profile, chronic conditions, and recorded allergies
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    allergies = db.query(AllergyDiet).filter(AllergyDiet.patient_id == current_user.id).all()
    allergy_list = [f"{a.allergen} ({a.reaction or 'reaction'})" for a in allergies] if allergies else []
    p_context = {
        "gender": profile.gender if profile else "Unspecified",
        "blood_group": profile.blood_group if profile else None,
        "chronic_conditions": profile.chronic_conditions if profile else None,
        "current_medications": profile.current_medications if profile else None,
        "allergies": allergy_list
    }
    
    # 4. Create initial conversation history
    initial_history = [
        {"role": "user", "content": req.chief_complaint, "timestamp": datetime.datetime.utcnow().isoformat()}
    ]

    session = SymptomSession(
        patient_id=current_user.id,
        status="in_progress",
        current_step=1,
        chief_complaint=req.chief_complaint,
        conversation_history=initial_history,
        extracted_entities=entities,
        emergency_flag=triage["is_emergency"],
        triage_level=triage["triage_level"],
        emergency_reasons=[w["warning"] for w in triage["warnings"]]
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 5. Generate next question via OpenRouter / Clinical Engine
    question_data = await openrouter_client.generate_symptom_follow_up(
        chief_complaint=req.chief_complaint,
        conversation_history=initial_history,
        current_step=1,
        extracted_entities=entities,
        patient_context=p_context
    )

    # Record system question in conversation history
    session.conversation_history.append({
        "role": "assistant",
        "content": question_data["question"],
        "options": question_data.get("suggested_options", []),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    db.commit()

    return {
        "session_id": session.id,
        "step": 1,
        "question": question_data["question"],
        "suggested_options": question_data.get("suggested_options", []),
        "is_last_step": question_data.get("is_last_step", False),
        "emergency_flag": triage["is_emergency"] or question_data.get("emergency_flag", False),
        "emergency_message": triage["recommended_action"] if triage["is_emergency"] else None
    }

@router.post("/answer")
async def answer_symptom_question(req: SymptomAnswerRequest, current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """
    Step 2 & 3: Patient submits answer. If final step, generates comprehensive health assessment
    and sends report to Doctor Portal with review tracking.
    """
    session = db.query(SymptomSession).filter(
        SymptomSession.id == req.session_id,
        SymptomSession.patient_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Symptom session not found or unauthorized.")

    # Append user answer
    history = list(session.conversation_history or [])
    history.append({
        "role": "user",
        "content": req.answer,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    session.conversation_history = history

    # Re-evaluate emergency conditions on the latest answer
    triage = evaluate_emergency_triage(f"{session.chief_complaint} {req.answer}")
    if triage["is_emergency"]:
        session.emergency_flag = True
        session.triage_level = "EMERGENCY"

    next_step = session.current_step + 1
    session.current_step = next_step

    # Fetch patient profile and allergy context
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    allergies = db.query(AllergyDiet).filter(AllergyDiet.patient_id == current_user.id).all()
    allergy_list = [f"{a.allergen} ({a.reaction or 'reaction'})" for a in allergies] if allergies else []
    p_context = {
        "gender": profile.gender if profile else "Unspecified",
        "blood_group": profile.blood_group if profile else None,
        "chronic_conditions": profile.chronic_conditions if profile else None,
        "current_medications": profile.current_medications if profile else None,
        "allergies": allergy_list
    }

    # Check if user requested doctor advice directly or if we should conclude
    wants_advice = bool(req.give_immediate_advice) or any(w in req.answer.lower() for w in [
        "give me advice", "give advice", "advice", "what should be done", "cure", "prevention", "why it happen", "why does it happen"
    ])

    # Check if we should conclude and produce final assessment
    if next_step >= 3 or session.emergency_flag or wants_advice:
        session.status = "completed"

        # Build full conversation text
        full_convo_text = " ".join([m.get("content", "") for m in history if m.get("role") == "user"])
        
        # Update entity extraction across full dialogue
        full_entities = clinical_extractor.extract_entities(full_convo_text)
        session.extracted_entities = full_entities

        print("\n======================================================================")
        print("[AI VIRTUAL DOCTOR CONSULTATION COMPLETED]")
        print(f"Chief Complaint       : {session.chief_complaint}")
        print(f"Full User Dialogue    : {full_convo_text}")
        print(f"Active Symptoms       : {full_entities['active_symptoms']}")
        print(f"Negated Symptoms      : {full_entities['negated_symptoms']}")
        print(f"Duration Extracted    : {full_entities['duration_info']}")
        print(f"Detected Syndromes    : {[s['syndrome'] for s in full_entities['detected_syndromes']]}")
        print("======================================================================\n")

        # Generate full AI Virtual Doctor health assessment
        assessment_data = await openrouter_client.generate_health_assessment(
            chief_complaint=session.chief_complaint,
            conversation_text=full_convo_text,
            patient_context=p_context,
            extracted_entities=full_entities
        )

        session.possible_conditions = assessment_data.get("possible_conditions", [])
        session.precautions = assessment_data.get("precautions", [])
        session.test_guidance = assessment_data.get("test_guidance", [])

        # Store in AssessmentRecord for doctor review and medical history
        assessment_record = AssessmentRecord(
            patient_id=current_user.id,
            session_id=session.id,
            title=f"AI Virtual Doctor: {session.chief_complaint[:60]}",
            chief_complaint=session.chief_complaint,
            symptoms_summary=full_convo_text,
            extracted_entities=full_entities,
            possible_conditions=assessment_data.get("possible_conditions", []),
            precautions=assessment_data.get("precautions", []),
            test_guidance=assessment_data.get("test_guidance", []),
            diet_guidance=assessment_data.get("diet_guidance", {}),
            medication_info=assessment_data.get("medication_info", []),
            consultation_summary=assessment_data.get("consultation_summary", {}),
            sources=assessment_data.get("sources", []),
            triage_level=session.triage_level,
            emergency_warning=session.emergency_flag,
            doctor_review_status="pending"
        )
        db.add(assessment_record)
        db.commit()
        db.refresh(assessment_record)

        advice_text = None
        if wants_advice:
            why_txt = assessment_data.get("why_it_happens", "")
            advice_text = f"Here is my doctor's advice on what should be done as a cure or relief, how to prevent it, and why this happens:\n\n🔍 Why It Happens:\n{why_txt}\n\nI have organized your complete home cure, prevention guide, exercises, and safety precautions below."

        return {
            "session_id": session.id,
            "is_completed": True,
            "step": next_step,
            "assessment_id": assessment_record.id,
            "assessment": assessment_data,
            "emergency_warning": session.emergency_flag,
            "triage_level": session.triage_level,
            "doctor_integration": {
                "status": "sent_to_doctor_portal",
                "assessment_id": assessment_record.id,
                "review_status": assessment_record.doctor_review_status,
                "message": "Consultation summary sent to Doctor Portal for review and physician sign-off."
            },
            "assistant_reply": advice_text,
            "message": "Assessment generated successfully."
        }
    else:
        # Generate next follow-up question
        user_history_text = " ".join([m.get("content", "") for m in history if m.get("role") == "user"])
        current_entities = clinical_extractor.extract_entities(user_history_text)
        question_data = await openrouter_client.generate_symptom_follow_up(
            chief_complaint=session.chief_complaint,
            conversation_history=history,
            current_step=next_step,
            extracted_entities=current_entities,
            patient_context=p_context
        )
        history.append({
            "role": "assistant",
            "content": question_data["question"],
            "options": question_data.get("suggested_options", []),
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        session.conversation_history = history
        db.commit()

        return {
            "session_id": session.id,
            "is_completed": False,
            "step": next_step,
            "question": question_data["question"],
            "suggested_options": question_data.get("suggested_options", []),
            "is_last_step": question_data.get("is_last_step", False),
            "emergency_flag": session.emergency_flag,
            "emergency_message": triage["recommended_action"] if session.emergency_flag else None
        }

@router.get("/sessions")
def get_user_symptom_sessions(current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """List all previous symptom checker sessions for current patient with doctor review status."""
    sessions = db.query(SymptomSession).filter(
        SymptomSession.patient_id == current_user.id
    ).order_by(SymptomSession.created_at.desc()).all()

    results = []
    for s in sessions:
        # Check linked assessment record
        assessment = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == s.id).first()
        results.append({
            "id": s.id,
            "assessment_id": assessment.id if assessment else None,
            "chief_complaint": s.chief_complaint,
            "status": s.status,
            "triage_level": s.triage_level,
            "emergency_flag": s.emergency_flag,
            "doctor_review_status": assessment.doctor_review_status if assessment else "pending",
            "doctor_notes": assessment.doctor_notes if assessment else None,
            "created_at": s.created_at.isoformat(),
            "possible_conditions_count": len(s.possible_conditions or [])
        })
    return results

@router.get("/session/{session_id}")
def get_symptom_session_detail(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve full details, chat transcript, and doctor review status of an AI Virtual Doctor session."""
    session = db.query(SymptomSession).filter(SymptomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    # Patients can only access their own
    if current_user.role == "patient" and session.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to patient record.")

    assessment = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == session.id).first()

    return {
        "id": session.id,
        "assessment_id": assessment.id if assessment else None,
        "patient_id": session.patient_id,
        "chief_complaint": session.chief_complaint,
        "status": session.status,
        "conversation_history": session.conversation_history,
        "extracted_entities": session.extracted_entities,
        "possible_conditions": session.possible_conditions,
        "precautions": session.precautions,
        "test_guidance": session.test_guidance,
        "emergency_flag": session.emergency_flag,
        "triage_level": session.triage_level,
        "emergency_reasons": session.emergency_reasons,
        "doctor_review_status": assessment.doctor_review_status if assessment else "pending",
        "doctor_notes": assessment.doctor_notes if assessment else None,
        "reviewed_at": assessment.reviewed_at.isoformat() if (assessment and assessment.reviewed_at) else None,
        "created_at": session.created_at.isoformat()
    }

@router.get("/doctor-status/{assessment_id}")
def get_consultation_doctor_status(assessment_id: int, current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """Check live doctor review status for an AI Virtual Doctor consultation."""
    assessment = db.query(AssessmentRecord).filter(
        AssessmentRecord.id == assessment_id,
        AssessmentRecord.patient_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment record not found.")

    reviewer = None
    if assessment.reviewed_by_id:
        doctor_user = db.query(User).filter(User.id == assessment.reviewed_by_id).first()
        if doctor_user:
            reviewer = doctor_user.full_name

    return {
        "assessment_id": assessment.id,
        "session_id": assessment.session_id,
        "doctor_review_status": assessment.doctor_review_status,
        "doctor_notes": assessment.doctor_notes,
        "reviewed_by": reviewer,
        "reviewed_at": assessment.reviewed_at.isoformat() if assessment.reviewed_at else None
    }

@router.post("/follow-up-start")
async def start_follow_up_session(
    req: VirtualDoctorFollowUpStartRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Starts a follow-up consultation linked to a previous session to track symptom evolution and progress.
    """
    prev_session = db.query(SymptomSession).filter(
        SymptomSession.id == req.previous_session_id,
        SymptomSession.patient_id == current_user.id
    ).first()
    if not prev_session:
        raise HTTPException(status_code=404, detail="Previous consultation session not found.")

    prev_complaint = prev_session.chief_complaint
    prev_active_syms = prev_session.extracted_entities.get("active_symptoms", []) if prev_session.extracted_entities else []
    prev_sym_str = ", ".join(prev_active_syms) if prev_active_syms else prev_complaint

    complaint_text = f"Follow-up on previous consultation regarding: {prev_complaint}."
    update_text = req.progress_update or req.update_note
    if update_text:
        complaint_text += f" Patient update: {update_text}"

    initial_question = (
        f"Welcome back! In our previous consultation on {prev_session.created_at.strftime('%b %d')}, "
        f"we evaluated: {prev_sym_str}. How are these symptoms progressing today?"
    )
    suggested_options = [
        "Significantly improved / almost resolved",
        "About the same / persistent discomfort",
        "Worse or new symptoms appeared",
        "💡 Give me advice: Cure, prevention & why it happens"
    ]

    initial_history = [
        {"role": "user", "content": complaint_text, "timestamp": datetime.datetime.utcnow().isoformat()},
        {"role": "assistant", "content": initial_question, "options": suggested_options, "timestamp": datetime.datetime.utcnow().isoformat()}
    ]

    new_session = SymptomSession(
        patient_id=current_user.id,
        status="in_progress",
        current_step=1,
        chief_complaint=complaint_text,
        conversation_history=initial_history,
        extracted_entities={"active_symptoms": prev_active_syms, "is_follow_up": True, "parent_session_id": prev_session.id},
        emergency_flag=False,
        triage_level="routine"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "session_id": new_session.id,
        "step": 1,
        "question": initial_question,
        "suggested_options": suggested_options,
        "is_last_step": False,
        "emergency_flag": False,
        "emergency_message": None,
        "is_follow_up": True,
        "parent_session_id": prev_session.id
    }

@router.get("/patient-history")
def get_patient_consultation_history(current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """
    Feature 8: Symptom tracking and longitudinal progress monitoring across consultations.
    """
    sessions = db.query(SymptomSession).filter(
        SymptomSession.patient_id == current_user.id
    ).order_by(SymptomSession.created_at.desc()).all()

    history_records = []
    for s in sessions:
        assessment = db.query(AssessmentRecord).filter(AssessmentRecord.session_id == s.id).first()
        reviewer_name = None
        if assessment and assessment.reviewed_by_id:
            doc = db.query(User).filter(User.id == assessment.reviewed_by_id).first()
            if doc:
                reviewer_name = doc.full_name

        history_records.append({
            "session_id": s.id,
            "assessment_id": assessment.id if assessment else None,
            "date": s.created_at.strftime("%b %d, %Y - %I:%M %p"),
            "chief_complaint": s.chief_complaint,
            "status": s.status,
            "triage_level": s.triage_level,
            "emergency_flag": s.emergency_flag,
            "active_symptoms": s.extracted_entities.get("active_symptoms", []) if s.extracted_entities else [],
            "possible_conditions": s.possible_conditions or [],
            "doctor_review_status": assessment.doctor_review_status if assessment else "pending",
            "doctor_notes": assessment.doctor_notes if assessment else None,
            "reviewed_by": reviewer_name,
            "reviewed_at": assessment.reviewed_at.isoformat() if (assessment and assessment.reviewed_at) else None
        })

    return {
        "total_consultations": len(history_records),
        "consultations": history_records
    }

