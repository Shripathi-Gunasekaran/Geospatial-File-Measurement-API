import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import geopandas as gpd
from pyproj import CRS, Transformer
from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
    shape,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from app.models.schemas import FeatureMeasurement, Measurement


class ProcessingError(Exception):
    """Raised when an uploaded geospatial file cannot be processed."""


@dataclass
class RawFeature:
    feature_id: int
    geometry: BaseGeometry
    properties: dict[str, Any]


@dataclass
class ProcessedFile:
    crs: str | None
    features: list[FeatureMeasurement]


class GeospatialProcessor:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def process(self, file_id: str, filename: str, path: Path) -> ProcessedFile:
        suffix = Path(filename).suffix.lower()
        if suffix == ".zip":
            raw_features, crs = self._read_shapefile_zip(path)
        elif suffix == ".kml":
            raw_features, crs = self._read_kml(path)
        else:
            raise ProcessingError("Unsupported file type.")

        if not raw_features:
            raise ProcessingError("No features were found in the uploaded file.")

        try:
            source_crs = CRS.from_user_input(crs) if crs else CRS.from_epsg(4326)
        except Exception as exc:
            raise ProcessingError(f"Could not interpret CRS '{crs}'.") from exc
        crs_label = source_crs.to_string()

        measured = [
            self._build_feature_measurement(raw_feature, source_crs, crs_label)
            for raw_feature in raw_features
        ]
        return ProcessedFile(crs=crs_label, features=measured)

    def _read_shapefile_zip(self, path: Path) -> tuple[list[RawFeature], str | None]:
        if not zipfile.is_zipfile(path):
            raise ProcessingError("The uploaded .zip file is not a valid zip archive.")

        with tempfile.TemporaryDirectory(dir=self.upload_dir) as tmp_dir:
            with zipfile.ZipFile(path) as archive:
                self._validate_archive_members(archive)
                archive.extractall(tmp_dir)

            shapefiles = list(Path(tmp_dir).rglob("*.shp"))
            if not shapefiles:
                raise ProcessingError("The zip archive must contain a .shp file.")
            if len(shapefiles) > 1:
                raise ProcessingError("The zip archive must contain exactly one Shapefile.")

            return self._read_with_geopandas(shapefiles[0])

    def _read_kml(self, path: Path) -> tuple[list[RawFeature], str | None]:
        try:
            features, crs = self._read_with_geopandas(path)
        except ProcessingError:
            return self._read_kml_with_element_tree(path)
        if features:
            return features, crs
        return self._read_kml_with_element_tree(path)

    def _read_with_geopandas(self, path: Path) -> tuple[list[RawFeature], str | None]:
        try:
            frame = gpd.read_file(path)
        except Exception as exc:
            raise ProcessingError(f"Could not read geospatial file: {exc}") from exc

        crs = frame.crs.to_string() if frame.crs else None
        features: list[RawFeature] = []
        for index, row in frame.iterrows():
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                continue

            properties = row.drop(labels=["geometry"]).to_dict()
            features.append(
                RawFeature(
                    feature_id=len(features) if index is None else int(index),
                    geometry=shape(mapping(geometry)),
                    properties=self._clean_properties(properties),
                )
            )
        return features, crs

    def _read_kml_with_element_tree(self, path: Path) -> tuple[list[RawFeature], str | None]:
        try:
            root = ElementTree.parse(path).getroot()
        except ElementTree.ParseError as exc:
            raise ProcessingError(f"Could not parse KML: {exc}") from exc

        namespace = self._namespace(root.tag)
        placemarks = root.findall(f".//{namespace}Placemark")
        features: list[RawFeature] = []

        for index, placemark in enumerate(placemarks):
            properties = self._kml_properties(placemark, namespace)
            geometries = self._kml_geometries(placemark, namespace)
            for geometry in geometries:
                if geometry.is_empty:
                    continue
                features.append(RawFeature(index, geometry, properties))

        return features, "EPSG:4326"

    def _build_feature_measurement(
        self,
        raw_feature: RawFeature,
        source_crs: CRS,
        crs_label: str,
    ) -> FeatureMeasurement:
        projected = self._project_for_measurement(raw_feature.geometry, source_crs)
        geometry_type = raw_feature.geometry.geom_type

        if isinstance(projected, (Polygon, MultiPolygon)):
            measurement = Measurement(area_square_meters=round(projected.area, 3))
        elif isinstance(projected, (LineString, MultiLineString)):
            measurement = Measurement(length_meters=round(projected.length, 3))
        elif isinstance(projected, (Point, MultiPoint)):
            measurement = Measurement(message="No measurement required for point geometries.")
        else:
            measurement = Measurement(
                message=f"Measurement is not supported for {geometry_type} geometries."
            )

        return FeatureMeasurement(
            feature_id=raw_feature.feature_id,
            geometry_type=geometry_type,
            geometry=mapping(raw_feature.geometry),
            crs=crs_label,
            properties=raw_feature.properties,
            measurement=measurement,
        )

    def _project_for_measurement(self, geometry: BaseGeometry, source_crs: CRS) -> BaseGeometry:
        wgs84_geometry = geometry
        if not source_crs.is_geographic:
            wgs84_transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
            wgs84_geometry = transform(wgs84_transformer.transform, geometry)

        target_crs = self._utm_crs_for_geometry(wgs84_geometry)
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        return transform(transformer.transform, geometry)

    def _utm_crs_for_geometry(self, geometry: BaseGeometry) -> CRS:
        centroid = geometry.centroid
        longitude = centroid.x
        latitude = centroid.y
        zone = int((longitude + 180) // 6) + 1
        zone = max(1, min(zone, 60))
        epsg = 32600 + zone if latitude >= 0 else 32700 + zone
        return CRS.from_epsg(epsg)

    def _validate_archive_members(self, archive: zipfile.ZipFile) -> None:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ProcessingError("The zip archive contains an unsafe file path.")

    def _clean_properties(self, properties: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in properties.items():
            if hasattr(value, "item"):
                value = value.item()
            if value is None:
                clean[key] = None
            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value
            else:
                clean[key] = str(value)
        return clean

    def _namespace(self, tag: str) -> str:
        if tag.startswith("{"):
            return tag.split("}", 1)[0] + "}"
        return ""

    def _kml_properties(self, placemark: ElementTree.Element, namespace: str) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for field in ("name", "description"):
            value = placemark.findtext(f"{namespace}{field}")
            if value:
                properties[field] = value.strip()

        for data in placemark.findall(f".//{namespace}ExtendedData/{namespace}Data"):
            name = data.attrib.get("name")
            value = data.findtext(f"{namespace}value")
            if name and value is not None:
                properties[name] = value

        return properties

    def _kml_geometries(
        self, placemark: ElementTree.Element, namespace: str
    ) -> list[BaseGeometry]:
        geometries: list[BaseGeometry] = []

        for point in placemark.findall(f".//{namespace}Point"):
            coords = self._parse_kml_coordinates(point.findtext(f"{namespace}coordinates"))
            if coords:
                geometries.append(Point(coords[0]))

        for line in placemark.findall(f".//{namespace}LineString"):
            coords = self._parse_kml_coordinates(line.findtext(f"{namespace}coordinates"))
            if len(coords) >= 2:
                geometries.append(LineString(coords))

        for polygon in placemark.findall(f".//{namespace}Polygon"):
            outer = polygon.find(
                f"{namespace}outerBoundaryIs/{namespace}LinearRing/{namespace}coordinates"
            )
            if outer is None:
                continue
            shell = self._parse_kml_coordinates(outer.text)
            holes = [
                self._parse_kml_coordinates(inner.text)
                for inner in polygon.findall(
                    f"{namespace}innerBoundaryIs/{namespace}LinearRing/{namespace}coordinates"
                )
            ]
            if len(shell) >= 4:
                geometries.append(Polygon(shell=shell, holes=[hole for hole in holes if hole]))

        return geometries

    def _parse_kml_coordinates(self, text: str | None) -> list[tuple[float, float]]:
        if not text:
            return []

        coordinates: list[tuple[float, float]] = []
        for token in text.replace("\n", " ").replace("\t", " ").split():
            parts = token.split(",")
            if len(parts) < 2:
                continue
            try:
                coordinates.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        return coordinates
