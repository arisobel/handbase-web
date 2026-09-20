from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.locales import SUPPORTED_LOCALES
from backend.app.db.session import get_db
from backend.app.db.migrations import current_revisions, expected_head

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Liveness: the process is up and the database answers.

    Intentionally free of configuration detail — no URLs, no secrets, no
    hostnames. Unauthenticated, because a load balancer has no credentials.
    """
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "revision": settings.app_build_revision,
        "rtl": True,
        "locales": list(SUPPORTED_LOCALES),
    }


@router.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: the schema is actually migrated to the revision this build expects.

    A container that is alive but running against an un-migrated database will
    fail every write; this is what distinguishes the two states. Returns 503 so
    an orchestrator can hold traffic back.
    """
    head = expected_head()
    applied = current_revisions(db)
    migrated = head is not None and head in applied

    if not migrated:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if migrated else "migrating",
        "database": "ok",
        "schema_revision": sorted(applied),
        "expected_revision": head,
    }
