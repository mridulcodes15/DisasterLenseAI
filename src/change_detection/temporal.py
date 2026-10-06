
from pathlib import Path
import json

import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


def compare_sar_backscatter(
    pre_path: str | Path,
    post_path: str | Path,
    output_dir: str | Path = "data/processed/temporal",
    threshold_db: float = -5.0,
    min_pixels: int = 4,
) -> dict:
    """Compare aligned pre/post SAR backscatter rasters.

    Inputs must use the same grid, CRS, resolution and calibrated dB units.
    Output is a candidate-change mask and GeoJSON, not a validated flood map.
    """
    pre_path, post_path = Path(pre_path), Path(post_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(pre_path) as pre, rasterio.open(post_path) as post:
        if (pre.width, pre.height) != (post.width, post.height):
            raise ValueError("Raster dimensions do not match.")
        if pre.crs != post.crs:
            raise ValueError("Raster CRS does not match.")
        if pre.transform != post.transform:
            raise ValueError("Raster grids are not aligned.")
        if pre.count < 1 or post.count < 1:
            raise ValueError("Input rasters have no data bands.")

        before = pre.read(1, masked=True).astype("float32")
        after = post.read(1, masked=True).astype("float32")
        profile = pre.profile.copy()
        transform = pre.transform
        crs = pre.crs

    valid = (
        ~np.ma.getmaskarray(before)
        & ~np.ma.getmaskarray(after)
        & np.isfinite(before.filled(np.nan))
        & np.isfinite(after.filled(np.nan))
    )
    difference = after.filled(np.nan) - before.filled(np.nan)

    # Negative dB change is a candidate signal, not proof of flooding.
    mask = valid & (difference <= threshold_db)

    # Remove small connected components.
    from scipy import ndimage
    labels, count = ndimage.label(mask)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_pixels
    keep[0] = False
    mask = keep[labels] & valid

    mask_path = output_dir / "candidate_change_mask.tif"
    profile.update(dtype="uint8", count=1, nodata=0, compress="deflate")
    with rasterio.open(mask_path, "w", **profile) as dst:
        dst.write(mask.astype("uint8"), 1)

    features = []
    geometries = []
    for geom, value in shapes(
        mask.astype("uint8"),
        mask=mask,
        transform=transform,
    ):
        if value != 1:
            continue
        geometry = shape(geom)
        geometries.append(geometry)
        features.append({
            "type": "Feature",
            "geometry": mapping(geometry),
            "properties": {
                "method": "pre_post_sar_backscatter_difference",
                "threshold_db": threshold_db,
                "validated_flood": False,
            },
        })

    geojson_path = output_dir / "candidate_change_extent.geojson"
    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "method": "pre_post_sar_backscatter_difference",
            "threshold_db": threshold_db,
            "pre_source": str(pre_path),
            "post_source": str(post_path),
            "crs": str(crs),
            "validated_flood": False,
            "warning": (
                "Candidate backscatter changes only. Confirm acquisition metadata, "
                "calibration, terrain correction, alignment and flood interpretation."
            ),
        },
        "features": features,
    }
    geojson_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    return {
        "mask_path": str(mask_path),
        "geojson_path": str(geojson_path),
        "candidate_pixels": int(mask.sum()),
        "valid_pixels": int(valid.sum()),
        "feature_count": len(features),
        "validated_flood": False,
    }
