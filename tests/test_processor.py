import zipfile
from pathlib import Path

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import GeometryCollection, LineString, Point, Polygon

from app.services.processor import GeospatialProcessor, RawFeature


def test_polygon_measurement_projects_geographic_coordinates(tmp_path):
    processor = GeospatialProcessor(tmp_path)
    polygon = Polygon(
        [
            (-73.9857, 40.7484),
            (-73.9847, 40.7484),
            (-73.9847, 40.7494),
            (-73.9857, 40.7494),
            (-73.9857, 40.7484),
        ]
    )

    result = processor._build_feature_measurement(
        RawFeature(0, polygon, {"name": "test"}),
        CRS.from_epsg(4326),
        "EPSG:4326",
    )

    assert result.measurement.area_square_meters is not None
    assert result.measurement.area_square_meters > 0
    assert result.measurement.length_meters is None


def test_line_measurement_projects_geographic_coordinates(tmp_path):
    processor = GeospatialProcessor(tmp_path)
    line = LineString([(-73.9857, 40.7484), (-73.9847, 40.7494)])

    result = processor._build_feature_measurement(
        RawFeature(1, line, {}),
        CRS.from_epsg(4326),
        "EPSG:4326",
    )

    assert result.measurement.length_meters is not None
    assert result.measurement.length_meters > 0
    assert result.measurement.area_square_meters is None


def test_point_measurement_is_not_required(tmp_path):
    processor = GeospatialProcessor(tmp_path)

    result = processor._build_feature_measurement(
        RawFeature(2, Point(-73.9857, 40.7484), {}),
        CRS.from_epsg(4326),
        "EPSG:4326",
    )

    assert result.measurement.area_square_meters is None
    assert result.measurement.length_meters is None
    assert "No measurement required" in result.measurement.message


def test_unsupported_geometry_returns_message_without_crashing(tmp_path):
    processor = GeospatialProcessor(tmp_path)
    geometry = GeometryCollection([Point(-73.9857, 40.7484)])

    result = processor._build_feature_measurement(
        RawFeature(3, geometry, {"name": "collection"}),
        CRS.from_epsg(4326),
        "EPSG:4326",
    )

    assert result.geometry_type == "GeometryCollection"
    assert result.properties == {"name": "collection"}
    assert result.measurement.area_square_meters is None
    assert result.measurement.length_meters is None
    assert "not supported" in result.measurement.message


def test_kml_reader_falls_back_when_geopandas_returns_no_features(tmp_path, monkeypatch):
    processor = GeospatialProcessor(tmp_path)
    monkeypatch.setattr(processor, "_read_with_geopandas", lambda path: ([], None))

    result = processor.process(
        file_id="sample",
        filename="sample.kml",
        path=Path("samples/sample.kml"),
    )

    assert len(result.features) == 3
    assert result.crs == "EPSG:4326"


def test_shapefile_zip_is_processed(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    shapefile_dir = tmp_path / "shapefile"
    shapefile_dir.mkdir()
    shapefile_path = shapefile_dir / "points.shp"
    gpd.GeoDataFrame(
        {"name": ["sample"]},
        geometry=[Point(77.5946, 12.9716)],
        crs="EPSG:4326",
    ).to_file(shapefile_path)

    archive_path = upload_dir / "points.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in shapefile_dir.iterdir():
            archive.write(path, path.name)

    result = GeospatialProcessor(upload_dir).process(
        file_id="sample",
        filename="points.zip",
        path=archive_path,
    )

    assert result.crs == "EPSG:4326"
    assert len(result.features) == 1
    assert result.features[0].geometry_type == "Point"
    assert result.features[0].properties["name"] == "sample"
    assert "No measurement required" in result.features[0].measurement.message
