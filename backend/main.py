import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.seed_data import seed_database

# Import routers
from backend.routers import (
    auth_router,
    symptom_router,
    report_router,
    history_router,
    precautions_router,
    test_guidance_router,
    allergy_diet_router,
    consultation_router,
    medication_router,
    doctor_router,
    knowledge_router,
    analysis_router
)

# Create database tables
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLM-Powered Healthcare Assistant & Clinical Decision-Support Platform with OpenRouter, MedSpaCy, and FHIR interoperability.",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth_router.router)
app.include_router(symptom_router.router)
app.include_router(report_router.router)
app.include_router(history_router.router)
app.include_router(precautions_router.router)
app.include_router(test_guidance_router.router)
app.include_router(allergy_diet_router.router)
app.include_router(consultation_router.router)
app.include_router(medication_router.router)
app.include_router(doctor_router.router)
app.include_router(knowledge_router.router)
app.include_router(analysis_router.router)

# Lifespan handles startup & shutdown above

@app.get("/api/health")
def health_check():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
        "disclaimer": "Smart Health AI is a clinical decision-support and educational assistant. Not a substitute for professional medical care."
    }

# Mount frontend production build if available
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root_fallback():
        return health_check()
