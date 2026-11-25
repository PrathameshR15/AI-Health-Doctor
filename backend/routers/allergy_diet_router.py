from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.database import get_db
from backend.models import User, AllergyDiet, PatientProfile
from backend.schemas import AllergyDietCreateRequest, AllergyDietApprovalRequest
from backend.auth import get_current_user, require_patient, require_doctor
from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list

router = APIRouter(prefix="/api/allergy-diet", tags=["Allergy & Diet Assistant"])

# Evidence-based allergen cross-reactivity & dietary guidance matrix
ALLERGEN_DIET_MATRIX = {
    "peanuts": {
        "foods_to_avoid": ["Peanut butter", "Mixed tree nuts (cross-contamination)", "Satay sauces", "Groundnut oil (unrefined)", "Certain baked pastries"],
        "recommended_substitutes": ["Sunflower seed butter", "Pumpkin seeds", "Roasted chickpeas", "Soy butter"],
        "guidance": "Strict avoidance of all peanut-containing foods. Check ingredient labels for 'processed in a facility that handles peanuts'."
    },
    "shellfish": {
        "foods_to_avoid": ["Shrimp, prawns, lobster, crab", "Oyster sauce and fish stock", "Sushi with crustacean roe", "Paella and bouillabaisse"],
        "recommended_substitutes": ["Skinless poultry", "Firm tofu / paneer", "Freshwater fish (if evaluated non-allergic by allergist)", "Lentils and legumes"],
        "guidance": "Crustacean and mollusk allergy is often lifelong. Be cautious of shared fryer oils at restaurants."
    },
    "dairy": {
        "foods_to_avoid": ["Cow milk, cheese, butter, cream", "Casein / whey protein powders", "Ice cream, milk chocolate"],
        "recommended_substitutes": ["Fortified almond or oat milk", "Soy milk with added calcium and vitamin D", "Tofu", "Coconut yogurt"],
        "guidance": "Distinguish between lactose intolerance (digestive enzyme deficiency) and cow milk protein allergy (immune-mediated)."
    },
    "gluten": {
        "foods_to_avoid": ["Wheat, barley, rye", "Traditional bread, pasta, pizza dough", "Standard soy sauce (contains wheat)", "Beer"],
        "recommended_substitutes": ["Rice, quinoa, buckwheat", "Millet (Bajra, Jowar, Ragi)", "Gluten-free certified oats", "Corn tortillas"],
        "guidance": "Patients with Celiac disease require strict gluten exclusion to prevent intestinal villous atrophy."
    },
    "eggs": {
        "foods_to_avoid": ["Eggs (whole, yolk, white)", "Mayonnaise", "Meringue, custard", "Certain bread glazes and pasta"],
        "recommended_substitutes": ["Mashed bananas or applesauce in baking", "Flaxseed meal with water", "Silken tofu", "Aquafaba (chickpea water)"],
        "guidance": "Egg proteins (ovalbumin) can cause cutaneous and gastrointestinal reactions. Read all food packaging labels carefully."
    }
}

@router.get("/my-records")
def get_patient_allergies_and_diet(
    patient_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all recorded allergies and diet plans for the patient.
    """
    target_id = current_user.id
    if current_user.role == "doctor" and patient_id is not None:
        target_id = patient_id

    records = db.query(AllergyDiet).filter(AllergyDiet.patient_id == target_id).all()
    
    # Retrieve ICMR / WHO healthy diet citations
    diet_sources = search_medical_knowledge("diet nutrition healthy eating icmr who", max_results=2)
    citations = get_sources_citation_list(diet_sources)

    return {
        "patient_id": target_id,
        "allergies_and_diet_plans": [
            {
                "id": r.id,
                "allergen": r.allergen,
                "reaction": r.reaction,
                "severity": r.severity,
                "foods_to_avoid": r.foods_to_avoid or [],
                "recommended_foods": r.recommended_foods or [],
                "doctor_approved": r.doctor_approved,
                "approved_by_id": r.approved_by_id,
                "doctor_notes": r.doctor_notes,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ],
        "general_guidelines": [
            "Maintain food diary to track symptoms related to meals.",
            "Verify all restaurant meals and packaged foods for hidden cross-contaminants.",
            "Adhere to doctor-approved dietary substitutions to prevent micronutrient deficiencies."
        ],
        "citations": citations
    }

@router.post("/add")
def add_allergy_and_diet_record(
    req: AllergyDietCreateRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Feature 6: Patient records an allergy and receives automated evidence-based food guidance.
    Flagged for doctor review.
    """
    allergen_key = req.allergen.strip().lower()
    
    # Check if we have pre-compiled nutrition matrix
    matched_matrix = None
    for k, v in ALLERGEN_DIET_MATRIX.items():
        if k in allergen_key or allergen_key in k:
            matched_matrix = v
            break

    foods_to_avoid = req.foods_to_avoid or []
    recommended_foods = req.recommended_foods or []

    if matched_matrix:
        if not foods_to_avoid:
            foods_to_avoid = matched_matrix["foods_to_avoid"]
        if not recommended_foods:
            recommended_foods = matched_matrix["recommended_substitutes"]

    record = AllergyDiet(
        patient_id=current_user.id,
        allergen=req.allergen,
        reaction=req.reaction,
        severity=req.severity,
        foods_to_avoid=foods_to_avoid,
        recommended_foods=recommended_foods,
        doctor_approved=False
    )
    db.add(record)
    
    # Also update profile summary
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if profile:
        existing = profile.allergies_summary or ""
        if req.allergen not in existing:
            profile.allergies_summary = f"{existing}, {req.allergen}".strip(", ")
            
    db.commit()
    db.refresh(record)

    return {
        "status": "success",
        "record_id": record.id,
        "allergen": record.allergen,
        "severity": record.severity,
        "foods_to_avoid": record.foods_to_avoid,
        "recommended_foods": record.recommended_foods,
        "doctor_approved": record.doctor_approved,
        "message": "Allergy and diet plan recorded. Pending doctor clinical sign-off."
    }

@router.put("/doctor-approve/{record_id}")
def doctor_approve_diet(
    record_id: int,
    approval_req: AllergyDietApprovalRequest,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """
    Doctor reviews and approves or customizes patient allergy & diet plan.
    """
    record = db.query(AllergyDiet).filter(AllergyDiet.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Allergy record not found.")

    record.doctor_approved = approval_req.approved
    record.approved_by_id = current_user.id
    if approval_req.doctor_notes:
        record.doctor_notes = approval_req.doctor_notes
    if approval_req.foods_to_avoid is not None:
        record.foods_to_avoid = approval_req.foods_to_avoid
    if approval_req.recommended_foods is not None:
        record.recommended_foods = approval_req.recommended_foods

    db.commit()
    return {
        "status": "success",
        "record_id": record.id,
        "doctor_approved": record.doctor_approved,
        "approved_by": current_user.full_name,
        "message": "Allergy and diet plan clinical sign-off updated."
    }
