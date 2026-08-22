"""Tests for the optional building-height extension."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from osm_classifier.features.optional_height import (
    HEIGHT_FEATURE,
    add_optional_height_feature,
    load_height_dataset,
)


def test_load_height_dataset(tmp_path):
    """A generic spatial height file should load correctly."""
    gdf = gpd.GeoDataFrame(
        {"height_m": [10.0, 20.0]},
        geometry=[box(0, 0, 10, 10), box(20, 20, 30, 30)],
        crs="EPSG:3035",
    )

    path = tmp_path / "heights.parquet"
    gdf.to_parquet(path, index=False)

    result = load_height_dataset(path, "height_m")

    assert len(result) == 2
    assert "height_m" in result.columns
    assert "geometry" in result.columns
    assert result.crs is not None


def test_exact_height_matching():
    """Identical external and OSM footprints should match exactly."""
    buildings = gpd.GeoDataFrame(
        {"id": [1, 2]},
        geometry=[box(0, 0, 10, 10), box(20, 20, 30, 30)],
        crs="EPSG:3035",
    )

    heights = gpd.GeoDataFrame(
        {"height_m": [12.5, 25.0]},
        geometry=[box(0, 0, 10, 10), box(20, 20, 30, 30)],
        crs="EPSG:3035",
    )

    result = add_optional_height_feature(
        buildings,
        heights,
        height_column="height_m",
        projected_crs="EPSG:3035",
    )

    assert HEIGHT_FEATURE in result.columns
    assert result[HEIGHT_FEATURE].tolist() == pytest.approx([12.5, 25.0])


def test_unmatched_height_returns_nan():
    """Buildings without an external footprint match should retain missing height."""
    buildings = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3035",
    )

    heights = gpd.GeoDataFrame(
        {"height_m": [15.0]},
        geometry=[box(100, 100, 110, 110)],
        crs="EPSG:3035",
    )

    result = add_optional_height_feature(
        buildings,
        heights,
        height_column="height_m",
        projected_crs="EPSG:3035",
    )

    assert np.isnan(result.loc[0, HEIGHT_FEATURE])


def test_missing_height_column(tmp_path):
    """The requested height column must exist."""
    gdf = gpd.GeoDataFrame(
        {"other": [10.0]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3035",
    )

    path = tmp_path / "heights.parquet"
    gdf.to_parquet(path, index=False)

    with pytest.raises(ValueError, match="Height column"):
        load_height_dataset(path, "height_m")