from typing import Any

from .client import load_dhm_report_text
from .parser import parse_dhm_flood_alerts


def get_relevant_flood_alerts(
    report_text_path: str,
    basin_name: str,
) -> list[dict[str, Any]]:
    """
    Return flood alerts relevant to the selected basin.
    """

    report_text = load_dhm_report_text(
        report_text_path
    )

    alerts = parse_dhm_flood_alerts(
        report_text
    )

    basin_name_normalized = (
        basin_name.strip().lower()
    )

    relevant_alerts = [
        alert
        for alert in alerts
        if alert.get("basin", "")
        .strip()
        .lower()
        == basin_name_normalized
    ]

    return relevant_alerts