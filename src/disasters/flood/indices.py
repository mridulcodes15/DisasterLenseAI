import numpy as np


def calculate_mndwi(green: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """
    Calculate Modified Normalized Difference Water Index (MNDWI).

    MNDWI = (Green - SWIR) / (Green + SWIR)
    """

    green = green.astype("float32")
    swir = swir.astype("float32")

    denominator = green + swir

    with np.errstate(divide="ignore", invalid="ignore"):
        mndwi = np.where(
            denominator != 0,
            (green - swir) / denominator,
            np.nan,
        )

    return mndwi