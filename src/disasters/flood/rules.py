import numpy as np


def classify_water(
    mndwi: np.ndarray,
    threshold: float = 0.0,
) -> np.ndarray:
    """
    Classify pixels as water based on MNDWI.

    Returns:
        Boolean array where True represents water-like pixels.
    """

    return np.isfinite(mndwi) & (mndwi > threshold)


def detect_new_water(
    pre_water: np.ndarray,
    post_water: np.ndarray,
) -> np.ndarray:
    """
    Detect newly inundated pixels.

    New flood water is water in the post-event image
    that was not water in the pre-event image.
    """

    return post_water & ~pre_water