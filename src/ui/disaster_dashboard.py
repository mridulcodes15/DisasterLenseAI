"""Streamlit response dashboard with an interactive Leaflet/Folium map."""

from __future__ import annotations

import json
import csv
import html
import io
import warnings
from pathlib import Path

import geopandas as gpd
import streamlit as st
from shapely.geometry import shape
from streamlit_folium import st_folium

from src.routing.service import build_routes
from .interactive_map import (
    build_response_map,
    dissolve_geometries,
    geocode_location,
    load_geojson_wgs84,
    parse_polygon_coordinates,
)


ROOT = Path(__file__).resolve().parents[2]
FLOOD_FILE = ROOT / "data/demo/flood/flood_extent.geojson"
AOI_FILE = ROOT / "data/demo/flood/aoi.geojson"
ROADS_FILE = ROOT / "data/raw/roads.geojson"
HOSPITALS_FILE = ROOT / "data/raw/hospitals.geojson"
SCHOOLS_FILE = ROOT / "data/raw/schools.geojson"
BRIDGES_FILE = ROOT / "data/raw/bridges.geojson"
DESTINATIONS_FILE = ROOT / "data/raw/demo_destinations.geojson"
POPULATION_FILE = ROOT / "data/raw/worldpop_nakhhu.tif"


@st.cache_data(show_spinner="Loading local response layers…")
def load_project_layers():
    paths = {
        "flood": FLOOD_FILE,
        "aoi": AOI_FILE,
        "roads": ROADS_FILE,
        "hospitals": HOSPITALS_FILE,
        "schools": SCHOOLS_FILE,
        "bridges": BRIDGES_FILE,
        "destinations": DESTINATIONS_FILE,
    }
    loaded = {}
    for key, path in paths.items():
        try:
            loaded[key] = load_geojson_wgs84(path)
        except Exception:
            loaded[key] = None
    return loaded


@st.cache_resource(show_spinner="Building candidate road-network routes…")
def get_route_assessment(geometry_json: str):
    return build_routes(
        flood_geometry=shape(json.loads(geometry_json)),
        roads_file=ROADS_FILE,
        aoi_file=AOI_FILE,
        destinations_file=DESTINATIONS_FILE,
    )


def _area_km2(geometry) -> float:
    return float(gpd.GeoSeries([geometry], crs="EPSG:4326").to_crs(6933).area.iloc[0] / 1_000_000)


def _count_intersections(frame, geometry) -> int | None:
    if frame is None:
        return None
    if frame.empty:
        return 0
    return int(frame.geometry.notna().mul(frame.geometry.intersects(geometry)).sum())


@st.cache_data(show_spinner=False)
def _raster_population_estimate(geometry_json: str) -> float | None:
    from src.context.population import estimate_population_exposed

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Use `@` matmul instead of `\*` mul operator.*",
            category=PendingDeprecationWarning,
        )
        return estimate_population_exposed(shape(json.loads(geometry_json)), POPULATION_FILE)


def _population_estimate(geometry) -> tuple[float | None, str]:
    if not POPULATION_FILE.exists():
        return None, "Population raster is not available."
    try:
        estimate = _raster_population_estimate(json.dumps(geometry.__geo_interface__, separators=(",", ":")))
        if estimate is None:
            return None, "Population raster returned no estimate."
        return estimate, "2025 WorldPop raster proxy · not an event-day count."
    except ValueError as exc:
        if "do not overlap" in str(exc).lower():
            return None, "Population raster does not cover the selected area."
        return None, "Population exposure is unavailable for this geometry."
    except Exception:
        return None, "Population exposure is unavailable for this geometry."


def _metric(label: str, value: str, note: str):
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>",
        unsafe_allow_html=True,
    )


def run_dashboard():
    st.set_page_config(page_title="DisasterLense AI · Flood response", page_icon="🌊", layout="wide", initial_sidebar_state="collapsed")
    night = bool(st.session_state.get("night_mode", False))
    if night:
        bg, panel, text, muted, border = "#101820", "#18232e", "#eef4f7", "#a1b1bd", "#344451"
    else:
        bg, panel, text, muted, border = "#f2f5f6", "#ffffff", "#192832", "#607581", "#d5dfe3"
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
    :root{{--bg:{bg};--panel:{panel};--ink:{text};--muted:{muted};--border:{border};--accent:#167c80}}
    html,body,[class*="css"]{{font-family:'DM Sans',sans-serif}}
    .stApp{{background:var(--bg);color:var(--ink)}}
    [data-testid="stHeader"]{{background:var(--bg)}}
    .block-container{{max-width:1920px;padding:3.5rem 1.1rem .65rem}}
    [data-testid="stMetric"]{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:11px 13px}}
    .brand{{font-size:24px;font-weight:800;letter-spacing:-.7px;color:var(--ink);line-height:1.1}}
    .brand span{{color:#16888b}}
    .kicker{{font:500 10px 'DM Mono',monospace;letter-spacing:1.4px;text-transform:uppercase;color:var(--muted)}}
    .event-title{{font-size:16px;font-weight:700;color:var(--ink);margin:0}}
    .event-meta{{font-size:13px;color:var(--muted);line-height:1.4}}
    .metric-card{{height:78px;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:9px 12px}}
    .metric-label{{font:600 12px 'DM Sans',sans-serif;letter-spacing:.2px;color:var(--muted)}}
    .metric-value{{font-size:24px;line-height:1.1;font-weight:700;color:var(--ink);margin-top:4px;white-space:nowrap}}
    .metric-note{{font-size:11px;line-height:1.3;color:var(--muted);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    .panel-card{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 15px;margin-bottom:11px}}
    .panel-title{{font-size:16px;font-weight:700;color:var(--ink);margin:0 0 7px}}
    .panel-copy{{font-size:13px;line-height:1.45;color:var(--muted)}}
    .panel-copy b{{color:var(--ink)}}
    .alert-box{{border:1px solid #dc994b;background:#fff7e8;border-radius:9px;color:#523d22;padding:8px 10px;font-size:13px;line-height:1.4;margin:6px 0}}
    .status-pill{{display:inline-block;border-radius:99px;background:#fff2d6;color:#79571e;border:1px solid #eccb8b;padding:4px 9px;font:500 10px 'DM Mono',monospace;letter-spacing:.3px}}
    .map-caption{{font:12px 'DM Sans',sans-serif;color:var(--muted);padding:2px 2px 4px}}
    [data-testid="stSidebar"]{{display:none}}
    [data-testid="stSidebarCollapsedControl"]{{display:none}}
    [class*="st-key-intelligence-panel"]{{max-height:580px;overflow-y:auto;padding-right:5px}}
    [data-testid="stRadio"] div[role="radiogroup"]{{gap:.3rem;flex-wrap:nowrap}}
    [data-testid="stRadio"] label{{font-size:13px!important;padding:.15rem .4rem}}
    .pipeline-strip{{border-top:1px solid var(--border);padding:7px 3px 0;font-size:12px;line-height:1.4;color:var(--muted)}}
    div[data-testid="stForm"]{{border:0;padding:0}}
    @media(max-width:1100px){{.block-container{{padding:3.5rem .45rem .65rem}}.metric-card{{height:76px;padding:8px}}.metric-value{{font-size:19px}}.metric-note{{font-size:10px}}}}
    @media(max-width:720px){{[data-testid="stRadio"] div[role="radiogroup"]{{flex-wrap:wrap}}.brand{{font-size:21px}}.panel-copy{{font-size:13px}}}}
    </style>
    """, unsafe_allow_html=True)

    data = load_project_layers()
    missing = [name for name in ["flood", "aoi"] if data.get(name) is None]
    if missing:
        st.error("Required map data is missing: " + ", ".join(missing))
        return
    project_flood = dissolve_geometries(data["flood"])
    aoi_geometry = dissolve_geometries(data["aoi"])
    if project_flood is None or project_flood.is_empty or aoi_geometry is None or aoi_geometry.is_empty:
        st.error("The project flood extent or analysis boundary is empty. Check the local GeoJSON data before starting the dashboard.")
        return
    flood_metadata = data["flood"].iloc[0] if data["flood"] is not None and not data["flood"].empty else {}
    if "custom_polygon" not in st.session_state:
        st.session_state.custom_polygon = None
    if "searched_location" not in st.session_state:
        st.session_state.searched_location = None
    if "location_label" not in st.session_state:
        st.session_state.location_label = "Lalitpur, Nepal"

    header_brand, event_col, search_col, theme_col = st.columns([1.65, 1.8, 4.1, 1.2], vertical_alignment="center")
    with header_brand:
        st.markdown("<div class='brand'>DisasterLense <span>AI</span></div><div class='event-meta'>Flood response intelligence</div>", unsafe_allow_html=True)
    with event_col:
        st.markdown("<div class='event-title'>Bagmati Flood Event</div><div class='event-meta'>Lalitpur District, Nepal · 27 Sep 2024 · Demo / unverified</div>", unsafe_allow_html=True)
    with search_col:
        with st.form("location_search_form", clear_on_submit=False):
            search_cols = st.columns([1, .2])
            address = search_cols[0].text_input("Search place or address", placeholder="Search a place or address", label_visibility="collapsed", key="location_query")
            submitted = search_cols[1].form_submit_button("Find", use_container_width=True)
            if submitted:
                try:
                    st.session_state.searched_location = geocode_location(address)
                    st.session_state.location_label = st.session_state.searched_location[2]
                    st.success(f"Found: {st.session_state.location_label}")
                except Exception as exc:
                    st.warning(f"Location search unavailable: {exc}. The map remains centered on the current area.")
    with theme_col:
        night = st.toggle("Night mode", value=night, key="night_mode")

    section = st.radio(
        "Dashboard sections",
        ["Dashboard", "Change Detection", "Population & Assets", "Risk Assessment", "Routes", "Incident Report", "Export"],
        horizontal=True,
        label_visibility="collapsed",
        key="active_section",
    )

    # Polygon input supports GeoJSON Polygon/MultiPolygon or a JSON lon/lat ring.
    with st.expander("Draw a different affected polygon · paste WGS84 GeoJSON or [longitude, latitude] coordinates", expanded=False):
        with st.form("polygon_form"):
            polygon_text = st.text_area(
                "Polygon coordinates (WGS84 lon, lat)",
                placeholder='Example: [[85.30,27.65],[85.32,27.65],[85.32,27.67],[85.30,27.65]]\nOr paste a GeoJSON Polygon / Feature.',
                height=90,
                label_visibility="collapsed",
                key="polygon_coordinates",
            )
            apply_col, clear_col = st.columns([1, 5])
            apply_polygon = apply_col.form_submit_button("Apply polygon", type="primary")
            clear_polygon = clear_col.form_submit_button("Use candidate satellite extent")
            if apply_polygon:
                try:
                    selected_geometry = parse_polygon_coordinates(polygon_text)
                    st.session_state.custom_polygon = json.dumps(selected_geometry.__geo_interface__)
                    st.success("Valid polygon applied. The red overlay and impact metrics now use this polygon.")
                except ValueError as exc:
                    st.error(str(exc))
            if clear_polygon:
                st.session_state.custom_polygon = None
                st.success("Using the project’s candidate satellite extent again.")

    selected_geometry = shape(json.loads(st.session_state.custom_polygon)) if st.session_state.custom_polygon else project_flood
    custom_selected = st.session_state.custom_polygon is not None
    extent_source = "User-supplied polygon" if custom_selected else "Sentinel‑1 candidate extent"
    selected_geojson = json.dumps(selected_geometry.__geo_interface__, separators=(",", ":"))

    aoi_area = _area_km2(aoi_geometry)
    affected_area = _area_km2(selected_geometry)
    affected_percent = affected_area / aoi_area * 100 if aoi_area > 0 else None
    roads_inside = _count_intersections(data["roads"], selected_geometry)
    hospitals_inside = _count_intersections(data["hospitals"], selected_geometry)
    population, population_note = _population_estimate(selected_geometry)

    values = [
        ("AOI area", f"{aoi_area:.2f} km²", "Project analysis boundary"),
        ("Affected area", f"{affected_area:.3f} km²", extent_source),
        ("Affected AOI", f"{affected_percent:.1f}%" if affected_percent is not None else "Unavailable", "Affected area ÷ AOI area"),
        ("Population exposure", f"{population:,.0f}" if population is not None else "Unavailable", population_note),
        ("Road segments", str(roads_inside) if roads_inside is not None else "Unavailable", "Intersect selected polygon"),
        ("Hospitals", str(hospitals_inside) if hospitals_inside is not None else "Unavailable", "Inside selected polygon"),
    ]
    route_result = None
    if section == "Dashboard":
        try:
            with st.spinner("Preparing candidate routes…"):
                route_result = get_route_assessment(selected_geojson)
        except Exception:
            route_result = None
    routes = route_result.routes if route_result else []
    route_labels = [f"{route.destination_name} · {route.distance_km:.1f} km" for route in routes]

    if section == "Dashboard":
        metric_cols = st.columns(6, gap="small")
        for col, (label, value, note) in zip(metric_cols, values):
            with col:
                _metric(label, value, note)
    elif section in {"Change Detection", "Risk Assessment", "Routes"}:
        return
    elif section == "Population & Assets":
        st.subheader("Population & Assets")
        metric_cols = st.columns(6, gap="small")
        for col, (label, value, note) in zip(metric_cols, values):
            with col:
                _metric(label, value, note)
        st.caption("Exposure describes spatial overlap with the selected candidate polygon; it does not establish damage, access, or service availability.")
        return
    elif section == "Incident Report":
        st.subheader("Incident Report")
        report_text = (
            "Bagmati Flood Event — Lalitpur District, Nepal — 27 September 2024\n\n"
            f"Candidate affected area: {affected_area:.3f} km² ({extent_source}).\n"
            f"Population exposure: {f'{population:,.0f}' if population is not None else 'Unavailable'} ({population_note}).\n"
            f"Road segments intersecting extent: {roads_inside if roads_inside is not None else 'Unavailable'}.\n"
            f"Hospitals inside extent: {hospitals_inside if hospitals_inside is not None else 'Unavailable'}.\n\n"
            "Limitations: extent is a candidate and requires field confirmation; population is a 2025 raster proxy; route and destination conditions are unverified."
        )
        st.text_area("Evidence-based summary", report_text, height=210)
        st.download_button("Download incident summary", report_text, file_name="disasterlense_incident_summary.txt", mime="text/plain")
        return
    elif section == "Export":
        st.subheader("Export")
        geojson_payload = json.dumps({"type": "Feature", "properties": {"provenance": extent_source, "verification_status": "UNVERIFIED CANDIDATE"}, "geometry": selected_geometry.__geo_interface__}, indent=2)
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["metric", "value", "note"])
        for row in values:
            writer.writerow(row)
        st.download_button("Download selected polygon (GeoJSON)", geojson_payload, file_name="candidate_affected_area.geojson", mime="application/geo+json")
        st.download_button("Download impact metrics (CSV)", csv_buffer.getvalue(), file_name="disasterlense_impact_metrics.csv", mime="text/csv")
        st.caption("Exports preserve candidate/unverified provenance. Population exposure uses the 2025 WorldPop raster proxy when available.")
        return

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
    map_col, operations_col = st.columns([2.35, 1], gap="medium", vertical_alignment="top")
    with operations_col:
        with st.container(border=True):
            st.markdown("<div class='panel-title'>Destination & candidate route</div>", unsafe_allow_html=True)
            if routes:
                selected_route_index = st.selectbox("Destination", range(len(routes)), format_func=lambda index: route_labels[index], key="selected_destination")
                selected_route = routes[selected_route_index]
                route_distance = float(selected_route.distance_km)
                route_origin = route_result.origin_label or "AOI centroid (approximate origin)"
                destination_record = None
                if data["destinations"] is not None and "id" in data["destinations"].columns:
                    found = data["destinations"][data["destinations"]["id"].astype(str) == str(selected_route.destination_id)]
                    if not found.empty:
                        destination_record = found.iloc[0]
                destination_type = destination_record.get("historical_classification", "Destination type unavailable") if destination_record is not None else "Destination type unavailable"
                verification = destination_record.get("verification_status", "NOT VERIFIED") if destination_record is not None else "NOT VERIFIED"
                destination_source = destination_record.get("source", "Source unavailable") if destination_record is not None else "Source unavailable"
                route_uncertainty = "Route intersects the candidate affected area; inspection required." if selected_route.affected_segments else "No mapped intersection detected; this is not a safety finding."
                st.markdown(
                    f"<div class='panel-copy'><span class='status-pill'>ROAD-NETWORK CANDIDATE · UNVERIFIED</span><br><br>"
                    f"<b>Destination:</b> {html.escape(str(selected_route.destination_name))} · {html.escape(str(destination_type))}<br>"
                    f"<b>Destination status:</b> {html.escape(str(verification))}<br><b>Source:</b> {html.escape(str(destination_source))}<br>"
                    f"<b>Origin:</b> {html.escape(str(route_origin))}<br><b>Distance:</b> {route_distance:.2f} km<br>"
                    f"<b>Duration:</b> Unavailable (no speed model)<br><b>Provider:</b> Local project road graph<br>"
                    f"<b>Status:</b> {html.escape(str(selected_route.status))}<br><b>Uncertainty:</b> {route_uncertainty}</div>", unsafe_allow_html=True)
            else:
                selected_route = None
                status = route_result.status if route_result else "unavailable"
                st.markdown(f"<div class='panel-copy'>No complete road-network candidate is available.<br><b>Assessment:</b> {status}<br><b>Route distance:</b> unavailable<br><b>Safety:</b> not assessed.</div>", unsafe_allow_html=True)
    with map_col:
        layer_keys = ["affected_area", "roads", "hospitals", "schools", "bridges", "destinations", "routes"]
        visible = {key: True for key in layer_keys}
        basemap = "Satellite imagery"
        st.markdown("<div class='map-caption'>LAYER AND BASEMAP CONTROLS · TOP RIGHT · CLICK A FACILITY LABEL FOR DETAILS</div>", unsafe_allow_html=True)

        fmap = build_response_map(
            flood_geometry=selected_geometry,
            roads=data["roads"],
            hospitals=data["hospitals"],
            schools=data["schools"],
            bridges=data["bridges"],
            destinations=data["destinations"],
            routes=routes,
            selected_route_id=selected_route.route_id if selected_route else None,
            selected_destination_id=selected_route.destination_id if selected_route else None,
            visible=visible,
            basemap=basemap,
            route_crs=data["roads"].estimate_utm_crs() if data["roads"] is not None and not data["roads"].empty else None,
            search_location=st.session_state.searched_location,
            height=580,
        )
        map_state = st_folium(fmap, height=580, use_container_width=True, returned_objects=["last_object_clicked", "bounds"], key="disaster_response_leaflet")
        st.markdown("<div class='map-caption'>Red extent is a candidate, not field-confirmed. Tile layers require internet; use Street map if imagery is unavailable.</div>", unsafe_allow_html=True)

    with operations_col:
      with st.container(key="intelligence-panel"):
        st.markdown(f"<div class='panel-card'><div class='panel-title'>⚠ Risk alerts</div><div class='alert-box'><b>{extent_source}</b><br>Automated flood detection is a candidate only; field confirmation is unavailable.</div><div class='panel-copy'>Roads outside the selected polygon are not thereby confirmed passable. No live closure feed is connected.</div></div>", unsafe_allow_html=True)

        schools_note = "No separate schools GeoJSON file is present." if data["schools"] is None else f"{len(data['schools'])} mapped school features."
        destinations_count = len(data["destinations"]) if data["destinations"] is not None else "Unavailable"
        bridges_count = _count_intersections(data["bridges"], selected_geometry) if data["bridges"] is not None else "Unavailable"
        st.markdown(f"<div class='panel-card'><div class='panel-title'>Infrastructure exposure</div><div class='panel-copy'><b>{roads_inside if roads_inside is not None else 'Unavailable'}</b> road segments intersect polygon<br><b>{hospitals_inside if hospitals_inside is not None else 'Unavailable'}</b> hospitals inside polygon<br><b>{bridges_count}</b> bridges intersect polygon<br><b>{schools_note}</b><br><b>{destinations_count}</b> historical destinations · unverified</div></div>", unsafe_allow_html=True)

        if custom_selected:
            evidence = "<b>Polygon:</b> user-supplied WGS84 coordinates<br><b>Satellite provenance:</b> this geometry is not the stored candidate extent"
        else:
            pre_date = html.escape(str(flood_metadata.get("pre_date", "Unavailable")))
            post_date = html.escape(str(flood_metadata.get("post_date", "Unavailable")))
            confidence_value = flood_metadata.get("confidence", None)
            confidence_note = f"{float(confidence_value):.0%} stored metadata · not calibrated" if confidence_value is not None else "Unavailable"
            evidence = (
                f"<b>Sensor:</b> {html.escape(str(flood_metadata.get('sensor', 'Unavailable')))}<br>"
                f"<b>Comparison:</b> {pre_date} → {post_date}<br>"
                f"<b>Method:</b> {html.escape(str(flood_metadata.get('method', 'Unavailable')))}<br>"
                f"<b>Confidence:</b> {confidence_note}"
            )
        population_provenance = "2025 WorldPop raster · proxy estimate, not a 2024 event-day count" if population is not None else population_note
        st.markdown(f"<div class='panel-card'><div class='panel-title'>Evidence & uncertainty</div><div class='panel-copy'>{evidence}<br><b>Origin:</b> selected extent centroid · approximate and demo only<br><b>Basemap:</b> visual reference; it does not confirm change or passability<br><b>Destinations:</b> historical locations; availability and capacity unknown<br><b>Population:</b> {population_provenance}</div></div>", unsafe_allow_html=True)

    route_status = route_result.status if route_result else "route assessment not run"
    routing_stage = "Demo · local road-network candidate" if routes else f"Warning · {route_status}"
    exposure_stage = "Complete" if any(value is not None for value in [population, roads_inside, hospitals_inside]) else "Warning · unavailable"
    pipeline = (
        "<b>PIPELINE</b> &nbsp; AOI: Complete &nbsp;·&nbsp; Evidence: Demo &nbsp;·&nbsp; "
        f"Change detection: Demo extent &nbsp;·&nbsp; Exposure: {exposure_stage} &nbsp;·&nbsp; "
        f"Prioritisation: Pending &nbsp;·&nbsp; Routing: {routing_stage} &nbsp;·&nbsp; Incident report: Pending"
    )
    st.markdown(f"<div class='pipeline-strip'>{pipeline}<br><b>PROVENANCE</b> &nbsp; flood_extent.geojson · local project roads & facilities · 2025 WorldPop raster proxy · destination status unverified</div>", unsafe_allow_html=True)
