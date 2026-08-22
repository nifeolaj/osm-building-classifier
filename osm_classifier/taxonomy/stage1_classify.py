"""Stage 1 direct-tag building classification."""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd

from osm_classifier.taxonomy.tag_maps.amenity_map import apply_amenity_map
from osm_classifier.taxonomy.tag_maps.building_map import apply_building_map
from osm_classifier.taxonomy.tag_maps.buildinguse_map import apply_building_use_map
from osm_classifier.taxonomy.tag_maps.shop_map import apply_shop_map


_ABANDONED_PREFIXES = {'disused:','abandoned:','demolished:','ruins:','ruin:','collapsed:','deserted:'}
_ABANDONED_VALUES = {'disused','abandoned','demolished','ruins','ruin','collapsed','deserted', 'destroyed', 'derelict'}


def _normalise(value) -> str:
    """Lowercase, collapse whitespace and remove trailing semicolons."""
    text = str(value).strip().lower()
    return re.sub(r"\s+", " ", text).rstrip(";")


def _tag_is_abandoned(value) -> bool:
    """Check whether a raw OSM value signals abandonment."""
    if pd.isna(value):
        return False
    parts = [part.strip() for part in _normalise(value).split(";") if part.strip()]

    return any(part in _ABANDONED_VALUES
        or any(part.startswith(prefix) for prefix in _ABANDONED_PREFIXES)
        for part in parts)


def update_abandoned_flag(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Combine tags-column abandonment with the four direct columns."""
    gdf = gdf.copy()

    if "is_abandoned" not in gdf.columns:
        gdf["is_abandoned"] = False
    else:
        gdf["is_abandoned"] = gdf["is_abandoned"].fillna(False).astype(bool)
    for column in ["building", "building:use", "amenity", "shop"]:
        if column in gdf.columns:
            gdf["is_abandoned"] |= gdf[column].map(_tag_is_abandoned)

    print(f"[stage1] Abandoned/disused buildings: {gdf['is_abandoned'].sum():,}")
    return gdf


def _map_column(gdf: gpd.GeoDataFrame, column: str, map_function, prefix: str,) -> gpd.GeoDataFrame:
    """Apply one existing taxonomy mapping function."""
    l1_col = f"{prefix}_l1"
    l2_col = f"{prefix}_l2"

    if column not in gdf.columns:
        gdf[l1_col] = None
        gdf[l2_col] = None
        print(f"[stage1] Missing column skipped: {column}")
        return gdf

    output_columns = [l1_col, l2_col]

    mapped = pd.DataFrame(map(map_function, gdf[column]), columns=output_columns, index=gdf.index,)

    for output_column in output_columns:
        gdf[output_column] = mapped[output_column]

    total = int(gdf[column].notna().sum())
    mapped_count = int(gdf[l1_col].notna().sum())
    percentage = mapped_count / total * 100 if total else 0

    print(f"[stage1] {column}: mapped {mapped_count:,} / {total:,} ({percentage:.1f}%)")
    return gdf


def _initialise_stage1_columns(gdf: gpd.GeoDataFrame) -> None:
    """Reset the Stage 1 output columns."""
    gdf["stage1_l1"] = None
    gdf["stage1_l2"] = None
    gdf["stage1_source"] = None
    gdf["raw_label"] = None


def _apply_building_source(gdf: gpd.GeoDataFrame) -> None:
    """Apply the building tag as the first Stage 1 source."""
    has_real = (gdf["building_l1"].notna() & gdf["building_l1"].ne("filter"))

    gdf.loc[has_real, "stage1_l1"] = gdf.loc[has_real, "building_l1"]
    gdf.loc[has_real, "stage1_l2"] = gdf.loc[has_real, "building_l2"]
    gdf.loc[has_real, "stage1_source"] = "building"
    gdf.loc[has_real, "raw_label"] = gdf.loc[has_real, "building"]

    is_filter = gdf["building_l1"].eq("filter")
    gdf.loc[is_filter, "stage1_l1"] = "filter"
    gdf.loc[is_filter, "stage1_source"] = "building_filter"
    gdf.loc[is_filter, "raw_label"] = gdf.loc[is_filter, "building"]

    print(f"[building] Classified: {has_real.sum():,} | filtered: {is_filter.sum():,}")


def _apply_source(gdf: gpd.GeoDataFrame, src_l1: str, src_l2: str,
    source_name: str, raw_col: str) -> None:
    """
    Merge one mapped source into Stage 1.

    A: fill rows without an existing classification;
    B: replace an existing filter with a real classification;
    C: inherit L2 when the source agrees with the existing L1.
    """
    has_data = gdf[src_l1].notna()
    is_real = has_data & gdf[src_l1].ne("filter")

    # --- Case A: row has no classification yet ---
    mask_a = gdf["stage1_l1"].isna() & has_data
    gdf.loc[mask_a, "stage1_l1"] = gdf.loc[mask_a, src_l1]
    gdf.loc[mask_a, "stage1_l2"] = gdf.loc[mask_a, src_l2] 
    gdf.loc[mask_a, "stage1_source"] = source_name
    if raw_col in gdf.columns:
        gdf.loc[mask_a, "raw_label"] = gdf.loc[mask_a, raw_col]

    # --- Case B: row was flagged as filter, but this source has a real value ---
    mask_b = gdf["stage1_l1"].eq("filter") & is_real
    gdf.loc[mask_b, "stage1_l1"] = gdf.loc[mask_b, src_l1]
    gdf.loc[mask_b, "stage1_l2"] = gdf.loc[mask_b, src_l2]
    gdf.loc[mask_b, "stage1_source"] = f"{source_name}_override_filter"
    if raw_col in gdf.columns:
        gdf.loc[mask_b, "raw_label"] = gdf.loc[mask_b, raw_col]

    # Case C: L1 already set, L2 missing, source agrees on L1 → inherit L2
    mask_c = (gdf["stage1_l1"].notna() & gdf["stage1_l1"].ne("filter") & gdf["stage1_l2"].isna()
             & is_real & gdf[src_l2].notna() & gdf[src_l1].eq(gdf["stage1_l1"]))
    gdf.loc[mask_c, "stage1_l2"] = gdf.loc[mask_c, src_l2]
    gdf.loc[mask_c, "stage1_source"] = (gdf.loc[mask_c, "stage1_source"] + f"_+{source_name}_l2")
    if raw_col in gdf.columns:
        gdf.loc[mask_c, "raw_label"] = gdf.loc[mask_c, raw_col]

    print(f"[{source_name}] A filled: {mask_a.sum():,} | "
        f"B filter override: {mask_b.sum():,} | "
        f"C L2 inherited: {mask_c.sum():,}")


def stage1_report(gdf: gpd.GeoDataFrame) -> None:
    """Print the final Stage 1 classification summary."""
    total = len(gdf)

    classified = (gdf["stage1_l1"].notna() & gdf["stage1_l1"].ne("filter"))
    filtered = gdf["stage1_l1"].eq("filter")
    unclassified = gdf["stage1_l1"].isna()

    with_l2 = classified & gdf["stage1_l2"].notna()
    without_l2 = classified & gdf["stage1_l2"].isna()

    print("\n" + "=" * 55)
    print("STAGE 1 CLASSIFICATION")
    print("=" * 55)
    print(f"Total:          {total:>12,}")
    print(f"Classified:     {classified.sum():>12,}")
    print(f"  with L2:      {with_l2.sum():>12,}")
    print(f"  without L2:   {without_l2.sum():>12,}")
    print(f"Filtered:       {filtered.sum():>12,}")
    print(f"Unclassified:   {unclassified.sum():>12,}")
    print("\nL1 distribution:")
    print(gdf["stage1_l1"].value_counts(dropna=False).to_string())
    print("\nSource distribution:")
    print(gdf["stage1_source"].value_counts(dropna=False).to_string())


def classify_stage1(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Run the complete Stage 1 direct-tag classification."""
    gdf = gdf.copy()
    gdf = update_abandoned_flag(gdf)

    gdf = _map_column(gdf, "building", apply_building_map, "building",)
    gdf = _map_column(gdf, "building:use", apply_building_use_map, "buse",)
    gdf = _map_column(gdf, "amenity", apply_amenity_map, "amenity",)
    gdf = _map_column(gdf, "shop", apply_shop_map, "shop",)

    for column in ["tag_l1", "tag_l2", "tag_used"]:
        if column not in gdf.columns:
            raise ValueError(f"Stage 1 requires '{column}'. Run tag mapping first.")

    _initialise_stage1_columns(gdf)
    _apply_building_source(gdf)
    _apply_source(gdf, "buse_l1", "buse_l2", "building:use", "building:use",)
    _apply_source(gdf, "amenity_l1", "amenity_l2", "amenity", "amenity",)
    _apply_source(gdf, "shop_l1", "shop_l2", "shop", "shop",)
    _apply_source(gdf, "tag_l1", "tag_l2", "tag", "tag_used",)

    stage1_report(gdf)
    return gdf