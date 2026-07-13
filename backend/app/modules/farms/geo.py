"""Geodesic geometry helpers for farm boundaries.

Boundaries are stored as GeoJSON — PostGIS-compatible (convertible with
``ST_GeomFromGeoJSON`` / ``ST_AsGeoJSON``) — and area/perimeter are computed with
closed-form geodesic formulas, so results are correct without a live
PostGIS/SpatiaLite backend and identical under the SQLite-based tests.
"""
from __future__ import annotations

import math

EARTH_RADIUS_M = 6_378_137.0  # WGS-84 semi-major axis
_SQM_PER_HECTARE = 10_000.0
_SQM_PER_ACRE = 4_046.8564224

# A ring is an ordered list of (longitude, latitude) positions.
Ring = list[tuple[float, float]]


class InvalidPolygonError(ValueError):
    """Raised when a GeoJSON polygon is structurally invalid."""


def extract_ring(geojson: dict) -> Ring:
    """Validate a GeoJSON Polygon and return its outer ring as (lng, lat) pairs."""
    if not isinstance(geojson, dict):
        raise InvalidPolygonError("boundary must be a GeoJSON object")
    if geojson.get("type") != "Polygon":
        raise InvalidPolygonError("boundary must be a GeoJSON Polygon")
    coordinates = geojson.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise InvalidPolygonError("polygon has no coordinates")
    outer = coordinates[0]
    if not isinstance(outer, list):
        raise InvalidPolygonError("polygon ring must be a list of positions")

    ring: Ring = []
    for position in outer:
        if not isinstance(position, list | tuple) or len(position) < 2:
            raise InvalidPolygonError("each position needs [lng, lat]")
        lng, lat = float(position[0]), float(position[1])
        if not -180.0 <= lng <= 180.0 or not -90.0 <= lat <= 90.0:
            raise InvalidPolygonError("coordinate out of range")
        ring.append((lng, lat))
    return ring


def _core_vertices(ring: Ring) -> Ring:
    """Drop the closing duplicate and any consecutive duplicate vertices."""
    points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    result: Ring = []
    for point in points:
        if not result or result[-1] != point:
            result.append(point)
    return result


def validate_ring(ring: Ring) -> Ring:
    """Return the distinct, unclosed vertices, or raise if fewer than three."""
    core = _core_vertices(ring)
    if len(core) < 3:
        raise InvalidPolygonError("polygon needs at least 3 distinct points")
    return core


def geodesic_area_sqm(ring: Ring) -> float:
    """Area of the polygon in square metres (spherical excess formula)."""
    core = validate_ring(ring)
    total = 0.0
    n = len(core)
    for i in range(n):
        lng1, lat1 = core[i]
        lng2, lat2 = core[(i + 1) % n]
        total += math.radians(lng2 - lng1) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return abs(total * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0)


def perimeter_m(ring: Ring) -> float:
    """Perimeter of the polygon in metres (sum of haversine edge lengths)."""
    core = validate_ring(ring)
    closed = [*core, core[0]]
    return sum(_haversine_m(closed[i], closed[i + 1]) for i in range(len(closed) - 1))


def centroid(ring: Ring) -> tuple[float, float]:
    """Approximate centroid as (latitude, longitude)."""
    core = validate_ring(ring)
    lat = sum(point[1] for point in core) / len(core)
    lng = sum(point[0] for point in core) / len(core)
    return lat, lng


def vertex_count(ring: Ring) -> int:
    return len(_core_vertices(ring))


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = a
    lng2, lat2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    h = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def sqm_to_hectares(sqm: float) -> float:
    return sqm / _SQM_PER_HECTARE


def sqm_to_acres(sqm: float) -> float:
    return sqm / _SQM_PER_ACRE
