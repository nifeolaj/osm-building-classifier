"""Land-use and surrounding-building-area features."""

from __future__ import annotations

import gc

import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree
from shapely import get_coordinates
from shapely.strtree import STRtree


LANDUSE_FEATURES = ["dist_to_residential", "dist_to_commercial", "dist_to_industrial",
    "dist_to_agricultural", "buildings_in_same_zone", "zone_total_area", "building_area_fraction",
    "zone_building_density", "neighbour_mean_area_200m", "neighbour_max_area_200m", "neighbour_std_area_200m",]

LANDUSE_ZONE_TYPES = ["residential", "commercial", "industrial", "agricultural",]


def _distance_to_landuse(building_coords: np.ndarray, building_centroids, landuse: gpd.GeoDataFrame,
    zone_type: str, *, max_distance_m: float, boundary_segment_m: float,) -> np.ndarray:
    """
    Approximate distance from every building centroid to a land-use zone.

    Zone boundaries are densified before constructing the coordinate tree.
    Buildings inside a zone receive a distance of zero.
    """
    zones = landuse[landuse["zone_l1"].eq(zone_type)]

    if zones.empty:
        print(f"[features] No {zone_type} zones; using {max_distance_m:g} m.")
        return np.full(len(building_coords), max_distance_m, dtype=np.float32,)

    dense_geometries = zones.geometry.segmentize(max_segment_length=boundary_segment_m)
    zone_coords = get_coordinates(dense_geometries)
    print(f"[features] {zone_type}: {len(zone_coords):,} boundary vertices")
    zone_coords = np.unique(zone_coords, axis=0)
    print(f"[features] {zone_type}: {len(zone_coords):,} unique vertices")

    coordinate_tree = cKDTree(zone_coords)
    distances, _ = coordinate_tree.query(building_coords, k=1, distance_upper_bound=max_distance_m,)
    distances = np.where(np.isinf(distances), max_distance_m, distances,).astype(np.float32)

    # Correct the boundary approximation for buildings located inside a zone polygon.
    polygon_tree = STRtree(zones.geometry.values)
    matches = polygon_tree.query(building_centroids, predicate="intersects",)

    if matches.size:
        inside_indices = np.unique(matches[0])
        distances[inside_indices] = 0.0
        print(f"[features] {zone_type}: {len(inside_indices):,} buildings inside zones")

    del coordinate_tree, polygon_tree
    del zone_coords, dense_geometries
    gc.collect()

    return distances


def _add_zone_cluster_features(buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame,) -> None:
    """Add statistics describing the building's assigned land-use polygon."""
    if "landuse_osm_id" not in buildings.columns:
        raise ValueError("Missing 'landuse_osm_id'. Stage 2 must attach land-use polygons first.")

    required_landuse_columns = {"id", "zone_area_sqm",}
    missing = required_landuse_columns - set(landuse.columns)
    if missing:
        raise ValueError(f"Land-use input is missing: {sorted(missing)}")

    zone_counts = (buildings.loc[buildings["landuse_osm_id"].notna(), "landuse_osm_id",].value_counts())
    buildings["buildings_in_same_zone"] = (buildings["landuse_osm_id"].map(zone_counts).fillna(0).astype(np.int32))

    zone_area_lookup = (landuse.loc[landuse["zone_area_sqm"].notna(),
            ["id", "zone_area_sqm"],].drop_duplicates("id").set_index("id")["zone_area_sqm"])
    buildings["zone_total_area"] = (buildings["landuse_osm_id"].map(zone_area_lookup).fillna(0).astype(np.float32))

    has_zone_area = buildings["zone_total_area"].gt(0)
    buildings["building_area_fraction"] = np.where(has_zone_area,
        buildings["area"] / buildings["zone_total_area"], 0.0,).astype(np.float32)
    buildings["zone_building_density"] = np.where(has_zone_area, buildings["buildings_in_same_zone"]
        / (buildings["zone_total_area"] / 10_000), 0.0,).astype(np.float32)

    print(f"[features] Median buildings in same zone: {buildings['buildings_in_same_zone'].median():.0f}")
    print(f"[features] Median building-area fraction: {buildings['building_area_fraction'].median():.4f}")
    print(f"[features] Median zone building density: {buildings['zone_building_density'].median():.2f}")


def _add_neighbour_area_features(buildings: gpd.GeoDataFrame, projected: gpd.GeoDataFrame,
    *, radius_m: float, chunk_size: int,) -> None:
    """Add building-area statistics within the specified radius."""
    geometries = projected.geometry.values

    building_areas = (buildings["area"].to_numpy(dtype=np.float64))

    tree = STRtree(geometries)

    neighbour_mean = np.zeros(len(buildings), dtype=np.float32,)
    neighbour_max = np.zeros(len(buildings), dtype=np.float32,)
    neighbour_std = np.zeros(len(buildings), dtype=np.float32,)

    print(f"[features] Computing neighbour-area statistics within {radius_m:g} m...")
    for start in range(0, len(buildings), chunk_size):
        end = min(start + chunk_size, len(buildings))

        left_indices, right_indices = tree.query(geometries[start:end], predicate="dwithin", distance=radius_m,)
        global_left = left_indices + start

        # Remove the building's match with itself.
        not_self = global_left != right_indices
        local_left = left_indices[not_self]
        neighbour_indices = right_indices[not_self]

        if len(local_left):
            areas = building_areas[neighbour_indices]
            batch_size = end - start
            counts = np.bincount(local_left, minlength=batch_size,)

            area_sum = np.bincount(local_left, weights=areas, minlength=batch_size,)
            area_squared_sum = np.bincount(local_left, weights=areas**2, minlength=batch_size,)

            batch_mean = np.zeros(batch_size, dtype=np.float64,)
            has_neighbours = counts > 0
            batch_mean[has_neighbours] = (area_sum[has_neighbours] / counts[has_neighbours])
            batch_max = np.zeros(batch_size, dtype=np.float64,)

            np.maximum.at(batch_max, local_left, areas,)
            batch_std = np.zeros(batch_size, dtype=np.float64,)
            multiple_neighbours = counts > 1
            variance = (area_squared_sum[multiple_neighbours] - (area_sum[multiple_neighbours] ** 2
                    / counts[multiple_neighbours])) / (counts[multiple_neighbours] - 1)

            batch_std[multiple_neighbours] = np.sqrt(np.maximum(variance, 0))
            neighbour_mean[start:end] = batch_mean.astype(np.float32)
            neighbour_max[start:end] = batch_max.astype(np.float32)
            neighbour_std[start:end] = batch_std.astype(np.float32)

        print(f"[features] Neighbour areas: {end:,} / {len(buildings):,}")

        del left_indices, right_indices
        del global_left, local_left, neighbour_indices
        gc.collect()

    buildings["neighbour_mean_area_200m"] = neighbour_mean
    buildings["neighbour_max_area_200m"] = neighbour_max
    buildings["neighbour_std_area_200m"] = neighbour_std

    del tree
    gc.collect()


def add_landuse_features(buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame, projected_crs: str, *, max_distance_m: float = 5000,
    boundary_segment_m: float = 50, neighbour_radius_m: float = 200, query_chunk_size: int = 100_000,) -> gpd.GeoDataFrame:
    """Add all selected land-use and local-building context features."""
    required_building_columns = {"geometry", "area", "landuse_osm_id",}
    missing = required_building_columns - set(buildings.columns)

    if missing:
        raise ValueError(f"Building input is missing: {sorted(missing)}")

    if buildings.crs is None or landuse.crs is None:
        raise ValueError("Buildings and land use must both have a CRS.")

    if "zone_l1" not in landuse.columns:
        raise ValueError("Land-use input is missing 'zone_l1'.")

    buildings = buildings.copy()

    projected = buildings.to_crs(projected_crs)
    projected_landuse = landuse.to_crs(projected_crs)

    centroids = projected.geometry.centroid
    building_coords = np.column_stack([centroids.x.to_numpy(), centroids.y.to_numpy(),])

    for zone_type in LANDUSE_ZONE_TYPES:
        column = f"dist_to_{zone_type}"

        print(f"[features] Computing distance to {zone_type}...")

        buildings[column] = _distance_to_landuse(building_coords=building_coords,
            building_centroids=centroids.values, landuse=projected_landuse,
            zone_type=zone_type, max_distance_m=max_distance_m, boundary_segment_m=boundary_segment_m,)

    _add_zone_cluster_features(buildings, landuse,)
    _add_neighbour_area_features(buildings, projected, radius_m=neighbour_radius_m, chunk_size=query_chunk_size,)

    print("[features] Land-use features completed:")

    for column in LANDUSE_FEATURES:
        missing_count = int(buildings[column].isna().sum())
        print(f"  {column:<30} missing={missing_count:,}")

    return buildings


# =====================================================================
# POI FEATURES
# =====================================================================

POI_COUNT_RADII = {
    "retail": (25, 50, 100, 250),
    "office": (25, 50, 100, 250),
    "food": (25, 50, 100, 250),
    "other_service": (25, 50, 100, 250),
    "accommodation": (50, 100, 250),
    "healthcare": (25, 50, 100),
    "education": (25, 50, 250),
    "civic": (25, 50, 100, 250),
}

POI_OUTPUT_COUNT_FEATURES = {
    "poi_count_retail_25m", "poi_count_retail_50m",
    "poi_count_retail_100m", "poi_count_retail_250m",
    "poi_count_office_25m", "poi_count_office_50m",
    "poi_count_office_100m", "poi_count_office_250m",
    "poi_count_food_25m", "poi_count_food_50m",
    "poi_count_food_100m", "poi_count_food_250m",
    "poi_count_other_service_25m", "poi_count_other_service_50m",
    "poi_count_other_service_100m", "poi_count_other_service_250m",
    "poi_count_accommodation_50m", "poi_count_accommodation_250m",
    "poi_count_healthcare_25m", "poi_count_healthcare_50m",
    "poi_count_healthcare_100m",
    "poi_count_education_25m", "poi_count_education_50m",
    "poi_count_education_250m",
    "poi_count_civic_25m", "poi_count_civic_50m",
    "poi_count_civic_100m", "poi_count_civic_250m",
}

POI_FEATURES = [
    *sorted(POI_OUTPUT_COUNT_FEATURES),
    "dist_nearest_transport", "dist_nearest_education",
    "poi_count_inside",
    "food_share_100m", "food_share_250m",
    "retail_share_100m", "retail_share_250m",
    "office_share_100m", "office_share_250m",
    "accom_share_100m", "accom_share_250m",
    "comm_diversity_100m", "comm_diversity_250m",
]


def _poi_category_mask(pois: gpd.GeoDataFrame, category: str):
    """Return the notebook's POI category mask."""
    if category == "retail":
        return pois["poi_l2"].eq("retail")
    if category == "office":
        return pois["poi_l2"].eq("office")
    if category == "food":
        return pois["poi_l2"].eq("food_drink")
    if category == "other_service":
        return pois["poi_l2"].eq("other_service")
    if category == "accommodation":
        return pois["poi_l2"].eq("accommodation")
    if category == "healthcare":
        return pois["poi_l2"].isin(["clinic", "hospital", "care_facility"])
    if category == "education":
        return pois["poi_l2"].isin(["school", "kindergarten", "higher_ed"])
    if category == "civic":
        return pois["poi_l1"].eq("civic")
    if category == "transport":
        return pois["poi_l1"].eq("transportation")
    raise ValueError(f"Unknown POI category: {category}")


def _count_points_within_radius(tree: cKDTree, building_coords: np.ndarray,
    radius_m: float, chunk_size: int,) -> np.ndarray:
    """Count POI points within a radius of every building centroid."""
    counts = np.zeros(len(building_coords), dtype=np.int32)

    for start in range(0, len(building_coords), chunk_size):
        end = min(start + chunk_size, len(building_coords))
        counts[start:end] = tree.query_ball_point(building_coords[start:end],
            r=radius_m, workers=-1, return_length=True,).astype(np.int32)

    return counts


def _nearest_point_distance(tree: cKDTree, building_coords: np.ndarray,
    max_distance_m: float, chunk_size: int,) -> np.ndarray:
    """Distance from every building centroid to the nearest POI."""
    distances = np.full(len(building_coords), max_distance_m, dtype=np.float32)

    for start in range(0, len(building_coords), chunk_size):
        end = min(start + chunk_size, len(building_coords))
        batch_distances, _ = tree.query(building_coords[start:end], k=1,
            distance_upper_bound=max_distance_m, workers=-1,)
        distances[start:end] = np.where(np.isinf(batch_distances),
            max_distance_m, batch_distances,).astype(np.float32)

    return distances


def _get_poi_count(buildings: gpd.GeoDataFrame, temporary_counts: dict[tuple[str, int], np.ndarray],
    category: str, radius: int,) -> np.ndarray:
    """Retrieve a saved or temporary POI count array."""
    column = f"poi_count_{category}_{radius}m"

    if column in buildings.columns:
        return buildings[column].to_numpy(dtype=np.float64)

    return temporary_counts[(category, radius)].astype(np.float64)


def _add_poi_ratio_features(buildings: gpd.GeoDataFrame, temporary_counts: dict[tuple[str, int], np.ndarray],) -> None:
    """Add the selected commercial POI share and diversity features."""
    epsilon = 1e-3

    for radius in (100, 250):
        retail = _get_poi_count(buildings, temporary_counts, "retail", radius)
        food = _get_poi_count(buildings, temporary_counts, "food", radius)
        office = _get_poi_count(buildings, temporary_counts, "office", radius)
        accommodation = _get_poi_count(buildings, temporary_counts, "accommodation", radius)
        service = _get_poi_count(buildings, temporary_counts, "other_service", radius)
        total_commercial = (retail + food + office + accommodation + service + epsilon)

        buildings[f"food_share_{radius}m"] = (food / total_commercial).clip(0, 1).astype(np.float32)
        buildings[f"retail_share_{radius}m"] = (retail / total_commercial).clip(0, 1).astype(np.float32)
        buildings[f"accom_share_{radius}m"] = (accommodation / total_commercial).clip(0, 1).astype(np.float32)
        buildings[f"office_share_{radius}m"] = (office / total_commercial).clip(0, 1).astype(np.float32)
        
        shares = np.column_stack([retail / total_commercial, food / total_commercial,
            office / total_commercial, accommodation / total_commercial,])

        buildings[f"comm_diversity_{radius}m"] = (1 - np.sum(shares**2, axis=1)).clip(0, 1).astype(np.float32)


def _count_pois_inside_buildings(building_geometries, poi_geometries, chunk_size: int,) -> np.ndarray:
    """Count mapped POIs contained inside every building polygon."""
    counts = np.zeros(len(building_geometries), dtype=np.int32)

    if len(poi_geometries) == 0:
        return counts

    tree = STRtree(poi_geometries)

    for start in range(0, len(building_geometries), chunk_size):
        end = min(start + chunk_size, len(building_geometries))
        building_indices, _ = tree.query(building_geometries[start:end], predicate="contains",)
        counts[start:end] = np.bincount(building_indices, minlength=end - start,).astype(np.int32)

    del tree
    gc.collect()
    return counts


def add_poi_features(buildings: gpd.GeoDataFrame, pois: gpd.GeoDataFrame, projected_crs: str,
    *, max_distance_m: float = 5000, query_chunk_size: int = 100_000,) -> gpd.GeoDataFrame:
    """Add the POI features required by the final models."""
    required = {"geometry", "poi_l1", "poi_l2"}
    missing = required - set(pois.columns)

    if missing:
        raise ValueError(f"POI input is missing: {sorted(missing)}")
    if buildings.crs is None or pois.crs is None:
        raise ValueError("Buildings and POIs must both have a CRS.")

    buildings = buildings.copy()
    projected_buildings = buildings.to_crs(projected_crs)
    building_centroids = projected_buildings.geometry.centroid
    building_coords = np.column_stack([building_centroids.x.to_numpy(), building_centroids.y.to_numpy(),])

    projected_pois = (pois.loc[pois["poi_l1"].notna()].to_crs(projected_crs).copy())

    # Converts all POIs, including polygon POIs to centroid points before neighbourhood calculations.
    projected_pois["geometry"] = projected_pois.geometry.centroid
    temporary_counts: dict[tuple[str, int], np.ndarray] = {}

    print(f"[features] Mapped POIs used: {len(projected_pois):,}")

    # Density counts
    for category, radii in POI_COUNT_RADII.items():
        mask = _poi_category_mask(projected_pois, category)
        subset = projected_pois.loc[mask, "geometry"]

        print(f"[features] POI category {category}: {len(subset):,}")
        if subset.empty:
            for radius in radii:
                values = np.zeros(len(buildings), dtype=np.int32)
                column = f"poi_count_{category}_{radius}m"

                if column in POI_OUTPUT_COUNT_FEATURES:
                    buildings[column] = values
                else:
                    temporary_counts[(category, radius)] = values
            continue

        category_coords = np.column_stack([subset.x.to_numpy(), subset.y.to_numpy(),])
        tree = cKDTree(category_coords)

        for radius in radii:
            values = _count_points_within_radius(tree, building_coords,
                radius_m=radius, chunk_size=query_chunk_size,)
            column = f"poi_count_{category}_{radius}m"

            if column in POI_OUTPUT_COUNT_FEATURES:
                buildings[column] = values
            else:
                # Needed to calculate selected ratios, but not
                # retained as a final model feature.
                temporary_counts[(category, radius)] = values

            print(f"[features] {column}: {values.sum():,} total hits")

        del tree, category_coords
        gc.collect()

    # Nearest transportation and education POIs
    for category in ("transport", "education"):
        mask = _poi_category_mask(projected_pois, category)
        subset = projected_pois.loc[mask, "geometry"]
        column = f"dist_nearest_{category}"

        if subset.empty:
            buildings[column] = np.full(len(buildings), max_distance_m, dtype=np.float32)
            continue

        category_coords = np.column_stack([subset.x.to_numpy(), subset.y.to_numpy(),])
        tree = cKDTree(category_coords)

        buildings[column] = _nearest_point_distance(tree, building_coords,
            max_distance_m=max_distance_m, chunk_size=query_chunk_size,)

        print(f"[features] {column}: median={buildings[column].median():.0f} m")

        del tree, category_coords
        gc.collect()

    # Commercial share and diversity features
    _add_poi_ratio_features(buildings, temporary_counts)

    # POIs physically inside each building polygon
    buildings["poi_count_inside"] = _count_pois_inside_buildings(projected_buildings.geometry.values,
        projected_pois.geometry.values, chunk_size=query_chunk_size,)

    print(f"[features] Buildings containing POIs: {buildings['poi_count_inside'].gt(0).sum():,}")

    print("[features] POI features completed:")
    for column in POI_FEATURES:
        missing_count = int(buildings[column].isna().sum())
        print(f"  {column:<35} missing={missing_count:,}")

    del projected_pois, temporary_counts
    gc.collect()
    return buildings

# =====================================================================
# ROAD FEATURES
# =====================================================================

ROAD_CATEGORIES = ("major_road", "secondary_road", "residential_road",
    "service_road", "rural_track", "pedestrian_zone",)

ROAD_THRESHOLDS = {"major_road": 700, "secondary_road": 115, "residential_road": 25,
    "service_road": 35, "rural_track": 250, "pedestrian_zone": 25,}

ROAD_DIRECT_COUNT_FEATURES = {    "major_road", "secondary_road", "residential_road", "service_road", "rural_track",}

ROAD_PROPORTIONS = {"pct_residential_roads_200m": "residential_road",
    "pct_rural_roads_200m": "rural_track",
    "pct_service_roads_200m": "service_road",
    "pct_major_roads_200m": "major_road",
    "pct_secondary_roads_200m": "secondary_road",}

ROAD_FEATURES = [*[f"dist_nearest_{category}" for category in ROAD_CATEGORIES],
    *[f"near_{category}_{threshold}m" for category, threshold in ROAD_THRESHOLDS.items()],
    "road_count_major_road_200m", "road_count_secondary_road_200m",
    "road_count_residential_road_200m", "road_count_service_road_200m",
    "road_count_rural_track_200m", "road_count_total_200m", *ROAD_PROPORTIONS,]

def _distance_to_roads(building_coords: np.ndarray, road_geometries, *,
    max_distance_m: float, boundary_segment_m: float,) -> np.ndarray:
    """Distance from every building centroid to the nearest road."""
    if len(road_geometries) == 0:
        return np.full(len(building_coords), max_distance_m, dtype=np.float32)

    # Segmentize road lines every 50 m, matching the notebook.
    dense_lines = road_geometries.segmentize(max_segment_length=boundary_segment_m)
    road_coords = np.unique(get_coordinates(dense_lines.values),axis=0,)

    if len(road_coords) == 0:
        return np.full(len(building_coords), max_distance_m, dtype=np.float32)

    tree = cKDTree(road_coords)
    distances, _ = tree.query(building_coords, k=1, distance_upper_bound=max_distance_m, workers=-1,)
    result = np.where(np.isinf(distances), max_distance_m, distances,).astype(np.float32)

    del tree, dense_lines, road_coords, distances
    gc.collect()
    return result


def _count_roads_within_radius(building_geometries, road_geometries, *, radius_m: float, chunk_size: int,) -> np.ndarray:
    """Count road segments within a radius of each building polygon."""
    counts = np.zeros(len(building_geometries), dtype=np.int32)

    if len(road_geometries) == 0:
        return counts

    tree = STRtree(road_geometries)

    for start in range(0, len(building_geometries), chunk_size):
        end = min(start + chunk_size, len(building_geometries))
        query_indices, _ = tree.query(building_geometries[start:end], predicate="dwithin", distance=radius_m,)
        counts[start:end] = np.bincount(query_indices, minlength=end - start,).astype(np.int32)

    del tree
    gc.collect()
    return counts


def add_road_features(buildings: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, projected_crs: str, *,
    max_distance_m: float = 5000, boundary_segment_m: float = 50, density_radius_m: float = 200,
    query_chunk_size: int = 100_000,) -> gpd.GeoDataFrame:
    """Add road-distance, proximity and density features."""
    required = {"geometry", "road_category"}
    missing = required - set(roads.columns)

    if missing:
        raise ValueError(f"Road input is missing: {sorted(missing)}")
    if buildings.crs is None or roads.crs is None:
        raise ValueError("Buildings and roads must both have a CRS.")

    buildings = buildings.copy()
    projected_buildings = buildings.to_crs(projected_crs)
    projected_roads = roads.to_crs(projected_crs)

    building_geometries = projected_buildings.geometry.values
    centroids = projected_buildings.geometry.centroid
    building_coords = np.column_stack([centroids.x.to_numpy(), centroids.y.to_numpy(),])

    roads_by_category = {category: projected_roads.loc[projected_roads["road_category"].eq(category),
            "geometry",] for category in ROAD_CATEGORIES}

    # Distance to each road category
    print("[features] Computing road distances...")

    for category, geometries in roads_by_category.items():
        column = f"dist_nearest_{category}"
        buildings[column] = _distance_to_roads(building_coords, geometries,
            max_distance_m=max_distance_m, boundary_segment_m=boundary_segment_m,)
        print(f"[features] {column}: median={buildings[column].median():.0f} m")

    # Meaningful binary road-distance thresholds
    print("[features] Applying binary road thresholds...")

    for category, threshold in ROAD_THRESHOLDS.items():
        distance_column = f"dist_nearest_{category}"
        flag_column = f"near_{category}_{threshold}m"

        buildings[flag_column] = (buildings[distance_column] <= threshold).astype(np.int8)

        print(f"[features] {flag_column}: {buildings[flag_column].sum():,}")

    # Road-segment counts within 200 m
    print("[features] Computing road density features...")

    category_counts: dict[str, np.ndarray] = {}

    for category, geometries in roads_by_category.items():
        counts = _count_roads_within_radius(building_geometries, geometries.values,
            radius_m=density_radius_m, chunk_size=query_chunk_size,)
        category_counts[category] = counts

        # Only retain direct count features used by final models.
        if category in ROAD_DIRECT_COUNT_FEATURES:
            column = f"road_count_{category}_200m"
            buildings[column] = counts

        print(f"[features] road_count_{category}_200m: {counts.sum():,} total hits")

    # Total includes every road category, matching the notebook.
    total_counts = np.zeros(len(buildings), dtype=np.int32)

    for counts in category_counts.values():
        total_counts += counts

    buildings["road_count_total_200m"] = total_counts

    # Road-category proportions
    for column, category in ROAD_PROPORTIONS.items():
        values = np.divide(category_counts[category], total_counts,out=np.zeros(len(buildings), 
                         dtype=np.float32), where=total_counts > 0,)
        buildings[column] = values.astype(np.float32)

    print("[features] Road features completed:")

    for column in ROAD_FEATURES:
        missing_count = int(buildings[column].isna().sum())
        print(f"  {column:<38} missing={missing_count:,}")

    del projected_roads, roads_by_category, category_counts
    del building_geometries, centroids, building_coords, total_counts
    gc.collect()
    return buildings


# =====================================================================
# RAILWAY AND WATERWAY FEATURES
# =====================================================================

RAIL_WATER_THRESHOLDS = {
    "major_waterway": 500,
    "minor_waterway": 300,
    "heavy_rail": 500,
    "light_rail": 200,
}

RAIL_WATER_COUNT_FEATURES = {
    "major_waterway",
    "minor_waterway",
    "heavy_rail",
    "light_rail",
}

RAIL_WATER_FEATURES = [
    *[f"dist_nearest_{category}" for category in RAIL_WATER_THRESHOLDS],
    *[
        f"near_{category}_{threshold}m"
        for category, threshold in RAIL_WATER_THRESHOLDS.items()
    ],
    "count_major_waterway_200m",
    "count_minor_waterway_200m",
    "count_heavy_rail_200m",
    "count_light_rail_200m",
]


def add_rail_water_features(buildings: gpd.GeoDataFrame, railways: gpd.GeoDataFrame, waterways: gpd.GeoDataFrame,
    projected_crs: str, *, max_distance_m: float = 5000, boundary_segment_m: float = 50, density_radius_m: float = 200,
    query_chunk_size: int = 100_000,) -> gpd.GeoDataFrame:
    """Add selected railway and waterway context features."""
    railway_required = {"geometry", "railway_category"}
    waterway_required = {"geometry", "waterway_category"}

    missing_rail = railway_required - set(railways.columns)
    missing_water = waterway_required - set(waterways.columns)

    if missing_rail:
        raise ValueError(f"Railway input is missing: {sorted(missing_rail)}")
    if missing_water:
        raise ValueError(f"Waterway input is missing: {sorted(missing_water)}")
    if buildings.crs is None or railways.crs is None or waterways.crs is None:
        raise ValueError("Buildings, railways and waterways must have a CRS.")

    buildings = buildings.copy()
    projected_buildings = buildings.to_crs(projected_crs)
    projected_railways = railways.to_crs(projected_crs)
    projected_waterways = waterways.to_crs(projected_crs)

    building_geometries = projected_buildings.geometry.values
    centroids = projected_buildings.geometry.centroid
    building_coords = np.column_stack([centroids.x.to_numpy(), centroids.y.to_numpy(),])

    layers = {"major_waterway": projected_waterways.loc[
            projected_waterways["waterway_category"].eq("major_waterway"), "geometry",],
        "minor_waterway": projected_waterways.loc[
            projected_waterways["waterway_category"].eq("minor_waterway"), "geometry",],
        "heavy_rail": projected_railways.loc[
            projected_railways["railway_category"].eq("heavy_rail"), "geometry",],
        "light_rail": projected_railways.loc[
            projected_railways["railway_category"].eq("light_rail"), "geometry",],}

    for category, geometries in layers.items():
        print(f"[features] Processing {category}: {len(geometries):,} segments")

        # Distance to nearest railway or waterway segment.
        distance_column = f"dist_nearest_{category}"
        buildings[distance_column] = _distance_to_roads(building_coords, geometries,
            max_distance_m=max_distance_m, boundary_segment_m=boundary_segment_m,)

        # Meaningful binary distance threshold.
        threshold = RAIL_WATER_THRESHOLDS[category]
        flag_column = f"near_{category}_{threshold}m"
        buildings[flag_column] = (buildings[distance_column] <= threshold).astype(np.int8)

        # Only calculate density counts selected by final models.
        if category in RAIL_WATER_COUNT_FEATURES:
            count_column = f"count_{category}_200m"
            buildings[count_column] = _count_roads_within_radius(building_geometries,
                geometries.values, radius_m=density_radius_m, chunk_size=query_chunk_size,)

        print(f"[features] {distance_column}: "
            f"median={buildings[distance_column].median():.0f} m | "
            f"{flag_column}={buildings[flag_column].sum():,}")

    print("[features] Railway and waterway features completed:")
    for column in RAIL_WATER_FEATURES:
        missing = int(buildings[column].isna().sum())
        print(f"  {column:<38} missing={missing:,}")

    del projected_railways, projected_waterways
    del projected_buildings, building_geometries
    del building_coords, centroids, layers
    gc.collect()

    return buildings