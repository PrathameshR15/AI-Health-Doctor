"""
Test Script: Medical Report Upload - Abnormal Extraction, Relevant Conclusion, and Doctor Portal Save
"""
import sys
import asyncio
import httpx
from httpx import ASGITransport
from backend.main import app

async def test_medical_report_system():
    print("=" * 60)
    print("STARTING MEDICAL REPORT EXAMINE & ANALYSIS TEST")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=90.0) as client:
        # 1. Login as Patient
        print("\n[Step 1] Authenticating patient...")
        pat_login = await client.post("/api/auth/login", json={"email": "patient@smarthealth.ai", "password": "Patient@123"})
        assert pat_login.status_code == 200, f"Patient login failed: {pat_login.text}"
        pat_token = pat_login.json()["access_token"]
        pat_headers = {"Authorization": f"Bearer {pat_token}"}
        print("  ✓ Patient authenticated (John Doe)")

        # 2. Upload an Abnormal Report (Low Platelets, High WBC, Low Hemoglobin)
        print("\n[Step 2] Patient uploads an abnormal lab report...")
        abnormal_report_text = """
        METROPOLITAN CLINICAL LABORATORY
        Patient Name: John Doe | Age: 35 | Gender: Male
        Complete Blood Count (CBC) with Differential:
        Hemoglobin: 9.2 g/dL (Reference: 12.0 - 16.0 g/dL)
        WBC Count: 16,500 /mcL (Reference: 4,000 - 11,000 /mcL)
        Platelet Count: 65,000 /mcL (Reference: 150,000 - 450,000 /mcL)
        Hematocrit (PCV): 48 % (Reference: 36 - 50 %)
        Serum Creatinine: 1.1 mg/dL (Reference: 0.6 - 1.2 mg/dL)
        Clinical Impression: Marked thrombocytopenia and leukocytosis noted.
        """
        upload_resp = await client.post(
            "/api/reports/upload",
            headers=pat_headers,
            files={"file": ("cbc_abnormal_report.txt", abnormal_report_text.encode("utf-8"), "text/plain")}
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        rep_data = upload_resp.json()

        print(f"  ✓ Report ID: {rep_data['report_id']}")
        print(f"  ✓ Assessment ID: {rep_data['assessment_id']}")
        print(f"  ✓ Has Abnormalities: {rep_data['has_abnormalities']}")
        print(f"  ✓ Abnormal Findings Count: {len(rep_data['abnormal_findings'])}")
        for abn in rep_data['abnormal_findings']:
            print(f"     - {abn['finding']}: {abn['patient_value']} ({abn['status']}) [Ref: {abn['normal_range']}]")

        print(f"  ✓ Short Analysis: {rep_data['short_analysis']}")
        print(f"  ✓ Relevant Conclusion: {rep_data['relevant_conclusion']}")
        print(f"  ✓ Doctor Integration Status: {rep_data['doctor_integration']['status']}")

        assert rep_data['has_abnormalities'] is True, "Failed to detect abnormalities"
        assert len(rep_data['abnormal_findings']) >= 2, "Expected multiple abnormal parameters (Platelets, WBC, Hb)"
        assert rep_data['doctor_review_status'] == "pending", "Doctor review status is not pending"
        assessment_id = rep_data['assessment_id']

        # 3. Doctor Login and Inspection
        print("\n[Step 3] Doctor logs into Doctor Portal to inspect saved report...")
        doc_login = await client.post("/api/auth/login", json={"email": "doctor@smarthealth.ai", "password": "Doctor@123"})
        assert doc_login.status_code == 200, f"Doctor login failed: {doc_login.text}"
        doc_token = doc_login.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}
        print("  ✓ Doctor authenticated (Dr. Sarah Chen, MD)")

        # Verify report appears in doctor's report detail
        doc_report_resp = await client.get(f"/api/reports/{rep_data['report_id']}", headers=doc_headers)
        assert doc_report_resp.status_code == 200
        doc_rep = doc_report_resp.json()
        print(f"  ✓ Doctor views report #{doc_rep['id']}: '{doc_rep['file_name']}'")
        print(f"  ✓ Doctor sees abnormal findings: {len(doc_rep['abnormal_findings'])} items")
        print(f"  ✓ Doctor sees relevant conclusion: '{doc_rep['relevant_conclusion']}'")

        # 4. Doctor Approves Report & Records Clinical Note
        print("\n[Step 4] Doctor reviews and approves report...")
        review_resp = await client.post(
            f"/api/doctor/assessment-review/{assessment_id}",
            headers=doc_headers,
            json={
                "status": "approved",
                "doctor_notes": "Reviewed CBC showing significant thrombocytopenia and leukocytosis. Advised daily platelet monitoring and peripheral blood smear."
            }
        )
        assert review_resp.status_code == 200, f"Doctor review failed: {review_resp.text}"
        print("  ✓ Doctor approved report and saved clinical notes successfully!")

        # 5. Verify Patient Sees Doctor Approval
        print("\n[Step 5] Checking patient report status after doctor review...")
        pat_report_resp = await client.get(f"/api/reports/{rep_data['report_id']}", headers=pat_headers)
        assert pat_report_resp.status_code == 200
        final_rep = pat_report_resp.json()
        print(f"  ✓ Patient sees Doctor Review Status: {final_rep['doctor_review_status']}")
        print(f"  ✓ Patient sees Doctor Notes: '{final_rep['doctor_notes']}'")
        print(f"  ✓ Reviewed by: '{final_rep['reviewed_by']}'")
        assert final_rep['doctor_review_status'] == "approved"

    print("\n" + "=" * 60)
    print("ALL MEDICAL REPORT EXAMINE & ANALYSIS TESTS PASSED! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_medical_report_system())
    except Exception as e:
        print(f"\n[FAIL] Test encountered error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
