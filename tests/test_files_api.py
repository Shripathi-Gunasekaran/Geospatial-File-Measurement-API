import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.api.files import get_file_info, get_measurements, upload_file
from app.services.processor import GeospatialProcessor
from app.services.storage import StorageService


@pytest.mark.parametrize("field_name", ["upload", "file"])
def test_upload_file_accepts_upload_aliases(tmp_path, field_name):
    upload_dir = tmp_path / "uploads"
    metadata_dir = tmp_path / "metadata"
    measurements_dir = tmp_path / "measurements"
    for directory in (upload_dir, metadata_dir, measurements_dir):
        directory.mkdir()

    storage = StorageService(upload_dir, metadata_dir, measurements_dir)
    processor = GeospatialProcessor(upload_dir)
    uploaded_file = UploadFile(
        file=BytesIO(
            b"<kml><Placemark><Point><coordinates>77.5946,12.9716"
            b"</coordinates></Point></Placemark></kml>"
        ),
        filename="sample.kml",
    )

    uploads = {"upload": None, "file": None}
    uploads[field_name] = uploaded_file
    result = asyncio.run(
        upload_file(storage=storage, processor=processor, **uploads)
    )

    assert result.filename == "sample.kml"
    assert result.feature_count == 1
    assert result.status == "COMPLETED"
    assert storage.get_measurements(result.id)
    assert get_file_info(result.id, storage).filename == "sample.kml"
    measurements = get_measurements(result.id, storage)
    assert measurements.file_id == result.id
    assert set(measurements.features[0].properties) == {"Name", "Description"}
    asyncio.run(uploaded_file.close())


def test_upload_file_returns_clear_error_when_file_is_missing(tmp_path):
    storage = StorageService(tmp_path, tmp_path, tmp_path)
    processor = GeospatialProcessor(tmp_path)

    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_file(upload=None, file=None, storage=storage, processor=processor))

    assert error.value.status_code == 400
    assert "No file received" in error.value.detail
