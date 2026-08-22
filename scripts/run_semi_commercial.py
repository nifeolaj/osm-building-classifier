"""Run national semi-commercial classification."""

from osm_classifier.pipeline import (
    run_semi_commercial_classification,
)


output = run_semi_commercial_classification(
    country="germany",
    overwrite=True,
)

print(f"\nSemi-commercial output: {output}")