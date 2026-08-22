"""Run national hierarchical building classification."""

from osm_classifier.pipeline import run_model_inference


output = run_model_inference(
    country="germany",
    overwrite=True,
)

print(f"\nFinal classification: {output}")