<<<<<<< HEAD
# Geospatial File Measurement API

FastAPI backend service that accepts a KML file or a zipped Shapefile, extracts geospatial features, and returns feature metadata plus measurements for supported geometry types.

## Features

- Upload `.kml` files or `.zip` archives containing one Shapefile.
- Extract feature ID, geometry type, GeoJSON geometry, CRS, and properties.
- Calculate polygon area in square meters.
- Calculate line length in meters.
- Handle point and unsupported geometries gracefully.
- Persist uploaded file metadata and measurements locally as JSON.
- Avoid measuring latitude/longitude degrees by projecting geographic data before calculation.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API documentation is available at:

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
  "status": "ok"
}
```

### Upload File

```http
POST /api/files/
Content-Type: multipart/form-data
```

Form field:

- `upload`: `.kml` file or `.zip` containing a Shapefile.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "upload=@survey.kml"
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
  core/             Configuration and application settings
  models/           Pydantic response and domain schemas
  services/         File storage and geospatial processing
tests/              Focused measurement tests
```

### File Processing Flow

1. `POST /api/files/` validates the extension.
2. The uploaded file is saved under `data/uploads/`.
3. Metadata is written with `PROCESSING` status.
4. `GeospatialProcessor` reads the file.
5. Features are normalized into a common internal representation.
6. Measurements are calculated and stored under `data/measurements/`.
7. File metadata is updated to `COMPLETED`.

For Shapefiles, the service expects a `.zip` archive with exactly one `.shp` file and rejects unsafe archive paths before extraction. For KML, it first uses GeoPandas and falls back to a built-in XML parser for common `Point`, `LineString`, and `Polygon` placemarks.

### Measurement Flow

Each feature is measured based on geometry type:

- `Polygon` and `MultiPolygon`: area in square meters.
- `LineString` and `MultiLineString`: length in meters.
- `Point` and `MultiPoint`: no measurement required.
- Other geometry types: returned with a clear unsupported message.

### CRS Handling

The service reads the source CRS from the uploaded dataset when available. If the CRS is geographic, such as `EPSG:4326`, it chooses a UTM projected CRS based on each feature centroid and transforms the geometry with `pyproj` before calculating area or length. If a Shapefile has no CRS metadata, the service assumes `EPSG:4326` so that measurements are still projected rather than calculated directly in degrees.

## Design Decisions

- **FastAPI** was chosen because it provides concise request handling, automatic OpenAPI docs, and strong Pydantic integration.
- **GeoPandas/Shapely/PyProj** were chosen for mature geospatial file reading, geometry operations, and CRS transformations.
- **Local JSON persistence** keeps the project easy to run without a database. In production, this would be replaced by PostgreSQL/PostGIS or object storage plus a relational metadata table.
- **Synchronous processing** keeps the implementation straightforward for the assignment. For large uploads, a background queue such as Celery, RQ, or FastAPI background workers would improve reliability.
- **Per-feature UTM projection** is simple and accurate for local measurements. For datasets covering very large regions, a geodesic calculation or equal-area projection strategy may be preferable.

## Tests

Run:

```bash
pytest
```

The included tests focus on the critical measurement behavior: geographic inputs are projected before area and length calculations.

## Learning

This project highlights a few practical geospatial API lessons:

- Geometry libraries can compute fast, but they need the correct CRS context.
- File upload APIs should validate both extension and archive contents.
- KML support varies across GDAL installations, so a narrow fallback parser improves portability.
- Clear unsupported-geometry responses are better than letting unexpected shapes crash the API.

## Future Scope

- Add PostgreSQL/PostGIS persistence.
- Move processing to a background job queue for large files.
- Add authenticated uploads and per-user file ownership.
- Add richer validation for required Shapefile sidecar files.
- Support GeoJSON, GPKG, and multiple layers.
- Add Docker packaging and CI.
- Add more precise geodesic calculations for long lines and global datasets.

## Submission

Create a public GitHub repository, push this project, and share the repository link. The repository should include this README, source code, tests, and `requirements.txt`.
=======
# Geospatial-File-Measurement-API
>>>>>>> d5d79a3b3b095619f62fe4f7d9adcaf61c3634be
