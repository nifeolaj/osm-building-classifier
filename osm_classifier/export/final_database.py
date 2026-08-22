"""Create the final building and industrial-site databases."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


BUILDING_CORE_COLUMNS = ['id', 'geometry', 'final_l1', 'final_l2', 'parent_id', 'parent_subtype', 'area', 'is_abandoned',]

BUILDING_PROVENANCE_COLUMNS = ["l1_confidence", "l2_confidence", "label_source",]

BUILDING_RENAME = {
    "id": "osm_building_id",
    "final_l1": "building_type",
    "final_l2": "building_subtype",
    "parent_id": "industrial_site_id",
    "parent_subtype": "industrial_site_subtype",
    "area": "footprint_area_m2",
    "l1_confidence": "building_type_confidence",
    "l2_confidence": "building_subtype_confidence",
    "label_source": "classification_source",
}

PARENT_COLUMNS = ['parent_id', 'landuse_geometry', 'subtype', 'zone_area_sqm',
                'n_buildings', 'n_industrial_buildings',  'parent_type',]

PARENT_RENAME = {
    "parent_id": "industrial_site_id",
    "landuse_osm_id": "osm_landuse_id",
    "subtype": "industrial_site_subtype",
    "n_buildings": "building_count",
    "n_industrial_buildings": "industrial_building_count",
    "zone_area_sqm": "site_area_m2",
    "parent_type": "grouping_type",
}

def _restore_id_column(buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Restore building ID from the index when necessary."""
    if "id" in buildings.columns:
        return buildings.copy()

    if buildings.index.name != "id":
        raise ValueError("Building dataset has no 'id' column or index.")

    return buildings.reset_index()


def create_final_databases(buildings: gpd.GeoDataFrame, parents: gpd.GeoDataFrame, *,
    include_provenance: bool = True,) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Create slim building and industrial-site output databases."""
    buildings = _restore_id_column(buildings)

    required_buildings = set(BUILDING_CORE_COLUMNS)
    missing = required_buildings - set(buildings.columns)

    if missing:
        raise ValueError(f"Building output is missing: {sorted(missing)}")

    required_parents = set(PARENT_COLUMNS)
    missing = required_parents - set(parents.columns)

    if missing:
        raise ValueError(f"Industrial-parent output is missing: {sorted(missing)}")

    # --------------------------------------------------------------
    # Generic package integrity checks
    # --------------------------------------------------------------
    if buildings["id"].duplicated().any():
        raise ValueError("Final building database contains duplicate IDs.")

    if parents["parent_id"].duplicated().any():
        raise ValueError("Industrial-parent database contains duplicate IDs.")

    if buildings["final_l1"].isna().any():
        count = int(buildings["final_l1"].isna().sum())
        raise ValueError(f"{count:,} buildings have no final L1 classification.")

    if buildings.geometry.isna().any():
        count = int(buildings.geometry.isna().sum())
        raise ValueError(f"{count:,} buildings have no geometry.")

    if buildings.crs is None:
        raise ValueError("Final building database has no CRS.")

    if parents.crs is None:
        raise ValueError("Industrial-parent database has no CRS.")

    linked_parent_ids = set(buildings["parent_id"].dropna().astype(str))
    available_parent_ids = set(parents["parent_id"].dropna().astype(str))
    orphan_ids = linked_parent_ids - available_parent_ids

    if orphan_ids:
        raise ValueError("Buildings reference unknown industrial parents: "f"{sorted(orphan_ids)[:10]}")

    invalid_area = buildings["area"].isna() | buildings["area"].le(0)

    if invalid_area.any():
        count = int(invalid_area.sum())
        raise ValueError(f"{count:,} buildings have missing or non-positive area.")

    invalid_parent_area = (parents["zone_area_sqm"].isna() | parents["zone_area_sqm"].le(0))

    if invalid_parent_area.any():
        count = int(invalid_parent_area.sum())
        raise ValueError(f"{count:,} industrial parents have invalid total area.")

    # --------------------------------------------------------------
    # Final building database
    # --------------------------------------------------------------
    building_columns = BUILDING_CORE_COLUMNS.copy()

    if include_provenance:
        building_columns += [column for column in BUILDING_PROVENANCE_COLUMNS if column in buildings.columns]

    final_buildings = buildings[building_columns].copy()
    final_buildings = final_buildings.rename(columns=BUILDING_RENAME)
    final_buildings = gpd.GeoDataFrame(final_buildings, geometry="geometry", crs=buildings.crs,)

    # --------------------------------------------------------------
    # Final industrial-site database
    # --------------------------------------------------------------
    final_parents = parents[PARENT_COLUMNS].copy()
    final_parents = gpd.GeoDataFrame(final_parents, geometry="landuse_geometry", crs=parents.crs,)
    final_parents = final_parents.rename(columns=PARENT_RENAME)
    final_parents = final_parents.rename_geometry("geometry")

    print("\n" + "=" * 60)
    print("FINAL DATABASE SUMMARY")
    print("=" * 60)
    print(f"Buildings:          {len(final_buildings):>12,}")
    print(f"Industrial sites:   {len(final_parents):>12,}")
    print(f"Linked buildings:   {final_buildings['industrial_site_id'].notna().sum():>12,}")
    print(f"Orphan references:  {len(orphan_ids):>12,}")

    print("\nFinal L1 distribution:")
    print(final_buildings["building_type"].value_counts(dropna=False).to_string())
    print(final_buildings["building_subtype"].value_counts(dropna=False).to_string())

    return final_buildings, final_parents