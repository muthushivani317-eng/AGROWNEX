from __future__ import annotations

import math
from typing import Any

MAX_AOI_VERTICES = 500
MAX_AOI_SPAN_DEGREES = 2.0


class AoiValidationError(ValueError):
    pass


def _ring(value: Any, *, vertices: list[list[float]]) -> list[list[float]]:
    if not isinstance(value, list) or len(value) < 4:
        raise AoiValidationError("AOI_RING_INVALID")
    normalized: list[list[float]] = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise AoiValidationError("AOI_COORDINATE_INVALID")
        lon, lat = point
        if (
            isinstance(lon, bool)
            or isinstance(lat, bool)
            or not all(isinstance(item, int | float) and math.isfinite(item) for item in (lon, lat))
        ):
            raise AoiValidationError("AOI_COORDINATE_INVALID")
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise AoiValidationError("AOI_COORDINATE_OUT_OF_BOUNDS")
        normalized.append([float(lon), float(lat)])
    if normalized[0] != normalized[-1]:
        raise AoiValidationError("AOI_RING_NOT_CLOSED")
    if len({tuple(point) for point in normalized[:-1]}) < 3:
        raise AoiValidationError("AOI_RING_DEGENERATE")
    vertices.extend(normalized[:-1])
    return normalized


def normalize_aoi(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - {"type", "coordinates"}:
        raise AoiValidationError("AOI_GEOJSON_INVALID")
    geometry_type = value.get("type")
    coordinates = value.get("coordinates")
    vertices: list[list[float]] = []
    if geometry_type == "Polygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise AoiValidationError("AOI_POLYGON_INVALID")
        normalized = [_ring(ring, vertices=vertices) for ring in coordinates]
    elif geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise AoiValidationError("AOI_MULTIPOLYGON_INVALID")
        normalized = []
        for polygon in coordinates:
            if not isinstance(polygon, list) or not polygon:
                raise AoiValidationError("AOI_MULTIPOLYGON_INVALID")
            normalized.append([_ring(ring, vertices=vertices) for ring in polygon])
    else:
        raise AoiValidationError("AOI_GEOMETRY_UNSUPPORTED")
    if len(vertices) > MAX_AOI_VERTICES:
        raise AoiValidationError("AOI_VERTEX_LIMIT_EXCEEDED")
    longitudes = [point[0] for point in vertices]
    latitudes = [point[1] for point in vertices]
    if (
        max(longitudes) - min(longitudes) > MAX_AOI_SPAN_DEGREES
        or max(latitudes) - min(latitudes) > MAX_AOI_SPAN_DEGREES
    ):
        raise AoiValidationError("AOI_SIZE_LIMIT_EXCEEDED")
    return {"type": geometry_type, "coordinates": normalized}
