"""Clean and prepare OSM land-use polygons."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from osm_classifier.cleaning.common import (drop_relations,filter_geometry_types,
    fix_invalid_geometries, replace_fake_nulls, report_duplicate_ids,)
from osm_classifier.taxonomy.tag_maps.landuse_map import apply_landuse_map


def prepare_landuse(gdf: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """Clean land-use polygons and map them to zone classes."""
    required = {"id", "landuse", "geometry"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(f"Land-use data is missing columns: {sorted(missing)}")

    gdf = replace_fake_nulls(gdf, "landuse")
    gdf = filter_geometry_types(gdf, {"Polygon", "MultiPolygon"}, "landuse",)
    gdf = fix_invalid_geometries(gdf, "landuse")
    gdf = drop_relations(gdf, "landuse")
    report_duplicate_ids(gdf, "landuse")

    mapped = gdf["landuse"].apply(apply_landuse_map)
    gdf["zone_l1"] = mapped.str[0]
    gdf["zone_l2"] = mapped.str[1]

    before = len(gdf)
    gdf = gdf[gdf["zone_l1"].notna()].copy()
    print(f"[landuse] Unmapped polygons removed: {before - len(gdf):,}")

    for col in ["industrial", "tags"]:
        if col not in gdf.columns:
            gdf[col] = pd.NA

    projected = gdf.to_crs(projected_crs)
    gdf["zone_area_sqm"] = projected.geometry.area

    columns = [
        "id",
        "landuse",
        "zone_l1",
        "zone_l2",
        "zone_area_sqm",
        "industrial",
        "tags",
        "geometry",
    ]

    print(f"[landuse] Prepared polygons: {len(gdf):,}")
    print(gdf["zone_l1"].value_counts().to_string())

    return gdf[columns].copy()