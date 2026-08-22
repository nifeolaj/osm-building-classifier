"""Clean and map OSM waterway lines."""

from __future__ import annotations

import geopandas as gpd

from osm_classifier.cleaning.common import (
    filter_geometry_types, replace_fake_nulls, report_duplicate_ids,)

WATERWAY_MAP = {
    "river": "major_waterway",
    "canal": "major_waterway",
    "stream": "minor_waterway",
    "drain": "minor_waterway",
    "ditch": "minor_waterway",
}


def map_waterways(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Map waterways into major and minor categories."""
    required = {"id", "waterway", "geometry"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(f"Waterway data is missing columns: {sorted(missing)}")

    gdf = replace_fake_nulls(gdf, "waterways")
    gdf = filter_geometry_types(gdf, {"LineString", "MultiLineString"}, "waterways",)

    valid = (gdf.geometry.is_valid & ~gdf.geometry.is_empty)
    removed = int((~valid).sum())
    gdf = gdf.loc[valid].copy()
    print(f"[waterways] Invalid or empty geometries removed: {removed:,}")

    gdf["waterway"] = (gdf["waterway"].astype("string").str.strip().str.lower())
    gdf["waterway_category"] = gdf["waterway"].map(WATERWAY_MAP)

    before = len(gdf)
    gdf = gdf[gdf["waterway_category"].notna()].copy()
    print(f"[waterways] Unmapped records removed: {before - len(gdf):,}")
    report_duplicate_ids(gdf, "waterways")
    print(f"[waterways] Mapped waterway segments: {len(gdf):,}")
    print(gdf["waterway_category"].value_counts().to_string())

    return gdf[["id", "waterway_category", "geometry"]].copy()