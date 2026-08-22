"""Run building cleaning and all context-layer mappings."""

from pathlib import Path

from osm_classifier.pipeline import run_context_mapping
from osm_classifier.pipeline import run_building_cleaning

country = "germany"
interim = Path("data/osm_classifier_data/interim")

extracted_paths = {
    "landuse": interim / "germany_landuse.parquet",
    "pois": interim / "germany_pois.parquet",
    "roads": interim / "germany_roads.parquet",
    "railways": interim / "germany_railways.parquet",
    "waterways": interim / "germany_waterways.parquet",
    "manmade": interim / "germany_manmade.parquet",
}

run_building_cleaning(
    country='country',
    buildings_path='data/osm_classifier_data/interim/germany_buildings.parquet',
    overwrite=True
)

outputs = run_context_mapping(
    country=country,
    extracted_paths=extracted_paths,
    cleaned_buildings_path=interim / "germany_buildings_cleaned.parquet",
    overwrite=True,
)

print("\nContext outputs:")
for layer, path in outputs.items():
    print(f"{layer}: {path}")