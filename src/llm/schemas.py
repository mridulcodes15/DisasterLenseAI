"""Structured output contract and validation for incident reports."""

from typing import Any

from src.core.models import IncidentReport


REPORT_JSON_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "observations": {"type": "ARRAY", "items": {"type": "STRING"}},
        "priority_zones": {"type": "ARRAY", "items": {"type": "STRING"}},
        "uncertainties": {"type": "ARRAY", "items": {"type": "STRING"}},
        "recommendations": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sources": {"type": "ARRAY", "items": {"type": "STRING"}},
        "confidence": {"type": "NUMBER", "nullable": True},
    },
    "required": [
        "summary", "observations", "priority_zones", "uncertainties",
        "recommendations", "sources", "confidence",
    ],
}


def validate_report(value: Any) -> IncidentReport:
    """Validate model output before constructing the shared report contract."""
    if isinstance(value, IncidentReport):
        data = vars(value)
    elif isinstance(value, dict):
        data = value
    else:
        raise ValueError("Report output must be a JSON object.")

    fields = set(REPORT_JSON_SCHEMA["required"])
    if set(data) != fields:
        raise ValueError("Report output has missing or unexpected fields.")

    for name in ("summary",):
        if not isinstance(data[name], str):
            raise ValueError(f"{name} must be a string.")
    for name in ("observations", "priority_zones", "uncertainties", "recommendations", "sources"):
        items = data[name]
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError(f"{name} must be a list of strings.")

    confidence = data["confidence"]
    if confidence is not None and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
    ):
        raise ValueError("confidence must be null or a number between 0 and 1.")

    return IncidentReport(
        summary=data["summary"],
        observations=list(data["observations"]),
        priority_zones=list(data["priority_zones"]),
        uncertainties=list(data["uncertainties"]),
        recommendations=list(data["recommendations"]),
        sources=list(data["sources"]),
        confidence=float(confidence) if confidence is not None else None,
    )
