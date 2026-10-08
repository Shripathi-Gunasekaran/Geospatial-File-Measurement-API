import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import FeatureMeasurement


@dataclass
class FileRecord:
    id: str
    filename: str
    stored_path: str
    feature_count: int
    crs: str | None
    status: str
    error: str | None = None


class StorageService:
    def __init__(self, upload_dir: Path, metadata_dir: Path, measurements_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.metadata_dir = metadata_dir
        self.measurements_dir = measurements_dir

    def create_file_id(self) -> str:
        return uuid.uuid4().hex

    def save_upload(self, file_id: str, filename: str, content: bytes) -> Path:
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        suffix = Path(filename).suffix.lower()
        target = self.upload_dir / f"{file_id}{suffix}"
        target.write_bytes(content)
        return target

    def save_record(self, record: FileRecord) -> None:
        path = self.metadata_dir / f"{record.id}.json"
        path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")

    def get_record(self, file_id: str) -> FileRecord | None:
        path = self.metadata_dir / f"{file_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return FileRecord(**data)

    def save_measurements(self, file_id: str, features: list[FeatureMeasurement]) -> None:
        path = self.measurements_dir / f"{file_id}.json"
        payload = [feature.model_dump(mode="json") for feature in features]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_measurements(self, file_id: str) -> list[FeatureMeasurement]:
        path = self.measurements_dir / f"{file_id}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [FeatureMeasurement.model_validate(item) for item in data]


def get_storage_service() -> StorageService:
    return StorageService(settings.upload_dir, settings.metadata_dir, settings.measurements_dir)
