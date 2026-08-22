"""Reusable cleaning functions for OSM GeoDataFrames."""

from __future__ import annotations

import geopandas as gpd
import numpy as np

FAKE_NULLS = {"nan", "NaN", "None", "none", "", " ", "NULL", "null"}


def replace_fake_nulls(gdf: gpd.GeoDataFrame, name: str = "dataset",) -> gpd.GeoDataFrame:
    """Replace string representations of nulls with np.nan."""
    gdf = gdf.copy()
    replaced = 0
    for col in gdf.select_dtypes(include=["object", "string"]).columns:
        if col == gdf.geometry.name:
            continue
        mask = gdf[col].isin(FAKE_NULLS)
        replaced += int(mask.sum())
        if mask.any():
            gdf.loc[mask, col] = np.nan
    print(f"[{name}] Replaced {replaced:,} fake-null values")
    return gdf

def filter_geometry_types(gdf: gpd.GeoDataFrame, valid_types: set[str], name: str = "dataset",) -> gpd.GeoDataFrame:
    """Keep only non-null geometries of the requested types."""
    before = len(gdf)
    mask = gdf.geometry.geom_type.isin(valid_types)
    gdf = gdf.loc[mask].copy()
    print(f"[{name}] Geometry filter: {before:,} -> {len(gdf):,} (removed {before - len(gdf):,})")
    return gdf


def fix_invalid_geometries(gdf: gpd.GeoDataFrame, name: str = "dataset",) -> gpd.GeoDataFrame:
    """Repair invalid geometries with buffer(0) and remove failures."""
    gdf = gdf.copy()
    invalid = ~gdf.geometry.is_valid
    invalid_count = int(invalid.sum())
    if invalid_count:
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
    keep = (gdf.geometry.is_valid & ~gdf.geometry.is_empty)
    removed = int((~keep).sum())
    gdf = gdf.loc[keep].copy()
    print(f"[{name}] Invalid geometries: {invalid_count:,}; unfixable/empty removed: {removed:,}")
    return gdf


def drop_relations(gdf: gpd.GeoDataFrame, name: str = "dataset",) -> gpd.GeoDataFrame:
    """Remove rows whose osm_type is relation."""
    if "osm_type" not in gdf.columns:
        return gdf
    before = len(gdf)
    gdf = gdf.loc[~gdf["osm_type"].eq("relation")].copy()
    print(f"[{name}] Relations removed: {before - len(gdf):,}")
    return gdf


def drop_small_id_artefacts(gdf: gpd.GeoDataFrame, min_digits: int = 7, name: str = "dataset",) -> gpd.GeoDataFrame:
    """Remove rows with suspiciously short OSM IDs."""
    if "id" not in gdf.columns:
        raise ValueError(f"[{name}] Dataset has no 'id' column.")
    before = len(gdf)
    mask = gdf["id"].astype(str).str.len().ge(min_digits)
    gdf = gdf.loc[mask].copy()
    print(f"[{name}] Short-ID artefacts removed: {before - len(gdf):,}")
    return gdf


def report_duplicate_ids(gdf: gpd.GeoDataFrame, name: str = "dataset",) -> int:
    """Report duplicate OSM IDs without deleting them."""
    if "id" not in gdf.columns:
        return 0
    count = int(gdf["id"].duplicated().sum())
    print(f"[{name}] Remaining duplicate IDs: {count:,}")
    return count