
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union


def _extract_lines(geometry: Any) -> list[LineString]:
    """Extract line components from noded road geometry."""
    if geometry is None or geometry.is_empty:
        return []

    if isinstance(geometry, LineString):
        return [geometry] if len(geometry.coords) >= 2 else []

    if isinstance(geometry, MultiLineString):
        return [
            line
            for line in geometry.geoms
            if not line.is_empty and len(line.coords) >= 2
        ]

    if hasattr(geometry, "geoms"):
        lines = []
        for part in geometry.geoms:
            lines.extend(_extract_lines(part))
        return lines

    return []


def build_road_graph(
    roads_file: str | Path,
    flood_geometry: Any,
) -> nx.Graph:
    """Build a road graph with geometric intersections noded."""
    path = Path(roads_file)

    if not path.exists():
        raise FileNotFoundError(f"Road data not found: {path}")

    if flood_geometry is None or flood_geometry.is_empty:
        raise ValueError("A valid flood geometry is required.")

    roads = gpd.read_file(path)

    if roads.crs is None:
        raise ValueError("Road dataset must have a defined CRS.")

    roads = roads[
        roads.geometry.notna() & ~roads.geometry.is_empty
    ].copy()

    if roads.empty:
        return nx.Graph()

    metric_crs = roads.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Could not determine a projected CRS.")

    roads = roads.to_crs(metric_crs)
    flood = gpd.GeoSeries(
        [flood_geometry], crs="EPSG:4326"
    ).to_crs(metric_crs).iloc[0]

    # Node linework at geometric intersections.
    # This can connect crossings even when the source features
    # do not share the same endpoint.
    noded_roads = unary_union(list(roads.geometry))

    graph = nx.Graph()
    graph.graph["crs"] = str(metric_crs)
    graph.graph["source"] = str(path)

    for segment_id, line in enumerate(_extract_lines(noded_roads)):
        coords = list(line.coords)
        start = tuple(coords[0][:2])
        end = tuple(coords[-1][:2])

        if start == end:
            continue

        intersects_flood = line.intersects(flood)

        graph.add_edge(
            start,
            end,
            route_id=f"road-segment-{segment_id}",
            distance_km=line.length / 1000.0,
            intersects_flood=bool(intersects_flood),
            risk_score=100.0 if intersects_flood else 0.0,
            geometry=line,
            source=str(path),
        )

    return graph
