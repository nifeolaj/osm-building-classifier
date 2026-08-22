"""Create the final public databases."""

from osm_classifier.pipeline import run_final_export


building_output, site_output = run_final_export(
    country="germany",
    include_provenance=True,
    overwrite=True,
)

print(f"\nBuildings:        {building_output}")
print(f"Industrial sites: {site_output}")