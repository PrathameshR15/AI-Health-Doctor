import sys
from backend.database import SessionLocal
from backend.models import User, AssessmentRecord, MedicalReport, DoctorNote
from backend.routers.history_router import (
    summarize_assessment_2_words,
    summarize_report_conclusion_3_words,
    build_health_timeline
)
from backend.routers.doctor_router import get_patient_detail

def test_timeline_generation():
    db = SessionLocal()
    try:
        doctor = db.query(User).filter(User.role == "doctor").first()
        patient = db.query(User).filter(User.role == "patient").first()
        if not doctor or not patient:
            print("Skipping: Doctor or Patient not in database.")
            return

        print(f"Testing for Patient #{patient.id} ({patient.full_name}) and Doctor #{doctor.id} ({doctor.full_name})")

        # Test 2-word summary
        dummy_assessment = AssessmentRecord(
            title="Suspected Sinusitis and Nasal Congestion",
            chief_complaint="I have had headache and runny nose for 3 days",
            possible_conditions=[{"condition": "Acute Sinusitis", "probability": "High"}]
        )
        two_words = summarize_assessment_2_words(dummy_assessment)
        word_count = len(two_words.split())
        print(f"2-word summary test: '{two_words}' (word count: {word_count})")
        assert word_count == 2, f"Expected 2 words, got {word_count}"

        # Test 3-word summary
        dummy_report = MedicalReport(
            file_name="blood_cbc_report.pdf",
            file_path="uploads/blood_cbc_report.pdf",
            file_type="pdf",
            extracted_text="Hemoglobin low, WBC elevated, Platelet normal",
            key_observations="Abnormal: Low Platelet Count Detected"
        )
        three_words = summarize_report_conclusion_3_words(dummy_report)
        word_count_3 = len(three_words.split())
        print(f"3-word summary test: '{three_words}' (word count: {word_count_3})")
        assert word_count_3 == 3, f"Expected 3 words, got {word_count_3}"

        # Test doctor patient detail API includes timeline
        detail = get_patient_detail(patient.id, current_user=doctor, db=db)
        assert "timeline" in detail, "detail must contain timeline"
        print(f"Doctor Patient Detail returned timeline with {len(detail['timeline'])} events.")
        for ev in detail['timeline'][:4]:
            print(f" - [{ev['event_label']}] {ev['date_time']} | Highlight: '{ev['highlight']}'")

        print("All Timeline tests passed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    test_timeline_generation()
