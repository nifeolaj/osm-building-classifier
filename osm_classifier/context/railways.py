"""Clean and map OSM railway lines."""

from __future__ import annotations

import geopandas as gpd

from osm_classifier.cleaning.common import (filter_geometry_types,
    replace_fake_nulls, report_duplicate_ids,)

RAILWAY_MAP = {
    "rail": "heavy_rail",
    "narrow_gauge": "heavy_rail",
    "light_rail": "light_rail",
    "tram": "light_rail",
    "subway": "light_rail",
}


def map_railways(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Map railway lines into heavy-rail and light-rail categories."""
    required = {"id", "railway", "geometry"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(f"Railway data is missing columns: {sorted(missing)}")

    gdf = replace_fake_nulls(gdf, "railways")
    gdf = filter_geometry_types(gdf, {"LineString", "MultiLineString"}, "railways",)
    valid = (gdf.geometry.is_valid & ~gdf.geometry.is_empty)
    removed = int((~valid).sum())
    gdf = gdf.loc[valid].copy()
    print(f"[railways] Invalid or empty geometries removed: {removed:,}")

    gdf["railway"] = (gdf["railway"].astype("string").str.strip().str.lower())
    gdf["railway_category"] = gdf["railway"].map(RAILWAY_MAP)

    before = len(gdf)
    gdf = gdf[gdf["railway_category"].notna()].copy()
    print(f"[railways] Unmapped records removed: {before - len(gdf):,}")
    report_duplicate_ids(gdf, "railways")
    print(f"[railways] Mapped railway segments: {len(gdf):,}")
    print(gdf["railway_category"].value_counts().to_string())

    return gdf[["id", "railway_category", "geometry"]].copy()