from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from src.core.models import RoutingResult
from src.routing.service import build_routes


ROOT = Path(__file__).resolve().parents[1]
FLOOD_FILE = ROOT / "data/demo/flood/flood_extent.geojson"
ROADS_FILE = ROOT / "data/raw/roads.geojson"
AOI_FILE = ROOT / "data/demo/flood/aoi.geojson"
DESTINATIONS_FILE = ROOT / "data/raw/demo_destinations.geojson"


@pytest.fixture(scope="module")
def routing_result():
    flood_data = gpd.read_file(FLOOD_FILE)
    flood_geometry = unary_union(
        list(flood_data.geometry.dropna())
    )

    return build_routes(
        flood_geometry=flood_geometry,
        roads_file=ROADS_FILE,
        aoi_file=AOI_FILE,
        destinations_file=DESTINATIONS_FILE,
    )


def test_routing_returns_result(routing_result):
    assert isinstance(routing_result, RoutingResult)
    assert routing_result.status == "routes_found"
    assert routing_result.destination_available is True
    assert len(routing_result.routes) > 0


def test_routes_have_connected_line_geometry(routing_result):
    for route in routing_result.routes:
        assert isinstance(route.geometry, LineString)
        assert route.geometry.is_valid
        assert route.distance_km > 0


def test_routes_disclose_unverified_destinations(routing_result):
    assert "candidate-extent centroid" in routing_result.origin_label.casefold()
    for route in routing_result.routes:
        assert route.status == "demo_unverified"
        assert any(
            "NOT VERIFIED" in warning
            for warning in route.warnings
        )


def test_route_warnings_do_not_claim_safety(routing_result):
    assert any(
        "not guaranteed safe" in warning.lower()
        or "not operational evacuation guidance" in warning.lower()
        for warning in routing_result.warnings
    )


def test_missing_destination_file_returns_unavailable():
    result = build_routes(
        flood_geometry=None,
        roads_file=ROADS_FILE,
        aoi_file=AOI_FILE,
        destinations_file=ROOT / "data/raw/file_that_does_not_exist.geojson",
    )

    assert result.status == "destinations_unavailable"
    assert result.destination_available is False
    assert result.routes == []
