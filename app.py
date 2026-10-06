"""DisasterLense AI — local, evidence-led flood response map demo."""

# The active application lives in the Leaflet dashboard module. Keep this
# legacy implementation below for reference while the redesigned app runs.
from src.ui.disaster_dashboard import run_dashboard
import streamlit as st

run_dashboard()
st.stop()

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st
from shapely.geometry import mapping
from shapely.ops import unary_union

from src.routing.service import build_routes

ROOT = Path(__file__).resolve().parent
FLOOD_FILE = ROOT / "data/demo/flood/flood_extent.geojson"
AOI_FILE = ROOT / "data/demo/flood/aoi.geojson"
ROADS_FILE = ROOT / "data/raw/roads.geojson"
HOSPITALS_FILE = ROOT / "data/raw/hospitals.geojson"
BRIDGES_FILE = ROOT / "data/raw/bridges.geojson"
DESTINATIONS_FILE = ROOT / "data/raw/demo_destinations.geojson"
POPULATION_FILE = ROOT / "data/demo/flood/population.tif"
DEM_FILE = ROOT / "data/raw/copernicus_dem_nakhhu.tif"

st.set_page_config(page_title="DisasterLense AI | Response map", page_icon="🌊", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&display=swap');
:root { --ink:#e8edf4; --muted:#8c9bad; --panel:#111923; --line:#263442; --cyan:#66e0d1; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:#0a1017; color:var(--ink); }
[data-testid="stHeader"] { background:#0a1017; }
[data-testid="stSidebar"] { background:#0e151e; border-right:1px solid var(--line); }
.block-container { padding:1.7rem 2.3rem 2rem; max-width:1700px; }
.brand { color:var(--cyan); font:500 12px 'DM Mono',monospace; letter-spacing:2.1px; }
.eyebrow { color:var(--muted); font:500 10px 'DM Mono',monospace; letter-spacing:1.7px; text-transform:uppercase; }
.hero-title { font-size:30px; font-weight:700; letter-spacing:-1px; color:var(--ink); margin:5px 0 1px; }
.hero-sub { color:var(--muted); font-size:13px; margin:0 0 16px; }
.pill { display:inline-block; padding:5px 10px; border-radius:99px; border:1px solid #78603b; background:#302718; color:#ffd18a; font:500 10px 'DM Mono',monospace; letter-spacing:.7px; }
.metric { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:13px 15px; min-height:81px; }
.metric-label { color:var(--muted); font:500 10px 'DM Mono',monospace; letter-spacing:1px; text-transform:uppercase; }
.metric-value { color:var(--ink); font-size:22px; font-weight:700; margin-top:5px; }
.metric-note,.small { color:var(--muted); font-size:11px; line-height:1.55; }
.section-head { color:var(--ink); font-size:14px; font-weight:700; margin:0; }
.map-shell { border:1px solid var(--line); border-radius:11px; overflow:hidden; background:#111923; }
.map-note { color:var(--muted); font-size:11px; padding:9px 12px; border-top:1px solid var(--line); }
.notice { border:1px solid #604b2c; background:#211d16; color:#e5c894; padding:12px 14px; border-radius:9px; font-size:12px; line-height:1.6; }
.info-card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }
.mono { font-family:'DM Mono',monospace; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading response map layers…")
def load_layers():
    layers = {}
    for key, path in {"flood": FLOOD_FILE, "aoi": AOI_FILE, "roads": ROADS_FILE, "hospitals": HOSPITALS_FILE, "bridges": BRIDGES_FILE, "destinations": DESTINATIONS_FILE}.items():
        if path.exists():
            layers[key] = gpd.read_file(path)
    return layers

def fc(gdf, color=None):
    features = []
    for _, row in gdf.iterrows():
        props = {str(k): str(v) if pd.notna(v) else "" for k, v in row.items() if k != "geometry"}
        if color:
            props["_color"] = color
        features.append({"type": "Feature", "geometry": mapping(row.geometry), "properties": props})
    return {"type": "FeatureCollection", "features": features}

def one_geom(geometry, color):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": mapping(geometry), "properties": {"_color": color}}]}

def metric(label, value, note=""):
    st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

missing = [p.name for p in [FLOOD_FILE, AOI_FILE, ROADS_FILE] if not p.exists()]
if missing:
    st.error("Required demo data is missing: " + ", ".join(missing))
    st.stop()

data = load_layers()
flood_geom = unary_union(list(data["flood"].geometry.dropna()))
aoi_geom = unary_union(list(data["aoi"].geometry.dropna()))
flood_properties = data["flood"].iloc[0]
area_km2 = gpd.GeoSeries([flood_geom], crs=data["flood"].crs).to_crs(6933).area.iloc[0] / 1_000_000
center = flood_geom.centroid

def intersecting_count(key):
    frame = data.get(key)
    if frame is None or frame.empty:
        return 0
    geometry = gpd.GeoSeries([flood_geom], crs=data["flood"].crs).to_crs(frame.crs).iloc[0]
    return int(frame.geometry.notna().mul(frame.geometry.intersects(geometry)).sum())

affected_roads = intersecting_count("roads")
affected_hospitals = intersecting_count("hospitals")
affected_bridges = intersecting_count("bridges")
population_exposed = None
terrain_stats = {}
try:
    if POPULATION_FILE.exists():
        from src.context.population import estimate_population_exposed
        population_exposed = estimate_population_exposed(flood_geom, POPULATION_FILE)
except Exception:
    pass
try:
    if DEM_FILE.exists():
        from src.context.terrain import analyze_terrain
        terrain_stats = analyze_terrain(flood_geom, DEM_FILE)
except Exception:
    pass

with st.sidebar:
    st.markdown('<div class="brand">◉ DISASTERLENSE <span style="color:#e8edf4">AI</span></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div><div class='eyebrow'>INCIDENT WORKSPACE</div>", unsafe_allow_html=True)
    st.markdown("### Bagmati flood event")
    st.caption("Lalitpur District · Nepal")
    st.markdown("---")
    st.markdown('<div class="eyebrow">MAP LAYERS</div>', unsafe_allow_html=True)
    show_flood = st.checkbox("Candidate flood extent", True)
    show_roads = st.checkbox("Road network", True)
    show_hospitals = st.checkbox("Hospitals", True)
    show_bridges = st.checkbox("Bridges", True)
    show_destinations = st.checkbox("Demo destinations", True)
    show_aoi = st.checkbox("Analysis boundary", False)
    st.markdown("---")
    st.markdown('<div class="eyebrow">DATA SNAPSHOT</div><div class="small"><br>Sentinel‑1 · 27 Sep 2024<br>Prototype layers · local project data</div>', unsafe_allow_html=True)

st.markdown('<div class="brand">RESPONSE INTELLIGENCE / FIELD OVERVIEW</div>', unsafe_allow_html=True)
left, right = st.columns([4, 1], vertical_alignment="center")
with left:
    st.markdown('<div class="hero-title">Flood impact & access</div><div class="hero-sub">Lalitpur, Bagmati Province · 27 September 2024 event</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div style="text-align:right"><span class="pill">● &nbsp;DEMO · UNVERIFIED</span></div>', unsafe_allow_html=True)
m1, m2, m3, m4, m5 = st.columns(5, gap="small")
with m1: metric("Candidate extent", f"{area_km2:.2f} km²", "Mapped polygon area")
with m2: metric("People in extent", f"{population_exposed:,.0f}" if population_exposed is not None else "Unavailable", "Population raster does not cover AOI" if population_exposed is None else "Raster estimate · not a census")
with m3: metric("Road segments", f"{affected_roads:,}", "Intersect candidate extent")
with m4: metric("Hospitals / bridges", f"{affected_hospitals} / {affected_bridges}", "Inside candidate extent")
with m5: metric("Extent confidence", f"{float(flood_properties.get('confidence', 0)):.0%}", "Metadata · not field verified")
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
map_col, side_col = st.columns([2.25, 1], gap="medium")

with side_col:
    st.markdown('<div class="eyebrow">ACCESS ASSESSMENT</div><p class="section-head">Candidate routes</p>', unsafe_allow_html=True)
    routes_result = None
    try:
        with st.spinner("Assessing candidate access routes…"):
            routes_result = build_routes(flood_geometry=flood_geom, roads_file=ROADS_FILE, aoi_file=AOI_FILE, destinations_file=DESTINATIONS_FILE)
    except Exception as exc:
        st.warning(f"Route assessment unavailable: {exc}")
    routes = routes_result.routes if routes_result else []
    selected_route = None
    if routes:
        labels = [f"{r.destination_name} · {r.distance_km:.1f} km" for r in routes]
        index = st.selectbox("Destination", range(len(routes)), format_func=lambda i: labels[i], label_visibility="collapsed")
        selected_route = routes[index]
        st.markdown(f"<div class='info-card'><div class='eyebrow'>ROUTE STATUS</div><div style='font-size:17px;font-weight:700;margin:6px 0'>{selected_route.distance_km:.1f} km <span style='font-size:12px;color:#8c9bad'>candidate route</span></div><div class='small'>From {routes_result.origin_label}<br>{selected_route.affected_segments} segment(s) intersect candidate flood extent</div></div>", unsafe_allow_html=True)
        if selected_route.affected_segments:
            st.warning("This route intersects mapped flood geometry. Do not use for navigation.")
        else:
            st.info("No mapped flood intersection detected. This does not establish safety.")
    else:
        st.info("No connected demo routes are available for the current data.")
    elevation_note = f"Mean elevation: {terrain_stats['mean_elevation_m']:.0f} m (DEM)" if terrain_stats.get("mean_elevation_m") is not None else "Terrain estimate unavailable"
    st.markdown(f'<div class="eyebrow">SITUATION NOTES</div><div class="info-card small"><b style="color:#e8edf4">Satellite change candidate</b><br>Sentinel‑1 backscatter decrease, 20 → 27 Sep 2024. Automated extent needs review before operational use.<br><br><b style="color:#e8edf4">Exposure context</b><br>{elevation_note}. Population is a raster estimate.<br><br><b style="color:#e8edf4">Destination provenance</b><br>Historical demo locations. Current opening status, capacity and safety are unknown.</div>', unsafe_allow_html=True)

with map_col:
    st.markdown('<div class="eyebrow">GEOSPATIAL OVERVIEW</div>', unsafe_allow_html=True)
    layers = []
    if show_aoi:
        layers.append(pdk.Layer("GeoJsonLayer", data=one_geom(aoi_geom, [90,110,130,35]), stroked=True, filled=True, get_fill_color="properties._color", get_line_color=[140,158,180,160], line_width_min_pixels=1, get_line_width=1))
    if show_roads:
        layers.append(pdk.Layer("GeoJsonLayer", data=fc(data["roads"]), stroked=True, filled=False, get_line_color=[111,132,151,130], line_width_min_pixels=1, get_line_width=1))
    if show_flood:
        layers.append(pdk.Layer("GeoJsonLayer", data=fc(data["flood"], [239,91,86,100]), stroked=True, filled=True, get_fill_color="properties._color", get_line_color=[255,111,100,220], line_width_min_pixels=1.5, get_line_width=2, pickable=True, auto_highlight=True))
    if show_hospitals and "hospitals" in data:
        layers.append(pdk.Layer("GeoJsonLayer", data=fc(data["hospitals"]), filled=True, point_type="circle", get_point_radius=70, point_radius_min_pixels=5, get_fill_color=[103,206,255,245], stroked=True, get_line_color=[8,24,35,255], line_width_min_pixels=1, pickable=True, auto_highlight=True))
    if show_bridges and "bridges" in data:
        layers.append(pdk.Layer("GeoJsonLayer", data=fc(data["bridges"]), filled=True, point_type="circle", get_point_radius=65, point_radius_min_pixels=5, get_fill_color=[255,184,91,255], stroked=True, get_line_color=[45,30,12,255], line_width_min_pixels=1, pickable=True, auto_highlight=True))
    if show_destinations and "destinations" in data:
        layers.append(pdk.Layer("GeoJsonLayer", data=fc(data["destinations"]), filled=True, point_type="circle", get_point_radius=95, point_radius_min_pixels=7, get_fill_color=[111,231,183,255], stroked=True, get_line_color=[8,34,28,255], line_width_min_pixels=1, pickable=True, auto_highlight=True))
    if selected_route is not None:
        color = [255,188,80,255] if selected_route.affected_segments else [102,224,209,255]
        layers.append(pdk.Layer("GeoJsonLayer", data=one_geom(selected_route.geometry, color), stroked=True, filled=False, get_line_color="properties._color", line_width_min_pixels=4, get_line_width=5))
    deck = pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=float(center.y), longitude=float(center.x), zoom=12.7, pitch=0, bearing=0), map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json", tooltip={"html":"<b>{name}</b><br/>{display_label}<br/>{verification_status}","style":{"backgroundColor":"#111923","color":"#e8edf4","fontSize":"12px"}})
    st.markdown('<div class="map-shell">', unsafe_allow_html=True)
    st.pydeck_chart(deck, use_container_width=True, height=520, key="response_map")
    st.markdown('<div class="map-note">Prototype layers only. Route lines use the AOI centroid; road and destination conditions are not live verified.</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
warn_col, source_col = st.columns([1.3, 1], gap="medium")
with warn_col:
    st.markdown('<div class="notice"><b>⚠ &nbsp;Operational caution</b><br>Candidate extent may include classification error. Destinations are historical and unverified; roads outside mapped flood geometry are not guaranteed passable. This prototype is not operational evacuation guidance.</div>', unsafe_allow_html=True)
with source_col:
    st.markdown('<div class="info-card small"><span class="eyebrow">DATA PROVENANCE</span><br><br><b style="color:#e8edf4">Flood extent:</b> Sentinel‑1 change detection · 27 Sep 2024<br><b style="color:#e8edf4">Roads, hospitals, bridges:</b> local project GeoJSON<br><b style="color:#e8edf4">Destinations:</b> historical demo locations · unverified<br><b style="color:#e8edf4">Route origin:</b> AOI centroid · demonstration only</div>', unsafe_allow_html=True)
