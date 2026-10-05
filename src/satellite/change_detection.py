import numpy as np
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union

from src.satellite.preprocessing import validate_pair


def calculate_difference(
    before: np.ndarray,
    after: np.ndarray,
) -> np.ndarray:
    """
    Calculate the absolute pixel-wise difference between
    before and after images.
    """
    validate_pair(before, after)

    before_float = before.astype(np.float32)
    after_float = after.astype(np.float32)

    difference = np.abs(after_float - before_float)

    invalid = ~np.isfinite(before_float) | ~np.isfinite(after_float)
    difference[invalid] = np.nan

    return difference


def detect_change(
    before: np.ndarray,
    after: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, float]:
    """
    Detect changed pixels using an absolute difference threshold.

    Returns:
        change_mask: Boolean array where True indicates change.
        change_percentage: Percentage of valid pixels classified as changed.
    """
    if threshold < 0:
        raise ValueError("Threshold must be non-negative.")

    difference = calculate_difference(before, after)

    valid_pixels = np.isfinite(difference)

    if not np.any(valid_pixels):
        raise ValueError("No valid pixels available for change detection.")

    change_mask = np.zeros(difference.shape, dtype=bool)
    change_mask[valid_pixels] = difference[valid_pixels] > threshold

    change_percentage = (
        np.count_nonzero(change_mask[valid_pixels])
        / np.count_nonzero(valid_pixels)
        * 100.0
    )

    return change_mask, float(change_percentage)


def mask_to_geometry(
    change_mask: np.ndarray,
    transform,
):
    """
    Convert a boolean change mask into a dissolved Shapely geometry.

    Args:
        change_mask: Boolean raster where True indicates changed pixels.
        transform: Rasterio affine transform describing pixel locations.

    Returns:
        Shapely geometry representing the changed area,
        or None if no pixels have changed.
    """
    if change_mask.ndim != 2:
        raise ValueError("Change mask must be a 2D array.")

    if not np.any(change_mask):
        return None

    geometries = []

    for geometry, value in shapes(
        change_mask.astype(np.uint8),
        mask=change_mask,
        transform=transform,
    ):
        if value == 1:
            geometries.append(shape(geometry))

    if not geometries:
        return None

    return unary_union(geometries)