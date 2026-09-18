from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.core.config import get_settings
from backend.app.db.session import get_db

router = APIRouter()
settings = get_settings()

@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "revision": settings.app_build_revision,
        "rtl": True,
        "locales": ["en", "he", "pt-BR"],
    }
