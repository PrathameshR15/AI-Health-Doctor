import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, PatientProfile
from backend.schemas import UserRegister, UserLogin, TokenResponse, UserProfileUpdate, ConsentUpdate
from backend.auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )

    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role if user_in.role in ["patient", "doctor"] else "patient",
        phone=user_in.phone
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # If patient, create initial profile
    if user.role == "patient":
        profile = PatientProfile(
            user_id=user.id,
            ai_consent_given=True,
            ai_consent_at=datetime.datetime.utcnow()
        )
        db.add(profile)
        db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "phone": user.phone
        }
    }

@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "phone": user.phone
        }
    }

@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile_data = {}
    if current_user.role == "patient":
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if profile:
            profile_data = {
                "date_of_birth": profile.date_of_birth,
                "gender": profile.gender,
                "blood_group": profile.blood_group,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "emergency_contact": profile.emergency_contact,
                "allergies_summary": profile.allergies_summary,
                "chronic_conditions": profile.chronic_conditions,
                "current_medications": profile.current_medications,
                "ai_consent_given": profile.ai_consent_given,
                "ai_consent_at": profile.ai_consent_at.isoformat() if profile.ai_consent_at else None
            }

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "phone": current_user.phone,
        "profile": profile_data
    }

@router.put("/profile")
def update_profile(update_in: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if update_in.full_name:
        current_user.full_name = update_in.full_name
    if update_in.phone is not None:
        current_user.phone = update_in.phone

    if current_user.role == "patient":
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not profile:
            profile = PatientProfile(user_id=current_user.id)
            db.add(profile)
        
        if update_in.date_of_birth is not None:
            profile.date_of_birth = update_in.date_of_birth
        if update_in.gender is not None:
            profile.gender = update_in.gender
        if update_in.blood_group is not None:
            profile.blood_group = update_in.blood_group
        if update_in.height_cm is not None:
            profile.height_cm = update_in.height_cm
        if update_in.weight_kg is not None:
            profile.weight_kg = update_in.weight_kg
        if update_in.emergency_contact is not None:
            profile.emergency_contact = update_in.emergency_contact
        if update_in.allergies_summary is not None:
            profile.allergies_summary = update_in.allergies_summary
        if update_in.chronic_conditions is not None:
            profile.chronic_conditions = update_in.chronic_conditions
        if update_in.current_medications is not None:
            profile.current_medications = update_in.current_medications

    db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/consent")
def update_ai_consent(consent_in: ConsentUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "patient":
        return {"message": "Consent applies to patient profiles."}
        
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)
        
    profile.ai_consent_given = consent_in.consent
    profile.ai_consent_at = datetime.datetime.utcnow()
    db.commit()
    
    return {
        "status": "success",
        "ai_consent_given": profile.ai_consent_given,
        "ai_consent_at": profile.ai_consent_at.isoformat()
    }
