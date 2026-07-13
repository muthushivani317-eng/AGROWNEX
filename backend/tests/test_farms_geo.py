"""Unit tests for the farm geometry helpers (pure, no DB)."""
from __future__ import annotations

import math

import pytest
from app.modules.farms.geo import (
    InvalidPolygonError,
    centroid,
    extract_ring,
    geodesic_area_sqm,
    perimeter_m,
    sqm_to_hectares,
    validate_ring,
    vertex_count,
)


def _square(side_deg: float, lat0: float = 0.0, lng0: float = 0.0) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lng0, lat0],
                [lng0 + side_deg, lat0],
                [lng0 + side_deg, lat0 + side_deg],
                [lng0, lat0 + side_deg],
                [lng0, lat0],  # closed ring
            ]
        ],
    }


def test_extract_ring_rejects_non_polygon():
    with pytest.raises(InvalidPolygonError):
        extract_ring({"type": "Point", "coordinates": [0, 0]})


def test_extract_ring_rejects_out_of_range_coord():
    with pytest.raises(InvalidPolygonError):
        extract_ring({"type": "Polygon", "coordinates": [[[200, 0], [1, 0], [1, 1]]]})


def test_validate_ring_requires_three_distinct_points():
    with pytest.raises(InvalidPolygonError):
        validate_ring([(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)])


def test_vertex_count_ignores_closing_point():
    ring = extract_ring(_square(0.001))
    assert vertex_count(ring) == 4


def test_area_of_small_square_matches_expected():
    # A ~0.01° square near the equator. One degree of latitude ≈ 111.32 km, and
    # longitude ≈ 111.32 km * cos(lat) (≈1 at the equator), so area ≈ (1113.2 m)².
    ring = extract_ring(_square(0.01))
    sqm = geodesic_area_sqm(ring)
    side_m = math.radians(0.01) * 6_378_137.0
    expected = side_m * side_m
    # Within 1% of the planar approximation at the equator.
    assert abs(sqm - expected) / expected < 0.01
    assert sqm_to_hectares(sqm) == pytest.approx(sqm / 10_000.0)


def test_perimeter_of_square_is_four_sides():
    ring = extract_ring(_square(0.01))
    side_m = math.radians(0.01) * 6_378_137.0
    assert perimeter_m(ring) == pytest.approx(4 * side_m, rel=0.01)


def test_centroid_of_square_is_center():
    ring = extract_ring(_square(0.02, lat0=10.0, lng0=78.0))
    lat, lng = centroid(ring)
    assert lat == pytest.approx(10.01, abs=1e-6)
    assert lng == pytest.approx(78.01, abs=1e-6)
