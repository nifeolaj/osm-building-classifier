"""Map classification signals found inside the OSM tags column."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from osm_classifier.taxonomy.tag_maps.shop_map import apply_shop_map
from osm_classifier.taxonomy.tag_maps.tag_map import apply_tag_map
from osm_classifier.taxonomy.tag_parser import parse_tags

DIRECT_MAP = {
    "community_centre": ("civic", "community"),
    "diocese": ("civic", "religious"),
    "military": ("military", None),
    "healthcare": ("civic", "clinic"),
    "social_facility": ("civic", "care_facility"),
    "social_facility:for": ("civic", "care_facility"),
    "building:use:retail": ("commercial", "retail"),
    "bunker_type": ("military", "bunker"),
    "religion": ("civic", "religious"),
    "denomination": ("civic", "religious"),
    "building:use:residential": ("residential", None),
    "substation": ("industrial", "utilities"),
    "cuisine": ("commercial", "food_drink"),
    "parish": ("civic", "religious"),
    "diet:vegetarian": ("commercial", "food_drink"),
    "railway:signal_box": ("transportation", "maintenance"),
    "castle_type": ("civic", "cultural"),
    "healthcare:speciality": ("civic", "clinic"),
    "diet:vegan": ("commercial", "food_drink"),
    "second_hand": ("commercial", "retail"),
    "building:use:office": ("commercial", "office"),
    "drive_through": ("commercial", None),
    "delivery": ("commercial", None),
    "organic": ("commercial", None),
    "service:vehicle:car_repair": ("commercial", "retail"),
    "education": ("civic", "school"),
    "diet:halal": ("commercial", None),
    "museum": ("civic", "cultural"),
    "building:use:education": ("civic", "school"),
    "townhall:type": ("civic", "government_office"),
    "product": ("industrial", "manufacturing"),
}

APPLY_MAP_KEYS = {"proposed", "construction", "man_made", "power", "leisure",
    "tourism", "historic", "building:type:de", "emergency", "aeroway",
    "railway", "public_transport", "building:type", "house", "government",
    "industrial", "disused", "disused:building", "abandoned:building", "ruins",
    "disused:shop", "disused:amenity", "disused:tourism",}

FILTER_KEYS = {"bicycle_parking", "abandoned", "demolished", "building:use:parking",
    "shelter_type", "bench", "parking", "toilets:disposal",}

STRATEGY = {
    **{key: "apply_map" for key in APPLY_MAP_KEYS},
    **DIRECT_MAP,
    **{key: "filter" for key in FILTER_KEYS},
}

ABANDONED_KEYS = {"disused", "disused:building", "abandoned", "abandoned:building",
    "demolished", "ruins", "disused:shop", "disused:amenity", "disused:tourism",}

YES_ONLY_KEYS = {"building:use:retail", "building:use:residential",
    "building:use:office", "building:use:education", "service:vehicle:car_repair",}

TAG_USED_OVERRIDES = {"bunker_type": "bunker", "castle_type": "castle",
    "social_facility:for": "social_facility", "museum": "museum",
    "townhall:type": "townhall", "railway:signal_box": "signal_box",}

CONFIDENCE = {
    'building:use:retail':      10, 'building:use:office':      10,
    'building:use:residential': 10, 'education':                10,
    'service:vehicle:car_repair':10,'castle_type':              10,
    'townhall:type':            10, 'bunker_type':              10,
    'museum':                   10, 'railway:signal_box':       10,
    'building:type':             9, 'building:type:de':          9,
    'healthcare:speciality':     8, 'house':                     9,
    'military':                  9, 'second_hand':               9,
    'industrial':                9, 'building:use:education':    9,
    'social_facility:for':       8, 'public_transport':          8,
    'social_facility':           8, 'leisure':                   8,
    'product':                   8, 'aeroway':                   8,
    'man_made':                  8, 'healthcare':                9,
    'community_centre':          6, 'government':                7,
    'tourism':                   7, 
    'delivery':                  7, 'drive_through':             7,
    'historic':                  5, 'proposed':                  5,
    'construction':              5, 'railway':                   4,
    'religion':                  2, 'denomination':              2,
    'diocese':                   2, 'parish':                    2,
    'organic':                   1, 'substation':                7,
    'power':                     7,    
}

DEFAULT_CONFIDENCE = 3

L1_PRIORITY = ["military", "industrial", "civic", "semi_commercial",
    "commercial", "residential", "transportation", "agricultural", "filter",]

TAG_RESULT_COLUMNS  = ["tag_l1", "tag_l2", "is_abandoned",
    "tag_source", "tag_used", "all_candidates",]

def _normalise(value) -> str:
    return str(value).strip().lower()


def _map_candidate(key: str, value: str) -> tuple[str | None, str | None]:
    """Map one selected tag key-value pair."""
    strategy = STRATEGY.get(key)
    value = _normalise(value)
    
    if isinstance(strategy, tuple):
        if key in YES_ONLY_KEYS and value != "yes":
            return None, None
        l1, l2 = strategy
        if key == "healthcare":
            if value == "hospital":
                l2 = "hospital"
            elif value == "pharmacy":
                l1, l2 = "commercial", "retail"
            elif value in {"rehabilitation", "nursing_home"}:
                l2 = "care_facility"
        elif key == "education":
            if value in {"kindergarten", "pre-school", "preschool"}:
                l2 = "kindergarten"
            elif value in {"college", "university"}:
                l2 = "higher_ed"
        return l1, l2

    if strategy == "apply_map":
        if key == "disused:shop":
            if value == "no":
                return "commercial", "retail"
            result = apply_shop_map(value)
            return result[:2] if result else (None, None)
        if key == "industrial":
            result = apply_tag_map(value)
            if result and result[0] == "industrial":
                return result[:2]
            return "industrial", None
        result = apply_tag_map(value)
        return result[:2] if result else (None, None)

    if strategy == "filter":
        if key == "parking" and value == "multi-storey":
            return "transportation", "parking"
        if key == "bench" and value == "no":
            return None, None
        if key == "building:use:parking" and value != "yes":
            return None, None
        if key in {"abandoned", "demolished"} and value == "no":
            return None, None
        return "filter", None

    return None, None


def extract_candidates(tags_value) -> tuple[list[dict], bool]:
    """Generate classification candidates from one tags value."""
    all_tags = parse_tags(tags_value)

    tags = {key: value for key, value in all_tags.items()
        if key in STRATEGY and value is not None
        and str(value).strip().lower() not in {"", "nan", "none", "null"}}

    is_abandoned = any(key in ABANDONED_KEYS and _normalise(value) != "no"
        for key, value in tags.items())

    candidates = []

    for key, value in tags.items():
        l1, l2 = _map_candidate(key, value)
        if l1 is None:
            continue
        candidates.append({"l1": l1, "l2": l2, "source": key,
            "tag": TAG_USED_OVERRIDES.get(key, _normalise(value)),
            "confidence": CONFIDENCE.get(key, DEFAULT_CONFIDENCE),})

    return candidates, is_abandoned

def _resolve_l2(candidates: list[dict]) -> str | None:
    """Resolve subtype conflicts using source confidence."""
    concrete = [candidate for candidate in candidates if candidate["l2"] is not None]

    if not concrete:
        return None

    unique_l2 = {candidate["l2"] for candidate in concrete}
    if len(unique_l2) == 1:
        return concrete[0]["l2"]

    highest = max(candidate["confidence"] for candidate in concrete)
    winners = [candidate for candidate in concrete if candidate["confidence"] == highest]
    if len(winners) > 1:
        return None
    
    return winners[0]["l2"]


def _l1_rank(l1: str) -> int:
    try:
        return L1_PRIORITY.index(l1)
    except ValueError:
        return 99


def _semi_commercial_l2(candidates: list[dict], secondary_l1: str,) -> str:
    """Resolve the L2 subtype for a semi-commercial building."""
    if secondary_l1 == "civic":
        return "residential_civic"

    commercial = [candidate for candidate in candidates if candidate["l1"] == "commercial"]
    subtype = _resolve_l2(commercial) or "commercial"
    return f"residential_{subtype}"

def resolve_candidates(candidates: list[dict]) -> dict:
    """Resolve candidates into one final tag classification."""
    result = {"tag_l1": None, "tag_l2": None, "tag_source": None, "tag_used": None, 
        "all_candidates": str([(candidate["source"], candidate["l1"], candidate["l2"],)
            for candidate in candidates]),}
    if not candidates:
        return result
    if len(candidates) == 1:
        winner = candidates[0]
        result.update(tag_l1=winner["l1"], tag_l2=winner["l2"],
            tag_source=winner["source"], tag_used=winner["tag"],)
        return result

    def all_sources(items: list[dict]) -> str:
        return "+".join(sorted({candidate["source"] for candidate in items}))

    l1_values = {candidate["l1"] for candidate in candidates}

    if len(l1_values) == 1:
        winner = max(candidates, key=lambda candidate: (
                candidate["confidence"], candidate["source"],),)
        result.update(tag_l1=next(iter(l1_values)), tag_l2=_resolve_l2(candidates),
            tag_source=all_sources(candidates), tag_used=winner["tag"],)
        return result

    if {"residential", "commercial"}.issubset(l1_values):
        secondary_l1 = "commercial"
    elif {"residential", "civic"}.issubset(l1_values):
        secondary_l1 = "civic"
    else:
        secondary_l1 = None

    if secondary_l1:
        winner = max(candidates, key=lambda candidate: 
            (candidate["confidence"], candidate["source"],),)
        result.update(tag_l1="semi_commercial", tag_l2=_semi_commercial_l2(
                candidates, secondary_l1,), tag_source=all_sources(candidates), tag_used=winner["tag"],)
        return result

    highest = max(candidate["confidence"] for candidate in candidates)
    top = [candidate for candidate in candidates if candidate["confidence"] == highest]
    best_l1 = min({candidate["l1"] for candidate in top}, key=_l1_rank,)
    winners = [candidate for candidate in top if candidate["l1"] == best_l1]

    winner = max(winners, key=lambda candidate: candidate["source"],)

    result.update(tag_l1=best_l1, tag_l2=_resolve_l2(winners),
        tag_source=winner["source"], tag_used=winner["tag"],)
    return result


def classify_tags(tags_value) -> dict:
    """Classify one raw OSM tags value."""
    candidates, is_abandoned = extract_candidates(tags_value)
    result = resolve_candidates(candidates)
    result["is_abandoned"] = is_abandoned
    return result


def map_building_tags(gdf: gpd.GeoDataFrame, chunk_size: int = 500_000,) -> gpd.GeoDataFrame:
    """Map the tags column."""
    if "tags" not in gdf.columns:
        raise ValueError("Building dataset has no 'tags' column.")

    gdf = gdf.copy()

    for column in ["tag_l1", "tag_l2", "tag_source", "tag_used", "all_candidates",]:
        gdf[column] = None

    gdf["is_abandoned"] = False

    has_tags = gdf["tags"].notna() & gdf["tags"].ne("{}")
    indices = gdf.index[has_tags]
    print(f"[tags] Buildings with tags to inspect: {len(indices):,}")

    for start in range(0, len(indices), chunk_size):
        batch_indices = indices[start:start + chunk_size]
        records = [classify_tags(value) for value in gdf.loc[batch_indices, "tags"]]
        mapped = pd.DataFrame(records, index=batch_indices)

        for column in TAG_RESULT_COLUMNS :
            gdf.loc[batch_indices, column] = mapped[column]

        completed = min(start + chunk_size, len(indices))
        print(f"[tags] Processed {completed:,} / "f"{len(indices):,}")

    classified = int(gdf["tag_l1"].notna().sum())
    abandoned = int(gdf["is_abandoned"].sum())

    print(f"[tags] Classified: {classified:,}")
    print(f"[tags] Abandoned/disused: {abandoned:,}")

    return gdf