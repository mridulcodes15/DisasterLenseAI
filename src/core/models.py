from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DisasterRequest:
    """Input request for a disaster analysis."""

    disaster_type: str
    latitude: float
    longitude: float
    radius_km: float
    event_date: str


@dataclass
class ChangeResult:
    """Output from the satellite/change-detection pipeline."""

    status: str
    disaster_type: str

    # Temporal comparison
    pre_date: Optional[str] = None
    post_date: Optional[str] = None
    sensor: Optional[str] = None

    # Spatial information
    change_mask: Any = None
    change_geometry: Any = None
    affected_area_km2: Optional[float] = None

    # Detection severity and confidence
    severity: Optional[float] = None
    confidence: Optional[float] = None

    # Supporting evidence
    image_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class ContextResult:
    """Geospatial, population, infrastructure and environmental context."""

    # Spatial impact
    aoi_area_km2: Optional[float] = None
    affected_area_km2: Optional[float] = None
    affected_percentage: Optional[float] = None

    # Population exposure
    population_exposed: Optional[float] = None

    affected_roads: list[Any] = field(default_factory=list)
    affected_bridges: list[Any] = field(default_factory=list)
    affected_hospitals: list[Any] = field(default_factory=list)

    # Environmental context
    weather: dict[str, Any] = field(default_factory=dict)
    terrain: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)

    # Supporting data sources
    sources: list[str] = field(default_factory=list)

@dataclass
class PriorityZone:
    """A spatial zone ranked for emergency response priority."""

    zone_id: str
    geometry: Any = None

    # 0-100 priority score
    priority_score: float = 0.0

    confidence: float = 0.0

    population_exposed: float = 0.0
    infrastructure_count: int = 0

    # Human-readable explanation
    reasons: list[str] = field(default_factory=list)


@dataclass
class PriorityResult:
    """Priority information generated from change + context."""

    disaster_type: Optional[str] = None

    zones: list[PriorityZone] = field(default_factory=list)

    # Zone ID -> score
    priority_scores: dict[str, float] = field(default_factory=dict)

    confidence: Optional[float] = None

    # Zone ID -> explanation
    reasons: dict[str, str] = field(default_factory=dict)


@dataclass
class FutureImpact:
    """Potential future impact based on observed evidence and external context."""

    severity: str = "UNKNOWN"

    affected_zones: list[str] = field(default_factory=list)

    rainfall_factor: Optional[float] = None
    alert_factor: Optional[float] = None

    confidence: float = 0.0

    # Explicit assumptions/limitations
    assumptions: list[str] = field(default_factory=list)


@dataclass
class RouteResult:
    """Candidate route ranked using known disaster-related risk."""

    route_id: str

    distance_km: float = 0.0

    affected_segments: int = 0

    risk_score: float = 0.0

    reasons: list[str] = field(default_factory=list)


@dataclass
class IncidentReport:
    """Evidence-grounded AI incident report."""

    summary: str = ""

    observations: list[str] = field(default_factory=list)

    priority_zones: list[str] = field(default_factory=list)

    uncertainties: list[str] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)

    sources: list[str] = field(default_factory=list)

    confidence: Optional[float] = None