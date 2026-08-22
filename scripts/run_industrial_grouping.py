"""Run national industrial-building grouping."""

from osm_classifier.pipeline import run_industrial_grouping


building_output, parent_output = run_industrial_grouping(
    country="germany",
    overwrite=True,
)

print(f"\nBuildings: {building_output}")
print(f"Parents:   {parent_output}")