from typing import Tuple

import numpy as np


def align_images(
    before: np.ndarray,
    after: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare before/after images for comparison.

    The initial implementation requires both images to already share
    the same pixel dimensions. More advanced geospatial reprojection
    can be added later when real satellite products are integrated.
    """
    if before.ndim != 2 or after.ndim != 2:
        raise ValueError("Images must be 2D arrays.")

    if before.shape != after.shape:
        raise ValueError(
            f"Images must have matching dimensions: "
            f"{before.shape} vs {after.shape}"
        )

    return before, after