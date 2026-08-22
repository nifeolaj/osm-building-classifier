"""Neighbouring-building spatial features."""

from __future__ import annotations

import gc

import geopandas as gpd
import numpy as np
from shapely.strtree import STRtree


NEIGHBOUR_FEATURES = ["dist_nearest_real_building", "is_touching_real_building", "real_touching_count",]

TOUCH_DISTANCE_M = 3.0


def add_neighbour_features(buildings: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """
    Add proximity and touching features for real buildings.

    Real buildings exclude:
    - Stage 1 filtered structures;
    - animal-keeping auxiliary structures.
    """
    required_columns = {"geometry", "stage1_l1", "stage1_l2", "stage2_l1", "stage2_l2",}
    missing = required_columns - set(buildings.columns)
    if missing:
        raise ValueError(f"Neighbour features require columns: {sorted(missing)}")

    if buildings.crs is None:
        raise ValueError("Building dataset has no CRS.")

    buildings = buildings.copy()
    projected = buildings.to_crs(projected_crs)

    geometries = projected.geometry.values

    final_l1 = buildings["stage2_l1"].combine_first(buildings["stage1_l1"])
    final_l2 = buildings["stage2_l2"].combine_first(buildings["stage1_l2"])

    is_filter = final_l1.eq("filter")
    is_animal_keeping = final_l2.eq("animal_keeping")

    real_mask = ~(is_filter | is_animal_keeping).to_numpy()
    real_geometries = geometries[real_mask]

    print(f"[features] Real buildings in neighbour tree: {real_mask.sum():,}")
    print(f"[features] Excluded auxiliary structures: {(~real_mask).sum():,}")

    if len(real_geometries) == 0:
        buildings["dist_nearest_real_building"] = np.nan
        buildings["is_touching_real_building"] = np.int8(0)
        buildings["real_touching_count"] = np.int8(0)

        print("[features] No real buildings available.")
        return buildings

    print("[features] Building real-building STRtree...")

    tree = STRtree(real_geometries)

    # Distance from every building to its nearest real building
    indices, distances = tree.query_nearest(geometries, exclusive=True, return_distance=True,)
    nearest_distances = np.full(len(geometries), np.nan, dtype=np.float32,)

    if distances.size:
        query_indices = indices[0]
        _, first_matches = np.unique(query_indices, return_index=True,)
        nearest_distances[query_indices[first_matches]] = distances[first_matches].astype(np.float32)

    buildings["dist_nearest_real_building"] = nearest_distances
    buildings["is_touching_real_building"] = (nearest_distances <= TOUCH_DISTANCE_M).astype(np.int8)

    # Number of real buildings whose polygons touch each other
    left_indices, right_indices = tree.query(real_geometries,predicate="touches",)
    not_self = left_indices != right_indices
    real_touch_counts = np.bincount(left_indices[not_self], minlength=len(real_geometries),).astype(np.int8)

    # Assign zero to excluded buildings.
    full_touch_counts = np.zeros(len(geometries), dtype=np.int8,)
    full_touch_counts[real_mask] = real_touch_counts
    buildings["real_touching_count"] = full_touch_counts

    print("[features] Buildings within 3 m of a real building: "
        f"{buildings['is_touching_real_building'].sum():,}")
    print("[features] Maximum real touching count: "
        f"{buildings['real_touching_count'].max():,}")

    del tree
    del indices, distances
    del left_indices, right_indices
    del real_touch_counts, full_touch_counts
    gc.collect()

    return buildings