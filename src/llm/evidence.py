"""Convert backend results into bounded, JSON-safe evidence for the LLM."""

from dataclasses import fields, is_dataclass
from typing import Any


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[truncated]"
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe_value(v, depth=depth + 1) for k, v in list(value.items())[:50]}
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item, depth=depth + 1) for item in list(value)[:50]]
    if is_dataclass(value):
        return {field.name: _safe_value(getattr(value, field.name), depth=depth + 1) for field in fields(value)}
    # Avoid serializing raster masks, geometry internals, or arbitrary objects.
    if hasattr(value, "__geo_interface__"):
        return {"geometry_type": getattr(value, "geom_type", "geometry")}
    return str(value)[:500]


def extract_evidence(
    change_result: Any,
    context_result: Any,
    priority_result: Any = None,
    future_impact: Any = None,
    routing_result: Any = None,
) -> dict[str, Any]:
    """Extract only supplied backend evidence; omit large spatial rasters/geometries."""
    evidence: dict[str, Any] = {}
    for name, result in (
        ("change_detection", change_result),
        ("context", context_result),
        ("priority", priority_result),
        ("future_impact", future_impact),
        ("routing", routing_result),
    ):
        if result is None:
            continue
        converted = _safe_value(result)
        if isinstance(converted, dict):
            converted.pop("change_mask", None)
            converted.pop("change_geometry", None)
            for zone in converted.get("zones", []) if isinstance(converted.get("zones"), list) else []:
                if isinstance(zone, dict):
                    zone.pop("geometry", None)
            for route in converted.get("routes", []) if isinstance(converted.get("routes"), list) else []:
                if isinstance(route, dict):
                    route.pop("geometry", None)
        evidence[name] = converted

    sources: list[str] = []
    for section in evidence.values():
        if isinstance(section, dict) and isinstance(section.get("sources"), list):
            for source in section["sources"]:
                if isinstance(source, str) and source not in sources:
                    sources.append(source)
    evidence["source_catalog"] = sources
    return evidence
