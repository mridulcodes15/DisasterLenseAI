
from collections.abc import Sequence
from src.core.models import RouteResult


def rank_routes(routes: Sequence[RouteResult]) -> list[RouteResult]:
    """Rank candidate paths by risk first, then distance."""
    return sorted(
        routes,
        key=lambda route: (
            route.risk_score,
            route.distance_km,
            route.route_id,
        ),
    )
