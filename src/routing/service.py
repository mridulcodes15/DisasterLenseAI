
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point

from src.core.models import RouteResult, RoutingResult
from .candidates import build_road_graph


DEFAULT_AOI_FILE = Path("data/demo/flood/aoi.geojson")
DEFAULT_DESTINATIONS_FILE = Path("data/raw/demo_destinations.geojson")

MAX_SNAP_DISTANCE_KM = 2.5


def _nearest_node(
    graph: nx.Graph,
    point: Point,
    max_distance_km: float = MAX_SNAP_DISTANCE_KM,
) -> tuple[Any, float] | None:
    """Snap a point to a nearby road node, within a strict distance limit."""
    if graph.number_of_nodes() == 0:
        return None

    node = min(
        graph.nodes,
        key=lambda candidate: Point(candidate).distance(point),
    )
    distance_km = Point(node).distance(point) / 1000.0

    if distance_km > max_distance_km:
        return None

    return node, distance_km


def _path_geometry(
    graph: nx.Graph,
    path: list[Any],
) -> LineString | None:
    """Join road-edge geometries in path order."""
    coordinates = []

    for start, end in zip(path, path[1:]):
        edge = graph.get_edge_data(start, end)
        if not edge:
            return None

        geometry = edge.get("geometry")
        if geometry is None or geometry.is_empty:
            return None

        parts = (
            list(geometry.geoms)
            if geometry.geom_type == "MultiLineString"
            else [geometry]
        )

        # Road graph edges should normally be single lines.
        # Reject ambiguous multipart edges rather than inventing a join.
        if len(parts) != 1 or parts[0].geom_type != "LineString":
            return None

        coords = list(parts[0].coords)

        if Point(coords[-1]).distance(Point(start)) < Point(coords[0]).distance(Point(start)):
            coords.reverse()

        if Point(coords[0]).distance(Point(start)) > 0.01:
            return None

        if Point(coords[-1]).distance(Point(end)) > 0.01:
            return None

        if coordinates and Point(coordinates[-1]).distance(Point(coords[0])) > 0.01:
            return None

        coordinates.extend(coords if not coordinates else coords[1:])

    if len(coordinates) < 2:
        return None

    return LineString(coordinates)


def _find_path(
    graph: nx.Graph,
    origin_node: Any,
    destination_node: Any,
) -> tuple[list[Any] | None, bool]:
    """Prefer a path avoiding observed flood geometry.

    Returns (path, uses_flood_exposed_fallback).
    """
    dry_edges = [
        (u, v)
        for u, v, data in graph.edges(data=True)
        if not data.get("intersects_flood", False)
    ]
    dry_graph = graph.edge_subgraph(dry_edges)

    try:
        return (
            nx.shortest_path(
                dry_graph,
                source=origin_node,
                target=destination_node,
                weight="distance_km",
            ),
            False,
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass

    try:
        return (
            nx.shortest_path(
                graph,
                source=origin_node,
                target=destination_node,
                weight="distance_km",
            ),
            True,
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, False


def build_routes(
    flood_geometry: Any,
    roads_file: str | Path,
    aoi_file: str | Path = DEFAULT_AOI_FILE,
    destinations_file: str | Path = DEFAULT_DESTINATIONS_FILE,
) -> RoutingResult:
    """Build complete demo evacuation paths to supplied destinations.

    The selected candidate-extent centroid is an approximate demo origin, never
    the user's location or an asserted safe pickup point.
    Historical demo destinations are always marked unverified.
    """
    roads_path = Path(roads_file)
    aoi_path = Path(aoi_file)
    destinations_path = Path(destinations_file)

    sources = [str(roads_path), str(aoi_path), str(destinations_path)]
    warnings = [
        "Origin is the selected candidate-extent centroid, approximate and for demonstration only; it is not a verified pickup point.",
        "All supplied destinations are historical demo locations and are NOT VERIFIED as open or safe.",
        "A road outside the observed flood extent is not guaranteed safe.",
        "Geometric road intersections may incorrectly connect grade-separated roads.",
        "This route is a prototype result, not operational evacuation guidance.",
    ]

    if not aoi_path.exists():
        return RoutingResult(
            status="aoi_unavailable",
            warnings=warnings + [f"AOI file not found: {aoi_path}"],
            sources=sources,
        )

    if not destinations_path.exists():
        return RoutingResult(
            status="destinations_unavailable",
            warnings=warnings + [f"Destination file not found: {destinations_path}"],
            sources=sources,
        )

    aoi = gpd.read_file(aoi_path)
    destinations = gpd.read_file(destinations_path)

    if aoi.empty or aoi.crs is None:
        return RoutingResult(
            status="aoi_invalid",
            warnings=warnings + ["The AOI dataset is empty or has no defined CRS."],
            sources=sources,
        )

    if destinations.empty or destinations.crs is None:
        return RoutingResult(
            status="destinations_invalid",
            warnings=warnings + ["The destination dataset is empty or has no defined CRS."],
            sources=sources,
        )

    if not destinations.geometry.geom_type.isin(["Point"]).all():
        return RoutingResult(
            status="destinations_invalid",
            warnings=warnings + ["Every destination must have Point geometry."],
            sources=sources,
        )

    graph = build_road_graph(
        roads_file=roads_path,
        flood_geometry=flood_geometry,
    )

    if graph.number_of_edges() == 0:
        return RoutingResult(
            status="road_network_unavailable",
            warnings=warnings + ["No usable road edges were found."],
            sources=sources,
        )

    metric_crs = graph.graph.get("crs")
    if not metric_crs:
        return RoutingResult(
            status="road_network_invalid",
            warnings=warnings + ["The road graph does not specify its projected CRS."],
            sources=sources,
        )

    candidate_metric = gpd.GeoSeries([flood_geometry], crs="EPSG:4326").to_crs(metric_crs).iloc[0]
    origin_point = candidate_metric.centroid

    origin_snap = _nearest_node(graph, origin_point)
    if origin_snap is None:
        return RoutingResult(
            status="origin_unconnected",
            warnings=warnings + [
                "No road node is within the permitted snapping distance of the candidate-extent centroid."
            ],
            sources=sources,
        )

    origin_node, origin_snap_km = origin_snap
    destinations_metric = destinations.to_crs(metric_crs)

    routes = []
    unreachable = []
    flood_fallback_used = False

    for index, (_, destination) in enumerate(destinations_metric.iterrows()):
        properties = destination.drop(labels=["geometry"]).to_dict()
        original_properties = destinations.iloc[index].drop(
            labels=["geometry"]
        ).to_dict()

        destination_name = (
            original_properties.get("name")
            or original_properties.get("display_label")
            or f"Demo destination {index + 1}"
        )
        destination_id = str(
            original_properties.get("id")
            or original_properties.get("osm_id")
            or f"demo-destination-{index + 1}"
        )

        destination_point = destination.geometry
        destination_snap = _nearest_node(graph, destination_point)

        if destination_snap is None:
            unreachable.append(
                f"{destination_name}: no road node within "
                f"{MAX_SNAP_DISTANCE_KM:.1f} km."
            )
            continue

        destination_node, destination_snap_km = destination_snap

        path, used_flood_fallback = _find_path(
            graph,
            origin_node,
            destination_node,
        )

        if path is None:
            unreachable.append(
                f"{destination_name}: no connected road path from the demo origin."
            )
            continue

        geometry = _path_geometry(graph, path)
        if geometry is None:
            unreachable.append(
                f"{destination_name}: route geometry could not be assembled reliably."
            )
            continue

        path_edges = [
            graph.get_edge_data(u, v)
            for u, v in zip(path, path[1:])
        ]

        if any(edge is None for edge in path_edges):
            unreachable.append(
                f"{destination_name}: incomplete road-edge data."
            )
            continue

        affected_edges = [
            edge for edge in path_edges
            if edge.get("intersects_flood", False)
        ]
        affected_segments = len(affected_edges)
        distance_km = sum(
            float(edge.get("distance_km", 0.0))
            for edge in path_edges
        )

        # Transparent heuristic: proportion of route distance on
        # flood-intersecting road edges. This is not a calibrated safety score.
        affected_distance_km = sum(
            float(edge.get("distance_km", 0.0))
            for edge in affected_edges
        )
        risk_score = (
            min(100.0, 100.0 * affected_distance_km / distance_km)
            if distance_km > 0
            else 100.0
        )

        route_warnings = [
            "Destination is a historical demo location, NOT VERIFIED as open or safe."
        ]
        reasons = []

        if affected_segments:
            reasons.append(
                f"{affected_segments} road segment(s) intersect the observed flood extent."
            )
            route_warnings.append(
                "The calculated fallback path crosses observed flood geometry; do not treat it as safe."
            )
        else:
            reasons.append(
                "No route edge intersects the supplied observed flood extent."
            )

        if used_flood_fallback:
            flood_fallback_used = True
            reasons.append(
                "No fully flood-avoiding path was found; shortest connected path used as fallback."
            )

        if origin_snap_km > 0.1:
            route_warnings.append(
                f"Demo origin was snapped {origin_snap_km:.2f} km to the nearest road node."
            )

        if destination_snap_km > 0.1:
            route_warnings.append(
                f"Destination was snapped {destination_snap_km:.2f} km to the nearest road node."
            )

        route_warnings.append(
            "The road graph may contain false connections at grade-separated crossings."
        )

        routes.append(
            RouteResult(
                route_id=f"demo-route-{destination_id}",
                distance_km=distance_km + origin_snap_km + destination_snap_km,
                affected_segments=affected_segments,
                risk_score=risk_score,
                reasons=reasons,
                geometry=geometry,
                destination_id=destination_id,
                destination_name=str(destination_name),
                status=(
                    "flood_exposed_demo_unverified"
                    if affected_segments
                    else "demo_unverified"
                ),
                warnings=route_warnings,
            )
        )

    if unreachable:
        warnings.extend(unreachable)

    if flood_fallback_used:
        warnings.append(
            "At least one destination required a fallback path crossing flood-intersecting roads."
        )

    if not routes:
        return RoutingResult(
            status="no_connected_routes",
            routes=[],
            origin_label="Candidate-extent centroid (approximate; demo only)",
            destination_available=True,
            warnings=warnings + [
                "No complete route could be assembled. No route has been fabricated."
            ],
            sources=sources,
        )

    routes.sort(
        key=lambda route: (
            route.affected_segments > 0,
            route.risk_score,
            route.distance_km,
        )
    )

    return RoutingResult(
        status="routes_found",
        routes=routes,
        origin_label="Candidate-extent centroid (approximate; demo only)",
        destination_available=True,
        warnings=warnings,
        sources=sources,
    )
