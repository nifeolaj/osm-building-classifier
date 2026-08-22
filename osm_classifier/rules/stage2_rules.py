"""Stage 2 contextual rule-based building classification."""

from __future__ import annotations

from collections.abc import Mapping

import geopandas as gpd
import pandas as pd


LANDUSE_PRIORITY = {'industrial': 1, 'retail': 2, 'commercial': 3,
                    'military': 2, 'residential': 4,}
    

POI_L1_PRIORITY = {'civic': 1, 'industrial': 2, 'semi_commercial': 3, 
                   'commercial': 4, 'residential': 5, 'transportation': 6}


def unclassified_mask(gdf: gpd.GeoDataFrame) -> pd.Series:
    """Buildings eligible for Stage 2."""
    return (gdf["stage1_l1"].isna() & gdf["stage2_l1"].isna())


def initialise_stage2(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Initialise Stage 2 output columns."""
    gdf = gdf.copy()
    gdf["stage2_l1"] = None
    gdf["stage2_l2"] = None
    gdf["stage2_source"] = None
    return gdf


def attach_landuse(buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame, projected_crs: str,) -> gpd.GeoDataFrame:
    """
    Assign one mapped land-use polygon to each building.

    Building centroids and polygon containment are calculated in the
    configured projected CRS.
    """
    required = {"id", "zone_l1", "zone_l2", "landuse", "geometry", "zone_area_sqm"}
    missing = required - set(landuse.columns)

    if missing:
        raise ValueError(f"Mapped land-use dataset is missing columns: {sorted(missing)}")

    buildings = buildings.copy()
    buildings_proj = buildings[["id", "geometry"]].to_crs(projected_crs)
    landuse_proj = landuse.to_crs(projected_crs).copy()

    if "zone_area_sqm" not in landuse_proj.columns:
        landuse_proj["zone_area_sqm"] = landuse_proj.geometry.area

    centroids = buildings_proj.copy()
    centroids["geometry"] = buildings_proj.geometry.centroid

    joined = gpd.sjoin(centroids, landuse_proj[
            ["id", "geometry", "zone_l1", "zone_l2", "landuse", "zone_area_sqm",]],
            how="left", predicate="within", lsuffix="bldg", rsuffix="zone",)

    # Handle buildings in multiple overlapping zones:
    # smallest zone + priority (industrial > commercial > residential) wins
    joined["_priority"] = (joined["landuse"].map(LANDUSE_PRIORITY).fillna(9))
    joined = joined.sort_values(["id_bldg", "zone_area_sqm", "_priority"], ascending=[True, True, True],)
    joined_clean = joined.drop_duplicates(subset="id_bldg", keep="first",)

    # Identify buildings whose centroid occurs in overlapping
    # residential and commercial land-use polygons.
    residential_ids = set(joined.loc[joined["zone_l1"].eq("residential"), "id_bldg",])
    commercial_ids = set(joined.loc[joined["zone_l1"].eq("commercial"), "id_bldg",])
    semi_commercial_ids = residential_ids & commercial_ids
    lookup = joined_clean.set_index("id_bldg")

    buildings["landuse_l1"] = buildings["id"].map(lookup["zone_l1"])
    buildings["landuse_l2"] = buildings["id"].map(lookup["zone_l2"])
    buildings["landuse_used"] = buildings["id"].map(lookup["landuse"])
    buildings["landuse_osm_id"] = buildings["id"].map(lookup["id_zone"])

    semi_mask = buildings["id"].isin(semi_commercial_ids)

    buildings.loc[semi_mask, "landuse_l1"] = "semi_commercial"
    buildings.loc[semi_mask, "landuse_used",] = "residential_commercial"

    print("[stage2] Buildings in mapped land-use zones: "
        f"{buildings['landuse_l1'].notna().sum():,}")
    print("[stage2] Buildings outside mapped zones: "
        f"{buildings['landuse_l1'].isna().sum():,}")
    
    return buildings


def get_trusted_zones(buildings: gpd.GeoDataFrame, zone_type: str, threshold: float, min_buildings: int,) -> set:
    """
    Returns a set of landuse_osm_id values that are 'trustworthy' enough
    to classify untagged buildings inside them.

    A zone is trusted if:
      - At least min_buildings stage1-classified buildings are inside it
      - At least threshold% of those buildings agree with zone_type
    """
    zone_buildings = buildings[buildings["stage1_l1"].notna() & buildings["stage1_l1"].ne("filter")
        & buildings["landuse_l1"].eq(zone_type) & buildings["landuse_osm_id"].notna()]

    if zone_buildings.empty:
        print(f"[stage2] No evaluable {zone_type} zones.")
        return set()

    per_polygon = (zone_buildings.groupby("landuse_osm_id")["stage1_l1"].agg(n_buildings="count",
            n_matching=lambda values: values.eq(zone_type).sum(),).reset_index())
    per_polygon["agreement_rate"] = (per_polygon["n_matching"] / per_polygon["n_buildings"])

    trusted = per_polygon[per_polygon["n_buildings"].ge(min_buildings)
        & per_polygon["agreement_rate"].ge(threshold)]
    trusted_ids = set(trusted["landuse_osm_id"])

    print(f"[stage2] Trusted {zone_type} zones: {len(trusted_ids):,} "
        f"(minimum={min_buildings}, agreement={threshold:.0%})")

    return trusted_ids


def prepare_polygon_poi_matches(buildings: gpd.GeoDataFrame,
    pois: gpd.GeoDataFrame, projected_crs: str,) -> pd.DataFrame:
    """Match building centroids to mapped polygon POIs."""
    required = {'id', 'geometry', 'poi_l1', 'poi_l2', 'poi_source', 'poi_used'}
    missing = required - set(pois.columns)

    if missing:
        raise ValueError(f"Mapped POI dataset is missing columns: {sorted(missing)}")

    polygon_pois = pois[pois.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

    polygon_pois = polygon_pois[['id', 'geometry', 'poi_l1', 'poi_l2', 'poi_source', 'poi_used']]

    if polygon_pois.empty:
        print("[stage2] No mapped polygon POIs found.")
        return pd.DataFrame(
            columns=["bldg_id", "poi_l1", "poi_l2", "poi_source", "poi_used",])

    buildings_proj = buildings[["id", "geometry"]].to_crs(projected_crs)
    polygon_pois = polygon_pois.to_crs(projected_crs)

    centroids = buildings_proj.copy()
    centroids["geometry"] = buildings_proj.geometry.centroid

    spatial_match = gpd.sjoin(centroids, polygon_pois, how="inner",
        predicate="within", lsuffix="bldg", rsuffix="poi",)

    # Remove POI polygons that are the same OSM object as the building.
    spatial_match = spatial_match[spatial_match["id_bldg"].ne(spatial_match["id_poi"])].copy()
    if spatial_match.empty:
        return pd.DataFrame(
            columns=["bldg_id", "poi_l1", "poi_l2", "poi_source", "poi_used",])

    spatial_match["_priority"] = (spatial_match["poi_l1"].map(POI_L1_PRIORITY).fillna(99))
    resolved = (spatial_match.sort_values(["id_bldg", "_priority"])
        .drop_duplicates("id_bldg", keep="first").rename(columns={"id_bldg": "bldg_id"}))
    result = resolved[['bldg_id', 'poi_l1', 'poi_l2', 'poi_source', 'poi_used']].copy()

    print(f"[stage2] Building-to-polygon-POI matches: {len(result):,}")

    return result


def apply_rule1_small_area(buildings: gpd.GeoDataFrame, config: Mapping,) -> int:
    """Filter very small buildings without address information."""
    rule = config["rules"]["small_building_filter"]

    mask = (unclassified_mask(buildings) & buildings["area"]
            .between(0, rule["max_area_sqm"],)
            & buildings["address_tier"].eq(rule["address_tier"]))

    buildings.loc[mask, "stage2_l1"] = "filter"
    buildings.loc[mask, "stage2_l2"] = None
    buildings.loc[mask, "stage2_source"] = "rule1_small_area"

    return int(mask.sum())


def apply_rule2_garage_filter(buildings: gpd.GeoDataFrame, trusted_residential: set, 
    projected_crs: str, config: Mapping,) -> int:
    """Filter garage-sized buildings close to addressed houses."""
    rule = config["rules"]["garage_filter"]

    candidate_mask = (unclassified_mask(buildings)
        & buildings["area"].between(rule["min_area_sqm"],rule["max_area_sqm"],)
        & buildings["address_tier"].eq(rule["address_tier"])
        & buildings["landuse_osm_id"].isin(trusted_residential))

    house_mask = (buildings["address_tier"].eq(rule["house_address_tier"])
        & buildings["stage1_l1"].eq("residential"))

    candidates = buildings.loc[candidate_mask,["id", "geometry"],]
    addressed_houses = buildings.loc[house_mask, ["id", "geometry"],]
    if candidates.empty or addressed_houses.empty:
        return 0
    candidates = candidates.to_crs(projected_crs)
    addressed_houses = addressed_houses.to_crs(projected_crs)

    nearest = gpd.sjoin_nearest(candidates, addressed_houses,
        how="left", max_distance=rule["max_distance_m"],
        distance_col="dist_to_house", lsuffix="cand", rsuffix="house",)
    
    garage_ids = (nearest.dropna(subset=["id_house"]).drop_duplicates("id_cand")["id_cand"])

    mask = (unclassified_mask(buildings) & buildings["id"].isin(garage_ids))

    buildings.loc[mask, "stage2_l1"] = "filter"
    buildings.loc[mask, "stage2_l2"] = None
    buildings.loc[mask, "stage2_source",] = "rule2_garage_filter"

    return int(mask.sum())


def apply_rule3_residential(buildings: gpd.GeoDataFrame, trusted_residential: set, config: Mapping,) -> int:
    """Classify addressed buildings in trusted residential zones."""
    rule = config["rules"]["residential_zone"]

    mask = (unclassified_mask(buildings)
        & buildings["area"].between(rule["min_area_sqm"], rule["max_area_sqm"],)
        & buildings["address_tier"].eq(rule["address_tier"])
        & buildings["landuse_osm_id"].isin(trusted_residential))

    buildings.loc[mask, "stage2_l1"] = buildings.loc[mask, "landuse_l1",]
    buildings.loc[mask, "stage2_l2"] = buildings.loc[mask, "landuse_l2",]
    buildings.loc[mask, "stage2_source",] = "rule3_trusted_residential_zone"

    return int(mask.sum())


def apply_trusted_zone_rule(buildings: gpd.GeoDataFrame, trusted_zone_ids: set, source: str,) -> int:
    """Classify unclassified buildings from a trusted land-use zone."""
    mask = (unclassified_mask(buildings) & buildings["landuse_osm_id"].isin(trusted_zone_ids))

    buildings.loc[mask, "stage2_l1"] = buildings.loc[mask, "landuse_l1",]
    buildings.loc[mask, "stage2_l2"] = buildings.loc[mask, "landuse_l2",]
    buildings.loc[mask, "stage2_source"] = source

    return int(mask.sum())


def trusted_poi_sources(buildings: gpd.GeoDataFrame, poi_matches: pd.DataFrame,
    l1_type: str, min_precision: float, min_buildings: int,) -> set | None:
    """
    Evaluate polygon POI sources against Stage 1 labels.

    """
    evaluation = poi_matches.merge(buildings[["id", "stage1_l1"]],
        left_on="bldg_id", right_on="id", how="left",)
    
    evaluation = evaluation[evaluation["poi_l1"].eq(l1_type)
        & evaluation["stage1_l1"].notna()
        & evaluation["stage1_l1"].ne("filter")]
    if evaluation.empty:
        return None

    source_precision = (evaluation.groupby("poi_source", dropna=False)["stage1_l1"]
        .agg(n="size", precision=lambda values: values.eq(l1_type).mean(),))

    trusted = set(source_precision[source_precision["n"].ge(min_buildings)
            & source_precision["precision"].ge(min_precision)].index)
    unevaluable = set(source_precision[source_precision["n"].lt(min_buildings)].index)

    return trusted | unevaluable


def apply_rule7_polygon_pois(buildings: gpd.GeoDataFrame, poi_matches: pd.DataFrame,
                              config: Mapping,) -> dict[str, int]:
    """Inherit classifications from trusted polygon POIs."""
    poi_config = config["polygon_poi"]

    trusted_l1 = tuple(poi_config["trusted_l1"])
    min_precision = poi_config["min_source_precision"]
    min_buildings = poi_config["min_source_buildings"]

    counts: dict[str, int] = {}

    if poi_matches.empty:
        return {l1_type: 0 for l1_type in trusted_l1}

    trusted_sources = {l1_type: trusted_poi_sources(buildings, poi_matches,
            l1_type, min_precision, min_buildings,) for l1_type in trusted_l1}

    clean_matches = poi_matches[poi_matches["poi_l1"].isin(trusted_l1)
        & poi_matches["poi_l1"].notna()].copy()

    keep_mask = pd.Series(False, index=clean_matches.index,)

    for l1_type, sources in trusted_sources.items():
        l1_mask = clean_matches["poi_l1"].eq(l1_type)

        if sources is None:
            keep_mask |= l1_mask
        else:
            keep_mask |= (l1_mask & clean_matches["poi_source"].isin(sources))

    clean_matches = (clean_matches.loc[keep_mask].drop_duplicates("bldg_id", keep="first"))

    for l1_type in trusted_l1:
        subset = clean_matches[clean_matches["poi_l1"].eq(l1_type)]
        mask = (unclassified_mask(buildings) & buildings["id"].isin(subset["bldg_id"]))
        indices = buildings.index[mask]

        if len(indices) == 0:
            counts[l1_type] = 0
            continue

        lookup = subset.set_index("bldg_id")
        building_ids = buildings.loc[indices, "id"]

        buildings.loc[indices, "stage2_l1"] = (building_ids.map(lookup["poi_l1"]).values)
        buildings.loc[indices, "stage2_l2"] = (building_ids.map(lookup["poi_l2"]).values)
        buildings.loc[indices, "stage2_source",] = f"rule7_polygon_poi_contained_{l1_type}"

        counts[l1_type] = len(indices)

    return counts


def stage2_report(buildings: gpd.GeoDataFrame) -> None:
    """Print the final Stage 2 summary."""
    combined_l1 = buildings["stage1_l1"].combine_first(buildings["stage2_l1"])
    combined_l2 = buildings["stage1_l2"].combine_first(buildings["stage2_l2"])

    total = len(buildings)
    classified = combined_l1.notna() & combined_l1.ne("filter")
    filtered = combined_l1.eq("filter")
    unclassified = combined_l1.isna()

    stage2_classified = (buildings["stage1_l1"].isna()
        & buildings["stage2_l1"].notna()& buildings["stage2_l1"].ne("filter"))

    stage2_filtered = (buildings["stage1_l1"].isna() & buildings["stage2_l1"].eq("filter"))

    print("\n" + "=" * 60)
    print("STAGE 2 CLASSIFICATION")
    print("=" * 60)
    print(f"Total:                {total:>12,}")
    print(f"Classified:           {classified.sum():>12,}")
    print(f"  with L2:            {(classified & combined_l2.notna()).sum():>12,}")
    print(f"  without L2:         {(classified & combined_l2.isna()).sum():>12,}")
    print(f"Filtered:             {filtered.sum():>12,}")
    print(f"Unclassified:         {unclassified.sum():>12,}")
    print(f"Added by Stage 2:     {stage2_classified.sum():>12,}")
    print(f"Filtered by Stage 2:  {stage2_filtered.sum():>12,}")

    print("\nStage 2 source distribution:")
    print(buildings["stage2_source"].value_counts(dropna=False).to_string())


def classify_stage2(buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame, pois: gpd.GeoDataFrame,
    projected_crs: str, config: Mapping,) -> gpd.GeoDataFrame:
    """Run the complete Stage 2 contextual rule pipeline."""
    buildings = initialise_stage2(buildings)

    required_building_columns = {"id", "geometry", "area",
        "address_tier", "stage1_l1", "stage1_l2",}
    missing = required_building_columns - set(buildings.columns)

    if missing:
        raise ValueError(f"Stage 2 building input is missing: {sorted(missing)}")

    buildings = attach_landuse(buildings, landuse, projected_crs,)

    trusted_config = config["trusted_zones"]
    threshold = trusted_config["agreement_threshold"]
    minimums = trusted_config["min_buildings"]

    trusted_residential = get_trusted_zones(buildings, "residential", threshold, minimums["residential"],)
    trusted_commercial = get_trusted_zones(buildings, "commercial", threshold, minimums["commercial"],)
    trusted_industrial = get_trusted_zones(buildings, "industrial", threshold, minimums["industrial"],)
    trusted_military = get_trusted_zones(buildings, "military", threshold, minimums["military"],)

    poi_matches = prepare_polygon_poi_matches(buildings, pois, projected_crs,)

    count = apply_rule1_small_area(buildings, config)
    print(f"[stage2] Rule 1 small-area filter: {count:,}")

    count = apply_rule2_garage_filter(buildings, trusted_residential, projected_crs, config,)
    print(f"[stage2] Rule 2 garage filter: {count:,}")

    count = apply_rule3_residential(buildings, trusted_residential, config,)
    print(f"[stage2] Rule 3 residential zone: {count:,}")

    count = apply_trusted_zone_rule(buildings, trusted_industrial, "rule4_trusted_industrial_zone",)
    print(f"[stage2] Rule 4 industrial zone: {count:,}")

    count = apply_trusted_zone_rule(buildings, trusted_commercial, "rule5_trusted_commercial_zone",)
    print(f"[stage2] Rule 5 commercial zone: {count:,}")

    count = apply_trusted_zone_rule(buildings, trusted_military, "rule6_trusted_military_zone",)
    print(f"[stage2] Rule 6 military zone: {count:,}")

    poi_counts = apply_rule7_polygon_pois(buildings, poi_matches, config,)

    for l1_type, count in poi_counts.items():
        print(f"[stage2] Rule 7 polygon POI {l1_type}: {count:,}")

    stage2_report(buildings)
    return buildings