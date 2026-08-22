"""Clean and map OSM man-made polygons."""

from __future__ import annotations

import geopandas as gpd

from osm_classifier.cleaning.common import (drop_relations, filter_geometry_types, 
    fix_invalid_geometries, replace_fake_nulls, report_duplicate_ids,)
from osm_classifier.taxonomy.tag_maps.ind_grouping_map import IND_MAP


NORMALISED_IND_MAP = {str(key).strip().lower(): value
    for key, value in IND_MAP.items()}


def map_manmade(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Map man-made polygons to industrial subtype categories."""
    required = {"id", "man_made", "geometry"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(
            f"Man-made data is missing columns: {sorted(missing)}")

    gdf = replace_fake_nulls(gdf, "manmade")
    gdf = filter_geometry_types(gdf, {"Polygon", "MultiPolygon"}, "manmade",)
    gdf = fix_invalid_geometries(gdf, "manmade")
    gdf = drop_relations(gdf, "manmade")

    gdf["man_made"] = (gdf["man_made"].astype("string").str.strip().str.lower())
    gdf["manmade_category"] = gdf["man_made"].map(NORMALISED_IND_MAP)

    before = len(gdf)
    gdf = gdf[gdf["manmade_category"].notna()].copy()

    print(f"[manmade] Unmapped records removed: {before - len(gdf):,}")
    report_duplicate_ids(gdf, "manmade")
    print(f"[manmade] Mapped polygons: {len(gdf):,}")
    print(gdf["manmade_category"].value_counts().to_string())

    return gdf[["id", "man_made", "manmade_category", "geometry"]].copy()