"""Clean and map OSM roads into feature categories."""

from __future__ import annotations

import geopandas as gpd

from osm_classifier.cleaning.common import (filter_geometry_types,
    replace_fake_nulls, report_duplicate_ids,)

ROAD_GROUPS = {
    "major_road": ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",],
    "secondary_road": ["secondary", "secondary_link", "tertiary", "tertiary_link",],
    "residential_road": ["residential", "living_street",],
    "service_road": ["service",],
    "rural_track": ["track", "unclassified", "trrack",],
    "pedestrian_zone": ["pedestrian", "footway", "path", "cycleway", "steps", "bridleway", "footpath", "fooway",],
}

HIGHWAY_TO_CATEGORY = {highway: category for category, highways in ROAD_GROUPS.items()
    for highway in highways}


def map_roads(gdf: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """Clean roads and map highway values into road categories."""
    required = {"id", "highway", "geometry"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(f"Road data is missing columns: {sorted(missing)}")

    gdf = replace_fake_nulls(gdf, "roads")
    gdf = filter_geometry_types(gdf, {"LineString", "MultiLineString"}, "roads",)
    valid = (gdf.geometry.is_valid & ~gdf.geometry.is_empty)
    removed = int((~valid).sum())
    gdf = gdf.loc[valid].copy()
    print(f"[roads] Invalid or empty geometries removed: {removed:,}")

    gdf["highway"] = (gdf["highway"].astype("string").str.strip().str.lower())
    gdf["road_category"] = gdf["highway"].map(HIGHWAY_TO_CATEGORY)

    before = len(gdf)
    gdf = gdf[gdf["road_category"].notna()].copy()
    print(f"[roads] Unmapped road records removed: {before - len(gdf):,}")

    projected = gdf.to_crs(projected_crs)
    gdf["length_m"] = projected.geometry.length

    before = len(gdf)
    gdf = gdf[gdf["length_m"] >= 1].copy()
    print(f"[roads] Segments shorter than 1 metre removed: {before - len(gdf):,}")
    report_duplicate_ids(gdf, "roads")

    columns = ["id", "highway", "road_category", "length_m", "geometry",]
    print(f"[roads] Mapped road segments: {len(gdf):,}")
    print(gdf["road_category"].value_counts().to_string())

    return gdf[columns].copy()