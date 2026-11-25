from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.database import get_db
from backend.models import User
from backend.schemas import PrecautionsRequest
from backend.auth import get_current_user
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list
from backend.emergency_triage import evaluate_emergency_triage

router = APIRouter(prefix="/api/precautions", tags=["Health Precautions"])

@router.post("/guidance")
def get_health_precautions(req: PrecautionsRequest, current_user: User = Depends(get_current_user)):
    """
    Feature 4: Provide general non-drug precautions and monitoring guidance.
    Strictly non-pharmacological evidence-based advice.
    """
    query = " ".join(req.symptoms_or_conditions)
    triage = evaluate_emergency_triage(query)
    sources = search_medical_knowledge(query, max_results=3)
    citations = get_sources_citation_list(sources)

    # Compile verified precautions from source guidelines
    compiled_precautions = []
    for s in sources:
        for p in s.get("precautions", []):
            if p not in compiled_precautions:
                compiled_precautions.append(p)

    if not compiled_precautions:
        compiled_precautions = [
            "Maintain adequate rest and minimize strenuous physical exertion.",
            "Ensure adequate hydration with clean water, clear broths, and electrolyte fluids.",
            "Monitor body temperature and pulse rate twice daily; record values in a log.",
            "Practice proper respiratory etiquette and frequent handwashing.",
            "Elevate head of bed if experiencing nighttime cough or breathing discomfort."
        ]

    # Specific self-monitoring parameters
    monitoring_guidelines = [
        {"metric": "Body Temperature", "frequency": "Every 6-8 hours", "alert_threshold": "> 101.5°F (38.6°C) or lasting > 3 days"},
        {"metric": "Oxygen Saturation (SpO2)", "frequency": "Morning & Evening", "alert_threshold": "< 94% on room air"},
        {"metric": "Hydration / Urine Output", "frequency": "Daily assessment", "alert_threshold": "Dark concentrated urine or < 3 urinations/day"},
        {"metric": "Respiratory Rate", "frequency": "At rest", "alert_threshold": "> 22 breaths per minute"}
    ]

    red_flags = [
        "Inability to breathe comfortably or severe shortness of breath",
        "Persistent chest pressure, pain, or palpitations",
        "Confusion, extreme dizziness, or inability to wake up",
        "Coughing up blood or persistent vomiting"
    ]

    return {
        "symptoms_evaluated": req.symptoms_or_conditions,
        "is_emergency": triage["is_emergency"],
        "emergency_warning": triage["recommended_action"] if triage["is_emergency"] else None,
        "non_drug_precautions": compiled_precautions,
        "monitoring_guidance": monitoring_guidelines,
        "red_flag_warnings": red_flags,
        "evidence_sources": citations,
        "disclaimer": "These precautions are supportive non-drug measures and do not substitute for a physician's medical evaluation."
    }
