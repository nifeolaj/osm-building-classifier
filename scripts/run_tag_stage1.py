"""Run building tag mapping followed by Stage 1 classification."""

from pathlib import Path

from osm_classifier.pipeline import (
    run_stage1_classification,
    run_tag_mapping,
)

country = "germany"
interim = Path("data/osm_classifier_data/interim")

tags_mapped_path = run_tag_mapping(
    country=country,
    buildings_path=interim / "germany_buildings_cleaned.parquet",
    overwrite=True,
)

stage1_path = run_stage1_classification(
    country=country,
    buildings_path=tags_mapped_path,
    overwrite=True,
)

print("\nOutputs:")
print(f"Tags mapped: {tags_mapped_path}")
print(f"Stage 1:     {stage1_path}")