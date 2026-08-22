"""Run Stage 2 contextual building classification."""

from osm_classifier.paths import INTERIM_DATA_DIR
from osm_classifier.pipeline import run_stage2_classification


country = "germany"

output = run_stage2_classification(
    country=country,
    buildings_path=(
        INTERIM_DATA_DIR
        / "germany_buildings_classified_stage1.parquet"
    ),
    landuse_path=(
        INTERIM_DATA_DIR
        / "germany_landuse_mapped.parquet"
    ),
    pois_path=(
        INTERIM_DATA_DIR
        / "germany_pois_mapped.parquet"
    ),
    overwrite=True,
)

print(f"\nStage 2 output: {output}")