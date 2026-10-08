from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.schemas import FileInfoResponse, MeasurementCollectionResponse
from app.services.processor import GeospatialProcessor, ProcessingError
from app.services.storage import FileRecord, StorageService, get_storage_service

router = APIRouter()


def get_processor() -> GeospatialProcessor:
    return GeospatialProcessor(settings.upload_dir)


@router.post("/", response_model=FileInfoResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    upload: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service),
    processor: GeospatialProcessor = Depends(get_processor),
) -> FileInfoResponse:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    extension = Path(upload.filename).suffix.lower()
    if extension not in {".zip", ".kml"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a .zip Shapefile archive or a .kml file.",
        )

    file_id = storage.create_file_id()
    stored_path = storage.save_upload(file_id, upload.filename, await upload.read())

    record = FileRecord(
        id=file_id,
        filename=upload.filename,
        stored_path=str(stored_path),
        feature_count=0,
        crs=None,
        status="PROCESSING",
    )
    storage.save_record(record)

    try:
        processed = processor.process(file_id=file_id, filename=upload.filename, path=stored_path)
    except ProcessingError as exc:
        record.status = "FAILED"
        record.error = str(exc)
        storage.save_record(record)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    completed = FileRecord(
        id=file_id,
        filename=upload.filename,
        stored_path=str(stored_path),
        feature_count=len(processed.features),
        crs=processed.crs,
        status="COMPLETED",
        error=None,
    )
    storage.save_record(completed)
    storage.save_measurements(file_id, processed.features)

    return FileInfoResponse.model_validate(completed)


@router.get("/", response_model=list[FileInfoResponse])
def list_files(
    storage: StorageService = Depends(get_storage_service),
) -> list[FileInfoResponse]:
    return [FileInfoResponse.model_validate(record) for record in storage.list_records()]


@router.get("/{file_id}/", response_model=FileInfoResponse)
def get_file_info(
    file_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> FileInfoResponse:
    record = storage.get_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return FileInfoResponse.model_validate(record)


@router.get("/{file_id}/measurements/", response_model=MeasurementCollectionResponse)
def get_measurements(
    file_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> MeasurementCollectionResponse:
    record = storage.get_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")

    features = storage.get_measurements(file_id)
    return MeasurementCollectionResponse(file_id=file_id, features=features)
