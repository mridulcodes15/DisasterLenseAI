import numpy as np


def calculate_confidence(
    before: np.ndarray,
    after: np.ndarray,
    change_mask: np.ndarray,
    threshold: float,
) -> float:
    """
    Calculate a confidence score for detected change.

    The score is based on how strongly changed pixels exceed
    the detection threshold.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    if threshold < 0:
        raise ValueError("Threshold must be non-negative.")

    if before.shape != after.shape:
        raise ValueError(
            f"Images must have matching dimensions: "
            f"{before.shape} vs {after.shape}"
        )

    if before.shape != change_mask.shape:
        raise ValueError(
            f"Change mask dimensions must match images: "
            f"{change_mask.shape} vs {before.shape}"
        )

    if not np.any(change_mask):
        return 0.0

    before_float = before.astype(np.float32)
    after_float = after.astype(np.float32)

    difference = np.abs(after_float - before_float)

    changed_difference = difference[change_mask]
    changed_difference = changed_difference[np.isfinite(changed_difference)]

    if changed_difference.size == 0:
        return 0.0

    mean_difference = float(np.mean(changed_difference))

    if threshold == 0:
        confidence = 1.0 if mean_difference > 0 else 0.0
    else:
        confidence = mean_difference / (mean_difference + threshold)

    return float(np.clip(confidence, 0.0, 1.0))