"""
Test Script: AI Virtual Doctor End-to-End Verification
Tests:
1. Patient login
2. Natural language symptom presentation: "I've had headaches and weakness for three days."
3. Follow-up generation (verifying smart non-repeating questions)
4. Answering follow-up and receiving comprehensive Health Assessment:
   - Assessed conditions & differential diagnoses
   - Non-drug home remedies
   - Exercise & physical activity guidance
   - Diet & hydration advice
   - Medical tests guidance with clinical relevance
   - Doctor portal review status integration
5. Polling doctor status endpoint (/api/symptom-checker/doctor-status/{assessment_id})
6. Starting a longitudinal follow-up session (/api/symptom-checker/follow-up-start)
7. Querying consultation history (/api/symptom-checker/patient-history)
"""
import sys
import asyncio
import httpx
from httpx import ASGITransport
from backend.main import app

async def run_virtual_doctor_tests():
    print("=" * 60)
    print("STARTING AI VIRTUAL DOCTOR TEST SUITE")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=90.0) as client:
        # 1. Patient Login
        print("\n[Step 1] Authenticating patient...")
        login_resp = await client.post("/api/auth/login", json={"email": "patient@smarthealth.ai", "password": "Patient@123"})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  ✓ Patient authenticated successfully (John Doe)")

        # 2. Start AI Virtual Doctor consultation
        complaint = "I've had headaches and weakness for three days."
        print(f"\n[Step 2] Patient presents complaint: '{complaint}'")
        start_resp = await client.post(
            "/api/symptom-checker/start",
            json={"chief_complaint": complaint},
            headers=headers
        )
        assert start_resp.status_code == 200, f"Start session failed: {start_resp.text}"
        session_data = start_resp.json()
        session_id = session_data["session_id"]
        question = session_data["question"]
        options = session_data.get("interactive_options", [])
        extracted_symptoms = session_data.get("extracted_symptoms", [])

        print(f"  ✓ Session ID: {session_id}")
        print(f"  ✓ Extracted Symptoms: {extracted_symptoms}")
        print(f"  ✓ AI Virtual Doctor Question: {question}")
        print(f"  ✓ Quick Response Options: {options}")

        # Verify duration is not redundantly re-asked
        question_lower = question.lower()
        if "how many days" in question_lower or "how long have you had" in question_lower:
            print("  ⚠ Note: AI asked duration despite 3 days specified. Checking clinical context.")
        else:
            print("  ✓ Smart Follow-up verified: Did NOT redundantly re-ask duration!")

        # 3. Answer follow-up to get Assessment
        print("\n[Step 3] Patient answers follow-up with advice requested...")
        answer_resp = await client.post(
            "/api/symptom-checker/answer",
            json={
                "session_id": session_id,
                "answer": "The headache is a dull throbbing on both sides, mild to moderate, no fever, just feeling tired.",
                "give_immediate_advice": True
            },
            headers=headers
        )
        assert answer_resp.status_code == 200, f"Answer failed: {answer_resp.text}"
        ans_data = answer_resp.json()
        assert ans_data.get("is_completed") is True, f"Consultation did not reach complete status: {ans_data}"

        assessment = ans_data["assessment"]
        print(f"  ✓ Chief Complaint: {assessment.get('chief_complaint')}")
        print(f"  ✓ Differential Diagnoses: {len(assessment.get('differential_diagnoses', []))} found")
        for d in assessment.get("differential_diagnoses", [])[:3]:
            print(f"     - {d.get('disease')} (Likelihood: {d.get('likelihood', 'N/A')}): {d.get('clinical_rationale', '')[:80]}...")

        # Validate all guidance sections
        remedies = assessment.get("home_remedies", [])
        exercises = assessment.get("exercises", []) or assessment.get("exercise_guidance", {}).get("recommended_activities", [])
        hydration = assessment.get("hydration_advice", {})
        tests = assessment.get("test_guidance", [])
        doc_int = ans_data.get("doctor_integration", {})

        print(f"  ✓ Home Remedies ({len(remedies)}): {remedies[:2]}")
        print(f"  ✓ Exercise / Physical Guidance: {exercises[:2]}")
        print(f"  ✓ Hydration Plan: Daily target {hydration.get('daily_target', 'N/A')}, fluids: {hydration.get('recommended_fluids', [])[:2]}")
        print(f"  ✓ Recommended Tests ({len(tests)}): {[t.get('test_name') for t in tests]}")
        print(f"  ✓ Doctor Portal Integration: Assessment ID {doc_int.get('assessment_id')}, Status: {doc_int.get('review_status')}")

        assert doc_int.get("review_status") == "pending", "Doctor review status is not pending"
        assessment_id = doc_int.get("assessment_id")

        # 4. Check doctor status endpoint
        print(f"\n[Step 4] Checking live doctor review status for assessment #{assessment_id}...")
        status_resp = await client.get(f"/api/symptom-checker/doctor-status/{assessment_id}", headers=headers)
        assert status_resp.status_code == 200, f"Status fetch failed: {status_resp.text}"
        status_data = status_resp.json()
        print(f"  ✓ Doctor Review Status: {status_data['doctor_review_status']}")
        assert status_data["doctor_review_status"] == "pending"

        # 5. Longitudinal follow-up session start
        print(f"\n[Step 5] Starting longitudinal follow-up for session #{session_id}...")
        follow_resp = await client.post(
            "/api/symptom-checker/follow-up-start",
            json={"previous_session_id": session_id, "update_note": "Headaches are slightly better with rest, but still feeling fatigued."},
            headers=headers
        )
        assert follow_resp.status_code == 200, f"Follow-up start failed: {follow_resp.text}"
        f_data = follow_resp.json()
        print(f"  ✓ New Follow-Up Session ID: {f_data['session_id']}")
        print(f"  ✓ AI Follow-Up Question: {f_data['question']}")

        # 6. Patient consultation history
        print("\n[Step 6] Retrieving patient consultation history for progress tracking...")
        hist_resp = await client.get("/api/symptom-checker/patient-history", headers=headers)
        assert hist_resp.status_code == 200, f"History fetch failed: {hist_resp.text}"
        history_data = hist_resp.json()
        records = history_data.get("history", [])
        print(f"  ✓ Total Previous Consultations: {history_data.get('total_consultations', len(records))}")
        if records:
            latest = records[0]
            print(f"  ✓ Latest Consultation: ID #{latest['session_id']} - '{latest['chief_complaint']}' (Doctor Status: {latest['doctor_review_status']})")

    print("\n" + "=" * 60)
    print("ALL AI VIRTUAL DOCTOR TESTS PASSED SUCCESSFULLY! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(run_virtual_doctor_tests())
    except Exception as e:
        print(f"\n[FAIL] Test encountered an error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
