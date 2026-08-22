"""Building-footprint geometry features."""

from __future__ import annotations

import numpy as np
import geopandas as gpd
from shapely import get_coordinates


GEOMETRY_FEATURES = ["area", "compactness", "convexity", "num_vertices",
    "mrr_long", "mrr_short", "elongation", "rectangularity", "diameter",]


def _get_mrr_dimensions(geometry) -> tuple[float, float]:
    """
    Return the longest and shortest sides of a polygon's
    minimum rotated rectangle.
    """
    if geometry is None or geometry.is_empty:
        return np.nan, np.nan

    mrr = geometry.minimum_rotated_rectangle

    if mrr.is_empty or not hasattr(mrr, "exterior"):
        return np.nan, np.nan

    coordinates = np.asarray(mrr.exterior.coords)
    sides = np.sqrt(np.diff(coordinates[:, 0]) ** 2+ np.diff(coordinates[:, 1]) ** 2)
    return float(sides.max()), float(sides.min())


def _count_vertices(geometry) -> int:
    """Count all coordinates in a building geometry."""
    if geometry is None or geometry.is_empty:
        return 0
    return int(get_coordinates(geometry).shape[0])


def add_geometry_features(buildings: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """
    Add the geometry features used by the trained models.

    Calculations are performed in the configured metric CRS, while
    the returned GeoDataFrame retains its original CRS.
    """
    if buildings.crs is None:
        raise ValueError("Building dataset has no CRS.")

    buildings = buildings.copy()
    projected = buildings.to_crs(projected_crs)
    geometry = projected.geometry

    print("[features] Computing building geometry features...")
    # Area and perimeter in metres.
    area = geometry.area.astype(np.float64)
    perimeter = geometry.length.astype(np.float64)
    buildings["area"] = area
    # 4πA / P²
    buildings["compactness"] = ((4 * np.pi * area) / perimeter.pow(2)).clip(0, 1)
    # Building area divided by convex-hull area.
    convex_hull_area = geometry.convex_hull.area
    buildings["convexity"] = area / convex_hull_area
    buildings["num_vertices"] = geometry.map(_count_vertices)

    print("[features] Computing minimum rotated rectangles...")
    dimensions = geometry.map(_get_mrr_dimensions)

    buildings["mrr_long"] = np.fromiter((value[0] for value in dimensions),
        dtype=np.float32, count=len(dimensions),)

    buildings["mrr_short"] = np.fromiter((value[1] for value in dimensions),
        dtype=np.float32, count=len(dimensions),)

    short_side = buildings["mrr_short"].replace(0, np.nan)
    buildings["elongation"] = buildings["mrr_long"] / short_side
    mrr_area = (buildings["mrr_long"] * buildings["mrr_short"]).replace(0, np.nan)
    buildings["rectangularity"] = buildings["area"] / mrr_area
    buildings["diameter"] = np.sqrt(buildings["mrr_long"].pow(2)
        + buildings["mrr_short"].pow(2))

    print("[features] Geometry features completed:")
    for column in GEOMETRY_FEATURES:
        missing = int(buildings[column].isna().sum())
        print(f"  {column:<18} missing={missing:,}")

    return buildings