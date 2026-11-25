import os
import io
import json
import uuid
import base64
import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional
from pypdf import PdfReader
from PIL import Image

from backend.database import get_db
from backend.config import settings
from backend.models import User, MedicalReport, AssessmentRecord
from backend.auth import get_current_user, require_patient
from backend.clinical_nlp import clinical_extractor
from backend.lab_report_parser import parse_lab_report_rows
from backend.openrouter_client import openrouter_client
from backend.fhir_service import fhir_service

router = APIRouter(prefix="/api/reports", tags=["Medical Report Analysis"])

@router.post("/upload")
async def upload_medical_report(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Feature 2: Upload PDF, image, or FHIR JSON medical report.
    Extracts text, structures clinical entities via MedSpaCy, runs LLM findings analysis,
    and constructs FHIR DiagnosticReport resource.
    """
    file_bytes = await file.read()
    file_size = len(file_bytes)
    filename = file.filename or "uploaded_report"
    ext = os.path.splitext(filename)[1].lower()

    # Determine file type
    if ext == ".pdf":
        file_type = "pdf"
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        file_type = "image"
    elif ext in [".json", ".fhir"]:
        file_type = "fhir_json"
    elif ext in [".txt"]:
        file_type = "text"
    else:
        file_type = "other"

    # NOTE: Zero-disk storage policy.
    # We do NOT save raw PDF/image files to disk to preserve disk space.
    # The file bytes are processed entirely in-memory and full structured clinical data is saved.
    file_path = "in-memory-data-only"

    # 1. Text Extraction (Processed directly in-memory from file_bytes)
    extracted_text = ""
    fhir_data = None
    image_data_url = None

    if file_type == "pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages:
                try:
                    page_txt = page.extract_text(extraction_mode="layout") or ""
                except Exception:
                    page_txt = page.extract_text() or ""
                if page_txt.strip():
                    pages_text.append(page_txt)
            extracted_text = "\n\n".join(pages_text).strip()

            # If PDF is scanned (no selectable text), extract embedded image for vision AI
            if len(extracted_text) < 25:
                for page in reader.pages[:2]:
                    try:
                        imgs = list(getattr(page, "images", []) or [])
                        if imgs:
                            img_bytes = imgs[0].data
                            img = Image.open(io.BytesIO(img_bytes))
                            mime_sub = (img.format or "png").lower()
                            b64_img = base64.b64encode(img_bytes).decode("ascii")
                            image_data_url = f"data:image/{mime_sub};base64,{b64_img}"
                            extracted_text = f"Scanned PDF Document: {filename} ({len(reader.pages)} page(s)). Image extracted for AI vision reading."
                            break
                    except Exception:
                        pass
        except Exception as e:
            extracted_text = f"Error reading PDF content: {e}"
    elif file_type == "image":
        try:
            img = Image.open(io.BytesIO(file_bytes))
            mime_sub = (img.format or "png").lower()
            b64_img = base64.b64encode(file_bytes).decode("ascii")
            image_data_url = f"data:image/{mime_sub};base64,{b64_img}"
            extracted_text = f"Diagnostic / Prescription Image: {filename} ({img.format}, {img.size[0]}x{img.size[1]}px). Uploaded for AI extraction and physician review."
        except Exception as e:
            extracted_text = f"Diagnostic Image file: {filename}."
    elif file_type == "fhir_json":
        try:
            json_obj = json.loads(file_bytes.decode("utf-8"))
            parsed_bundle = fhir_service.parse_fhir_bundle(json_obj)
            fhir_data = json_obj
            # Build textual representation
            lines = [f"Imported FHIR Bundle for: {parsed_bundle.get('patient_info', {}).get('full_name', 'Patient')}"]
            for cond in parsed_bundle.get("conditions", []):
                lines.append(f"Condition: {cond.get('name')} (Status: {cond.get('status')})")
            for obs in parsed_bundle.get("observations", []):
                lines.append(f"Observation: {obs.get('type')}: {obs.get('value')}")
            for allg in parsed_bundle.get("allergies", []):
                lines.append(f"Allergy: {allg.get('allergen')} - Reaction: {allg.get('reaction')} ({allg.get('severity')})")
            extracted_text = "\n".join(lines)
        except Exception as e:
            extracted_text = f"FHIR JSON parse error: {e}"
    else:
        try:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            extracted_text = f"Uploaded file: {filename}"

    if not extracted_text:
        extracted_text = f"Medical record uploaded: {filename}."

    # 2. Extract medical entities with MedSpaCy / ConText & structured multi-panel lab rows
    entities = clinical_extractor.extract_entities(extracted_text)
    parsed_report = parse_lab_report_rows(extracted_text)
    parsed_rows = parsed_report.get("rows", [])
    sections_detected = parsed_report.get("sections", [])

    # 3. Analyze report findings & prescription medications via OpenRouter / Clinical Knowledge Engine
    analysis = await openrouter_client.analyze_report_text(
        extracted_text,
        filename,
        parsed_rows=parsed_rows,
        image_data_url=image_data_url
    )
    findings = analysis.get("findings", [])
    abnormal_findings = analysis.get("abnormal_findings", [])
    has_abnormalities = analysis.get("has_abnormalities", len(abnormal_findings) > 0)
    is_prescription = analysis.get("is_prescription", False)
    medications = analysis.get("medications", [])
    short_analysis = analysis.get("short_analysis", "")
    relevant_conclusion = analysis.get("relevant_conclusion", "")
    explanation = analysis.get("explanation", f"{relevant_conclusion} {short_analysis}".strip())

    # 4. Generate FHIR DiagnosticReport resource
    diag_resource = fhir_service.create_diagnostic_report_resource(
        patient_id=current_user.id,
        title=f"{'Prescription' if is_prescription else 'Lab Report'}: {filename}",
        conclusion=relevant_conclusion or explanation,
        findings=findings
    )

    # 5. Persist MedicalReport
    report = MedicalReport(
        patient_id=current_user.id,
        file_name=filename,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size,
        extracted_text=extracted_text,
        extracted_entities={
            "entities": entities,
            "sections_detected": sections_detected,
            "parsed_parameters": parsed_rows,
            "is_prescription": is_prescription,
            "medications": medications,
            "abnormal_findings": abnormal_findings,
            "relevant_conclusion": relevant_conclusion,
            "short_analysis": short_analysis,
            "has_abnormalities": has_abnormalities
        },
        clinical_findings=findings,
        key_observations=f"{relevant_conclusion}\n\n{short_analysis}".strip(),
        fhir_bundle=diag_resource
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 6. Also create AssessmentRecord for doctor review visibility
    assessment = AssessmentRecord(
        patient_id=current_user.id,
        report_id=report.id,
        title=f"{'Prescription' if is_prescription else 'Lab Report'}: {filename}",
        chief_complaint=f"Medical Document: {filename}. {relevant_conclusion[:140]}",
        symptoms_summary=short_analysis,
        extracted_entities={
            "is_prescription": is_prescription,
            "medications": medications,
            "abnormal_findings": abnormal_findings,
            "relevant_conclusion": relevant_conclusion,
            "short_analysis": short_analysis,
            "total_parameters": len(findings)
        },
        medication_info=medications,
        possible_conditions=[
            {
                "condition": f"{f.get('finding')} ({f.get('status', 'Abnormal')})",
                "likelihood": f.get("status", "Moderate"),
                "clinical_explanation": f.get("explanation", "")
            }
            for f in abnormal_findings
        ] if abnormal_findings else [
            {
                "condition": "Within Normal Reference Limits",
                "likelihood": "Normal",
                "clinical_explanation": "All evaluated parameters are within standard physiological reference ranges."
            }
        ],
        test_guidance=[
            {
                "test_name": f.get("finding", "Parameter"),
                "purpose": f.get("explanation", ""),
                "when_considered": f"Status: {f.get('status', 'Evaluated')} (Patient value: {f.get('patient_value')} vs ref {f.get('normal_range')})"
            }
            for f in (abnormal_findings or findings[:3])
        ],
        triage_level="urgent" if has_abnormalities else "routine",
        emergency_warning=any(
            ("platelet" in f.get("finding", "").lower() and "low" in f.get("status", "").lower()) or
            ("creatinine" in f.get("finding", "").lower() and "high" in f.get("status", "").lower())
            for f in abnormal_findings
        ),
        doctor_review_status="pending"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {
        "status": "success",
        "report_id": report.id,
        "assessment_id": assessment.id,
        "file_name": filename,
        "file_type": file_type,
        "extracted_text_preview": extracted_text[:300] + ("..." if len(extracted_text) > 300 else ""),
        "short_analysis": short_analysis,
        "is_prescription": is_prescription,
        "medications": medications,
        "abnormal_findings": abnormal_findings,
        "has_abnormalities": has_abnormalities,
        "relevant_conclusion": relevant_conclusion,
        "findings": findings,
        "explanation": explanation,
        "doctor_review_status": "pending",
        "doctor_integration": {
            "status": "saved_for_doctor",
            "assessment_id": assessment.id,
            "review_status": "pending",
            "message": "Report analysis, abnormal findings, and clinical conclusion have been saved to the Doctor Portal for physician review."
        },
        "fhir_diagnostic_report": diag_resource
    }

@router.get("/list")
def get_user_reports(current_user: User = Depends(require_patient), db: Session = Depends(get_db)):
    """List all uploaded reports for current patient."""
    reports = db.query(MedicalReport).filter(
        MedicalReport.patient_id == current_user.id
    ).order_by(MedicalReport.uploaded_at.desc()).all()

    result = []
    for r in reports:
        assessment = db.query(AssessmentRecord).filter(AssessmentRecord.report_id == r.id).first()
        ext_ent = r.extracted_entities or {}
        abn_f = ext_ent.get("abnormal_findings", [])
        rel_conc = ext_ent.get("relevant_conclusion", "")
        short_an = ext_ent.get("short_analysis", "")
        has_abn = ext_ent.get("has_abnormalities", len(abn_f) > 0)

        result.append({
            "id": r.id,
            "assessment_id": assessment.id if assessment else None,
            "file_name": r.file_name,
            "file_type": r.file_type,
            "file_size_bytes": r.file_size_bytes,
            "findings_count": len(r.clinical_findings or []),
            "has_abnormalities": has_abn,
            "is_prescription": ext_ent.get("is_prescription", False),
            "medications": ext_ent.get("medications", []),
            "abnormal_count": len(abn_f),
            "abnormal_findings": abn_f,
            "relevant_conclusion": rel_conc,
            "short_analysis": short_an,
            "key_observations": r.key_observations,
            "doctor_review_status": assessment.doctor_review_status if assessment else "pending",
            "doctor_notes": assessment.doctor_notes if assessment else None,
            "uploaded_at": r.uploaded_at.isoformat()
        })
    return result

@router.get("/{report_id}")
def get_report_detail(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve full details, extracted text, and FHIR resource of a report."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
        
    if current_user.role == "patient" and report.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to patient report.")

    assessment = db.query(AssessmentRecord).filter(AssessmentRecord.report_id == report.id).first()
    ext_ent = report.extracted_entities or {}
    abn_f = ext_ent.get("abnormal_findings", [])
    rel_conc = ext_ent.get("relevant_conclusion", "")
    short_an = ext_ent.get("short_analysis", "")
    has_abn = ext_ent.get("has_abnormalities", len(abn_f) > 0)

    reviewer_name = None
    if assessment and assessment.reviewed_by_id:
        doc = db.query(User).filter(User.id == assessment.reviewed_by_id).first()
        if doc:
            reviewer_name = doc.full_name

    return {
        "id": report.id,
        "patient_id": report.patient_id,
        "assessment_id": assessment.id if assessment else None,
        "file_name": report.file_name,
        "file_type": report.file_type,
        "extracted_text": report.extracted_text,
        "extracted_entities": report.extracted_entities,
        "clinical_findings": report.clinical_findings,
        "abnormal_findings": abn_f,
        "has_abnormalities": has_abn,
        "is_prescription": ext_ent.get("is_prescription", False),
        "medications": ext_ent.get("medications", []),
        "relevant_conclusion": rel_conc,
        "short_analysis": short_an,
        "key_observations": report.key_observations,
        "doctor_review_status": assessment.doctor_review_status if assessment else "pending",
        "doctor_notes": assessment.doctor_notes if assessment else None,
        "reviewed_by": reviewer_name,
        "fhir_bundle": report.fhir_bundle,
        "uploaded_at": report.uploaded_at.isoformat()
    }
