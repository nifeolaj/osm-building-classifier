"""Clean and map OSM points of interest."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from osm_classifier.cleaning.common import (drop_relations, filter_geometry_types,
    fix_invalid_geometries, replace_fake_nulls, report_duplicate_ids,)
from osm_classifier.taxonomy.tag_maps.amenity_map import apply_amenity_map
from osm_classifier.taxonomy.tag_maps.building_map import apply_building_map
from osm_classifier.taxonomy.tag_maps.shop_map import apply_shop_map
from osm_classifier.taxonomy.tag_maps.tourism_map import apply_tourism_map

DIRECT_MAP = {
    "bank": ("commercial", "office"),
    "bureau_de_change": ("commercial", "office"),
    "post_office": ("commercial", "office"),
    "restaurant": ("commercial", "food_drink"),
    "cafe": ("commercial", "food_drink"),
    "bar": ("commercial", "food_drink"),
    "fast_food": ("commercial", "food_drink"),
    "pub": ("commercial", "food_drink"),
    "ice_cream": ("commercial", None),
    "food_court": ("commercial", "food_drink"),
    "biergarten": ("commercial", "food_drink"),
    "bakery": ("commercial", "food_drink"),
    "cinema": ("civic", "cultural"),
    "gambling": ("civic", "recreation"),
    "nightclub": ("commercial", "food_drink"),
    "car_rental": ("commercial", "office"),
    "car_wash": ("commercial", "retail"),
    "car_repair": ("commercial", "retail"),
    "bicycle_rental": ("commercial", "office"),
    "travel_agency": ("commercial", "office"),
    "hotel": ("commercial", "accommodation"),
    "hostel": ("commercial", "accommodation"),
    "guest_house": ("commercial", "accommodation"),
    "arts_centre": ("civic", "cultural"),
    "library": ("civic", "cultural"),
    "museum": ("civic", "cultural"),
    "theatre": ("civic", "cultural"),
    "zoo": ("civic", "cultural"),
    "school": ("civic", "school"),
    "driving_school": ("civic", "school"),
    "music_school": ("civic", "school"),
    "university": ("civic", "higher_ed"),
    "college": ("civic", "higher_ed"),
    "police": ("civic", "emergency_service"),
    "social_facility": ("civic", "care_facility"),
    "social_centre": ("civic", "community"),
    "hospital": ("civic", "hospital"),
    "dentist": ("civic", "clinic"),
    "doctors": ("civic", "clinic"),
    "clinic": ("civic", "clinic"),
    "kindergarten": ("civic", "kindergarten"),
    "childcare": ("civic", "kindergarten"),
    "parking": ("transportation", "parking"),
}

POI_TAG_COLUMNS = [
    "amenity", "building", "tourism", "shop", *DIRECT_MAP
]

CONFIDENCE = {
    "hospital": 10, "clinic": 10, "doctors": 10, "dentist": 10,
    "police": 10, "school": 10, "university": 10, "college": 10,
    "kindergarten": 10, "childcare": 10, "amenity": 11,
    "museum": 9, "library": 9, "theatre": 9, "cinema": 9,
    "hotel": 9, "hostel": 9, "guest_house": 9,
    "nightclub": 8, "gambling": 8, "bank": 8, "post_office": 8,
    "car_repair": 8, "car_wash": 8, "car_rental": 8,
    "bicycle_rental": 8, "travel_agency": 8,
    "bureau_de_change": 8, "driving_school": 8,
    "music_school": 8, "social_facility": 8, "arts_centre": 8,
    "restaurant": 7, "fast_food": 7, "cafe": 7, "pub": 7,
    "bar": 7, "biergarten": 7, "food_court": 7, "bakery": 7,
    "building": 7, "shop": 6, "zoo": 6, "ice_cream": 5,
    "tourism": 3, "parking": 2,
}

L1_PRIORITY = [
    "military", "industrial", "civic", "semi_commercial",
     "commercial", "residential", "transportation",
    "agricultural", "filter",
]


def _map_value(column: str, value: str):
    """Apply the correct mapping function for a POI column."""
    if column == "amenity":
        return apply_amenity_map(value)[:2]
    if column == "building":
        return apply_building_map(value)[:2]
    if column == "shop":
        return apply_shop_map(value)[:2]
    if column == "tourism":
        return apply_tourism_map(value)
    # For direct columns such as restaurant=True, use the column name.
    return DIRECT_MAP.get(column, (None, None))


def _extract_candidates(row: dict) -> list[dict]:
    """Extract all valid classification candidates from one POI."""
    candidates = []

    for column in POI_TAG_COLUMNS:
        value = row.get(column)

        if pd.isna(value) or str(value).strip().lower() in {"", "no"}:
            continue

        value = str(value).strip().lower()
        l1, l2 = _map_value(column, value)

        if column == "bicycle_rental" and value not in {"shop", "institutional"}:
            continue
        if column == "parking" and value != "multi-storey":
            continue
        if column == "police" and value == "academy":
            l2 = "school"
        if l1 is None:
            continue

        display_value = value if column in {"amenity", "building", "shop", "tourism"} else column

        candidates.append({
            "l1": l1,
            "l2": l2,
            "source": column,
            "tag": display_value,
            "confidence": CONFIDENCE.get(column, 3),
        })

    return candidates


def _resolve_l2(candidates: list[dict]):
    """Resolve the most appropriate L2 subtype from compatible candidates."""
    
    concrete = [candidate for candidate in candidates if candidate["l2"] is not None]
    if not concrete:
        return None
    # When all candidates agree, return the shared subtype.
    if len({candidate["l2"] for candidate in concrete}) == 1:
        return concrete[0]["l2"]
    # Otherwise choose the subtype supported by the highest-confidence tag
    highest = max(candidate["confidence"] for candidate in concrete)
    return next(candidate["l2"] for candidate in concrete if candidate["confidence"] == highest)


def _semi_commercial_l2(candidates: list[dict], secondary_l1: str) -> str:
    """
    When residential + commercial coexist, build a semi_commercial L2.
    E.g.  residential + retail  →  residential_retail
          residential + office  →  residential_office
          residential + None    →  residential_commercial
    """
    secondary = [candidate for candidate in candidates if candidate["l1"] == secondary_l1]
    subtype = _resolve_l2(secondary) or secondary_l1
    return f"residential_{subtype}"


def _resolve_candidates(candidates: list[dict]) -> dict:
    """Resolve all candidates for one POI into one final classification."""
    result = {"poi_l1": None, "poi_l2": None, "poi_source": None, "poi_used": None, 
            "all_candidates": str([(candidate["source"], candidate["l1"], candidate["l2"])
            for candidate in candidates]),}
    # No usable classification evidence.
    if not candidates:
        return result
    # A single candidate requires no conflict resolution.
    if len(candidates) == 1:
        winner = candidates[0]
        result.update(poi_l1=winner["l1"], poi_l2=winner["l2"],
            poi_source=winner["source"], poi_used=winner["tag"],)
        return result

    l1_values = {candidate["l1"] for candidate in candidates}
    # Multiple tags agree at L1 but may differ at L2.
    if len(l1_values) == 1:
        winner = max(candidates, key=lambda candidate: candidate["confidence"])
        result.update(poi_l1=winner["l1"], poi_l2=_resolve_l2(candidates),
            poi_source="+".join(sorted({c["source"] for c in candidates})),
            poi_used=winner["tag"],)
        return result
    
    # Residential plus commercial evidence indicates mixed use.
    if {"residential", "commercial"}.issubset(l1_values):
        winner = max(candidates, key=lambda candidate: candidate["confidence"])
        result.update(poi_l1="semi_commercial", poi_l2=_semi_commercial_l2(candidates, "commercial"),
            poi_source="+".join(sorted({c["source"] for c in candidates})), poi_used=winner["tag"],)
        return result

    if {"residential", "civic"}.issubset(l1_values):
        winner = max(candidates, key=lambda candidate: candidate["confidence"])
        result.update(poi_l1="semi_commercial", poi_l2="residential_civic",
            poi_source="+".join(sorted({c["source"] for c in candidates})), poi_used=winner["tag"],)
        return result

    # For all remaining conflicts, keep candidates with the highest
    # confidence and use L1_PRIORITY only to break equal-confidence ties.
    highest = max(candidate["confidence"] for candidate in candidates)
    top = [candidate for candidate in candidates if candidate["confidence"] == highest]
    best_l1 = min({candidate["l1"] for candidate in top}, key=lambda value: L1_PRIORITY.index(value)
        if value in L1_PRIORITY else 99,)
    winning = [candidate for candidate in top if candidate["l1"] == best_l1]
    winner = winning[0]

    result.update(poi_l1=best_l1, poi_l2=_resolve_l2(winning),
        poi_source=winner["source"], poi_used=winner["tag"],)
    return result


def map_pois(gdf: gpd.GeoDataFrame, building_ids: pd.Series | None = None,) -> gpd.GeoDataFrame:
    """Clean POIs, resolve their tags and retain mapped POIs."""
    gdf = replace_fake_nulls(gdf, "pois")
    gdf = filter_geometry_types(gdf, {"Point", "Polygon", "MultiPolygon"}, "pois")
    gdf = fix_invalid_geometries(gdf, "pois")
    gdf = drop_relations(gdf, "pois")
    gdf["id"] = gdf["id"].astype(str)

    if building_ids is not None:
        building_ids = set(building_ids.dropna().astype(str))
        # Pyrosm may return a building way both in the building layer and in
        # the POI layer. Remove the POI copy to avoid double representation.
        duplicate_way = gdf["osm_type"].eq("way") & gdf["id"].isin(building_ids)
        print(f"[pois] Building-way duplicates removed: {duplicate_way.sum():,}")
        gdf = gdf.loc[~duplicate_way].copy()

    # Node and way IDs use separate OSM namespaces and may share the same
    # numeric value. Prefix only duplicated IDs with their OSM object type.
    duplicate_ids = gdf["id"].duplicated(keep=False)
    gdf.loc[duplicate_ids, "id"] = (gdf.loc[duplicate_ids, "osm_type"].astype(str)
        + "_" + gdf.loc[duplicate_ids, "id"])
    report_duplicate_ids(gdf, "pois")

    available_tags = [column for column in POI_TAG_COLUMNS if column in gdf.columns]
    has_tags = gdf[available_tags].notna().any(axis=1)
    records = gdf.loc[has_tags, ["id", *available_tags]].to_dict("records")

    results = []
    for row in records:
        resolution = _resolve_candidates(_extract_candidates(row))
        resolution["id"] = row["id"]
        results.append(resolution)

    mapped = pd.DataFrame(results)
    gdf = gdf.merge(mapped, on="id", how="left")
    # Remove unmapped POIs and values intentionally marked as filters.
    gdf = gdf[gdf["poi_l1"].notna() & gdf["poi_l1"].ne("filter")].copy()

    keep = ["id", "poi_l1", "poi_l2", "poi_source", "poi_used", "all_candidates","geometry",]

    keep = [column for column in keep if column in gdf.columns]
    print(f"[pois] Mapped POIs retained: {len(gdf):,}")
    return gdf[keep].copy()