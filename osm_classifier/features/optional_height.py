"""Optional building-height integration.

This module accepts a generic geospatial building-height dataset, spatially
matches its geometries to OSM building footprints, and adds the standardized
``building_height_m`` feature.

The source dataset may come from any provider or format supported by
GeoPandas. The package only requires:

    1. building geometries;
    2. a user-specified column containing building height values.

The source height-column name does not need to be standardized.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely


HEIGHT_FEATURE = "building_height_m"


def load_height_dataset(path: str | Path, height_column: str) -> gpd.GeoDataFrame:
    """Load and validate a generic external building-height dataset."""
    path = Path(path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Height dataset not found: {path}")

    heights = gpd.read_parquet(path) if path.suffix.lower() in {".parquet", ".geoparquet"} else gpd.read_file(path)

    if "geometry" not in heights.columns:
        raise ValueError("Height dataset must contain a geometry column.")
    if height_column not in heights.columns:
        raise ValueError(f"Height column '{height_column}' not found. Available columns: {list(heights.columns)}")
    if heights.crs is None:
        raise ValueError("Height dataset must define a CRS.")

    heights = heights[["geometry", height_column]].copy()
    heights[height_column] = pd.to_numeric(heights[height_column], errors="coerce")
    heights = heights[heights.geometry.notna() & ~heights.geometry.is_empty].copy()

    if heights.empty:
        raise ValueError("Height dataset contains no valid geometries.")
    if heights[height_column].notna().sum() == 0:
        raise ValueError(f"Height column '{height_column}' contains no usable numeric values.")

    return heights


def add_optional_height_feature(buildings: gpd.GeoDataFrame, heights: gpd.GeoDataFrame, height_column: str,
    projected_crs: str, *, min_intersection_m2: float = 1.0, max_height_m: float = 400.0) -> gpd.GeoDataFrame:
    """Spatially match external building heights to OSM building footprints.

    Matching is based on footprint intersection. For every candidate pair,
    intersection area, IoU, OSM-footprint coverage, and source-footprint
    coverage are calculated. The strongest acceptable match is retained for
    each OSM building.

    Parameters
    ----------
    buildings
        OSM building GeoDataFrame.
    heights
        External height GeoDataFrame containing geometry and height values.
    height_column
        Name of the source column containing building heights in metres.
    projected_crs
        Metric projected CRS used for area and overlap calculations.
    min_intersection_m2
        Minimum candidate intersection area.
    max_height_m
        Maximum accepted height. Values outside (0, max_height_m] become NaN.

    Returns
    -------
    geopandas.GeoDataFrame
        Copy of the input buildings with ``building_height_m`` added.
    """
    if "geometry" not in buildings.columns:
        raise ValueError("Building dataset must contain a geometry column.")
    if buildings.crs is None:
        raise ValueError("Building dataset must define a CRS.")
    if "geometry" not in heights.columns:
        raise ValueError("Height dataset must contain a geometry column.")
    if height_column not in heights.columns:
        raise ValueError(f"Height column not found: {height_column}")
    if heights.crs is None:
        raise ValueError("Height dataset must define a CRS.")
    if min_intersection_m2 < 0:
        raise ValueError("min_intersection_m2 cannot be negative.")
    if max_height_m <= 0:
        raise ValueError("max_height_m must be greater than zero.")

    result = buildings.copy()

    # Keep stable row IDs so matched heights can be restored to the original building order.
    osm = buildings[["geometry"]].copy()
    osm["_osm_row"] = np.arange(len(osm), dtype=np.int64)

    height = heights[["geometry", height_column]].copy()
    height[height_column] = pd.to_numeric(height[height_column], errors="coerce")
    height = height[height[height_column].notna()].copy()

    # Remove empty geometries before spatial operations.
    osm = osm[osm.geometry.notna() & ~osm.geometry.is_empty].copy()
    height = height[height.geometry.notna() & ~height.geometry.is_empty].copy()

    if osm.empty:
        raise ValueError("Building dataset contains no valid geometries.")
    if height.empty:
        raise ValueError("Height dataset contains no usable geometry-height records.")

    # Repair invalid geometries where possible.
    invalid_osm = ~np.asarray(shapely.is_valid(osm.geometry.array))
    invalid_height = ~np.asarray(shapely.is_valid(height.geometry.array))

    if invalid_osm.any():
        osm.loc[invalid_osm, "geometry"] = list(shapely.make_valid(osm.loc[invalid_osm].geometry.array))
    if invalid_height.any():
        height.loc[invalid_height, "geometry"] = list(shapely.make_valid(height.loc[invalid_height].geometry.array))

    osm = osm[osm.geometry.notna() & ~osm.geometry.is_empty].copy()
    height = height[height.geometry.notna() & ~height.geometry.is_empty].copy()

    if osm.empty:
        raise ValueError("No valid OSM building geometries remain after repair.")
    if height.empty:
        raise ValueError("No valid height geometries remain after repair.")

    # Use one metric CRS for all overlap and area calculations.
    osm = osm.to_crs(projected_crs).reset_index(drop=True)
    height = height.to_crs(projected_crs).reset_index(drop=True)
    height["_height_row"] = np.arange(len(height), dtype=np.int64)

    # Calculate footprint areas once.
    osm["osm_area_m2"] = shapely.area(osm.geometry.array)
    height["height_area_m2"] = shapely.area(height.geometry.array)

    osm = osm[np.isfinite(osm["osm_area_m2"]) & osm["osm_area_m2"].gt(0)].reset_index(drop=True)
    height = height[np.isfinite(height["height_area_m2"]) & height["height_area_m2"].gt(0)].reset_index(drop=True)

    if osm.empty:
        raise ValueError("No OSM buildings with positive footprint area remain.")
    if height.empty:
        raise ValueError("No height features with positive footprint area remain.")

    # Generate candidate pairs using the spatial index.
    candidates = gpd.sjoin(osm[["_osm_row", "geometry"]], height[["_height_row", "geometry"]],
        how="inner", predicate="intersects")

    # Height is optional, so no intersection simply produces missing height values.
    if candidates.empty:
        result[HEIGHT_FEATURE] = np.nan
        print("[height] No intersections found between OSM buildings and height data.")
        return result

    pairs = pd.DataFrame(candidates[["_osm_row", "_height_row"]]).reset_index(drop=True)
    osm_lookup = osm.set_index("_osm_row")
    height_lookup = height.set_index("_height_row")

    osm_rows = pairs["_osm_row"].to_numpy(dtype=np.int64)
    height_rows = pairs["_height_row"].to_numpy(dtype=np.int64)
    osm_geom = osm_lookup.loc[osm_rows, "geometry"].array
    height_geom = height_lookup.loc[height_rows, "geometry"].array

    # Calculate exact overlap for every candidate pair.
    pairs["intersection_area_m2"] = shapely.area(shapely.intersection(osm_geom, height_geom))
    pairs = pairs[np.isfinite(pairs["intersection_area_m2"]) & pairs["intersection_area_m2"].ge(min_intersection_m2)].copy()

    if pairs.empty:
        result[HEIGHT_FEATURE] = np.nan
        print("[height] No candidate matches satisfy the minimum overlap requirement.")
        return result

    osm_rows = pairs["_osm_row"].to_numpy(dtype=np.int64)
    height_rows = pairs["_height_row"].to_numpy(dtype=np.int64)
    pairs["osm_area_m2"] = osm_lookup.loc[osm_rows, "osm_area_m2"].to_numpy()
    pairs["height_area_m2"] = height_lookup.loc[height_rows, "height_area_m2"].to_numpy()

    # Compare footprint agreement using coverage and intersection-over-union.
    pairs["osm_coverage"] = (pairs["intersection_area_m2"] / pairs["osm_area_m2"]).clip(0, 1)
    pairs["height_coverage"] = (pairs["intersection_area_m2"] / pairs["height_area_m2"]).clip(0, 1)
    union_area = pairs["osm_area_m2"] + pairs["height_area_m2"] - pairs["intersection_area_m2"]
    pairs["iou"] = (pairs["intersection_area_m2"] / union_area).clip(0, 1)
    pairs["score"] = 0.50 * pairs["iou"] + 0.25 * pairs["osm_coverage"] + 0.25 * pairs["height_coverage"]

    # Accept strong overall overlap or substantial coverage of either footprint.
    accepted = pairs[
        pairs["iou"].ge(0.25)
        | (pairs["osm_coverage"].ge(0.70) & pairs["height_coverage"].ge(0.20))
        | (pairs["height_coverage"].ge(0.70) & pairs["osm_coverage"].ge(0.20))
    ].copy()

    if accepted.empty:
        result[HEIGHT_FEATURE] = np.nan
        print("[height] No acceptable footprint matches were found.")
        return result

    # Keep the strongest external-height match for each OSM building.
    accepted = accepted.sort_values(["_osm_row", "score", "intersection_area_m2", "iou", "_height_row"],
        ascending=[True, False, False, False, True], kind="mergesort")
    best = accepted.drop_duplicates("_osm_row", keep="first").copy()

    matched_height = pd.to_numeric(height_lookup.loc[best["_height_row"], height_column],
        errors="coerce").to_numpy(dtype=np.float32)

    # Retain only positive and physically plausible height values.
    plausible = np.isfinite(matched_height) & (matched_height > 0) & (matched_height <= max_height_m)
    matched_height = np.where(plausible, matched_height, np.nan).astype(np.float32)

    # Restore matched values to the full original building table.
    output = np.full(len(result), np.nan, dtype=np.float32)
    output[best["_osm_row"].to_numpy(dtype=np.int64)] = matched_height
    result[HEIGHT_FEATURE] = output

    usable = int(result[HEIGHT_FEATURE].notna().sum())
    coverage = usable / len(result) * 100 if len(result) else 0.0

    print("[height] Optional height matching completed.")
    print(f"[height] Source footprints:       {len(height):,}")
    print(f"[height] Candidate intersections: {len(candidates):,}")
    print(f"[height] Accepted matches:        {len(best):,}")
    print(f"[height] Usable building heights: {usable:,} ({coverage:.2f}%)")

    return result