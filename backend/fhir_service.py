import datetime
import uuid
from typing import Dict, Any, List, Optional

class FHIRService:
    """
    HL7 FHIR R4 Interoperability Service.
    Handles serialization of patient data, clinical observations, conditions,
    allergies, and diagnostic reports into standard FHIR R4 JSON resources,
    as well as parsing imported FHIR bundles.
    """

    @staticmethod
    def create_patient_resource(user_id: int, full_name: str, dob: Optional[str] = None, gender: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
        name_parts = full_name.split()
        family_name = name_parts[-1] if len(name_parts) > 1 else ""
        given_names = name_parts[:-1] if len(name_parts) > 1 else name_parts

        resource = {
            "resourceType": "Patient",
            "id": f"patient-{user_id}",
            "identifier": [
                {
                    "system": "https://smarthealthai.org/patients",
                    "value": str(user_id)
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": family_name,
                    "given": given_names,
                    "text": full_name
                }
            ]
        }
        if gender:
            resource["gender"] = gender.lower() if gender.lower() in ["male", "female", "other", "unknown"] else "unknown"
        if dob:
            resource["birthDate"] = dob
        if phone:
            resource["telecom"] = [
                {
                    "system": "phone",
                    "value": phone,
                    "use": "mobile"
                }
            ]
        return resource

    @staticmethod
    def create_condition_resource(patient_id: int, condition_name: str, verification_status: str = "unconfirmed", onset_date: Optional[str] = None) -> Dict[str, Any]:
        return {
            "resourceType": "Condition",
            "id": f"condition-{uuid.uuid4().hex[:8]}",
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": verification_status,
                        "display": verification_status.capitalize()
                    }
                ]
            },
            "code": {
                "text": condition_name
            },
            "subject": {
                "reference": f"Patient/patient-{patient_id}"
            },
            "recordedDate": datetime.datetime.utcnow().isoformat()
        }

    @staticmethod
    def create_observation_resource(patient_id: int, observation_type: str, value: str, unit: Optional[str] = None, status: str = "final") -> Dict[str, Any]:
        resource = {
            "resourceType": "Observation",
            "id": f"obs-{uuid.uuid4().hex[:8]}",
            "status": status,
            "code": {
                "text": observation_type
            },
            "subject": {
                "reference": f"Patient/patient-{patient_id}"
            },
            "effectiveDateTime": datetime.datetime.utcnow().isoformat(),
            "valueString": f"{value} {unit or ''}".strip()
        }
        return resource

    @staticmethod
    def create_allergy_intolerance_resource(patient_id: int, allergen: str, reaction: Optional[str] = None, severity: str = "mild") -> Dict[str, Any]:
        severity_map = {
            "mild": "mild",
            "moderate": "moderate",
            "severe": "severe",
            "anaphylactic": "severe"
        }
        return {
            "resourceType": "AllergyIntolerance",
            "id": f"allergy-{uuid.uuid4().hex[:8]}",
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "confirmed"
                    }
                ]
            },
            "substance": {
                "text": allergen
            },
            "patient": {
                "reference": f"Patient/patient-{patient_id}"
            },
            "reaction": [
                {
                    "manifestation": [{"text": reaction or "Hypersensitivity"}],
                    "severity": severity_map.get(severity.lower(), "mild")
                }
            ]
        }

    @staticmethod
    def create_diagnostic_report_resource(patient_id: int, title: str, conclusion: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "resourceType": "DiagnosticReport",
            "id": f"diag-{uuid.uuid4().hex[:8]}",
            "status": "final",
            "code": {
                "text": title
            },
            "subject": {
                "reference": f"Patient/patient-{patient_id}"
            },
            "effectiveDateTime": datetime.datetime.utcnow().isoformat(),
            "conclusion": conclusion,
            "result": [
                {"display": f"{f.get('finding')}: {f.get('patient_value')} (Ref: {f.get('normal_range')})"}
                for f in findings if isinstance(f, dict) and "finding" in f
            ]
        }

    @staticmethod
    def create_bundle(resources: List[Dict[str, Any]], bundle_type: str = "collection") -> Dict[str, Any]:
        """
        Package multiple FHIR resources into a valid FHIR R4 Bundle.
        """
        entries = []
        for r in resources:
            entries.append({
                "fullUrl": f"urn:uuid:{uuid.uuid4()}",
                "resource": r
            })

        return {
            "resourceType": "Bundle",
            "id": f"bundle-{uuid.uuid4().hex[:12]}",
            "type": bundle_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "total": len(resources),
            "entry": entries
        }

    @staticmethod
    def parse_fhir_bundle(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured entities from an imported FHIR JSON bundle.
        """
        extracted = {
            "patient_info": {},
            "conditions": [],
            "observations": [],
            "allergies": [],
            "medications": [],
            "diagnostic_reports": []
        }

        entries = bundle_data.get("entry", [])
        if not entries and bundle_data.get("resourceType"):
            # Single resource uploaded directly
            entries = [{"resource": bundle_data}]

        for item in entries:
            res = item.get("resource", {})
            rtype = res.get("resourceType")

            if rtype == "Patient":
                name_list = res.get("name", [])
                full_name = name_list[0].get("text") if name_list else "Unknown"
                extracted["patient_info"] = {
                    "full_name": full_name,
                    "gender": res.get("gender"),
                    "dob": res.get("birthDate"),
                    "id": res.get("id")
                }
            elif rtype == "Condition":
                code_obj = res.get("code", {})
                cond_text = code_obj.get("text") or (code_obj.get("coding", [{}])[0].get("display", "Unknown Condition"))
                ver_status = res.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "unconfirmed")
                extracted["conditions"].append({
                    "name": cond_text,
                    "status": ver_status
                })
            elif rtype == "Observation":
                code_obj = res.get("code", {})
                obs_text = code_obj.get("text") or (code_obj.get("coding", [{}])[0].get("display", "Observation"))
                val = res.get("valueString") or res.get("valueQuantity", {}).get("value") or "Recorded"
                extracted["observations"].append({
                    "type": obs_text,
                    "value": str(val)
                })
            elif rtype == "AllergyIntolerance":
                substance = res.get("substance", {}).get("text") or "Unknown allergen"
                reactions = res.get("reaction", [])
                reaction_text = reactions[0].get("manifestation", [{}])[0].get("text") if reactions else "Allergic reaction"
                severity = reactions[0].get("severity", "mild") if reactions else "mild"
                extracted["allergies"].append({
                    "allergen": substance,
                    "reaction": reaction_text,
                    "severity": severity
                })
            elif rtype == "DiagnosticReport":
                code_obj = res.get("code", {})
                title = code_obj.get("text") or "Diagnostic Report"
                conclusion = res.get("conclusion", "")
                extracted["diagnostic_reports"].append({
                    "title": title,
                    "conclusion": conclusion
                })
            elif rtype in ["MedicationRequest", "MedicationStatement"]:
                med_code = res.get("medicationCodeableConcept", {}).get("text") or "Medication"
                extracted["medications"].append({"name": med_code})

        return extracted

fhir_service = FHIRService()
