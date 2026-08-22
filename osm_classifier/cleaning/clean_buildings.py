"""Building-specific cleaning."""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from osm_classifier.paths import INTERIM_DATA_DIR

from osm_classifier.cleaning.common import (drop_relations, drop_small_id_artefacts,
    filter_geometry_types, fix_invalid_geometries, replace_fake_nulls, report_duplicate_ids,)

USEFUL_COLUMNS = ["addr:city", "addr:housenumber", "addr:postcode", "addr:street",
    "name", "building", "amenity", "building:use",
    "craft", "office", "shop", "id", "tags", "osm_type", "geometry",]


def select_useful_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep columns required by later classification stages."""
    available = [col for col in USEFUL_COLUMNS if col in gdf.columns]
    missing = [col for col in USEFUL_COLUMNS if col not in gdf.columns]
    if missing:
        print(f"[buildings] Missing columns skipped: {missing}")
    return gdf[available].copy()


def add_address_tier(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add address completeness: 0=no address, 1=partial, 2=complete."""
    columns = ["addr:street", "addr:housenumber", "addr:postcode"]
    gdf = gdf.copy()
    for col in columns:
        if col not in gdf.columns:
            gdf[col] = np.nan
    score = gdf[columns].notna().sum(axis=1)
    gdf["address_tier"] = 0
    gdf.loc[score.between(1, 2), "address_tier"] = 1
    gdf.loc[score == 3, "address_tier"] = 2
    print(f"[buildings] Address tiers: "
        f"0={(gdf['address_tier'] == 0).sum():,}, "
        f"1={(gdf['address_tier'] == 1).sum():,}, "
        f"2={(gdf['address_tier'] == 2).sum():,}")
    return gdf

def add_area(gdf: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """Calculate building footprint area in square metres."""
    gdf = gdf.copy()
    projected = gdf.to_crs(projected_crs)
    gdf["area"] = projected.geometry.area
    print(f"[buildings] Area calculated in {projected_crs}; missing={(gdf['area'].isna()).sum():,}")
    return gdf

def clean_buildings(gdf: gpd.GeoDataFrame, projected_crs:str, min_id_digits: int = 7,) -> gpd.GeoDataFrame:
    """Run building cleaning in the notebook order."""
    gdf = replace_fake_nulls(gdf, "buildings")
    gdf = filter_geometry_types(gdf, {"Polygon", "MultiPolygon"}, "buildings")
    gdf = fix_invalid_geometries(gdf, "buildings")
    gdf = drop_relations(gdf, "buildings")
    gdf = drop_small_id_artefacts(gdf, min_digits=min_id_digits, name="buildings")
    gdf = select_useful_columns(gdf)
    gdf = add_address_tier(gdf)
    gdf = add_area(gdf, projected_crs)
    report_duplicate_ids(gdf, "buildings")
    return gdf