
from typing import Any


def calculate_route_risk(candidate: dict[str, Any]) -> tuple[float, list[str]]:
    """Calculate a transparent heuristic risk score from observed geometry."""
    geometry = candidate.get("geometry")

    if geometry is None or geometry.is_empty:
        raise ValueError("Road candidate must contain valid geometry.")

    score = 0.0
    reasons = []

    if candidate.get("intersects_flood", False):
        score += 100.0
        reasons.append("Road geometry intersects the observed flood extent")
    else:
        reasons.append("No intersection with the observed flood extent detected")

    return min(score, 100.0), reasons
