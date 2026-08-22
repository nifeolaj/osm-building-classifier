"""Main orchestration functions for the OSM Building Classifier."""

from __future__ import annotations

from pathlib import Path
import geopandas as gpd
import pandas as pd
from contextlib import contextmanager
from time import perf_counter
from copy import deepcopy

from osm_classifier.config import load_config
from osm_classifier.extraction.download import obtain_osm_pbf
from osm_classifier.extraction.osm_extract import extract_osm_layers
from osm_classifier.cleaning.clean_buildings import clean_buildings
from osm_classifier.context.landuse import prepare_landuse
from osm_classifier.context.poi import map_pois
from osm_classifier.context.roads import map_roads
from osm_classifier.context.railways import map_railways
from osm_classifier.context.waterways import map_waterways
from osm_classifier.context.manmade import map_manmade
from osm_classifier.taxonomy.tag_mapping import map_building_tags
from osm_classifier.taxonomy.stage1_classify import classify_stage1
from osm_classifier.rules.stage2_rules import classify_stage2
from osm_classifier.features.build_feature_matrix import build_feature_matrix
from osm_classifier.models.preprocessing import (load_level_feature_columns,prepare_inference_data,)
from osm_classifier.models.predict import (load_prediction_artifacts, predict_full_cascade,
    predict_missing_subtypes,)
from osm_classifier.postprocess.assemble_labels import assemble_final_labels
from osm_classifier.postprocess.semi_commercial import classify_semi_commercial
from osm_classifier.postprocess.industrial_grouping import group_industrial_buildings
from osm_classifier.export.final_database import create_final_databases
from osm_classifier.paths import (INTERIM_DATA_DIR, MODEL_WEIGHTS_DIR, PROCESSED_DATA_DIR, OUTPUTS_DIR,)
from osm_classifier.features.optional_height import load_height_dataset, add_optional_height_feature
from pyproj import CRS

MODEL_SOURCE_COUNTRY = "germany"

def _country_slug(country: str) -> str:
    """Normalise a country name for configs and filenames."""
    slug = country.strip().lower().replace("-", "_")
    slug = "_".join(slug.split())
    if not slug:
        raise ValueError("Country name cannot be empty.")
    return slug

def _validate_projected_crs(value: str) -> str:
    """Validate and normalise a projected CRS."""
    try:
        crs = CRS.from_user_input(value)
    except Exception as exc:
        raise ValueError(f"Invalid projected CRS: {value}") from exc

    if not crs.is_projected:
        raise ValueError(
            f"{value} is not a projected CRS. "
            "Use a metric projected CRS appropriate for the target country."
        )

    return crs.to_string()


def _validate_pbf_path(path: str | Path) -> Path:
    """Validate a local OSM PBF path."""
    path = Path(path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"PBF file not found: {path}")
    if not path.name.lower().endswith((".osm.pbf", ".pbf")):
        raise ValueError(f"Expected an .osm.pbf or .pbf file: {path}")

    return path

def _format_duration(seconds: float) -> str:
    """Format elapsed seconds as HH:MM:SS."""
    seconds = int(round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@contextmanager
def _timed_stage(name: str, timings: dict[str, float]):
    """Measure and report one pipeline stage."""
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        timings[name] = elapsed
        print(
            f"[timing] {name}: "
            f"{_format_duration(elapsed)}"
        )


def run_extraction(country: str, *, continent: str | None = None, geofabrik_region: str | None = None,
    pbf_path: str | Path | None = None, overwrite: bool | None = None,) -> dict[str, Path]:
    """
    Obtain an OSM PBF and extract all required OSM layers.

    The PBF may come from:
    1. an existing local file;
    2. an explicit Geofabrik region;
    3. a continent and country;
    4. an optional country configuration.
    """
    
    country = _country_slug(country)
    config = load_config(country, required=False)

    local_pbf = obtain_osm_pbf(country=country, continent=continent, 
                               geofabrik_region=geofabrik_region, pbf_path=pbf_path,
                               config=config, overwrite=overwrite,)

    return extract_osm_layers(pbf_path=local_pbf, country=country, config=config, overwrite=overwrite,)

def run_building_cleaning(country: str, buildings_path: str | Path, *, projected_crs: str | None = None,
    overwrite: bool = False,) -> Path:
    """Load, clean, and save the extracted building layer."""
    country = _country_slug(country)
    config = load_config(country, required=False)

    projected_crs = projected_crs or config.get("crs", {}).get("projected")
    if not projected_crs:
        raise ValueError(
            "A projected CRS is required to calculate building area. "
            "Provide projected_crs or define crs.projected in the country config."
        )

    input_path = Path(buildings_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Building file not found: {input_path}")

    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = INTERIM_DATA_DIR / f"{country}_buildings_cleaned.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    print(f"[load] {input_path}")
    gdf = gpd.read_parquet(input_path)
    gdf = clean_buildings(gdf, projected_crs=projected_crs)
    gdf.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_landuse_mapping(country: str, landuse_path: str | Path, *,
    projected_crs: str | None = None, overwrite: bool = False,) -> Path:
    """Load, prepare, and save the land-use layer."""
    country = _country_slug(country)
    config = load_config(country, required=False)

    projected_crs = projected_crs or config.get("crs", {}).get("projected")
    if not projected_crs:
        raise ValueError("A projected CRS is required for zone-area calculation.")

    input_path = Path(landuse_path)
    output_path = INTERIM_DATA_DIR / f"{country}_landuse_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    gdf = gpd.read_parquet(input_path)
    gdf = prepare_landuse(gdf, projected_crs)
    gdf.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_poi_mapping(country: str, pois_path: str | Path, buildings_path: str | Path, *,
    overwrite: bool = False,) -> Path:
    """Load, map and save the POI layer."""
    country = _country_slug(country)
    output_path = INTERIM_DATA_DIR / f"{country}_pois_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    pois = gpd.read_parquet(pois_path)
    buildings = pd.read_parquet(buildings_path, columns=["id"])
    pois = map_pois(pois, building_ids=buildings["id"])
    pois.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_road_mapping(country: str, roads_path: str | Path, *,
    projected_crs: str | None = None, overwrite: bool = False,) -> Path:
    """Load, map, and save the road layer."""
    country = _country_slug(country)
    config = load_config(country, required=False)

    projected_crs = projected_crs or config.get("crs", {}).get("projected")
    if not projected_crs:
        raise ValueError("A projected CRS is required to calculate road length.")

    output_path = INTERIM_DATA_DIR / f"{country}_roads_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    roads = gpd.read_parquet(roads_path)
    roads = map_roads(roads, projected_crs)
    roads.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_railway_mapping(country: str, railways_path: str | Path,
    *, overwrite: bool = False,) -> Path:
    """Load, map and save the railway layer."""
    country = _country_slug(country)
    output_path = INTERIM_DATA_DIR / f"{country}_railways_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    railways = gpd.read_parquet(railways_path)
    railways = map_railways(railways)
    railways.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_waterway_mapping(country: str, waterways_path: str | Path,
    *, overwrite: bool = False,) -> Path:
    """Load, map, and save the waterway layer."""
    country = _country_slug(country)
    output_path = INTERIM_DATA_DIR / f"{country}_waterways_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    waterways = gpd.read_parquet(waterways_path)
    waterways = map_waterways(waterways)
    waterways.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_manmade_mapping(country: str, manmade_path: str | Path,
    *, overwrite: bool = False,) -> Path:
    """Load, map, and save the man-made layer."""
    country = _country_slug(country)
    output_path = (INTERIM_DATA_DIR / f"{country}_manmade_mapped.parquet")

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    manmade = gpd.read_parquet(manmade_path)
    manmade = map_manmade(manmade)
    manmade.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_context_mapping(country: str, extracted_paths: dict[str, Path],
    cleaned_buildings_path: str | Path, *, projected_crs: str | None = None, 
    overwrite: bool = False,) -> dict[str, Path]:
    """Map all extracted context layers."""
    country = _country_slug(country)

    outputs = {
        "landuse": run_landuse_mapping(country, extracted_paths["landuse"],
            projected_crs=projected_crs, overwrite=overwrite,),
        "pois": run_poi_mapping(country, extracted_paths["pois"],
            cleaned_buildings_path, overwrite=overwrite,),
        "roads": run_road_mapping(country, extracted_paths["roads"],
            projected_crs=projected_crs,  overwrite=overwrite,),
        "railways": run_railway_mapping(
            country, extracted_paths["railways"], overwrite=overwrite,),
        "waterways": run_waterway_mapping(
            country, extracted_paths["waterways"], overwrite=overwrite,),
        "manmade": run_manmade_mapping(
            country, extracted_paths["manmade"], overwrite=overwrite,),
    }
    return outputs

def run_tag_mapping(country: str, buildings_path: str | Path,
    *, overwrite: bool = False,) -> Path:
    """Map classification signals from the building tags column."""
    country = _country_slug(country)
    output_path = INTERIM_DATA_DIR / f"{country}_buildings_tags_mapped.parquet"

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    buildings = gpd.read_parquet(buildings_path)
    buildings = map_building_tags(buildings)
    buildings.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_stage1_classification(country: str,buildings_path: str | Path,
    *, overwrite: bool = False,) -> Path:
    """Run Stage 1 direct-tag classification."""
    country = _country_slug(country)
    output_path = (INTERIM_DATA_DIR / f"{country}_buildings_classified_stage1.parquet")

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    buildings = gpd.read_parquet(buildings_path)
    buildings = classify_stage1(buildings)
    buildings.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_stage2_classification(country: str, buildings_path: str | Path,
    landuse_path: str | Path, pois_path: str | Path, small_building_max_area: float | None = None,
    garage_min_area: float | None = None, garage_max_area: float | None = None,
    residential_zone_min_area: float | None = None, residential_zone_max_area: float | None = None, *, 
    projected_crs: str | None = None, overwrite: bool = False,) -> Path:
    """Run Stage 2 contextual rule-based classification."""
    country = _country_slug(country)
    config = load_config(country, required=False)
    projected_crs = projected_crs or config.get("crs", {}).get("projected")

    if not projected_crs:
        raise ValueError("A projected CRS is required for Stage 2 classification.")

    stage2_config = deepcopy(config["stage2"])
    rules = stage2_config["rules"]

    if small_building_max_area is not None:
        rules["small_building_filter"]["max_area_sqm"] = small_building_max_area

    if garage_min_area is not None:
        rules["garage_filter"]["min_area_sqm"] = garage_min_area

    if garage_max_area is not None:
        rules["garage_filter"]["max_area_sqm"] = garage_max_area

    if residential_zone_min_area is not None:
        rules["residential_zone"]["min_area_sqm"] = residential_zone_min_area

    if residential_zone_max_area is not None:
        rules["residential_zone"]["max_area_sqm"] = residential_zone_max_area

    area_values = {"small_building_max_area": rules["small_building_filter"]["max_area_sqm"],
        "garage_min_area": rules["garage_filter"]["min_area_sqm"],
        "garage_max_area": rules["garage_filter"]["max_area_sqm"],
        "residential_zone_min_area": rules["residential_zone"]["min_area_sqm"],
        "residential_zone_max_area": rules["residential_zone"]["max_area_sqm"],}

    for name, value in area_values.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative.")

    if rules["garage_filter"]["min_area_sqm"] > rules["garage_filter"]["max_area_sqm"]:
        raise ValueError("Garage minimum area cannot exceed garage maximum area.")

    if rules["residential_zone"]["min_area_sqm"] > rules["residential_zone"]["max_area_sqm"]:
        raise ValueError(
            "Residential-zone minimum area cannot exceed residential-zone maximum area."
        )

    print("[stage2] Effective area thresholds:")
    print(f"  Small-building maximum:  {rules['small_building_filter']['max_area_sqm']} m²")
    print(f"  Garage range:            {rules['garage_filter']['min_area_sqm']}–"
        f"{rules['garage_filter']['max_area_sqm']} m²")
    print(f"  Residential-zone range:  {rules['residential_zone']['min_area_sqm']}–"
        f"{rules['residential_zone']['max_area_sqm']} m²")

    
    output_path = (INTERIM_DATA_DIR / f"{country}_buildings_classified_stage2.parquet")

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    buildings_path = Path(buildings_path)
    landuse_path = Path(landuse_path)
    pois_path = Path(pois_path)

    for path in [buildings_path, landuse_path, pois_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    buildings = gpd.read_parquet(buildings_path)
    landuse = gpd.read_parquet(landuse_path)
    pois = gpd.read_parquet(pois_path)

    buildings = classify_stage2(buildings=buildings, landuse=landuse,
        pois=pois, projected_crs=projected_crs, config=stage2_config,)

    buildings.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_optional_height(country: str, features_path: str | Path, height_data: str | Path,
    height_column: str, projected_crs: str, *, overwrite: bool = False) -> Path:
    """Add optional externally supplied building heights to the ML feature matrix."""
    country = _country_slug(country)
    features_path = Path(features_path)
    output_path = features_path.with_name(f"{country}_buildings_features_height.parquet")

    if output_path.exists() and not overwrite:
        print(f"[height] Reusing existing output: {output_path}")
        return output_path

    print("[height] Loading building feature matrix...")
    buildings = gpd.read_parquet(features_path)

    print(f"[height] Loading optional height dataset: {height_data}")
    heights = load_height_dataset(height_data, height_column)

    buildings = add_optional_height_feature(
        buildings=buildings,
        heights=heights,
        height_column=height_column,
        projected_crs=projected_crs,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    buildings.to_parquet(output_path, index=False)

    print(f"[height] Saved: {output_path}")
    return output_path

def run_feature_engineering(country: str, buildings_path: str | Path, landuse_path: str | Path,
    pois_path: str | Path, roads_path: str | Path, railways_path: str | Path,
    waterways_path: str | Path, *, projected_crs: str | None = None, overwrite: bool = False,) -> Path:
    """Generate all features required by the trained models."""
    country = _country_slug(country)
    config = load_config(country, required=False)
    projected_crs = projected_crs or config.get("crs", {}).get("projected")

    if not projected_crs:
        raise ValueError("A projected CRS is required for feature engineering.")

    output_path = (INTERIM_DATA_DIR / f"{country}_buildings_features.parquet")

    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    paths = {"buildings": Path(buildings_path), "landuse": Path(landuse_path),
        "pois": Path(pois_path), "roads": Path(roads_path),
        "railways": Path(railways_path), "waterways": Path(waterways_path),}

    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{name}: {path}")

    buildings = gpd.read_parquet(paths["buildings"])
    landuse = gpd.read_parquet(paths["landuse"])
    pois = gpd.read_parquet(paths["pois"])
    roads = gpd.read_parquet(paths["roads"])
    railways = gpd.read_parquet(paths["railways"])
    waterways = gpd.read_parquet(paths["waterways"])

    buildings = build_feature_matrix(buildings=buildings, landuse=landuse, pois=pois, roads=roads,
        railways=railways, waterways=waterways, projected_crs=projected_crs, config=config,)

    buildings.to_parquet(output_path, index=False)

    print(f"[saved] {output_path}")
    return output_path

def run_model_inference(country: str, features_path: str | Path | None = None,
    *, use_height: bool = False, overwrite: bool = False) -> Path:
    """Run hierarchical ML inference and assemble final labels."""
    country = _country_slug(country)
    model_config = load_config(MODEL_SOURCE_COUNTRY, required=True)

    suffix = "_height" if use_height else ""
    if features_path is None:
        features_path = INTERIM_DATA_DIR / f"{country}_buildings_features{suffix}.parquet"
    else:
        features_path = Path(features_path)

    model_variant = "with_height" if use_height else "osm_only"
    model_dir = MODEL_WEIGHTS_DIR / MODEL_SOURCE_COUNTRY / model_variant
    output_path = PROCESSED_DATA_DIR / f"{country}_buildings_classified_final{suffix}.parquet"
    
    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    if not features_path.exists():
        raise FileNotFoundError(features_path)
    if not model_dir.exists():
        raise FileNotFoundError(f"German model bundle not found: {model_dir}")

    print(f"[models] Target country: {country}")
    print(f"[models] Model source: {MODEL_SOURCE_COUNTRY}")
    print(f"[models] Model variant: {model_variant}")
    print(f"[models] Loading features: {features_path}")

    buildings = gpd.read_parquet(features_path)

    level_features = load_level_feature_columns(model_dir)
    buildings, masks = prepare_inference_data(buildings, level_features,)
    models, encoders = load_prediction_artifacts(model_dir)
    thresholds = model_config["models"]["thresholds"]

    # Fully unclassified buildings receive the complete cascade.
    cascade_predictions = predict_full_cascade(buildings=buildings,
        predict_mask=masks["predict"], models=models, encoders=encoders,
        level_features=level_features, thresholds=thresholds,)

    # Buildings with an existing L1 but missing L2 receive subtype ML.
    subtype_predictions = predict_missing_subtypes(buildings=buildings, masks=masks,
        models=models, encoders=encoders, level_features=level_features,)

    final_labels = assemble_final_labels(buildings=buildings, masks=masks,
        cascade_predictions=cascade_predictions, subtype_predictions=subtype_predictions,)

    # Match the final notebook's storage dtypes.
    final_labels["final_l1"] = final_labels["final_l1"].astype("category")
    final_labels["final_l2"] = final_labels["final_l2"].astype("category")
    final_labels["label_source"] = final_labels["label_source"].astype("category")
    final_labels["l1_confidence"] = final_labels["l1_confidence"].astype("float32")
    final_labels["l2_confidence"] = final_labels["l2_confidence"].astype("float32")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_labels.to_parquet(output_path, index=True, compression="snappy",)

    # Confirm that the written file is readable and complete.
    saved = pd.read_parquet(output_path)

    if len(saved) != len(final_labels):
        raise RuntimeError("Row count changed after saving the final classification.")

    print(f"\n[saved] {output_path}")
    print(f"[saved] Rows: {len(saved):,}")
    print(f"[saved] Columns: {saved.columns.tolist()}")

    return output_path

def run_semi_commercial_classification(country: str, classified_path: str | Path | None = None,
    buildings_path: str | Path | None = None, pois_path: str | Path | None = None, *,
    use_height: bool = False, overwrite: bool = False) -> Path:
    """Apply semi-commercial post-processing rules."""
    country = _country_slug(country)

    suffix = "_height" if use_height else ""
    classified_path = Path(classified_path or PROCESSED_DATA_DIR / f"{country}_buildings_classified_final{suffix}.parquet")
    buildings_path = Path(buildings_path or INTERIM_DATA_DIR / f"{country}_buildings_features{suffix}.parquet")
    pois_path = Path(pois_path or INTERIM_DATA_DIR / f"{country}_pois_mapped.parquet")

    output_path = PROCESSED_DATA_DIR / f"{country}_buildings_classified_semi_comm{suffix}.parquet"
    if output_path.exists() and not overwrite:
        print(f"[skip] {output_path}")
        return output_path

    inputs = {"classified": classified_path, "buildings": buildings_path, "pois": pois_path,}

    for name, path in inputs.items():
        if not path.exists():
            raise FileNotFoundError(f"{name}: {path}")

    print(f"[semi-commercial] Loading {classified_path}")
    classified = pd.read_parquet(classified_path)

    print(f"[semi-commercial] Loading {buildings_path}")
    buildings = gpd.read_parquet(buildings_path)

    print(f"[semi-commercial] Loading {pois_path}")
    pois = gpd.read_parquet(pois_path)

    result = classify_semi_commercial(classified=classified, buildings=buildings, pois=pois,)
    result["final_l1"] = result["final_l1"].astype("category")
    result["final_l2"] = result["final_l2"].astype("category")
    result["label_source"] = result["label_source"].astype("category")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=True, compression="snappy",)

    saved = pd.read_parquet(output_path)

    if len(saved) != len(result):
        raise RuntimeError("Row count changed after saving semi-commercial results.")

    print(f"\n[saved] {output_path}")
    print(f"[saved] Rows: {len(saved):,}")

    return output_path


def run_industrial_grouping(country: str, classified_path: str | Path | None = None,
    buildings_path: str | Path | None = None, landuse_path: str | Path | None = None,
    manmade_path: str | Path | None = None, projected_crs: str | None = None, *,
    use_height: bool = False, overwrite: bool = False) -> tuple[Path, Path]:
    """Group industrial buildings into zone and standalone parents."""

    country = _country_slug(country)
    suffix = "_height" if use_height else ""
    config = load_config(country, required=False)
    projected_crs = projected_crs or config.get("crs", {}).get("projected")

    if not projected_crs:
        raise ValueError("A projected CRS is required for industrial grouping.")

    projected_crs = _validate_projected_crs(projected_crs)
    
    classified_path = Path(classified_path or PROCESSED_DATA_DIR
    / f"{country}_buildings_classified_semi_comm{suffix}.parquet")
    buildings_path = Path(buildings_path or INTERIM_DATA_DIR / f"{country}_buildings_features{suffix}.parquet")
    landuse_path = Path(landuse_path or INTERIM_DATA_DIR / f"{country}_landuse_mapped.parquet")
    manmade_path = Path(manmade_path or INTERIM_DATA_DIR / f"{country}_manmade_mapped.parquet")

    building_output = PROCESSED_DATA_DIR / f"{country}_buildings_with_parent_id{suffix}.parquet"
    parent_output = PROCESSED_DATA_DIR / f"{country}_industrial_parents{suffix}.parquet"
    if (building_output.exists() and parent_output.exists() and not overwrite):
        print(f"[skip] {building_output}")
        print(f"[skip] {parent_output}")
        return building_output, parent_output

    inputs = {"classified": classified_path, "buildings": buildings_path,
        "landuse": landuse_path, "manmade": manmade_path,}

    for name, path in inputs.items():
        if not path.exists():
            raise FileNotFoundError(f"{name}: {path}")

    classified = pd.read_parquet(classified_path)
    buildings = gpd.read_parquet(buildings_path)
    landuse = gpd.read_parquet(landuse_path)
    manmade = gpd.read_parquet(manmade_path)

    buildings_with_parents, industrial_parents = (group_industrial_buildings(
            classified=classified, buildings=buildings, landuse=landuse, 
            manmade=manmade, projected_crs=projected_crs))

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Preserve building IDs stored in the index.
    buildings_with_parents.to_parquet(building_output, index=True, compression="snappy",)

    # GeoParquet should contain one geometry column. Store the
    # child-building union as WKT.
    parents_to_save = industrial_parents.copy()

    if "buildings_union_geometry" in parents_to_save.columns:
        parents_to_save["buildings_union_wkt"] = (parents_to_save["buildings_union_geometry"]
            .apply(lambda geometry: (geometry.wkt if geometry is not None
                    and not pd.isna(geometry)else None)))
        parents_to_save = parents_to_save.drop(columns="buildings_union_geometry")

    parents_to_save.to_parquet(parent_output, index=False, compression="snappy",)

    # Confirm that both written files are readable.
    saved_buildings = gpd.read_parquet(building_output)
    saved_parents = gpd.read_parquet(parent_output)

    if len(saved_buildings) != len(buildings_with_parents):
        raise RuntimeError("Building row count changed after industrial grouping save.")

    if len(saved_parents) != len(parents_to_save):
        raise RuntimeError("Parent row count changed after industrial grouping save.")

    print(f"\n[saved] {building_output}")
    print(f"[saved] Buildings: {len(saved_buildings):,}")
    print(f"[saved] {parent_output}")
    print(f"[saved] Parents:   {len(saved_parents):,}")

    return building_output, parent_output

def run_final_export(country: str, buildings_path: str | Path | None = None,
    parents_path: str | Path | None = None, *, use_height: bool = False,
    include_provenance: bool = True, overwrite: bool = False) -> tuple[Path, Path]:

    """Create the final public building and industrial-site databases."""
    country = _country_slug(country)
    suffix = "_height" if use_height else ""

    buildings_path = Path(buildings_path or PROCESSED_DATA_DIR
        / f"{country}_buildings_with_parent_id{suffix}.parquet")
    parents_path = Path(parents_path or PROCESSED_DATA_DIR / f"{country}_industrial_parents{suffix}.parquet")

    output_dir = OUTPUTS_DIR / country
    building_output = output_dir / f"buildings{suffix}.parquet"
    site_output = output_dir / f"industrial_sites{suffix}.parquet"

    if (building_output.exists() and site_output.exists() and not overwrite):
        print(f"[skip] {building_output}")
        print(f"[skip] {site_output}")
        return building_output, site_output

    for name, path in {"buildings": buildings_path, "industrial parents": parents_path,}.items():
        if not path.exists():
            raise FileNotFoundError(f"{name}: {path}")

    print(f"[export] Loading {buildings_path}")
    buildings = gpd.read_parquet(buildings_path)

    print(f"[export] Loading {parents_path}")
    parents = gpd.read_parquet(parents_path)

    final_buildings, final_sites = create_final_databases(buildings=buildings,
        parents=parents, include_provenance=include_provenance,)

    output_dir.mkdir(parents=True, exist_ok=True)

    final_buildings.to_parquet(building_output, index=False, compression="snappy",)
    final_sites.to_parquet(site_output, index=False, compression="snappy",)

    saved_buildings = gpd.read_parquet(building_output)
    saved_sites = gpd.read_parquet(site_output)

    if len(saved_buildings) != len(final_buildings):
        raise RuntimeError("Building row count changed during final export.")
    if len(saved_sites) != len(final_sites):
        raise RuntimeError("Industrial-site row count changed during final export.")

    print("\n" + "=" * 60)
    print("FINAL EXPORT COMPLETED")
    print("=" * 60)
    print(f"Buildings:        {len(saved_buildings):>12,}")
    print(f"Industrial sites: {len(saved_sites):>12,}")
    print(f"Building file:    {building_output}")
    print(f"Site file:        {site_output}")

    return building_output, site_output

def run_full_pipeline(country: str, continent: str | None = None,
    geofabrik_region: str | None = None, pbf_path: str | Path | None = None,
    projected_crs: str | None = None, small_building_max_area: float | None = None,
    height_data: str | Path | None = None, height_column: str | None = None,
    garage_min_area: float | None = None, garage_max_area: float | None = None,
    residential_zone_min_area: float | None = None,
    residential_zone_max_area: float | None = None,
    include_provenance: bool = True, overwrite: bool = False) -> dict[str, Path]:
    """Run the complete workflow from OSM acquisition to final export."""
    country = _country_slug(country)
    config = load_config(country, required=False)

    if projected_crs is None:
        projected_crs = config.get("crs", {}).get("projected")

    if not projected_crs:
        raise ValueError("A projected CRS is required. Use --projected-crs EPSG:<code>.")

    projected_crs = _validate_projected_crs(projected_crs)

    if pbf_path is not None:
        pbf_path = _validate_pbf_path(pbf_path)

    if pbf_path is None and geofabrik_region is None:
        geofabrik_region = config.get("download", {}).get("geofabrik_region")

    if pbf_path is None and not geofabrik_region:
        raise ValueError("Provide either --pbf or --geofabrik-region.")
    
    if (height_data is None) != (height_column is None):
        raise ValueError("--height-data and --height-column must be supplied together.")

    timings: dict[str, float] = {}
    pipeline_start = perf_counter()

    print("\n" + "=" * 70)
    print(f"OSM BUILDING CLASSIFIER — {country.upper()}")
    print("=" * 70)

    # Obtain the PBF and extract the seven required OSM layers.
    print("\n[pipeline] 1/11 Extraction")
    with _timed_stage("extraction", timings):
        extracted = run_extraction(country=country, continent=continent,
        geofabrik_region=geofabrik_region, pbf_path=pbf_path, overwrite=overwrite,)

    required_layers = {"buildings", "landuse", "pois", "roads",
        "railways", "waterways", "manmade",}
    missing_layers = required_layers - set(extracted)

    if missing_layers:
        raise ValueError(f"Extraction did not return: {sorted(missing_layers)}")

    # Clean building footprints.
    print("\n[pipeline] 2/11 Building cleaning")
    with _timed_stage("building_cleaning", timings):
        cleaned_buildings = run_building_cleaning(country=country,
        buildings_path=extracted["buildings"], projected_crs=projected_crs, overwrite=overwrite,)

    # Prepare and map all contextual layers.
    print("\n[pipeline] 3/11 Context mapping")
    with _timed_stage("context_mapping", timings):
        context = run_context_mapping(country=country, extracted_paths=extracted,
        cleaned_buildings_path=cleaned_buildings, projected_crs=projected_crs, overwrite=overwrite,)

    # Map direct classification evidence from building tags.
    print("\n[pipeline] 4/11 Building-tag mapping")
    with _timed_stage("tag_mapping", timings):
        tagged_buildings = run_tag_mapping(country=country, buildings_path=cleaned_buildings, 
                                       overwrite=overwrite,)

    # Run direct-tag classification.
    print("\n[pipeline] 5/11 Stage 1 classification")
    with _timed_stage("stage1_classification", timings):
        stage1_buildings = run_stage1_classification(country=country,
        buildings_path=tagged_buildings, overwrite=overwrite,)

    # Apply contextual classification rules.
    print("\n[pipeline] 6/11 Stage 2 classification")
    with _timed_stage("stage2_classification", timings):
        stage2_buildings = run_stage2_classification(country=country, buildings_path=stage1_buildings,
            landuse_path=context["landuse"], pois_path=context["pois"], projected_crs=projected_crs,
            small_building_max_area=small_building_max_area, garage_min_area=garage_min_area,
            garage_max_area=garage_max_area, residential_zone_min_area=residential_zone_min_area,
            residential_zone_max_area=residential_zone_max_area, overwrite=overwrite,)

    # Generate all features required by the trained models.
    print("\n[pipeline] 7/11 Feature engineering")
    with _timed_stage("feature_engineering", timings):
        feature_buildings = run_feature_engineering(country=country, buildings_path=stage2_buildings,
            landuse_path=context["landuse"], pois_path=context["pois"], roads_path=context["roads"],
            railways_path=context["railways"], waterways_path=context["waterways"],
            projected_crs=projected_crs, overwrite=overwrite,)

    # Optional height extension: affects only the machine-learning feature matrix.
    if height_data is not None and height_column is not None:
        print("\n[pipeline] 7b/11 Optional building-height integration")
        with _timed_stage("optional_height", timings):
            feature_buildings = run_optional_height(country=country, features_path=feature_buildings,
                height_data=height_data, height_column=height_column, projected_crs=projected_crs,
                overwrite=overwrite,)
            
    # Run hierarchical machine-learning inference.
    print("\n[pipeline] 8/11 Model inference")
    with _timed_stage("model_inference", timings):
        classified_buildings = run_model_inference(country=country, features_path=feature_buildings,
            use_height=height_data is not None, overwrite=overwrite,)

    # Detect and classify semi-commercial buildings.
    print("\n[pipeline] 9/11 Semi-commercial classification")
    with _timed_stage("semi_commercial", timings):
        semi_commercial_buildings = run_semi_commercial_classification(
        country=country, classified_path=classified_buildings, buildings_path=feature_buildings,
        pois_path=context["pois"], use_height=height_data is not None, overwrite=overwrite,)
        
    # Group industrial buildings into industrial sites.
    print("\n[pipeline] 10/11 Industrial grouping")
    with _timed_stage("industrial_grouping", timings):
        buildings_with_parents, industrial_parents = run_industrial_grouping(
            country=country, classified_path=semi_commercial_buildings, buildings_path=feature_buildings,
            landuse_path=context["landuse"], manmade_path=context["manmade"],
            projected_crs=projected_crs, use_height=height_data is not None, overwrite=overwrite,)
        
    # Create the slim public-facing databases.
    print("\n[pipeline] 11/11 Final export")
    with _timed_stage("final_export", timings):
        final_buildings, final_sites = run_final_export(
            country=country, buildings_path=buildings_with_parents, parents_path=industrial_parents,
            use_height=height_data is not None, include_provenance=include_provenance,
            overwrite=overwrite,)
        
    outputs = {
        "pbf": Path(pbf_path) if pbf_path else extracted.get("pbf"),
        "cleaned_buildings": cleaned_buildings,
        "stage1_buildings": stage1_buildings,
        "stage2_buildings": stage2_buildings,
        "feature_buildings": feature_buildings,
        "classified_buildings": classified_buildings,
        "semi_commercial_buildings": semi_commercial_buildings,
        "buildings_with_parents": buildings_with_parents,
        "industrial_parents": industrial_parents,
        "final_buildings": final_buildings,
        "final_industrial_sites": final_sites,
    }

    # Remove optional entries that were not returned.
    outputs = {name: path for name, path in outputs.items() if path is not None}

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETED")
    print("=" * 70)
    print(f"Buildings:        {final_buildings}")
    print(f"Industrial sites: {final_sites}")

    total_elapsed = perf_counter() - pipeline_start

    print("\n" + "=" * 70)
    print("PIPELINE TIMING SUMMARY")
    print("=" * 70)

    for stage, elapsed in timings.items():
        print(f"{stage:<30} {_format_duration(elapsed):>12}")

    print("-" * 42)
    print(f"{'total':<30} {_format_duration(total_elapsed):>12}")

    return outputs