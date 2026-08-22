"""Tests for CLI arguments and pipeline input validation."""

from pathlib import Path

import pytest

from osm_classifier.cli import build_parser
from osm_classifier.pipeline import _validate_projected_crs, run_full_pipeline


def test_cli_osm_only():
    """The CLI should continue to support normal OSM-only runs."""
    args = build_parser().parse_args([
        "run",
        "netherlands",
        "--geofabrik-region",
        "europe/netherlands",
        "--projected-crs",
        "EPSG:3035",
    ])

    assert args.country == "netherlands"
    assert args.height_data is None
    assert args.height_column is None


def test_cli_accepts_height_arguments():
    """The CLI should accept generic external height data."""
    args = build_parser().parse_args([
        "run",
        "germany",
        "--geofabrik-region",
        "europe/germany",
        "--projected-crs",
        "EPSG:3035",
        "--height-data",
        "/data/heights.gpkg",
        "--height-column",
        "height_m",
    ])

    assert args.height_data == Path("/data/heights.gpkg")
    assert args.height_column == "height_m"


@pytest.mark.parametrize(
    "height_data,height_column",
    [
        ("heights.parquet", None),
        (None, "height_m"),
    ],
)
def test_height_arguments_must_be_supplied_together(height_data, height_column):
    """Supplying only one height argument should fail before pipeline execution."""
    with pytest.raises(ValueError, match="must be supplied together"):
        run_full_pipeline(
            country="germany",
            geofabrik_region="europe/germany",
            projected_crs="EPSG:3035",
            height_data=height_data,
            height_column=height_column,
        )


def test_projected_crs_is_accepted():
    assert _validate_projected_crs("EPSG:3035") == "EPSG:3035"


def test_geographic_crs_is_rejected():
    with pytest.raises(ValueError, match="not a projected CRS"):
        _validate_projected_crs("EPSG:4326")