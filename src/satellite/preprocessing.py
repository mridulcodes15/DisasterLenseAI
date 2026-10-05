from pathlib import Path

import numpy as np
import rasterio


def load_raster(path: str | Path) -> tuple[np.ndarray, dict]:
    """
    Load the first band of a raster image.

    Returns:
        image: 2D NumPy array
        metadata: raster metadata
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Raster file not found: {path}")

    with rasterio.open(path) as src:
        image = src.read(1)
        metadata = src.meta.copy()

    if image.size == 0:
        raise ValueError(f"Raster contains no data: {path}")

    return image, metadata


def validate_pair(
    before: np.ndarray,
    after: np.ndarray,
) -> None:
    """
    Validate that two raster arrays can be compared.
    """
    if before.ndim != 2 or after.ndim != 2:
        raise ValueError("Before and after images must be 2D arrays.")

    if before.shape != after.shape:
        raise ValueError(
            f"Image dimensions do not match: "
            f"{before.shape} vs {after.shape}"
        )

    if not np.isfinite(before).any():
        raise ValueError("Before image contains no finite values.")

    if not np.isfinite(after).any():
        raise ValueError("After image contains no finite values.")