
"""Group buildings into industrial-site parent records."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from osm_classifier.taxonomy.tag_parser import parse_tags
from osm_classifier.taxonomy.tag_maps.ind_grouping_map import IND_MAP


POWER_MAP = {
    "plant": "energy_generation", "generator": "energy_generation",
    "substation": "grid_infrastructure", "converter": "grid_infrastructure",
    "transformer": "grid_infrastructure",
}
PIPELINE_MAP = {
    "substation": "grid_infrastructure", "valve_group": "grid_infrastructure",
    "valve": "grid_infrastructure",
}
UTILITY_MAP = {
    "gas": "grid_infrastructure", "water": "water_utilities",
    "power": "grid_infrastructure", "oil": "grid_infrastructure",
    "heating": "heating_supply", "sewerage": "water_utilities",
}
LANDUSE_OVERRIDE = {
    "quarry": "mining_quarry", "storage": "storage",
    "storage_depot": "storage", "warehouse": "warehouse",
    "water_storage": "water_utilities",
}

CORE_SUBTYPE_PRIORITY = [
    "metal_industry", "petroleum_industry", "chemical_industry", "food_processing",
    "pharmaceutical_industry", "wood_processing", "construction_materials",
    "engineering", "mining_quarry", "hightech_manufacturing",
    "logistics", "light_manufacturing", "manufacturing",
]
SUPPORT_SUBTYPE_PRIORITY = [
    "energy_generation", "grid_infrastructure", "waste_management",
    "heating_supply", "water_utilities", "cold_storage", "warehouse",
    "silo", "storage", "utilities",
]
CORE_SUBTYPES = set(CORE_SUBTYPE_PRIORITY)
SUPPORT_SUBTYPES = set(SUPPORT_SUBTYPE_PRIORITY)

ZONE_TAG_KEY_PRECEDENCE = [
    "resource", "power", "pipeline", "product",
    "industrial", "man_made", "utility",
]
ZONE_TAG_MAPS = {
    "resource": None, "power": POWER_MAP, "pipeline": PIPELINE_MAP,
    "product": IND_MAP, "industrial": IND_MAP,
    "man_made": IND_MAP, "utility": UTILITY_MAP,
}


def _clean_id_str(values: pd.Series) -> pd.Series:
    """Convert numeric OSM IDs to stable strings without '.0'."""
    return pd.to_numeric(values, errors="coerce").astype("Int64").astype("string")


def _priority_rank(subtype: str) -> tuple[int, int]:
    """Lower rank means higher priority."""
    if subtype in CORE_SUBTYPE_PRIORITY:
        return 0, CORE_SUBTYPE_PRIORITY.index(subtype)
    if subtype in SUPPORT_SUBTYPE_PRIORITY:
        return 1, SUPPORT_SUBTYPE_PRIORITY.index(subtype)
    return 2, 0


def _attach_manmade_evidence(
    buildings: gpd.GeoDataFrame,
    manmade: gpd.GeoDataFrame,
    projected_crs: str,
) -> gpd.GeoDataFrame:
    """Attach the first man-made polygon containing each building centroid."""
    required = {"id", "geometry", "man_made", "manmade_category"}
    missing = required - set(manmade.columns)
    if missing:
        raise ValueError(f"Man-made input is missing: {sorted(missing)}")

    if buildings.crs is None or manmade.crs is None:
        raise ValueError("Buildings and man-made polygons must have a CRS.")

    result = buildings.drop(
        columns=["manmade_osm_id", "man_made", "manmade_category",],errors="ignore",).copy()

    projected_buildings = result[["geometry"]].to_crs(projected_crs)

    centroids = gpd.GeoDataFrame(
        {"building_id": result.index.to_numpy(),},
        geometry=projected_buildings.geometry.centroid.to_numpy(),
        crs=projected_crs,)

    polygons = (manmade[["id", "geometry", "man_made", "manmade_category",]]
                .rename(columns={"id": "manmade_osm_id"}).to_crs(projected_crs))

    polygons = polygons.loc[polygons.geometry.notna() & ~polygons.geometry.is_empty]

    joined = gpd.sjoin(centroids, polygons, how="left", predicate="within",)

    joined = (joined.drop_duplicates(subset="building_id", keep="first").set_index("building_id"))

    result = result.join(joined[["manmade_osm_id", "man_made", "manmade_category",]])

    result["manmade_osm_id"] = pd.to_numeric(result["manmade_osm_id"],
        errors="coerce",).astype("Int64")

    return result


def _build_zone_lookup(landuse: gpd.GeoDataFrame) -> dict[str, dict]:
    """Build a consistently keyed lookup of industrial-zone OSM tags."""
    required = {"id", "tags", "industrial"}
    missing = required - set(landuse.columns)
    if missing:
        raise ValueError(f"Land-use input is missing: {sorted(missing)}")

    def build_tags(row) -> dict:
        tags = dict(parse_tags(row["tags"]))
        if pd.notna(row["industrial"]):
            tags["industrial"] = row["industrial"]
        return tags

    table = landuse[["id", "tags", "industrial"]].copy()
    table["id_key"] = _clean_id_str(table["id"])
    table["tags_parsed"] = table.apply(build_tags, axis=1)
    return table.dropna(subset=["id_key"]).set_index("id_key")["tags_parsed"].to_dict()


def _resolve_zone_tags(zone_tags: dict) -> tuple[str | None, str | None, str | None]:
    """Tier 1: resolve subtype from zone-level OSM tags."""
    for key in ZONE_TAG_KEY_PRECEDENCE:
        raw = zone_tags.get(key)
        if raw is None:
            continue
        raw = str(raw).strip().lower()
        subtype = "mining_quarry" if key == "resource" else ZONE_TAG_MAPS[key].get(raw)
        if subtype is not None:
            return subtype, key, raw
    return None, None, None


def _resolve_landuse_used(value) -> tuple[str | None, str | None]:
    """Tier 2: resolve subtype from the mapped land-use class."""
    if pd.isna(value):
        return None, None
    raw = str(value).strip().lower()
    subtype = LANDUSE_OVERRIDE.get(raw)
    return subtype, raw if subtype else None


def _resolve_building_votes(voters: pd.DataFrame, value_col: str, total_buildings: int, *,
    bypass_if_weak_support: bool = False,) -> tuple[str | None, str | None]:
    """Resolve core/support votes using count first and priority for ties."""
    counts = voters[value_col].dropna().value_counts()
    if counts.empty:
        return None, None

    core = counts[counts.index.isin(CORE_SUBTYPES)]
    support = counts[counts.index.isin(SUPPORT_SUBTYPES)]

    if not core.empty:
        top = core[core.eq(core.max())].index.tolist()
        return sorted(top, key=_priority_rank)[0], "core"

    turnout = len(voters[value_col].dropna()) / total_buildings * 100 if total_buildings else 0
    if bypass_if_weak_support and turnout < 50:
        return None, None
    if support.empty:
        return None, None

    top = support[support.eq(support.max())].index.tolist()
    return sorted(top, key=_priority_rank)[0], "support"


def _resolve_fallback(group: pd.DataFrame) -> tuple[str, str]:
    """Tier 5: fall back to the modal L1 class."""
    labels = group["final_l1"].dropna()
    winner = labels.mode().iloc[0] if len(labels) else None
    if winner == "filter":
        return "low_demand_infrastructure", "filter_fallback"
    if winner is not None:
        return winner, "final_l1_fallback"
    return "unclassified", "generic_fallback"


def _resolve_group_subtype(
    group: pd.DataFrame,
    zone_tags_lookup: dict[str, dict],
) -> tuple[str, str, object]:
    """Apply the notebook's five-tier industrial-zone hierarchy."""
    total_buildings = len(group)
    landuse_id = group["landuse_osm_id"].iloc[0]
    id_key = _clean_id_str(pd.Series([landuse_id])).iloc[0]

    # Tier 1: zone-level OSM tags.
    subtype, key, raw = _resolve_zone_tags(zone_tags_lookup.get(id_key, {}))
    if subtype is not None:
        return subtype, f"zone_tag_{key}", raw

    # Tier 2: mapped land-use override.
    values = group["landuse_used"].dropna().unique()
    subtype, raw = _resolve_landuse_used(values[0] if len(values) else None)
    if subtype is not None:
        return subtype, "landuse_override", raw

    voters = group[group["final_l1"].eq("industrial")]

    # Tier 3a: direct building raw-label evidence; accept core immediately.
    subtype, kind = _resolve_building_votes(
        voters, "ind_mapped_subtype", total_buildings,
        bypass_if_weak_support=True,
    )
    if subtype is not None and kind == "core":
        return subtype, "ind_map_vote", f"{kind}, n_voters={len(voters)}"
    raw_result = subtype, kind

    # Tier 3b: inherited man-made polygon evidence; accept core immediately.
    subtype, kind = _resolve_building_votes(
        voters, "manmade_category", total_buildings,
        bypass_if_weak_support=False,
    )
    if subtype is not None and kind == "core":
        return subtype, "manmade_vote", f"{kind}, n_voters={len(voters)}"

    # Tier 3c: support-only fallback, preferring direct raw-label evidence.
    if raw_result[0] is not None:
        return raw_result[0], "ind_map_vote", f"{raw_result[1]}, n_voters={len(voters)}"
    if subtype is not None:
        return subtype, "manmade_vote", f"{kind}, n_voters={len(voters)}"

    # Tier 4: final model/rule subtype votes.
    subtype, kind = _resolve_building_votes(
        voters, "final_l2", total_buildings,
        bypass_if_weak_support=False,
    )
    if subtype is not None:
        return subtype, "final_l2_vote", f"{kind}, n_voters={len(voters)}"

    # Tier 5: broad fallback.
    subtype, source = _resolve_fallback(group)
    return subtype, source, None


def group_industrial_buildings(
    classified: pd.DataFrame,
    buildings: gpd.GeoDataFrame,
    landuse: gpd.GeoDataFrame,
    manmade: gpd.GeoDataFrame, projected_crs: str,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Create building-to-parent links and industrial parent records."""
    required_labels = {"final_l1", "final_l2"}
    missing = required_labels - set(classified.columns)
    if missing:
        raise ValueError(f"Classified input is missing: {sorted(missing)}")

    context_columns = [
        "geometry", "raw_label", "landuse_l1", "landuse_l2",
        "landuse_osm_id", "landuse_used", "area", 'is_abandoned',
    ]
    missing = {"id", *context_columns} - set(buildings.columns)
    if missing:
        raise ValueError(f"Building context is missing: {sorted(missing)}")
    missing = {"id", "geometry", "zone_l1", "tags", "industrial", "zone_area_sqm"} - set(landuse.columns)
    if missing:
        raise ValueError(f"Land-use input is missing: {sorted(missing)}")
    if classified.index.name != "id":
        if "id" not in classified.columns:
            raise ValueError("Classified input has no building ID.")
        classified = classified.set_index("id")
    if classified.index.has_duplicates or buildings["id"].duplicated().any():
        raise ValueError("Duplicate building IDs found.")

    context = buildings.set_index("id")[context_columns]
    missing_ids = classified.index.difference(context.index)
    if len(missing_ids):
        raise ValueError(f"{len(missing_ids):,} classified IDs lack building context.")

    work = classified.join(context, how="left")
    work = gpd.GeoDataFrame(work, geometry="geometry", crs=buildings.crs)
    work = _attach_manmade_evidence(work, manmade, projected_crs=projected_crs,)

    # Every building in an industrial zone belongs to that zone parent,
    # regardless of its own final L1 class.
    in_zone = work["landuse_l1"].eq("industrial") & work["landuse_osm_id"].notna()
    standalone = work["final_l1"].eq("industrial") & ~in_zone

    work["parent_id"] = pd.Series(pd.NA, index=work.index, dtype="string")
    work.loc[in_zone, "parent_id"] = "IND_" + _clean_id_str(work.loc[in_zone, "landuse_osm_id"])
    work.loc[standalone, "parent_id"] = "BLDG_" + _clean_id_str(pd.Series(work.index[standalone], index=work.index[standalone]))

    work["ind_mapped_subtype"] = work["raw_label"].map(IND_MAP)
    zone_tags_lookup = _build_zone_lookup(landuse)
    grouped = work.loc[in_zone]

    # Resolve industrial land-use zone parents.
    rows = []
    for parent_id, group in grouped.groupby("parent_id", sort=True):
        subtype, source, evidence = _resolve_group_subtype(group, zone_tags_lookup)
        rows.append({
            "parent_id": parent_id,
            "landuse_osm_id": group["landuse_osm_id"].iloc[0],
            "subtype": subtype,
            "subtype_source": source,
            "subtype_evidence": evidence,
            "n_buildings": len(group),
            "n_industrial_buildings": int(group["final_l1"].eq("industrial").sum()),
            "total_area": group["area"].sum(),
        })
    zone_parents = pd.DataFrame(rows)

    # Resolve standalone industrial parents: final_l2 < man-made < raw tag.
    standalone_bldg = work.loc[standalone].copy()
    standalone_bldg["resolved_subtype"] = standalone_bldg["final_l2"].astype("object")
    standalone_bldg["resolved_source"] = "standalone_final_l2"
    standalone_bldg["resolved_evidence"] = standalone_bldg["final_l2"].astype("object")

    mask = standalone_bldg["manmade_category"].notna()
    standalone_bldg.loc[mask, "resolved_subtype"] = standalone_bldg.loc[mask, "manmade_category"]
    standalone_bldg.loc[mask, "resolved_source"] = "standalone_manmade"
    standalone_bldg.loc[mask, "resolved_evidence"] = standalone_bldg.loc[mask, "man_made"]

    mask = standalone_bldg["ind_mapped_subtype"].notna()
    standalone_bldg.loc[mask, "resolved_subtype"] = standalone_bldg.loc[mask, "ind_mapped_subtype"]
    standalone_bldg.loc[mask, "resolved_source"] = "standalone_ind_map"
    standalone_bldg.loc[mask, "resolved_evidence"] = standalone_bldg.loc[mask, "raw_label"]

    standalone_parents = pd.DataFrame({
        "parent_id": standalone_bldg["parent_id"].to_numpy(),
        "landuse_osm_id": pd.array([pd.NA] * len(standalone_bldg), dtype="Int64"),
        "subtype": standalone_bldg["resolved_subtype"].to_numpy(),
        "subtype_source": standalone_bldg["resolved_source"].to_numpy(),
        "subtype_evidence": standalone_bldg["resolved_evidence"].to_numpy(),
        "n_buildings": 1,
        "n_industrial_buildings": 1,
        "total_area": standalone_bldg["area"].to_numpy(),
        "parent_type": "standalone_building",
    })

    # Add zone and child-union geometries to industrial-zone parents.
    industrial_zones = landuse.loc[landuse["zone_l1"].eq("industrial")].copy()
    zone_geometry = pd.DataFrame({
        "parent_id": "IND_" + _clean_id_str(industrial_zones["id"]),
        "landuse_geometry": industrial_zones.geometry.to_numpy(),
        "zone_area_sqm": industrial_zones["zone_area_sqm"].to_numpy(),
    })
    building_union = (
        grouped.groupby("parent_id")["geometry"]
        .apply(lambda geometries: gpd.GeoSeries(geometries, crs=work.crs).union_all())
        .rename("buildings_union_geometry").reset_index()
    )

    zone_parents["parent_id"] = zone_parents["parent_id"].astype("string")
    zone_geometry["parent_id"] = zone_geometry["parent_id"].astype("string")
    zone_parent_gdf = zone_parents.merge(zone_geometry, on="parent_id", how="left")
    zone_parent_gdf = zone_parent_gdf.merge(building_union, on="parent_id", how="left")
    zone_parent_gdf["parent_type"] = "industrial_landuse_zone"
    zone_parent_gdf = gpd.GeoDataFrame(
        zone_parent_gdf, geometry="landuse_geometry", crs=work.crs
    )

    standalone_parent_gdf = gpd.GeoDataFrame(
        standalone_parents,
        geometry=standalone_bldg.geometry.to_numpy(),
        crs=work.crs,
    ).rename_geometry("landuse_geometry")
    standalone_parent_gdf["buildings_union_geometry"] = standalone_parent_gdf.geometry
    standalone_parent_gdf["zone_area_sqm"] = standalone_parent_gdf["total_area"]

    parents = pd.concat([zone_parent_gdf, standalone_parent_gdf], ignore_index=True)
    parents = gpd.GeoDataFrame(parents, geometry="landuse_geometry", crs=work.crs)
    if parents["parent_id"].duplicated().any():
        raise ValueError("Duplicate industrial parent IDs found.")

    parent_lookup = parents.set_index("parent_id")
    work["parent_subtype"] = work["parent_id"].map(parent_lookup["subtype"])
    work["parent_subtype_source"] = work["parent_id"].map(parent_lookup["subtype_source"])
    work["parent_subtype_evidence"] = work["parent_id"].map(parent_lookup["subtype_evidence"])

    # Integrity checks from the notebook.
    linked_ids = set(work["parent_id"].dropna().astype(str))
    known_ids = set(parents["parent_id"].astype(str))
    orphans = linked_ids - known_ids
    if orphans:
        raise ValueError(f"Orphaned parent references: {list(orphans)[:10]}")

    area_check = work.groupby("parent_id")["area"].sum()
    discrepancy = parents.set_index("parent_id")["total_area"].subtract(area_check).abs()
    max_discrepancy = float(discrepancy.max()) if len(discrepancy) else 0.0
    if max_discrepancy > 1e-6:
        raise ValueError(f"Maximum parent-area discrepancy is {max_discrepancy:.6f} m².")

    print("\n" + "=" * 60)
    print("INDUSTRIAL GROUPING SUMMARY")
    print("=" * 60)
    print(f"Buildings in industrial zones: {in_zone.sum():>12,}")
    print(f"Standalone industrial:         {standalone.sum():>12,}")
    print(f"Industrial-zone parents:       {len(zone_parent_gdf):>12,}")
    print(f"Standalone parents:            {len(standalone_parent_gdf):>12,}")
    print(f"Total parent records:          {len(parents):>12,}")
    print(f"Orphaned references:           {len(orphans):>12,}")
    print(f"Maximum area discrepancy:      {max_discrepancy:>12.6f}")

    return work, parents
