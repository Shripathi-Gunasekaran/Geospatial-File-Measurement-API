from pyproj import CRS
from shapely.geometry import LineString, Point, Polygon

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
