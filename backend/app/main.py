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

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Map service-layer errors to HTTP so routers stay free of try/except."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_payload()})


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
