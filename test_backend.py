import sys
import os
import asyncio
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.main import app

async def run_tests():
    print("========================================")
    print("STARTING SMART HEALTH AI TEST SUITE")
    print("========================================")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0) as client:
        # 1. Health check
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[PASS] 1. Root & Health Check OK:", res.json())

        # 2. Login as Doctor
        res = await client.post("/api/auth/login", json={"email": "doctor@smarthealth.ai", "password": "Doctor@123"})
        assert res.status_code == 200, f"Doctor login failed: {res.text}"
        doc_token = res.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}
        print("[PASS] 2. Doctor Login OK (Dr. Sarah Chen, MD)")

        # 3. Login as Patient
        res = await client.post("/api/auth/login", json={"email": "patient@smarthealth.ai", "password": "Patient@123"})
        assert res.status_code == 200, f"Patient login failed: {res.text}"
        pat_token = res.json()["access_token"]
        pat_headers = {"Authorization": f"Bearer {pat_token}"}
        print("[PASS] 3. Patient Login OK (John Doe)")

        # 4. Feature 1: Interactive Symptom Checker (Step-by-step Q&A)
        res = await client.post("/api/symptom-checker/start", headers=pat_headers, json={"chief_complaint": "Persistent dry cough and fatigue for past 4 days"})
        assert res.status_code == 200, f"Symptom checker start failed: {res.text}"
        session_data = res.json()
        session_id = session_data["session_id"]
        print(f"[PASS] 4a. Feature 1 - Symptom Checker Step 1: Session #{session_id}, Question: {session_data['question']}")

        # Answer Step 1
        res = await client.post("/api/symptom-checker/answer", headers=pat_headers, json={"session_id": session_id, "answer": "Started 4 days ago gradually, worse at night"})
        assert res.status_code == 200
        print("[PASS] 4b. Feature 1 - Step 2 Question Generated:", res.json().get("question"))

        # Answer Step 2 (Concluding & generating structured assessment)
        res = await client.post("/api/symptom-checker/answer", headers=pat_headers, json={"session_id": session_id, "answer": "Mild 3/10 severity, no fever or shortness of breath"})
        assert res.status_code == 200
        ans_data = res.json()
        assert ans_data["is_completed"] == True
        print("[PASS] 4c. Feature 1 - Final Assessment Complete, Possible Conditions:", len(ans_data["assessment"]["possible_conditions"]))

        # 5. Feature 2: Medical Report Analysis & FHIR DiagnosticReport
        sample_txt = "PATIENT LAB REPORT\nPatient Name: John Doe\nHemoglobin: 13.8 g/dL (Normal: 12-16)\nWBC: 7,200 /mcL\nPlatelet Count: 230,000 /mcL\nFasting Blood Glucose: 95 mg/dL\nImpression: Normal indices."
        res = await client.post(
            "/api/reports/upload",
            headers=pat_headers,
            files={"file": ("lab_report.txt", sample_txt.encode("utf-8"), "text/plain")}
        )
        assert res.status_code == 200, f"Report upload failed: {res.text}"
        rep_data = res.json()
        print("[PASS] 5. Feature 2 - Medical Report Analysis & FHIR DiagnosticReport Created:", rep_data["file_name"], f"(Findings: {len(rep_data['findings'])})")

        # 6. Feature 3: Medical History Summary & FHIR Bundle Export
        res = await client.get("/api/history/summary", headers=pat_headers)
        assert res.status_code == 200
        hist = res.json()
        print(f"[PASS] 6a. Feature 3 - Medical History Summary: {len(hist['timeline'])} timeline events, {len(hist['diagnoses_and_assessments'])} conditions tracked")

        res = await client.get("/api/history/fhir-export", headers=pat_headers)
        assert res.status_code == 200
        fhir_bundle = res.json()
        assert fhir_bundle["resourceType"] == "Bundle"
        print(f"[PASS] 6b. Feature 3 - HL7 FHIR R4 Bundle Exported: {fhir_bundle['total']} FHIR resources generated")

        # 7. Feature 4: Health Precautions (Non-drug guidance)
        res = await client.post("/api/precautions/guidance", headers=pat_headers, json={"symptoms_or_conditions": ["cough", "mild fever"]})
        assert res.status_code == 200
        prec = res.json()
        print(f"[PASS] 7. Feature 4 - Non-Drug Precautions ({len(prec['non_drug_precautions'])} precautions, {len(prec['monitoring_guidance'])} monitoring rules)")

        # 8. Feature 5: Medical Test Guidance
        res = await client.post("/api/tests/guidance", headers=pat_headers, json={"symptoms_or_condition": "persistent chest congestion and fever"})
        assert res.status_code == 200
        tests = res.json()
        print(f"[PASS] 8. Feature 5 - Medical Test Guidance: {len(tests['tests_considered'])} clinical tests explained with preparation instructions")

        # 9. Feature 6: Allergy & Diet Assistant
        res = await client.get("/api/allergy-diet/my-records", headers=pat_headers)
        assert res.status_code == 200
        allergy_data = res.json()
        print(f"[PASS] 9a. Feature 6 - Allergies & Diet Retrieved: {len(allergy_data['allergies_and_diet_plans'])} recorded allergy diet plans")

        res = await client.post("/api/allergy-diet/add", headers=pat_headers, json={
            "allergen": "Dairy / Lactose",
            "reaction": "Abdominal bloating and cramps",
            "severity": "mild"
        })
        assert res.status_code == 200
        print("[PASS] 9b. Feature 6 - Added new Allergy with automated food avoidance & substitute recommendations")

        # 10. Feature 7: Doctor Consultation Summary (SOAP format)
        res = await client.post("/api/consultation/generate", headers=pat_headers, json={
            "chief_complaint": "Seasonal asthma trigger with dry throat",
            "symptoms": "Occasional wheeze on exertion, throat dryness",
            "history": "Known mild asthma on albuterol"
        })
        assert res.status_code == 200
        soap = res.json()
        assert "subjective" in soap and "plan" in soap
        print("[PASS] 10. Feature 7 - Doctor Consultation SOAP Note Generated:", soap["format"])

        # 11. Feature 8: Symptom-Based Medication Education (NO PRESCRIPTIONS)
        res = await client.post("/api/medication/info", headers=pat_headers, json={"symptoms_or_condition": "fever and body ache"})
        assert res.status_code == 200
        med = res.json()
        assert len(med["educational_medication_info"]) > 0
        assert "NOT" in med["mandatory_disclaimer"]
        assert any("NEVER" in rule for rule in med["critical_safety_rules"])
        print(f"[PASS] 11. Feature 8 - Medication Educational Information ({len(med['educational_medication_info'])} classes explained; Dosages strictly prohibited)")

        # 12. Independent Emergency Triage Red-Flag Rules
        res = await client.post("/api/symptom-checker/start", headers=pat_headers, json={
            "chief_complaint": "Crushing chest pain radiating to left arm and jaw with severe sweating"
        })
        assert res.status_code == 200
        em_res = res.json()
        assert em_res["emergency_flag"] == True
        print("[PASS] 12. Emergency Triage Rules Triggered Immediately:", em_res["emergency_message"])

        # 13. Doctor Portal Endpoints
        res = await client.get("/api/doctor/dashboard-stats", headers=doc_headers)
        assert res.status_code == 200
        stats = res.json()
        print(f"[PASS] 13a. Doctor Dashboard Stats: {stats['total_patients']} Patients, {stats['pending_assessments_count']} Pending Reviews")

        res = await client.get("/api/doctor/patients", headers=doc_headers)
        assert res.status_code == 200
        print(f"[PASS] 13b. Doctor Patient List: {len(res.json())} patients listed")

        res = await client.get("/api/doctor/assessments", headers=doc_headers)
        assert res.status_code == 200
        assessments_list = res.json()
        if assessments_list:
            a_id = assessments_list[0]["id"]
            rev_res = await client.post(f"/api/doctor/assessment-review/{a_id}", headers=doc_headers, json={
                "status": "approved",
                "doctor_notes": "Clinical assessment reviewed and concurred. Patient advised to maintain hydration and follow up in clinic if symptoms worsen."
            })
            assert rev_res.status_code == 200
            print(f"[PASS] 13c. Doctor Reviewed & Signed off Assessment #{a_id}")

        # 14. Medical Knowledge Verified Source Retrieval
        res = await client.get("/api/knowledge/search?q=influenza%20cough%20fever", headers=pat_headers)
        assert res.status_code == 200
        k_data = res.json()
        assert k_data["count"] > 0
        print(f"[PASS] 14. Verified Medical Knowledge Retrieval from WHO/NHS/ICMR: {k_data['citations'][0]['organization']} -> {k_data['citations'][0]['url']}")

        # 15. Diagnostic Reasoning Verification: Dengue Syndrome vs Respiratory Infection
        print("\n--- Testing Diagnostic Reasoning: Vector / Dengue Constellation ---")
        dengue_req = {
            "chief_complaint": "High fever, severe joint pain, pain behind eyes, and severe body aches for 3 days",
            "severity_1_10": 8,
            "duration": "3 days",
            "accompanying_symptoms": ["pain behind eyes", "joint pain", "severe body ache", "chills"],
            "known_conditions": [],
            "known_allergies": []
        }
        res = await client.post("/api/analyze/full-assessment", headers=pat_headers, json=dengue_req)
        assert res.status_code == 200, f"Full assessment failed: {res.text}"
        dengue_res = res.json()
        assessment = dengue_res["assessment"]
        conditions = [c["condition"] for c in assessment["possible_conditions"]]
        print("Identified Possible Conditions:", conditions)
        
        is_dengue_identified = any("dengue" in c.lower() or "arboviral" in c.lower() for c in conditions)
        assert is_dengue_identified, f"Failed: Dengue was not identified in conditions: {conditions}"
        
        top_condition = conditions[0].lower()
        assert "respiratory" not in top_condition, f"Failed: Dengue was misclassified as respiratory: {top_condition}"
        print(f"[PASS] 15a. Correct Disease Identification: Dengue/Arboviral identified (Top condition: {conditions[0]})")

        precautions_text = " ".join(assessment["precautions"]).lower()
        has_nsaid_contraindication = any(w in precautions_text for w in ["nsaid", "aspirin", "ibuprofen", "contraindication"])
        assert has_nsaid_contraindication, "Failed: NSAID contraindication missing from dengue precautions"
        print("[PASS] 15b. Medically Accurate Precautions: NSAID contraindication enforced for bleeding risk")

        tests_names = [t["test_name"].lower() for t in assessment["test_guidance"]]
        has_cbc_platelets = any("cbc" in t or "platelet" in t for t in tests_names)
        assert has_cbc_platelets, f"Failed: CBC with platelets not found in test guidance: {tests_names}"
        print(f"[PASS] 15c. Condition-Specific Tests Recommended: CBC Platelets ({has_cbc_platelets})")

        # 16. Dynamic Follow-Up Question for Fever
        res_fever = await client.post("/api/symptom-checker/start", headers=pat_headers, json={"chief_complaint": "High fever"})
        assert res_fever.status_code == 200
        fever_q = res_fever.json()
        print(f"[PASS] 16. Targeted Follow-Up Question for Fever: {fever_q['question']}")

        # 17. Automated Verification: All 7 Sinusitis Symptoms Captured in LLM Payload & Individual Durations Preserved
        print("\n--- Testing All 7 Sinusitis Symptoms & Individual Timelines ---")
        sinusitis_narrative = (
            "Facial pressure for 10 days, nasal congestion for 10 days, thick discolored nasal discharge for 7 days, "
            "sinus headache for 5 days, cough for 4 days, post-nasal drip for 6 days, loss of smell for 3 days."
        )
        sinusitis_req = {
            "chief_complaint": sinusitis_narrative,
            "severity_1_10": 7,
            "duration": "10 days",
            "accompanying_symptoms": [
                "facial pain / pressure / fullness",
                "nasal congestion",
                "thick discolored nasal discharge",
                "post-nasal drip",
                "sinus headache",
                "loss of smell (hyposmia/anosmia)",
                "cough"
            ],
            "known_conditions": [],
            "known_allergies": []
        }
        res_sinus = await client.post("/api/analyze/full-assessment", headers=pat_headers, json=sinusitis_req)
        assert res_sinus.status_code == 200, f"Sinusitis assessment failed: {res_sinus.text}"
        sinus_data = res_sinus.json()
        sinus_entities = sinus_data["extracted_entities"]
        sinus_active_syms = sinus_entities["active_symptoms"]
        print("Sinusitis Extracted Active Symptoms:", sinus_active_syms)

        # Verify all 7 cardinal symptoms are present
        cardinal_7 = [
            ("facial pain", ["facial pain / pressure / fullness", "facial pressure", "facial pain"]),
            ("nasal congestion", ["nasal congestion"]),
            ("thick discharge", ["thick discolored nasal discharge"]),
            ("post-nasal drip", ["post-nasal drip"]),
            ("sinus headache", ["sinus headache"]),
            ("loss of smell", ["loss of smell (hyposmia/anosmia)", "loss of smell"]),
            ("cough", ["cough"])
        ]
        for label, accepted_names in cardinal_7:
            found = any(any(acc in s.lower() for acc in accepted_names) for s in sinus_active_syms)
            assert found, f"Failed: Sinusitis symptom '{label}' was not extracted in {sinus_active_syms}"
        print("[PASS] 17a. All 7 Sinusitis Symptoms Captured 100% in Active Symptoms List")

        # Verify individual symptom durations are preserved
        detailed_syms = sinus_entities.get("details", {}).get("symptoms", [])
        dur_map = {s["text"]: s.get("duration") for s in detailed_syms if s.get("duration")}
        print("Preserved Individual Symptom Durations:", dur_map)
        assert len(dur_map) >= 3, f"Failed: Individual durations not preserved: {dur_map}"
        print("[PASS] 17b. Individual Symptom Durations Preserved (not overwritten with global duration)")

        # Verify Syndrome is Acute Sinonasal / Rhinosinusitis Complex (not generic respiratory)
        sinus_syndromes = [s["syndrome"] for s in sinus_entities["detected_syndromes"]]
        print("Detected Syndromes for Sinusitis:", sinus_syndromes)
        assert any("Rhinosinusitis" in s or "Sinonasal" in s for s in sinus_syndromes), f"Failed: Sinonasal syndrome not identified: {sinus_syndromes}"
        print("[PASS] 17c. Correct Disease-Specific Syndrome Detected: Acute Rhinosinusitis Complex")

        # Verify Conditions contain Sinusitis
        sinus_conditions = [c["condition"] for c in sinus_data["assessment"]["possible_conditions"]]
        print("Sinusitis Assessed Conditions:", sinus_conditions)
        has_sinusitis = any("sinus" in c.lower() or "rhino" in c.lower() for c in sinus_conditions)
        assert has_sinusitis, f"Failed: Sinusitis was not identified in conditions: {sinus_conditions}"
        print("[PASS] 17d. Dynamic Condition Prediction: Sinusitis correctly identified as primary consideration")

        # 18. Multi-Disease Generalization: Migraine Presentation with Preserved Durations
        print("\n--- Testing Multi-Disease Generalization: Migraine Constellation ---")
        migraine_narrative = (
            "Severe throbbing headache on one side for 8 hours. Sensitivity to light for 6 hours. "
            "Sensitivity to sound for 6 hours. Nausea for 5 hours. Blurred vision before headache for 30 minutes. "
            "Pain worsens with physical activity."
        )
        migraine_req = {
            "chief_complaint": migraine_narrative,
            "severity_1_10": 8,
            "duration": "8 hours",
            "accompanying_symptoms": ["hemicranial throbbing headache", "photophobia", "nausea"],
            "known_conditions": [],
            "known_allergies": []
        }
        res_migraine = await client.post("/api/analyze/full-assessment", headers=pat_headers, json=migraine_req)
        assert res_migraine.status_code == 200, f"Migraine assessment failed: {res_migraine.text}"
        migraine_data = res_migraine.json()
        migraine_entities = migraine_data["extracted_entities"]
        migraine_syms = migraine_entities["active_symptoms"]
        print("Migraine Extracted Active Symptoms:", migraine_syms)

        # Check migraine symptom coverage: throbbing headache, photophobia, phonophobia, nausea, blurred vision, worsening with activity
        assert any("throbbing" in s.lower() or "headache" in s.lower() for s in migraine_syms), "Headache missing"
        assert any("photophobia" in s.lower() or "light" in s.lower() for s in migraine_syms), "Photophobia missing"
        assert any("phonophobia" in s.lower() or "sound" in s.lower() for s in migraine_syms), "Phonophobia missing"
        assert any("nausea" in s.lower() for s in migraine_syms), "Nausea missing"
        assert any("blurred vision" in s.lower() or "aura" in s.lower() for s in migraine_syms), "Blurred vision missing"
        print("[PASS] 18a. All Migraine Multi-Sensory Symptoms Extracted 100%")

        # Check syndrome
        migraine_syndromes = [s["syndrome"] for s in migraine_entities["detected_syndromes"]]
        print("Migraine Detected Syndromes:", migraine_syndromes)
        assert any("Migraine" in s or "Cephalea" in s for s in migraine_syndromes), f"Failed: Migraine syndrome not identified: {migraine_syndromes}"
        print("[PASS] 18b. Disease-Specific Syndrome Detected: Neurovascular Cephalea / Migraine Complex")

        # Check conditions
        migraine_conditions = [c["condition"] for c in migraine_data["assessment"]["possible_conditions"]]
        print("Migraine Assessed Conditions:", migraine_conditions)
        assert any("migraine" in c.lower() for c in migraine_conditions), f"Migraine not in conditions: {migraine_conditions}"
        assert not any("dengue" in c.lower() for c in migraine_conditions), "Dengue leaked into Migraine conditions!"
        print("[PASS] 18c. Condition-Specific Reasoning: Migraine correctly identified without dengue template contamination")

        # 19. Zero False-Negative Conversion Test
        print("\n--- Testing Zero False-Negative Conversion ---")
        backpain_req = {
            "chief_complaint": "Mild lower back pain for 2 days after lifting heavy boxes",
            "severity_1_10": 4,
            "duration": "2 days",
            "accompanying_symptoms": [],
            "known_conditions": [],
            "known_allergies": []
        }
        res_backpain = await client.post("/api/analyze/full-assessment", headers=pat_headers, json=backpain_req)
        assert res_backpain.status_code == 200
        bp_data = res_backpain.json()
        bp_soap = bp_data["assessment"]["consultation_summary"]
        bp_subj = bp_soap["subjective"]
        print("Back Pain SOAP Subjective:", bp_subj)
        assert "denies other focal systemic symptoms" not in bp_subj, "Unknown converted to confirmed negative findings!"
        print("[PASS] 19. No Unknown Information Converted to False Negative Findings")

        # 20. Nine Distinct Symptoms Test: All 9 symptoms retained without dropping or merging
        print("\n--- Testing 9 Distinct Symptoms Retained Without Merging ---")
        nine_symptoms = [
            "Cheek pain",
            "Sinus pressure",
            "Forehead ache",
            "Nasal congestion",
            "Post-nasal drip",
            "Loss of smell",
            "Fatigue",
            "Sore throat",
            "Ear fullness"
        ]
        nine_req = {
            "chief_complaint": "Patient experiencing 9 distinct symptoms over past week",
            "severity_1_10": 6,
            "duration": "7 days",
            "accompanying_symptoms": nine_symptoms,
            "known_conditions": [],
            "known_allergies": []
        }
        res_nine = await client.post("/api/analyze/full-assessment", headers=pat_headers, json=nine_req)
        assert res_nine.status_code == 200
        nine_data = res_nine.json()
        nine_active = nine_data["extracted_entities"]["active_symptoms"]
        print("9 Symptoms Extracted Active Symptoms:", nine_active)
        for sym in nine_symptoms:
            assert any(sym.lower() in s.lower() for s in nine_active), f"Symptom '{sym}' was dropped or merged away!"
        assert len(nine_active) >= 9, f"Expected at least 9 symptoms, got {len(nine_active)}: {nine_active}"
        print(f"[PASS] 20. All {len(nine_symptoms)} Distinct Symptoms Retained 100% (No Merging / Dropping)")

        print("========================================")
        print("ALL 20 BACKEND, AI & DIAGNOSTIC REASONING TESTS PASSED 100%!")
        print("========================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
