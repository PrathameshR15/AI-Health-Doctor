import os
import secrets
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file from backend or root directory
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

class Settings(BaseModel):
    APP_NAME: str = "Smart Health AI"
    APP_VERSION: str = "1.1.0"
    ENV: str = os.getenv("ENV", "development")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_health_ai.db")
    
    # OpenAI Direct Integration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o") # Top medical reasoning flagship model: gpt-4o (or gpt-4o-mini)
    
    # OpenRouter LLM Integration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "openai/gpt-4o-mini") # Best-in-class clinical disease identification
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "meta-llama/llama-3.3-70b-instruct")
    
    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
    MAX_UPLOAD_SIZE_MB: int = 20

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
