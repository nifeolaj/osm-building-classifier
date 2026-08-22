"""Classify semi-commercial buildings using post-processing rules."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


UPDATED_COLUMNS = ["final_l1", "final_l2", "label_source"]

CONTEXT_COLUMNS = ["geometry", "tag_l1", "tag_l2", "building_l1", "building_l2",
    "buse_l1", "buse_l2", "amenity_l1", "amenity_l2", "landuse_l1", "landuse_l2",
    "craft", "office", "shop",]


def classify_semi_commercial(classified: pd.DataFrame, buildings: gpd.GeoDataFrame, 
                             pois: gpd.GeoDataFrame,) -> pd.DataFrame:
    """Apply the five semi-commercial rules from the final notebook."""
    required_labels = {"final_l1", "final_l2", "label_source"}
    missing = required_labels - set(classified.columns)
    if missing:
        raise ValueError(f"Classified data is missing: {sorted(missing)}")

    missing = set(CONTEXT_COLUMNS) - set(buildings.columns)
    if missing:
        raise ValueError(f"Building context is missing: {sorted(missing)}")

    missing = {"geometry", "poi_l1", "poi_l2"} - set(pois.columns)
    if missing:
        raise ValueError(f"POI data is missing: {sorted(missing)}")

    classified = classified.copy()
    buildings = buildings.copy()

    if classified.index.name != "id":
        if "id" not in classified.columns:
            raise ValueError("Classified data has no building ID.")
        classified = classified.set_index("id")

    if buildings.index.name != "id":
        if "id" not in buildings.columns:
            raise ValueError("Building context has no building ID.")
        buildings = buildings.set_index("id")

    if classified.index.has_duplicates:
        raise ValueError("Classified data contains duplicate IDs.")
    if buildings.index.has_duplicates:
        raise ValueError("Building context contains duplicate IDs.")

    missing_ids = classified.index.difference(buildings.index)
    if len(missing_ids):
        raise ValueError(f"{len(missing_ids):,} classified IDs are missing from the building context.")

    # Join only the columns required by the semi-commercial rules.
    work = classified.join(buildings[CONTEXT_COLUMNS], how="left")
    work = gpd.GeoDataFrame(work, geometry="geometry", crs=buildings.crs,)

    # Allow assignment of new string labels when parquet columns are categorical.
    for column in UPDATED_COLUMNS:
        work[column] = work[column].astype("object")

    work["semi_commercial_type"] = pd.Series(None, index=work.index, dtype="object",)
    work["rule_source"] = pd.Series(None, index=work.index, dtype="object",)

    # =================================================================
    # Rule 1: direct craft, shop and office tags
    # Later checks take precedence: office > shop > craft.
    # =================================================================
    is_residential = work["final_l1"].eq("residential")

    mask = is_residential & work["craft"].notna()
    work.loc[mask, "semi_commercial_type"] = "residential_commercial"
    work.loc[mask, "rule_source"] = "Rule 1: Direct Tags (craft)"

    mask = is_residential & work["shop"].notna()
    work.loc[mask, "semi_commercial_type"] = "residential_retail"
    work.loc[mask, "rule_source"] = "Rule 1: Direct Tags (shop)"

    mask = is_residential & work["office"].notna()
    work.loc[mask, "semi_commercial_type"] = "residential_office"
    work.loc[mask, "rule_source"] = "Rule 1: Direct Tags (office)"

    # =================================================================
    # Rule 2a: residential buildings with commercial tag evidence
    # The first matching source wins:
    # amenity -> tags -> building:use -> building.
    # =================================================================
    l1_columns = ["amenity_l1", "tag_l1", "buse_l1", "building_l1",]
    l2_columns = ["amenity_l2", "tag_l2", "buse_l2", "building_l2",]

    still_looking = (work["final_l1"].eq("residential") & work["rule_source"].isna())

    for l1_column, l2_column in zip(l1_columns, l2_columns):
        valid = (still_looking & work[l1_column].notna()
            & work[l1_column].isin(["commercial", "civic", "industrial"]))

        if not valid.any():
            continue

        commercial = valid & work[l1_column].eq("commercial")
        commercial_l2 = commercial & work[l2_column].notna()
        commercial_generic = commercial & work[l2_column].isna()

        work.loc[commercial_l2, "semi_commercial_type"] = ("residential_"
            + work.loc[commercial_l2, l2_column].astype(str))
        work.loc[commercial_generic, "semi_commercial_type",] = "residential_commercial"
        work.loc[commercial, "rule_source"] = (f"Rule 2: L1/L2 Conflict ({l1_column}=commercial)")

        civic = valid & work[l1_column].eq("civic")
        work.loc[civic, "semi_commercial_type"] = "residential_civic"
        work.loc[civic, "rule_source"] = (f"Rule 2: L1/L2 Conflict ({l1_column}=civic)")

        industrial = valid & ~commercial & ~civic
        work.loc[industrial, "semi_commercial_type",] = "residential_commercial"
        work.loc[industrial, "rule_source"] = ("Rule 2: L1/L2 Conflict ("
            + l1_column + "=" + work.loc[industrial, l1_column].astype(str)+ ")")

        still_looking &= ~valid

        if not still_looking.any():
            break

    # =================================================================
    # Rule 2b: commercial buildings with residential tag evidence
    # =================================================================
    still_looking = (work["final_l1"].eq("commercial")& work["rule_source"].isna())

    for l1_column, _ in zip(l1_columns, l2_columns):
        matched = still_looking & work[l1_column].eq("residential")

        if not matched.any():
            continue

        commercial_l2 = work.loc[matched, "final_l2"].astype("object")
        specific = (commercial_l2.notna() & commercial_l2.astype(str).ne("commercial"))
        specific_ids = commercial_l2.index[specific]
        generic_ids = commercial_l2.index[~specific]

        work.loc[specific_ids, "semi_commercial_type"] = ("residential_"
            + commercial_l2.loc[specific_ids].astype(str))
        work.loc[generic_ids, "semi_commercial_type",] = "residential_commercial"
        work.loc[matched, "rule_source"] = ("Rule 2: Commercial/Residential Conflict "
            f"({l1_column}=residential)")

        still_looking &= ~matched

        if not still_looking.any():
            break

    # =================================================================
    # Rule 3: POI spatial intersection
    # All mapped POIs are checked.
    # =================================================================
    needs_poi_check = (work["final_l1"].eq("residential") & work["rule_source"].isna())
    buildings_to_check = work.loc[needs_poi_check, ["geometry"]]

    print(f"[semi-commercial] Checking {len(buildings_to_check):,} "
        f"residential buildings against {len(pois):,} POIs")

    if not buildings_to_check.empty:
        aligned_pois = (pois.to_crs(buildings_to_check.crs) if pois.crs != buildings_to_check.crs else pois)

        intersecting = gpd.sjoin(buildings_to_check, aligned_pois[["geometry", "poi_l1", "poi_l2"]],
            how="inner", predicate="intersects",)

        # Prefer an intersecting POI with a specific L2 value.
        intersecting = (intersecting.assign(_has_l2=intersecting["poi_l2"].notna())
            .sort_values("_has_l2", ascending=False).drop(columns="_has_l2"))
        # A single building might intersect multiple POIs. We keep the first one to avoid duplicate rows.
        intersecting = intersecting[~intersecting.index.duplicated(keep="first")]
        intersecting["calculated_subtype"] = ("residential_commercial")

        civic = intersecting["poi_l1"].eq("civic")
        intersecting.loc[civic,"calculated_subtype",] = "residential_civic"

        commercial = intersecting["poi_l1"].eq("commercial")
        commercial_l2 = commercial & intersecting["poi_l2"].notna()

        intersecting.loc[commercial_l2, "calculated_subtype",] = (
            "residential_" + intersecting.loc[commercial_l2, "poi_l2"].astype(str))

        matched_ids = intersecting.index
        work.loc[matched_ids, "semi_commercial_type"] = (intersecting["calculated_subtype"])
        work.loc[matched_ids, "rule_source",] = "Rule 3: POI Spatial Intersection"

    # =================================================================
    # Rule 4: residential buildings in commercial or mixed land use
    # =================================================================
    landuse_base = (work["final_l1"].eq("residential") & work["landuse_l1"].isin(
            ["commercial", "semi_commercial"]) & work["rule_source"].isna())

    retail = landuse_base & work["landuse_l2"].eq("retail")
    office = landuse_base & work["landuse_l2"].eq("office")
    general = landuse_base & ~retail & ~office

    work.loc[retail, "semi_commercial_type"] = "residential_retail"
    work.loc[retail, "rule_source",] = "Rule 4: Commercial Landuse (retail)"
    work.loc[office, "semi_commercial_type"] = "residential_office"
    work.loc[office, "rule_source",] = "Rule 4: Commercial Landuse (office)"
    work.loc[general, "semi_commercial_type",] = "residential_commercial"
    work.loc[general, "rule_source",] = "Rule 4: Commercial Landuse"

    # Rules 1-4 convert matched residential/commercial records.
    matched = work["rule_source"].notna()
    work.loc[matched, "final_l1"] = "semi_commercial"

    # =================================================================
    # Rule 5: commercial building in semi-commercial land use
    # =================================================================
    rule5 = (work["final_l1"].eq("commercial") & work["landuse_l1"].eq("semi_commercial")
        & work["rule_source"].isna())

    rule5_with_l2 = rule5 & work["final_l2"].notna()
    rule5_without_l2 = rule5 & work["final_l2"].isna()

    work.loc[rule5_with_l2, "semi_commercial_type"] = (
        "residential_" + work.loc[rule5_with_l2, "final_l2"].astype(str))
    work.loc[rule5_without_l2, "semi_commercial_type",] = "residential_commercial"
    work.loc[rule5, "rule_source",] = "Rule 5: Semi-Commercial Landuse"

    matched = work["rule_source"].notna()
    work.loc[matched, "final_l1"] = "semi_commercial"

    # =================================================================
    # Final subtype and provenance updates
    # =================================================================
    all_semi_commercial = work["final_l1"].eq("semi_commercial")
    new_semi_commercial = (all_semi_commercial & work["rule_source"].notna()
        & work["semi_commercial_type"].notna())

    work.loc[new_semi_commercial, "final_l2"] = work.loc[new_semi_commercial, "semi_commercial_type",]
    work.loc[new_semi_commercial, "label_source",] = "semi_commercial_rule"

    # Standardise kindergarten as the broader civic subtype.
    kindergarten = (all_semi_commercial & work["final_l2"].astype("string")
        .str.strip().str.lower().eq("residential_kindergarten"))
    work.loc[kindergarten, "final_l2"] = "residential_civic"
    work.loc[kindergarten, "semi_commercial_type",] = "residential_civic"

    invalid_l2 = (work["final_l2"].isna() | work["final_l2"].astype("string")
        .str.strip().str.lower().isin(["", "mixed", "nan", "none"]))
    fallback = all_semi_commercial & invalid_l2

    work.loc[fallback, "final_l2",] = "residential_commercial"
    work.loc[fallback, "semi_commercial_type",] = "residential_commercial"

    # =================================================================
    # Integrity checks and output
    # =================================================================
    if len(work) != len(classified):
        raise RuntimeError("Semi-commercial processing changed row count.")
    if not work.index.equals(classified.index):
        raise RuntimeError("Semi-commercial processing changed ID order.")
    if work["final_l1"].isna().any():
        raise ValueError("Some buildings have no final L1 label.")

    output = classified.copy()

    for column in UPDATED_COLUMNS:
        output[column] = work[column]

    print("\n" + "=" * 60)
    print("SEMI-COMMERCIAL CLASSIFICATION")
    print("=" * 60)
    print(f"New assignments:       {new_semi_commercial.sum():>12,}")
    print(f"Existing assignments:  {(all_semi_commercial & ~new_semi_commercial).sum():>12,}")
    print(f"Fallback subtypes:     {fallback.sum():>12,}")
    print(f"Total semi-commercial: {all_semi_commercial.sum():>12,}")

    print("\nRule contribution:")
    print(work["rule_source"].value_counts().to_string())

    print("\nSemi-commercial subtypes:")
    print(output.loc[output["final_l1"].eq("semi_commercial"), "final_l2",]
          .value_counts(dropna=False).to_string())

    return output