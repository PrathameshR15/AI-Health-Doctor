import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="patient") # 'patient' or 'doctor'
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    symptom_sessions = relationship("SymptomSession", back_populates="patient", foreign_keys="SymptomSession.patient_id")
    medical_reports = relationship("MedicalReport", back_populates="patient")
    assessments = relationship("AssessmentRecord", back_populates="patient", foreign_keys="AssessmentRecord.patient_id")
    allergies_diet = relationship("AllergyDiet", back_populates="patient", foreign_keys="AllergyDiet.patient_id")
    doctor_notes_received = relationship("DoctorNote", back_populates="patient", foreign_keys="DoctorNote.patient_id")
    doctor_notes_written = relationship("DoctorNote", back_populates="doctor", foreign_keys="DoctorNote.doctor_id")

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    blood_group = Column(String(10), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    allergies_summary = Column(Text, nullable=True)
    chronic_conditions = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    
    # Consent tracking for external AI services
    ai_consent_given = Column(Boolean, default=True)
    ai_consent_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="patient_profile")

class SymptomSession(Base):
    __tablename__ = "symptom_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="in_progress") # in_progress, completed
    current_step = Column(Integer, default=1)
    chief_complaint = Column(Text, nullable=False)
    # Chat / Q&A conversation history stored as JSON list of {role, content, timestamp}
    conversation_history = Column(JSON, default=list)
    # Structured entities extracted by MedSpaCy
    extracted_entities = Column(JSON, default=dict)
    # AI Analysis Output
    possible_conditions = Column(JSON, default=list) # [{condition, likelihood, explanation, sources}]
    precautions = Column(JSON, default=list)
    test_guidance = Column(JSON, default=list)
    emergency_flag = Column(Boolean, default=False)
    triage_level = Column(String(50), default="routine") # emergency, urgent, routine, self_care
    emergency_reasons = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="symptom_sessions", foreign_keys=[patient_id])

class MedicalReport(Base):
    __tablename__ = "medical_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True, default="in-memory-data-only")
    file_type = Column(String(50), nullable=False) # pdf, image, fhir_json
    file_size_bytes = Column(Integer, default=0)
    
    extracted_text = Column(Text, nullable=True)
    extracted_entities = Column(JSON, default=dict)
    clinical_findings = Column(JSON, default=list) # [{finding, normal_range, patient_value, status, explanation}]
    key_observations = Column(Text, nullable=True)
    fhir_bundle = Column(JSON, nullable=True)
    
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="medical_reports")

class AssessmentRecord(Base):
    __tablename__ = "assessment_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("symptom_sessions.id"), nullable=True)
    report_id = Column(Integer, ForeignKey("medical_reports.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    chief_complaint = Column(Text, nullable=False)
    symptoms_summary = Column(Text, nullable=True)
    extracted_entities = Column(JSON, default=dict)
    
    # 8 Features payload
    possible_conditions = Column(JSON, default=list)
    precautions = Column(JSON, default=list)
    test_guidance = Column(JSON, default=list)
    diet_guidance = Column(JSON, default=dict)
    medication_info = Column(JSON, default=list)
    consultation_summary = Column(JSON, default=dict) # SOAP format: Subjective, Objective, Assessment, Plan
    sources = Column(JSON, default=list) # Verified references with live URLs
    
    # Triage and Doctor Review
    triage_level = Column(String(50), default="routine")
    emergency_warning = Column(Boolean, default=False)
    doctor_review_status = Column(String(50), default="pending") # pending, reviewed, modified, approved
    doctor_notes = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="assessments", foreign_keys=[patient_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

class AllergyDiet(Base):
    __tablename__ = "allergy_diet_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allergen = Column(String(255), nullable=False)
    reaction = Column(String(255), nullable=True)
    severity = Column(String(50), default="mild") # mild, moderate, severe, anaphylactic
    foods_to_avoid = Column(JSON, default=list)
    recommended_foods = Column(JSON, default=list)
    doctor_approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="allergies_diet", foreign_keys=[patient_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class DoctorNote(Base):
    __tablename__ = "doctor_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="clinical") # clinical, prescription_review, lab_followup, dietary
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="doctor_notes_received", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="doctor_notes_written", foreign_keys=[doctor_id])
