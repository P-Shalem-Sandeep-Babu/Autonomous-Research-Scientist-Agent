import os
import secrets
import logging
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

logger = logging.getLogger("arsa.config")

def _get_or_create_secret_key() -> str:
    env_key = os.getenv("JWT_SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    
    # Check if a persistent local keyfile exists in dev
    keyfile_path = os.path.join(os.path.dirname(__file__), "..", "..", ".jwt_secret")
    try:
        if os.path.exists(keyfile_path):
            with open(keyfile_path, "r", encoding="utf-8") as f:
                saved_key = f.read().strip()
                if saved_key:
                    return saved_key
        # Generate a new cryptographically secure 256-bit random key
        new_key = secrets.token_hex(32)
        with open(keyfile_path, "w", encoding="utf-8") as f:
            f.write(new_key)
        return new_key
    except Exception:
        # Fallback to in-memory secure random key
        return secrets.token_hex(32)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Autonomous Research Scientist Agent (ARSA)"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = _get_or_create_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Server Host / Public URL
    SERVER_HOST: str = os.getenv("SERVER_HOST", "http://127.0.0.1:8000")
    
    # Allowed CORS Origins (comma separated)
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./arsa.db")

    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # PubMed API
    PUBMED_EMAIL: str = os.getenv("PUBMED_EMAIL", "your_email@example.com")

    # Gemini API Key (or other LLMs)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")

    # ChromaDB Configuration
    CHROMA_DB_DIR: str = "chroma_db"
    
    # Database Backup Configuration
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "./backups")
    BACKUP_SCHEDULE_HOURS: int = int(os.getenv("BACKUP_SCHEDULE_HOURS", "24"))
    BACKUP_RETENTION_COUNT: int = int(os.getenv("BACKUP_RETENTION_COUNT", "7"))
    BACKUP_S3_BUCKET: Optional[str] = os.getenv("BACKUP_S3_BUCKET", None)
    BACKUP_S3_REGION: Optional[str] = os.getenv("BACKUP_S3_REGION", "us-east-1")

    # Logging & Observability
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json" if os.getenv("ENVIRONMENT") == "production" else "text")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN", None)
    SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2"))
    
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
        protected_namespaces=()
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()
