"""Run national building feature engineering."""

from osm_classifier.paths import INTERIM_DATA_DIR
from osm_classifier.pipeline import run_feature_engineering


country = "germany"

output = run_feature_engineering(
    country=country,
    buildings_path=(
        INTERIM_DATA_DIR
        / "germany_buildings_classified_stage2.parquet"
    ),
    landuse_path=(
        INTERIM_DATA_DIR
        / "germany_landuse_mapped.parquet"
    ),
    pois_path=(
        INTERIM_DATA_DIR
        / "germany_pois_mapped.parquet"
    ),
    roads_path=(
        INTERIM_DATA_DIR
        / "germany_roads_mapped.parquet"
    ),
    railways_path=(
        INTERIM_DATA_DIR
        / "germany_railways_mapped.parquet"
    ),
    waterways_path=(
        INTERIM_DATA_DIR
        / "germany_waterways_mapped.parquet"
    ),
    overwrite=True,
)

print(f"\nFeature-engineered output: {output}")