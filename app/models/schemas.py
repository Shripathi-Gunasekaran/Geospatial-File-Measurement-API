from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Measurement(BaseModel):
    area_square_meters: float | None = None
    length_meters: float | None = None
    message: str | None = None


class FeatureMeasurement(BaseModel):
    feature_id: int
    geometry_type: str
    geometry: dict[str, Any]
    crs: str | None
    properties: dict[str, Any] = Field(default_factory=dict)
    measurement: Measurement


class FileInfoResponse(BaseModel):
    id: str
    filename: str
    feature_count: int
    crs: str | None
    status: Literal["PROCESSING", "COMPLETED", "FAILED"]
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MeasurementCollectionResponse(BaseModel):
    file_id: str
    features: list[FeatureMeasurement]
