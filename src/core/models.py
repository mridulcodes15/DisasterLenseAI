from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChangeResult:
    """Output from the satellite/change-detection pipeline."""

    status: str
    hazard: str

    # Spatial information
    change_geometry: Any = None
    affected_area_km2: Optional[float] = None

    # Detection metadata
    pre_date: Optional[str] = None
    post_date: Optional[str] = None
    sensor: Optional[str] = None
    confidence: Optional[float] = None

    # Supporting evidence
    image_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class ContextResult:
    """Geospatial and environmental context for a detected change."""

    population_exposed: Optional[float] = None
    affected_roads: list[Any] = field(default_factory=list)
    affected_bridges: list[Any] = field(default_factory=list)
    affected_hospitals: list[Any] = field(default_factory=list)

    # Supporting environmental context
    weather: dict[str, Any] = field(default_factory=dict)

    # Data sources used for the context analysis
    sources: list[str] = field(default_factory=list)


@dataclass
class PriorityResult:
    """Priority information generated from change + context."""

    hazard: Optional[str] = None
    zones: list[Any] = field(default_factory=list)

    # Priority scores should use a 0-100 scale
    priority_scores: dict[str, float] = field(default_factory=dict)

    confidence: Optional[float] = None
    reasons: dict[str, str] = field(default_factory=dict)


@dataclass
class IncidentReport:
    """Evidence-grounded incident report."""

    summary: str = ""
    priority_zones: list[Any] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: Optional[float] = None