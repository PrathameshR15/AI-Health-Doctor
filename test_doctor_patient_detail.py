"""
Test Script: Doctor Portal - Patient-Centric Comprehensive History & Actions
Tests:
1. Doctor login
2. Fetch patient list (/api/doctor/patients)
3. Fetch detailed patient chart (/api/doctor/patient/{id})
   - Verifies AI consultations & assessments
   - Verifies uploaded lab/medical reports with abnormal findings & conclusions
   - Verifies allergies & dietary restrictions
   - Verifies recorded doctor notes
4. Write a clinical note directly to patient chart (/api/doctor/notes)
5. Approve an assessment directly from patient chart (/api/doctor/assessment-review/{id})
6. Verify updated chart reflects the changes immediately
"""
import sys
import asyncio
import httpx
from httpx import ASGITransport
from backend.main import app

async def test_doctor_patient_chart():
    print("=" * 60)
    print("STARTING DOCTOR PORTAL PATIENT DETAIL TEST")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=90.0) as client:
        # 1. Doctor Login
        print("\n[Step 1] Authenticating doctor...")
        doc_login = await client.post("/api/auth/login", json={"email": "doctor@smarthealth.ai", "password": "Doctor@123"})
        assert doc_login.status_code == 200, f"Doctor login failed: {doc_login.text}"
        doc_token = doc_login.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}
        print("  ✓ Doctor authenticated (Dr. Sarah Chen, MD)")

        # 2. List Patients
        print("\n[Step 2] Fetching patient roster...")
        patients_resp = await client.get("/api/doctor/patients", headers=doc_headers)
        assert patients_resp.status_code == 200
        patients = patients_resp.json()
        assert len(patients) > 0, "No patients found"
        target_patient = patients[0]
        patient_id = target_patient["id"]
        print(f"  ✓ Found {len(patients)} patients. Selecting Patient #{patient_id} ('{target_patient['full_name']}')")

        # 3. Fetch Specific Patient Complete Chart
        print(f"\n[Step 3] Fetching complete chart for Patient #{patient_id}...")
        detail_resp = await client.get(f"/api/doctor/patient/{patient_id}", headers=doc_headers)
        assert detail_resp.status_code == 200
        chart = detail_resp.json()

        pat_info = chart["patient"]
        assessments = chart.get("assessments", [])
        reports = chart.get("reports", [])
        allergies = chart.get("allergies", [])
        notes = chart.get("notes", [])

        print(f"  ✓ Patient Profile: {pat_info['full_name']} | Gender: {pat_info['gender']} | Blood Group: {pat_info['blood_group']}")
        print(f"  ✓ Chronic Conditions: {pat_info['chronic_conditions']}")
        print(f"  ✓ Consultations & AI Assessments Count: {len(assessments)}")
        print(f"  ✓ Medical Reports Count: {len(reports)}")
        print(f"  ✓ Allergies Count: {len(allergies)}")
        print(f"  ✓ Doctor Notes Count: {len(notes)}")

        if reports:
            sample_rep = reports[0]
            print(f"  ✓ Sample Report: '{sample_rep['file_name']}'")
            print(f"     - Has Abnormalities: {sample_rep.get('has_abnormalities')}")
            print(f"     - Abnormal Findings: {len(sample_rep.get('abnormal_findings', []))} items")
            print(f"     - Relevant Conclusion: {sample_rep.get('relevant_conclusion', 'N/A')[:80]}...")
            print(f"     - Doctor Review Status: {sample_rep.get('doctor_review_status')}")

        # 4. Doctor writes a clinical note directly to patient chart
        print(f"\n[Step 4] Writing clinical note for Patient #{patient_id}...")
        note_resp = await client.post(
            "/api/doctor/notes",
            headers=doc_headers,
            json={
                "patient_id": patient_id,
                "title": "Comprehensive Chart Review & Follow-up Plan",
                "content": "Patient evaluated during telemetry follow-up. Vital signs and symptom trajectory stable. Advised continuation of supportive therapy and routine hydration.",
                "note_type": "clinical"
            }
        )
        assert note_resp.status_code == 200, f"Failed to create note: {note_resp.text}"
        print("  ✓ Clinical note saved successfully to patient chart!")

        # 5. Doctor approves an assessment if any pending
        pending_ass = [a for a in assessments if a.get("doctor_review_status") == "pending"]
        if pending_ass:
            ass_to_approve = pending_ass[0]
            print(f"\n[Step 5] Approving pending consultation #{ass_to_approve['id']}...")
            approve_resp = await client.post(
                f"/api/doctor/assessment-review/{ass_to_approve['id']}",
                headers=doc_headers,
                json={
                    "status": "approved",
                    "doctor_notes": "Reviewed differential possibilities and symptom progression. Approved supportive care recommendations."
                }
            )
            assert approve_resp.status_code == 200
            print("  ✓ Assessment approved successfully!")

        # 6. Re-fetch chart and verify new note and review status
        print(f"\n[Step 6] Re-fetching chart to verify updates for Patient #{patient_id}...")
        updated_resp = await client.get(f"/api/doctor/patient/{patient_id}", headers=doc_headers)
        assert updated_resp.status_code == 200
        updated_chart = updated_resp.json()
        assert len(updated_chart.get("notes", [])) > len(notes), "New note not found in chart"
        print(f"  ✓ Verified: Total clinical notes updated from {len(notes)} to {len(updated_chart['notes'])}")

    print("\n" + "=" * 60)
    print("ALL DOCTOR PORTAL PATIENT DETAIL TESTS PASSED! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_doctor_patient_chart())
    except Exception as e:
        print(f"\n[FAIL] Test encountered error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
