from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.files import router as files_router
from app.core.config import settings

OPENAPI_TAGS = [
    {
        "name": "files",
        "description": "Upload geospatial files and inspect extracted measurements.",
    },
    {
        "name": "health",
        "description": "Service health endpoint.",
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Upload Shapefile ZIP or KML files and return feature measurements.",
        openapi_tags=OPENAPI_TAGS,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(files_router, prefix="/api/files", tags=["files"])
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse("app/static/index.html")

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
