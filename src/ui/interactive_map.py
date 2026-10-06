"""Leaflet map helpers for the DisasterLense response dashboard."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import folium
import geopandas as gpd
import pandas as pd
from pyproj import CRS, Transformer
from geopy.geocoders import Nominatim
from shapely.geometry import Polygon, shape
from shapely.ops import transform as transform_geometry, unary_union


LAYER_STYLES = {
    "affected_area": {"label": "Candidate affected area", "color": "#f04444"},
    "roads": {"label": "Road network", "color": "#2684ff"},
    "hospitals": {"label": "Hospitals", "color": "#25c9e6"},
    "schools": {"label": "Schools", "color": "#9b7bfa"},
    "bridges": {"label": "Bridges", "color": "#ff9f43"},
    "destinations": {"label": "Shelters / destinations", "color": "#52d69a"},
    "routes": {"label": "Candidate routes", "color": "#20a464"},
}


def load_geojson_wgs84(path: str | Path) -> gpd.GeoDataFrame | None:
    """Read a vector layer and normalize it to Leaflet's lon/lat coordinates."""
    source = Path(path)
    if not source.exists():
        return None
    frame = gpd.read_file(source)
    if frame.empty:
        return frame
    if frame.crs is None:
        raise ValueError(f"Layer has no CRS and cannot be safely mapped: {source}")
    return frame.to_crs("EPSG:4326")


def parse_polygon_coordinates(raw: str) -> Polygon | Any:
    """Parse GeoJSON Polygon/MultiPolygon or a lon/lat ring and validate it."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Enter valid JSON containing GeoJSON or a coordinate ring.") from exc

    if isinstance(payload, dict) and payload.get("type") == "Feature":
        payload = payload.get("geometry")
    if isinstance(payload, dict) and payload.get("type") in {"Polygon", "MultiPolygon"}:
        try:
            geometry = shape(payload)
        except Exception as exc:
            raise ValueError("The supplied GeoJSON polygon could not be read.") from exc
    elif isinstance(payload, list):
        try:
            if payload and isinstance(payload[0], (list, tuple)) and payload[0] and isinstance(payload[0][0], (list, tuple)):
                geometry = Polygon(payload[0], payload[1:])
            else:
                geometry = Polygon(payload)
        except Exception as exc:
            raise ValueError("Coordinates must be a list of [longitude, latitude] pairs.") from exc
    else:
        raise ValueError("Expected GeoJSON Polygon/MultiPolygon or a list of [longitude, latitude] pairs.")

    if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty:
        raise ValueError("The selected geometry must be a non-empty Polygon or MultiPolygon.")
    if not geometry.is_valid:
        raise ValueError("Polygon is invalid (for example, its boundary self-intersects). Please correct it.")
    min_x, min_y, max_x, max_y = geometry.bounds
    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise ValueError("Coordinates must be WGS84 longitude/latitude: longitude −180…180, latitude −90…90.")
    if geometry.area == 0:
        raise ValueError("Polygon must enclose an area.")
    return geometry


def geocode_location(query: str, geocoder: Any | None = None) -> tuple[float, float, str]:
    """Resolve an address to (latitude, longitude, display name), when possible."""
    query = query.strip()
    if len(query) < 2:
        raise ValueError("Enter a place or address to search.")
    client = geocoder or Nominatim(user_agent="disasterlense-ai-response-map", timeout=8)
    result = client.geocode(query, exactly_one=True, addressdetails=False)
    if result is None:
        raise ValueError("No matching place was found. Try a nearby town or landmark.")
    latitude, longitude = float(result.latitude), float(result.longitude)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("The location service returned invalid coordinates.")
    return latitude, longitude, str(result.address)


def _safe(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return html.escape(str(value))


def _usable_label(*values: Any, fallback: str = "") -> str:
    for value in values:
        text = _safe(value).strip()
        if text and text.casefold() not in {"nan", "none", "null", "<na>"}:
            return text
    return fallback


def _facility_group(
    fmap: folium.Map,
    frame: gpd.GeoDataFrame | None,
    layer_name: str,
    visible: bool,
    color: str,
    type_label: str,
) -> int:
    if frame is None or frame.empty or not visible:
        return 0
    group = folium.FeatureGroup(name=layer_name, show=True, overlay=True, control=True)
    count = 0
    seen = set()
    for _, row in frame.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        point = geom if geom.geom_type == "Point" else geom.representative_point()
        lat, lon = float(point.y), float(point.x)
        if not (pd.notna(lat) and pd.notna(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        name = _usable_label(row.get("name"), row.get("display_label"), row.get("historical_classification"))
        if not name:
            continue
        display_name = name
        if layer_name == "Shelters / destinations":
            facility_type = _usable_label(row.get("historical_classification"), fallback="Destination")
            display_name = f"{name} · {facility_type}"
        identity = (name.casefold(), round(lat, 6), round(lon, 6))
        if identity in seen:
            continue
        seen.add(identity)
        metadata = [(str(k), _safe(v)) for k, v in row.items() if k != "geometry" and _safe(v)]
        metadata_html = "".join(f"<tr><th>{html.escape(key)}</th><td>{value}</td></tr>" for key, value in metadata)
        popup_html = (
            f"<div style='min-width:220px'><b>{html.escape(type_label)}</b>"
            f"<h4 style='margin:4px 0'>{html.escape(name)}</h4>"
            f"<p style='margin:4px 0'>Coordinates: {lat:.6f}, {lon:.6f}</p>"
            f"<table style='font-size:12px'>{metadata_html}</table></div>"
        )
        folium.CircleMarker(
            [lat, lon],
            radius=6, color="white", weight=2, fill=True, fill_color=color, fill_opacity=1,
            title=name,
            tooltip=folium.Tooltip(html.escape(display_name), permanent=True, direction="right", offset=(8, 0), class_name="facility-label"),
            popup=folium.Popup(popup_html, max_width=400),
        ).add_to(group)
        count += 1
    if count:
        group.add_to(fmap)
    return count


def _add_legend(fmap: folium.Map, counts: dict[str, int]) -> None:
    rows = []
    for key, spec in LAYER_STYLES.items():
        n = counts.get(key)
        if n is None or n <= 0:
            continue
        swatch = (
            f"<span style='display:inline-block;width:18px;height:10px;border-radius:3px;"
            f"background:{spec['color']};opacity:.75'></span>"
            if key != "routes"
            else f"<span style='display:inline-block;width:20px;border-top:4px solid {spec['color']}'></span>"
        )
        rows.append(f"<div class='legend-row'>{swatch}<span>{spec['label']}</span><b>{n}</b></div>")
    legend_html = """
    <style>
    .dl-legend{position:fixed;z-index:999;bottom:26px;left:26px;background:#fff;color:#18242d;
      border:1px solid #d6dee5;border-radius:10px;padding:10px 12px;min-width:205px;
      box-shadow:0 3px 16px #0018;font:12px Arial,sans-serif}
    .dl-legend-title{font-weight:700;font-size:12px;margin-bottom:7px;letter-spacing:.05em}
    .legend-row{display:grid;grid-template-columns:24px 1fr auto;gap:5px;align-items:center;margin:5px 0}
    .leaflet-tooltip.facility-label{white-space:normal;max-width:145px;padding:2px 5px;border:1px solid #b7c4cb;
      border-radius:4px;background:rgba(255,255,255,.88);color:#17212a;font:600 10px Arial,sans-serif;
      box-shadow:0 1px 3px #0015;pointer-events:none}
    @media(max-width:700px){.dl-legend{left:12px;bottom:18px;min-width:170px}.leaflet-tooltip.facility-label{max-width:105px;font-size:9px}}
    </style>
    <div class='dl-legend'><div class='dl-legend-title'>MAP LEGEND</div>
    """ + "".join(rows) + "</div>"
    fmap.get_root().html.add_child(folium.Element(legend_html))


def build_response_map(
    *,
    flood_geometry: Any,
    roads: gpd.GeoDataFrame | None,
    hospitals: gpd.GeoDataFrame | None,
    schools: gpd.GeoDataFrame | None,
    bridges: gpd.GeoDataFrame | None,
    destinations: gpd.GeoDataFrame | None,
    routes: list[Any],
    selected_route_id: str | None,
    visible: dict[str, bool],
    basemap: str,
    route_crs: Any | None = None,
    selected_destination_id: str | None = None,
    search_location: tuple[float, float, str] | None = None,
    height: int = 760,
) -> folium.Map:
    """Create a CRS-normalized Leaflet map with named facility pins and routes."""
    flood_geometry = flood_geometry
    center = flood_geometry.centroid
    fmap = folium.Map(
        location=[center.y, center.x],
        zoom_start=13,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        height=f"{height}px",
    )
    tile_options = {
        "Satellite imagery": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "Esri World Imagery"),
        "Street map": ("OpenStreetMap", "OpenStreetMap contributors"),
        "Night map": ("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", "CARTO"),
    }
    for tile_name, (tile_url, attribution) in tile_options.items():
        folium.TileLayer(tiles=tile_url, attr=attribution, name=tile_name, overlay=False,
                         control=True, show=tile_name == basemap, max_zoom=19).add_to(fmap)

    if visible.get("affected_area", True):
        group = folium.FeatureGroup(name="Candidate affected area", show=True, overlay=True, control=True)
        folium.GeoJson(
            data=flood_geometry.__geo_interface__,
            name="Candidate affected area",
            style_function=lambda _: {"fillColor": "#f04444", "color": "#d20f25", "weight": 3, "fillOpacity": 0.36},
            highlight_function=lambda _: {"weight": 5, "color": "#a50b1d", "fillOpacity": 0.48},
            tooltip="Candidate satellite-detected flood extent · unverified",
        ).add_to(group)
        group.add_to(fmap)

    counts: dict[str, int] = {"affected_area": 1 if visible.get("affected_area", True) else 0}
    if roads is not None and visible.get("roads", True):
        group = folium.FeatureGroup(name="Road network", show=True, overlay=True, control=True)
        folium.GeoJson(
            data=json.loads(roads.to_json(drop_id=True)),
            style_function=lambda _: {"color": "#2684ff", "weight": 1.5, "opacity": 0.72},
            tooltip=folium.GeoJsonTooltip(fields=[c for c in ["name", "highway"] if c in roads.columns], aliases=["Road", "Type"][:len([c for c in ["name", "highway"] if c in roads.columns])]) if any(c in roads.columns for c in ["name", "highway"]) else None,
        ).add_to(group)
        if not roads.empty:
            group.add_to(fmap)
        counts["roads"] = len(roads)
    else:
        counts["roads"] = 0

    counts["hospitals"] = _facility_group(fmap, hospitals, "Hospitals", visible.get("hospitals", True), LAYER_STYLES["hospitals"]["color"], "Hospital")
    counts["schools"] = _facility_group(fmap, schools, "Schools", visible.get("schools", True), LAYER_STYLES["schools"]["color"], "School")
    counts["bridges"] = _facility_group(fmap, bridges, "Bridges", visible.get("bridges", True), LAYER_STYLES["bridges"]["color"], "Bridge")
    counts["destinations"] = _facility_group(fmap, destinations, "Shelters / destinations", visible.get("destinations", True), LAYER_STYLES["destinations"]["color"], "Historical demo shelter · not verified")

    route_count = 0
    selected_route_bounds = []
    if visible.get("routes", True):
        group = folium.FeatureGroup(name="Candidate routes", show=True, overlay=True, control=True)
        rendered_routes = []
        for route in routes:
            geometry = route_geometry_wgs84(getattr(route, "geometry", None), route_crs)
            if geometry is None or geometry.is_empty:
                continue
            affected = bool(getattr(route, "affected_segments", 0))
            selected = getattr(route, "route_id", None) == selected_route_id
            color = "#20a464"
            folium.GeoJson(
                data=geometry.__geo_interface__,
                style_function=lambda _, c=color, s=selected: {"color": c, "weight": 6 if s else 5, "opacity": 0.98},
                tooltip=f"Candidate road-network route · {getattr(route, 'destination_name', 'Destination')} · {getattr(route, 'distance_km', 0):.1f} km · SAFETY NOT VERIFIED",
            ).add_to(group)
            route_count += 1
            rendered_routes.append((route, geometry))
            if selected or selected_route_id is None:
                selected_route_bounds.append(geometry.bounds)
        if rendered_routes:
            first, first_geometry = next(((r, g) for r, g in rendered_routes if getattr(r, "route_id", None) == selected_route_id), rendered_routes[0])
            coords = list(first_geometry.coords) if getattr(first_geometry, "geom_type", None) == "LineString" else []
            if coords:
                origin_lon, origin_lat = coords[0][:2]
                folium.Marker([origin_lat, origin_lon], tooltip=folium.Tooltip("Origin · candidate-extent centroid (approximate; demo)", permanent=True, direction="right", offset=(8, 0), class_name="facility-label"), popup="Approximate origin from candidate-extent centroid, snapped to local road graph. Not a verified pickup point.", icon=folium.Icon(color="red", icon="play")).add_to(group)
            if destinations is not None and selected_destination_id is not None and not destinations.empty:
                id_column = "id" if "id" in destinations.columns else "osm_id" if "osm_id" in destinations.columns else None
                if id_column:
                    selected_rows = destinations[destinations[id_column].astype(str) == str(selected_destination_id)]
                    if not selected_rows.empty:
                        row = selected_rows.iloc[0]
                        point = row.geometry if row.geometry.geom_type == "Point" else row.geometry.representative_point()
                        name = _usable_label(row.get("name"), row.get("display_label"), fallback="Candidate destination")
                        facility_type = _usable_label(row.get("historical_classification"), fallback="Destination")
                        status = _usable_label(row.get("verification_status"), fallback="NOT VERIFIED")
                        metadata = f"{html.escape(name)} · {html.escape(facility_type)} · {html.escape(status)}"
                        folium.CircleMarker(
                            [point.y, point.x],
                            radius=10, color="#16834d", weight=3, fill=True, fill_color="#20a464", fill_opacity=0.25,
                            tooltip=folium.Tooltip(f"Selected route destination · {metadata}", sticky=True),
                            popup=folium.Popup(f"<b>{metadata}</b><br>Coordinates: {point.y:.6f}, {point.x:.6f}<br>Route: road-network candidate; passability unverified", max_width=320),
                        ).add_to(group)
        if route_count:
            group.add_to(fmap)
    counts["routes"] = route_count

    if search_location is not None:
        lat, lon, label = search_location
        folium.Marker([lat, lon], tooltip=label, popup=html.escape(label), icon=folium.Icon(color="purple", icon="search")).add_to(fmap)

    # Fit the selected polygon together with all visible facilities and route endpoints.
    bounds = [flood_geometry.bounds]
    bounds.extend(selected_route_bounds)
    for frame, key in [(hospitals, "hospitals"), (schools, "schools"), (bridges, "bridges"), (destinations, "destinations")]:
        if frame is not None and visible.get(key, True) and not frame.empty:
            frame_bounds = frame.total_bounds
            bounds.append((frame_bounds[0], frame_bounds[1], frame_bounds[2], frame_bounds[3]))
    if search_location is not None:
        search_lat, search_lon, _ = search_location
        bounds.append((search_lon, search_lat, search_lon, search_lat))
    min_x = min(b[0] for b in bounds)
    min_y = min(b[1] for b in bounds)
    max_x = max(b[2] for b in bounds)
    max_y = max(b[3] for b in bounds)
    fmap.fit_bounds([[min_y, min_x], [max_y, max_x]], padding=(22, 22), max_zoom=14)
    _add_legend(fmap, counts)
    folium.LayerControl(collapsed=False, position="topright").add_to(fmap)
    return fmap


def dissolve_geometries(frame: gpd.GeoDataFrame):
    if frame is None or frame.empty or "geometry" not in frame:
        return None
    geometries = [geom for geom in frame.geometry.dropna() if not geom.is_empty]
    return unary_union(geometries) if geometries else None


def route_geometry_wgs84(geometry: Any, source_crs: Any | None = None):
    """Normalize route geometry from the routing graph's projected CRS to lon/lat."""
    if geometry is None or geometry.is_empty:
        return None
    min_x, min_y, max_x, max_y = geometry.bounds
    if min_x >= -180 and max_x <= 180 and min_y >= -90 and max_y <= 90:
        return geometry
    if source_crs is None:
        return None
    transformer = Transformer.from_crs(CRS.from_user_input(source_crs), CRS.from_epsg(4326), always_xy=True)
    normalized = transform_geometry(transformer.transform, geometry)
    min_x, min_y, max_x, max_y = normalized.bounds
    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        return None
    return normalized
