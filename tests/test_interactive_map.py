import json
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pytest
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import transform as transform_geometry
from src.context.population import estimate_population_exposed

from src.ui.interactive_map import (
    build_response_map,
    dissolve_geometries,
    geocode_location,
    load_geojson_wgs84,
    parse_polygon_coordinates,
)


ROOT = Path(__file__).resolve().parents[1]
FLOOD_FILE = ROOT / "data/demo/flood/flood_extent.geojson"


def test_coordinate_input_accepts_geojson_and_lon_lat_rings():
    ring = [[85.30, 27.65], [85.32, 27.65], [85.32, 27.67], [85.30, 27.65]]
    assert parse_polygon_coordinates(json.dumps(ring)).is_valid
    assert parse_polygon_coordinates(json.dumps([ring])).is_valid
    feature = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}}
    assert parse_polygon_coordinates(json.dumps(feature)).is_valid


@pytest.mark.parametrize("value", ["not json", "[]", "[[200, 10], [201, 10], [200, 11], [200, 10]]"])
def test_coordinate_input_rejects_invalid_or_out_of_range_polygons(value):
    with pytest.raises(ValueError):
        parse_polygon_coordinates(value)


def test_empty_geojson_layer_dissolves_to_none():
    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    assert dissolve_geometries(empty) is None


def test_location_search_uses_geocoder_and_returns_lat_lon():
    fake = SimpleNamespace(geocode=lambda *_args, **_kwargs: SimpleNamespace(latitude=27.67, longitude=85.32, address="Lalitpur, Nepal"))
    assert geocode_location("Lalitpur", geocoder=fake) == (27.67, 85.32, "Lalitpur, Nepal")


def test_location_search_reports_no_result():
    fake = SimpleNamespace(geocode=lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="No matching place"):
        geocode_location("Somewhere", geocoder=fake)


def _map_data():
    flood = load_geojson_wgs84(FLOOD_FILE)
    geometry = dissolve_geometries(flood)
    return geometry, {
        "roads": load_geojson_wgs84(ROOT / "data/raw/roads.geojson"),
        "hospitals": load_geojson_wgs84(ROOT / "data/raw/hospitals.geojson"),
        "schools": load_geojson_wgs84(ROOT / "data/raw/schools.geojson"),
        "bridges": load_geojson_wgs84(ROOT / "data/raw/bridges.geojson"),
        "destinations": load_geojson_wgs84(ROOT / "data/raw/demo_destinations.geojson"),
    }


def test_project_layers_are_wgs84_and_flood_area_overlaps_road_network():
    geometry, layers = _map_data()
    assert geometry.is_valid
    assert 85.29 < geometry.centroid.x < 85.33
    assert 27.64 < geometry.centroid.y < 27.68
    for frame in layers.values():
        if frame is not None:
            assert frame.crs.to_epsg() == 4326
    roads = layers["roads"]
    assert roads.geometry.intersects(geometry).any()


@pytest.mark.filterwarnings(r"ignore:Use `@` matmul instead of `\*` mul operator:PendingDeprecationWarning")
def test_worldpop_population_raster_overlaps_selected_flood_extent():
    geometry, _ = _map_data()
    estimate = estimate_population_exposed(geometry, ROOT / "data/raw/worldpop_nakhhu.tif")
    assert estimate is not None
    assert estimate > 0


def test_leaflet_map_renders_red_extent_satellite_facility_labels_routes_and_layer_control():
    geometry, layers = _map_data()
    route_crs = layers["roads"].estimate_utm_crs()
    route_wgs84 = LineString([(85.30, 27.65), (85.31, 27.66)])
    to_metric = Transformer.from_crs("EPSG:4326", route_crs, always_xy=True)
    route_metric = transform_geometry(to_metric.transform, route_wgs84)
    route = SimpleNamespace(
        route_id="route-test",
        geometry=route_metric,
        affected_segments=1,
        destination_name="Test Shelter",
        destination_id=str(layers["destinations"].iloc[0]["id"]),
        distance_km=1.4,
    )
    fmap = build_response_map(
        flood_geometry=geometry,
        **layers,
        routes=[route],
        selected_route_id="route-test",
        selected_destination_id=route.destination_id,
        visible={key: True for key in ["affected_area", "roads", "hospitals", "schools", "bridges", "destinations", "routes"]},
        basemap="Satellite imagery",
        route_crs=route_crs,
    )
    document = fmap.get_root().render()
    assert "World_Imagery/MapServer/tile" in document
    assert "#f04444" in document
    assert "Candidate affected area" in document
    assert "Hospitals" in document and "Bridges" in document
    assert "Shree Krishna Higher Secondary School" in document
    assert "Coordinates:" in document
    assert "Test Shelter" in document and "SAFETY NOT VERIFIED" in document
    assert "#20a464" in document
    assert "NOT VERIFIED" in document
    assert f"{geometry.bounds[0]:.6f}" in document
    assert f"{geometry.bounds[1]:.6f}" in document
    assert route_metric.bounds[0] > 1000  # routing backend returns projected meters
    assert "85.3" in document  # Leaflet route is transformed back to longitude/latitude
    assert str(int(route_metric.coords[0][0])) not in document
    assert "layer_control" in document.lower() or "Candidate routes" in document


def test_layer_toggle_hides_facility_features_and_candidate_routes():
    geometry, layers = _map_data()
    visibility = {key: True for key in ["affected_area", "roads", "hospitals", "schools", "bridges", "destinations", "routes"]}
    visibility.update({"hospitals": False, "destinations": False, "routes": False})
    route = SimpleNamespace(route_id="route-hidden", geometry=LineString([(85.30, 27.65), (85.31, 27.66)]), affected_segments=0, destination_name="Hidden Route", distance_km=1.0)
    fmap = build_response_map(flood_geometry=geometry, **layers, routes=[route], selected_route_id=None, visible=visibility, basemap="Street map")
    document = fmap.get_root().render()
    assert layers["hospitals"].iloc[0]["name"] not in document
    assert layers["destinations"].iloc[0]["name"] not in document
    assert "Hidden Route" not in document


def test_candidate_route_layer_toggle_is_independent_of_destination_layer():
    geometry, layers = _map_data()
    destination_id = str(layers["destinations"].iloc[0]["id"])
    route = SimpleNamespace(
        route_id="toggle-route", geometry=LineString([(85.30, 27.65), (85.31, 27.66)]),
        affected_segments=0, destination_name="Toggle route", destination_id=destination_id, distance_km=1.0)
    visible = {"affected_area": True, "roads": True, "hospitals": True, "schools": True,
               "bridges": True, "destinations": True, "routes": False}
    fmap = build_response_map(
        flood_geometry=geometry, **layers, routes=[route], selected_route_id="toggle-route",
        selected_destination_id=destination_id, visible=visible, basemap="Street map")
    document = fmap.get_root().render()
    assert "Shree Krishna Higher Secondary School" in document
    assert "Toggle route" not in document
    assert "Selected route destination" not in document


def test_missing_and_duplicate_facility_labels_are_skipped_and_collapsed():
    geometry, layers = _map_data()
    point = layers["hospitals"].geometry.iloc[0]
    hospitals = gpd.GeoDataFrame(
        {"name": [None, "nan", "City Hospital", "City Hospital"],
         "geometry": [point, point, point, point]}, crs="EPSG:4326")
    fmap = build_response_map(
        flood_geometry=geometry, roads=None, hospitals=hospitals, schools=None,
        bridges=None, destinations=None, routes=[], selected_route_id=None,
        visible={"affected_area": True, "hospitals": True}, basemap="Street map")
    document = fmap.get_root().render()
    assert "City Hospital" in document
    assert document.count("City Hospital") == 3  # one marker label, tooltip, and popup
    assert "facility-label" in document
    assert "nan" not in document


def test_streamlit_entrypoint_renders_leaflet_component_and_dashboard_controls():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45).run()
    assert len(app.exception) == 0
    assert len(app.get("component_instance")) == 1
    assert len(app.checkbox) == 0  # Folium has the single layer and basemap control
    assert len(app.toggle) == 1  # day/night theme
    assert len(app.text_input) == 1  # location search
    assert len(app.text_area) == 1  # polygon coordinates
    assert len(app.selectbox) >= 1  # destination when route candidates are available

    app.toggle[0].set_value(True).run()
    assert len(app.exception) == 0
