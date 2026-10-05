from pathlib import Path


def load_dhm_report_text(
    report_text_path: str | Path,
) -> str:
    """
    Load extracted text from the official Nepal DHM flood report.
    """

    path = Path(report_text_path)

    if not path.exists():
        raise FileNotFoundError(
            f"DHM report text not found: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )