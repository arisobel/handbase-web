import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.health import router as health_router
from backend.app.api.meta import router as meta_router
from backend.app.api.v1 import api_router
from backend.app.core.config import get_settings
from backend.app.services.errors import DomainError

logger = logging.getLogger(__name__)
settings = get_settings()

# Tokens and the refresh cookie are signed with APP_SECRET_KEY. Booting
# production with the shipped placeholder would make every session forgeable, so
# refuse to start rather than run insecurely.
if settings.is_production and settings.secret_key_is_insecure():
    raise RuntimeError(
        "APP_SECRET_KEY is unset or still the placeholder value. "
        "Set a long random secret before running with APP_ENV=production."
    )
if settings.secret_key_is_insecure():
    logger.warning("APP_SECRET_KEY is a placeholder. Acceptable for local development only.")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Required for the refresh-token cookie to travel on cross-origin calls
    # during local development (Vite on :5173 -> API on :8000).
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Map service-layer errors to HTTP so routers stay free of try/except."""
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.to_payload()}, headers=headers
    )


app.include_router(health_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(api_router, prefix="/api")

frontend_dist = Path("/app/frontend/dist")
if not frontend_dist.exists():
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if frontend_dist.exists():
    assets = frontend_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        requested = frontend_dist / full_path
        if full_path and requested.is_file():
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": settings.app_name, "frontend": "not built"}
