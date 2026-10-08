from fastapi import FastAPI

from app.api.files import router as files_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Upload Shapefile ZIP or KML files and return feature measurements.",
)

app.include_router(files_router, prefix="/api/files", tags=["files"])


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
