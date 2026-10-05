from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChangeResult:
    """
    Result produced by the satellite change-detection pipeline.
    """

    status: str
    hazard: str
    change_geometry: Any = None
    affected_area_km2: Optional[float] = None
    pre_date: Optional[str] = None
    post_date: Optional[str] = None
    sensor: Optional[str] = None
    confidence: Optional[float] = None
    image_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class ContextResult:
    """
    Geospatial context associated with a detected change.
    """

    population: Optional[float] = None
    roads: list[Any] = field(default_factory=list)
    bridges: list[Any] = field(default_factory=list)
    hospitals: list[Any] = field(default_factory=list)
    weather: Optional[dict[str, Any]] = None
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class PriorityResult:
    """
    Priority assessment for a disaster incident.
    """

    priority_score: float
    priority_level: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class IncidentReport:
    """
    Final incident report combining satellite, context,
    priority, and routing information.
    """

    incident_id: str
    hazard: str
    change: Optional[ChangeResult] = None
    context: Optional[ContextResult] = None
    priority: Optional[PriorityResult] = None
    route: Optional[Any] = None
    summary: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)