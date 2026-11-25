import datetime
from sqlalchemy.orm import Session
from backend.models import User, PatientProfile, SymptomSession, MedicalReport, AssessmentRecord, AllergyDiet, DoctorNote
from backend.auth import get_password_hash
from backend.fhir_service import fhir_service

def seed_database(db: Session):
    """Populates the database with realistic synthetic patients, doctor, and clinical data."""
    # Check if already seeded
    existing_doctor = db.query(User).filter(User.email == "doctor@smarthealth.ai").first()
    if existing_doctor:
        return

    print("Seeding synthetic healthcare demo data...")

    # 1. Doctor Account
    doctor = User(
        email="doctor@smarthealth.ai",
        password_hash=get_password_hash("Doctor@123"),
        full_name="Dr. Sarah Chen, MD",
        role="doctor",
        phone="+1-555-0199"
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    # 2. Patient 1: John Doe
    patient1 = User(
        email="patient@smarthealth.ai",
        password_hash=get_password_hash("Patient@123"),
        full_name="John Doe",
        role="patient",
        phone="+1-555-0142"
    )
    db.add(patient1)
    db.commit()
    db.refresh(patient1)

    profile1 = PatientProfile(
        user_id=patient1.id,
        date_of_birth="1984-06-15",
        gender="Male",
        blood_group="O+",
        height_cm=178.0,
        weight_kg=76.5,
        allergies_summary="Penicillin (Urticaria/Rash), Peanuts",
        chronic_conditions="Mild seasonal asthma",
        current_medications="Albuterol inhaler PRN for wheezing",
        emergency_contact="Jane Doe (Spouse) +1-555-0143",
        ai_consent_given=True,
        ai_consent_at=datetime.datetime.utcnow()
    )
    db.add(profile1)

    # 3. Patient 2: Priya Sharma
    patient2 = User(
        email="patient2@smarthealth.ai",
        password_hash=get_password_hash("Patient@123"),
        full_name="Priya Sharma",
        role="patient",
        phone="+91-98765-43210"
    )
    db.add(patient2)
    db.commit()
    db.refresh(patient2)

    profile2 = PatientProfile(
        user_id=patient2.id,
        date_of_birth="1991-03-22",
        gender="Female",
        blood_group="B+",
        height_cm=164.0,
        weight_kg=58.0,
        allergies_summary="Shellfish, Sulfonamides",
        chronic_conditions="None",
        current_medications="None",
        emergency_contact="Raj Sharma (Brother) +91-98765-43211",
        ai_consent_given=True,
        ai_consent_at=datetime.datetime.utcnow()
    )
    db.add(profile2)
    db.commit()

    # 4. Allergies & Diet Records for Patient 1
    allergy1 = AllergyDiet(
        patient_id=patient1.id,
        allergen="Peanuts",
        reaction="Lip swelling, hives, difficulty breathing",
        severity="severe",
        foods_to_avoid=["Peanut butter", "Mixed nuts", "Satay sauce", "Groundnut oil"],
        recommended_foods=["Sunflower seed butter", "Pumpkin seeds", "Oat milk"],
        doctor_approved=True,
        approved_by_id=doctor.id,
        doctor_notes="Confirmed IgE-mediated peanut allergy. Patient carries prescribed EpiPen auto-injector."
    )
    db.add(allergy1)

    allergy2 = AllergyDiet(
        patient_id=patient1.id,
        allergen="Penicillin",
        reaction="Maculopapular cutaneous rash",
        severity="moderate",
        foods_to_avoid=["None dietary"],
        recommended_foods=["Standard balanced diet"],
        doctor_approved=True,
        approved_by_id=doctor.id,
        doctor_notes="Avoid all beta-lactam antibiotic formulations. Document in EHR chart."
    )
    db.add(allergy2)

    # 5. Symptom Session & Assessment for Patient 1
    session1 = SymptomSession(
        patient_id=patient1.id,
        status="completed",
        current_step=3,
        chief_complaint="Dry cough and mild evening fever for 3 days",
        conversation_history=[
            {"role": "user", "content": "Dry cough and mild evening fever for 3 days"},
            {"role": "assistant", "content": "How long have you had this cough, and does it produce any phlegm?"},
            {"role": "user", "content": "Started 3 days ago, dry cough with no phlegm, slight throat irritation"},
            {"role": "assistant", "content": "On a scale of 1 to 10, how severe is it, and are you having any shortness of breath?"},
            {"role": "user", "content": "Mild to moderate, about 4/10. No shortness of breath, just tired."}
        ],
        extracted_entities={
            "active_symptoms": ["cough", "fever", "throat irritation", "fatigue"],
            "negated_symptoms": ["shortness of breath", "phlegm"],
            "historical_conditions": ["asthma"]
        },
        possible_conditions=[
            {
                "condition": "Acute Viral Upper Respiratory Infection",
                "likelihood": "High",
                "rationale": "Dry cough, mild fever, throat tickle, and absence of purulent sputum or dyspnea.",
                "clinical_explanation": "Self-limiting viral irritation of pharyngeal and tracheobronchial mucosa."
            },
            {
                "condition": "Cough Variant Asthma exacerbation",
                "likelihood": "Moderate",
                "rationale": "Patient has background of mild asthma triggered by viral prodrome.",
                "clinical_explanation": "Airway hyperreactivity provoked by upper airway viral infection."
            }
        ],
        precautions=[
            "Warm fluids and honey-lemon steam inhalation twice daily.",
            "Rest and avoid cold drafts or irritant smoke.",
            "Monitor body temperature twice daily."
        ],
        test_guidance=[
            {"test_name": "Peak Expiratory Flow (PEF)", "purpose": "Checks baseline airway mechanics given asthma history", "when_considered": "Routine home monitoring"},
            {"test_name": "Complete Blood Count (CBC)", "purpose": "Checks white cell count if fever persists past 5 days", "when_considered": "Persistent fever"}
        ],
        emergency_flag=False,
        triage_level="ROUTINE"
    )
    db.add(session1)
    db.commit()
    db.refresh(session1)

    # Assessment Record
    assessment1 = AssessmentRecord(
        patient_id=patient1.id,
        session_id=session1.id,
        title="Assessment: Dry cough and mild evening fever",
        chief_complaint="Dry cough and mild evening fever for 3 days",
        symptoms_summary="3-day history of dry cough and mild fever. No dyspnea reported.",
        extracted_entities=session1.extracted_entities,
        possible_conditions=session1.possible_conditions,
        precautions=session1.precautions,
        test_guidance=session1.test_guidance,
        diet_guidance={
            "avoid": ["Cold beverages", "Greasy fried food"],
            "recommended": ["Warm chicken/veg soup", "Ginger-honey tea"],
            "hydration": "2.5 liters warm water daily"
        },
        medication_info=[
            {
                "drug_class": "Analgesics & Antipyretics",
                "common_examples": ["Paracetamol"],
                "clinical_purpose": "Relief of body ache and fever reduction",
                "precautions": "Take only as directed. Do not exceed 4g/day. Never prescribe without physician.",
                "side_effects": "Rare at standard doses."
            }
        ],
        consultation_summary={
            "subjective": "Patient reports 3-day history of dry cough, low-grade fever, no sputum or dyspnea.",
            "objective": "Asthma history noted. Lungs clear to conversational review. Vitals pending clinic visit.",
            "assessment": "Viral upper respiratory tract infection vs cough-variant asthma trigger.",
            "plan": "Hydration, honey-lemon soothe, maintain peak flow monitoring. Follow up if fever >101F."
        },
        sources=[
            {
                "title": "WHO Guidelines on Acute Respiratory Infections & Influenza",
                "organization": "WHO",
                "url": "https://www.who.int/health-topics/influenza-seasonal",
                "key_takeaway": "Emphasizes hydration, antipyretics for fever, and rest."
            },
            {
                "title": "NHS Overview: Coughs, Colds and Chest Infections",
                "organization": "NHS",
                "url": "https://www.nhs.uk/conditions/cough/",
                "key_takeaway": "Most coughs resolve in 3-4 weeks. Antibiotics not indicated for viral illness."
            }
        ],
        triage_level="ROUTINE",
        emergency_warning=False,
        doctor_review_status="reviewed",
        doctor_notes="Reviewed conversational history and assessment. Continue supportive care. If wheezing occurs, use Albuterol inhaler 2 puffs and contact office.",
        reviewed_by_id=doctor.id,
        reviewed_at=datetime.datetime.utcnow()
    )
    db.add(assessment1)

    # 6. Synthetic Medical Report for Patient 1
    sample_findings = [
        {"finding": "Hemoglobin", "patient_value": "14.2 g/dL", "normal_range": "13.5 - 17.5 g/dL", "status": "Normal", "explanation": "Healthy red blood cell oxygen carrying capacity."},
        {"finding": "WBC Count", "patient_value": "6,800 /mcL", "normal_range": "4,500 - 11,000 /mcL", "status": "Normal", "explanation": "Normal immune leukocyte count."},
        {"finding": "Platelet Count", "patient_value": "240,000 /mcL", "normal_range": "150,000 - 450,000 /mcL", "status": "Normal", "explanation": "Adequate blood clotting platelets."},
        {"finding": "Fasting Blood Sugar", "patient_value": "92 mg/dL", "normal_range": "70 - 100 mg/dL", "status": "Normal", "explanation": "Normal metabolic glucose regulation."}
    ]
    diag_res = fhir_service.create_diagnostic_report_resource(
        patient_id=patient1.id,
        title="Annual Wellness CBC & Metabolic Screen",
        conclusion="Hematological and basic metabolic indices within standard biological reference ranges.",
        findings=sample_findings
    )
    report1 = MedicalReport(
        patient_id=patient1.id,
        file_name="Annual_CBC_Metabolic_Report.pdf",
        file_path="uploads/synthetic_annual_cbc.pdf",
        file_type="pdf",
        file_size_bytes=142800,
        extracted_text="Complete Blood Count (CBC) with Differential:\nHemoglobin: 14.2 g/dL (Ref: 13.5 - 17.5)\nWBC: 6,800 /mcL (Ref: 4,500 - 11,000)\nPlatelets: 240,000 /mcL (Ref: 150,000 - 450,000)\nFasting Blood Glucose: 92 mg/dL (Ref: 70 - 100)\nImpression: Normal routine screening panel.",
        extracted_entities={
            "tests_mentioned": ["complete blood count", "cbc", "fasting blood glucose"],
            "active_symptoms": [],
            "treatments_mentioned": []
        },
        clinical_findings=sample_findings,
        key_observations="All CBC parameters and fasting glucose values are within normal limits.",
        fhir_bundle=diag_res
    )
    db.add(report1)

    # 7. Doctor Note for Patient 1
    note1 = DoctorNote(
        patient_id=patient1.id,
        doctor_id=doctor.id,
        title="Routine Follow-up & Asthma Action Plan",
        content="Patient seen for annual review. Asthma well controlled on PRN Albuterol. Re-emphasized strict avoidance of peanuts and penicillin. Annual bloodwork reviewed and normal.",
        note_type="clinical"
    )
    db.add(note1)

    db.commit()
    print("Database successfully seeded with demo doctor and patients!")
