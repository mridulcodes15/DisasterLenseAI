import re
from typing import Any


def parse_dhm_flood_alerts(
    report_text: str,
) -> list[dict[str, Any]]:
    """
    Extract flood-warning evidence from the official Nepal DHM report.

    Nothing is invented here:
    values are extracted from the source text itself.
    """

    alerts = []

    normalized = " ".join(report_text.split())

    # Find the sentence describing the special flood bulletin.
    bulletin_match = re.search(
        r"special flood forecasting bulletin was issued at 5 PM.*?"
        r"extremely high flood risk \(above danger level\).*?"
        r"for the (.*?) basins",
        normalized,
        flags=re.IGNORECASE,
    )

    if bulletin_match:
        basins_text = bulletin_match.group(1)

        basins = [
            basin.strip()
            for basin in re.split(
                r",| and ",
                basins_text,
            )
            if basin.strip()
        ]

        for basin in basins:
            alerts.append(
                {
                    "type": "flood_forecast",
                    "basin": basin,
                    "severity": "extremely_high",
                    "risk_level": "above_danger_level",
                    "source": (
                        "Government of Nepal - "
                        "Department of Hydrology and Meteorology"
                    ),
                }
            )

    return alerts