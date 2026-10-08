# Geospatial File Measurement API

FastAPI backend service with a browser frontend for uploading KML files or zipped Shapefiles, extracting geospatial features, and returning measurements.

## Features

- Upload `.kml` files or `.zip` archives containing one Shapefile.
- View uploaded files in a browser UI at `/`.
- Extract feature ID, geometry type, GeoJSON geometry, CRS, and properties.
- Calculate polygon area in square meters.
- Calculate line length in meters.
- Handle point and unsupported geometries gracefully.
- Persist uploaded file metadata and measurements locally as JSON.
- Project geographic coordinates before measurement so area/length are not calculated in latitude/longitude degrees.

## Setup

Requires Python 3.12 or later.

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn app.main:app --reload
```

Open the frontend:

```text
http://127.0.0.1:8000/
```

Interactive API documentation:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## API

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "app": "Geospatial File Measurement API",
  "version": "1.0.0"
}
```

Errors use FastAPI's standard `{"detail": "..."}` response shape. Missing or
unsupported uploads return `400`; files that cannot be parsed or contain no
features return `422`.

### Upload File

```http
POST /api/files/
Content-Type: multipart/form-data
```

Form field:

- `upload` (or `file`): `.kml` file or `.zip` containing a Shapefile.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "upload=@samples/sample.kml"
```

Response:

```json
{
  "id": "abc123",
  "filename": "sample.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error": null
}
```

### List Files

```http
GET /api/files/
```

Response:

```json
[
  {
    "id": "abc123",
    "filename": "sample.kml",
    "feature_count": 3,
    "crs": "EPSG:4326",
    "status": "COMPLETED",
    "error": null
  }
]
```

### File Information

```http
GET /api/files/{id}/
```

Response:

```json
{
  "id": "abc123",
  "filename": "survey.kml",
  "feature_count": 120,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error": null
}
```

### Measurements

```http
GET /api/files/{id}/measurements/
```

Response:

```json
{
  "file_id": "abc123",
  "features": [
    {
      "feature_id": 0,
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[77.1, 12.9], [77.2, 12.9], [77.2, 13.0], [77.1, 12.9]]]
      },
      "crs": "EPSG:4326",
      "properties": {
        "name": "Plot A"
      },
      "measurement": {
        "area_square_meters": 60411234.25,
        "length_meters": null,
        "message": null
      }
    }
  ]
}
```

## Architecture

```text
app/
  api/              FastAPI route handlers
  core/             Settings and application configuration
  models/           Pydantic response and domain schemas
  services/         File storage and geospatial processing
  static/           Browser frontend
samples/            Sample geospatial file for manual testing
tests/              Focused measurement tests
```

### Backend Framework

The backend uses FastAPI with:

- Application factory: `create_app()` in `app/main.py`.
- OpenAPI metadata and route tags.
- CORS middleware controlled by `GEO_API_CORS_ORIGINS`.
- Static file serving for the frontend.
- Dependency-injected storage and processing services.
- Pydantic response models for API contracts.

### File Processing Flow

1. `POST /api/files/` validates the file extension.
2. The uploaded file is saved under `data/uploads/`.
3. Metadata is written with `PROCESSING` status.
4. `GeospatialProcessor` reads the file.
5. Features are normalized into a common internal representation.
6. Measurements are calculated and stored under `data/measurements/`.
7. File metadata is updated to `COMPLETED`.

For Shapefiles, the service expects a `.zip` archive with exactly one `.shp` file and rejects unsafe archive paths before extraction. For KML, it first uses GeoPandas and falls back to a built-in XML parser for common `Point`, `LineString`, and `Polygon` placemarks.

### Measurement Flow

- `Polygon` and `MultiPolygon`: area in square meters.
- `LineString` and `MultiLineString`: length in meters.
- `Point` and `MultiPoint`: no measurement required.
- Other geometry types: returned with a clear unsupported message.

### CRS Handling

The service reads the source CRS from the uploaded dataset when available. If the CRS is geographic, such as `EPSG:4326`, it chooses a UTM projected CRS based on each feature centroid and transforms the geometry with `pyproj` before calculating area or length. If a Shapefile has no CRS metadata, the service assumes `EPSG:4326` so that measurements are still projected rather than calculated directly in degrees.

## Design Decisions

- **FastAPI** was chosen for concise route handling, automatic OpenAPI documentation, and Pydantic integration.
- **GeoPandas/Shapely/PyProj** were chosen for mature geospatial file reading, geometry operations, and CRS transformations.
- **Local JSON persistence** keeps the project easy to run without a database. In production, this can be replaced by PostgreSQL/PostGIS or object storage plus relational metadata.
- **Synchronous processing** keeps the assignment implementation straightforward. For large uploads, a background queue such as Celery, RQ, or FastAPI background workers would improve reliability.
- **Per-feature UTM projection** is simple and accurate for local measurements. For very large regions, a geodesic calculation or equal-area projection strategy may be preferable.

## Tests

Run:

```bash
python -m pytest
```

The tests cover KML and Shapefile ZIP processing, upload field aliases, saved
file and measurement responses, unsupported geometries, and projected area and
length calculations.

## Learning

- Geometry libraries need correct CRS context.
- File upload APIs should validate extension and archive contents.
- KML support varies across GDAL installations, so a narrow fallback parser improves portability.
- Clear unsupported-geometry responses are better than unexpected API crashes.

## Future Scope

- Add PostgreSQL/PostGIS persistence.
- Move processing to a background job queue for large files.
- Add authenticated uploads and per-user file ownership.
- Add richer validation for required Shapefile sidecar files.
- Support GeoJSON, GPKG, and multiple layers.
- Add Docker packaging and CI.
- Add more precise geodesic calculations for long lines and global datasets.

## Submission

Public GitHub repository: [Shripathi-Gunasekaran/Geospatial-File-Measurement-API](https://github.com/Shripathi-Gunasekaran/Geospatial-File-Measurement-API).

The repository includes this README, source code, tests, sample data, and
`requirements.txt`.
