"""Build the complete model feature matrix."""

from __future__ import annotations

from collections.abc import Mapping

import geopandas as gpd
import numpy as np

from osm_classifier.features.geometry_features import (GEOMETRY_FEATURES, add_geometry_features,)
from osm_classifier.features.neighbour_features import (NEIGHBOUR_FEATURES, add_neighbour_features,)
from osm_classifier.features.context_features import (LANDUSE_FEATURES, POI_FEATURES,
    ROAD_FEATURES, RAIL_WATER_FEATURES, add_landuse_features, add_poi_features,
    add_road_features, add_rail_water_features,)


FEATURE_COLUMNS = ["address_tier", *GEOMETRY_FEATURES, *NEIGHBOUR_FEATURES, 
    *LANDUSE_FEATURES, *POI_FEATURES, *ROAD_FEATURES, *RAIL_WATER_FEATURES,]


def _validate_inputs(buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame,
    pois: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, railways: gpd.GeoDataFrame,
    waterways: gpd.GeoDataFrame,) -> None:
    """Validate required input layers and columns."""
    required_building_columns = {"geometry", "address_tier",
        "stage1_l1", "stage1_l2", "stage2_l1", "stage2_l2",}

    missing = required_building_columns - set(buildings.columns)
    if missing:
        raise ValueError(f"Building input is missing: {sorted(missing)}")

    layers = {"buildings": buildings, "landuse": landuse, "pois": pois,
        "roads": roads,"railways": railways, "waterways": waterways,}

    for name, layer in layers.items():
        if layer.crs is None:
            raise ValueError(f"{name} dataset has no CRS.")


def _feature_report(buildings: gpd.GeoDataFrame) -> None:
    """Report missing and infinite values in generated features."""
    missing_columns = [
        column for column in FEATURE_COLUMNS
        if column not in buildings.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Feature engineering did not create: {missing_columns}"
        )

    feature_data = buildings[FEATURE_COLUMNS]
    null_counts = feature_data.isna().sum()
    null_counts = null_counts[null_counts > 0]

    numeric = feature_data.select_dtypes(include=[np.number])
    infinite_counts = np.isinf(numeric).sum()
    infinite_counts = infinite_counts[infinite_counts > 0]

    print("\n" + "=" * 60)
    print("FEATURE ENGINEERING SUMMARY")
    print("=" * 60)
    print(f"Buildings:          {len(buildings):>12,}")
    print(f"Model features:     {len(FEATURE_COLUMNS):>12,}")

    if null_counts.empty:
        print("Missing values:                0")
    else:
        print("\nFeatures containing missing values:")
        print(null_counts.to_string())

    if infinite_counts.empty:
        print("Infinite values:               0")
    else:
        print("\nFeatures containing infinite values:")
        print(infinite_counts.to_string())


def build_feature_matrix(
    buildings: gpd.GeoDataFrame,
    landuse: gpd.GeoDataFrame,
    pois: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    railways: gpd.GeoDataFrame,
    waterways: gpd.GeoDataFrame,
    projected_crs: str,
    config: Mapping,
) -> gpd.GeoDataFrame:
    """Run the complete feature-engineering pipeline."""
    _validate_inputs(
        buildings, landuse, pois,
        roads, railways, waterways,
    )

    feature_config = config["features"]

    print("\n[features] 1/6 Geometry")
    buildings = add_geometry_features(
        buildings, projected_crs
    )

    print("\n[features] 2/6 Building neighbours")
    buildings = add_neighbour_features(
        buildings, projected_crs
    )

    print("\n[features] 3/6 Land use")
    landuse_config = feature_config["landuse"]
    buildings = add_landuse_features(
        buildings,
        landuse,
        projected_crs,
        max_distance_m=landuse_config["max_distance_m"],
        boundary_segment_m=landuse_config["boundary_segment_m"],
        neighbour_radius_m=landuse_config["neighbour_radius_m"],
        query_chunk_size=landuse_config["query_chunk_size"],
    )

    print("\n[features] 4/6 POIs")
    poi_config = feature_config["poi"]
    buildings = add_poi_features(
        buildings,
        pois,
        projected_crs,
        max_distance_m=poi_config["max_distance_m"],
        query_chunk_size=poi_config["query_chunk_size"],
    )

    print("\n[features] 5/6 Roads")
    road_config = feature_config["roads"]
    buildings = add_road_features(
        buildings,
        roads,
        projected_crs,
        max_distance_m=road_config["max_distance_m"],
        boundary_segment_m=road_config["boundary_segment_m"],
        density_radius_m=road_config["density_radius_m"],
        query_chunk_size=road_config["query_chunk_size"],
    )

    print("\n[features] 6/6 Railways and waterways")
    rail_water_config = feature_config["rail_water"]
    buildings = add_rail_water_features(
        buildings,
        railways,
        waterways,
        projected_crs,
        max_distance_m=rail_water_config["max_distance_m"],
        boundary_segment_m=rail_water_config["boundary_segment_m"],
        density_radius_m=rail_water_config["density_radius_m"],
        query_chunk_size=rail_water_config["query_chunk_size"],
    )

    _feature_report(buildings)
    return buildings