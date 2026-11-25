from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
import datetime

# --- Auth & User Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = "patient" # 'patient' or 'doctor'
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    emergency_contact: Optional[str] = None
    allergies_summary: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None

class ConsentUpdate(BaseModel):
    consent: bool

# --- Feature 1: Interactive Symptom Checker ---
class SymptomInitRequest(BaseModel):
    chief_complaint: str
    patient_context: Optional[str] = None

class SymptomAnswerRequest(BaseModel):
    session_id: int
    answer: str
    give_immediate_advice: Optional[bool] = False

class SymptomFollowUpQuestion(BaseModel):
    session_id: int
    step: int
    question: str
    suggested_options: List[str] = []
    is_last_step: bool = False
    emergency_flag: bool = False
    emergency_message: Optional[str] = None

# --- Feature 2: Medical Report Analysis ---
class ReportAnalysisResponse(BaseModel):
    report_id: int
    file_name: str
    file_type: str
    extracted_text_preview: str
    entities: Dict[str, Any]
    findings: List[Dict[str, Any]]
    explanation: str
    fhir_summary: Optional[Dict[str, Any]] = None

# --- Feature 3: Medical History ---
class MedicalHistoryTimelineItem(BaseModel):
    id: int
    date: str
    type: str # 'symptom_assessment', 'lab_report', 'doctor_note', 'allergy'
    title: str
    summary: str
    details: Dict[str, Any]

# --- Feature 4: Health Precautions ---
class PrecautionsRequest(BaseModel):
    symptoms_or_conditions: List[str]
    patient_context: Optional[str] = None

# --- Feature 5: Medical Test Guidance ---
class TestGuidanceRequest(BaseModel):
    symptoms_or_condition: str

# --- Feature 6: Allergy & Diet Assistant ---
class AllergyDietCreateRequest(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: str = "mild"
    foods_to_avoid: Optional[List[str]] = []
    recommended_foods: Optional[List[str]] = []

class AllergyDietApprovalRequest(BaseModel):
    approved: bool
    doctor_notes: Optional[str] = None
    foods_to_avoid: Optional[List[str]] = None
    recommended_foods: Optional[List[str]] = None

# --- Feature 7: Doctor Consultation Summary ---
class ConsultationSummaryGenerateRequest(BaseModel):
    session_id: Optional[int] = None
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    history: Optional[str] = None

# --- Feature 8: Medication Information ---
class MedicationInfoRequest(BaseModel):
    symptoms_or_condition: str
    medication_name: Optional[str] = None

# --- Unified Assessment / Analyze My Health ---
class FullHealthAnalysisRequest(BaseModel):
    chief_complaint: str
    duration: Optional[str] = None
    severity_1_10: Optional[int] = 5
    accompanying_symptoms: Optional[List[str]] = []
    known_conditions: Optional[List[str]] = []
    known_allergies: Optional[List[str]] = []

class AssessmentReviewRequest(BaseModel):
    doctor_notes: str
    status: str = "approved" # approved, modified, reviewed

# --- Doctor Notes ---
class DoctorNoteCreate(BaseModel):
    patient_id: int
    title: str
    content: str
    note_type: str = "clinical"
