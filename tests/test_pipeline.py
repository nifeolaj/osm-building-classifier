import pytest
import osm_classifier.pipeline as pipeline

def test_run_full_pipeline(monkeypatch, tmp_path):
    calls = []
    pbf = tmp_path / "test.osm.pbf"
    pbf.touch()

    extracted = {
        name: tmp_path / f"{name}.parquet"
        for name in ["buildings", "landuse", "pois", "roads", "railways", "waterways", "manmade"]
    }
    context = {
        name: tmp_path / f"{name}_mapped.parquet"
        for name in ["landuse", "pois", "roads", "railways", "waterways", "manmade"]
    }

    def mock_stage(name, result):
        def run(*args, **kwargs):
            calls.append(name)
            return result
        return run

    stages = {
        "run_extraction": ("extraction", extracted),
        "run_building_cleaning": ("building_cleaning", tmp_path / "cleaned.parquet"),
        "run_context_mapping": ("context_mapping", context),
        "run_tag_mapping": ("tag_mapping", tmp_path / "tags.parquet"),
        "run_stage1_classification": ("stage1", tmp_path / "stage1.parquet"),
        "run_stage2_classification": ("stage2", tmp_path / "stage2.parquet"),
        "run_feature_engineering": ("features", tmp_path / "features.parquet"),
        "run_model_inference": ("inference", tmp_path / "classified.parquet"),
        "run_semi_commercial_classification": ("semi_commercial", tmp_path / "semi.parquet"),
        "run_industrial_grouping": (
            "industrial_grouping",
            (tmp_path / "grouped.parquet", tmp_path / "parents.parquet"),
        ),
        "run_final_export": (
            "final_export",
            (tmp_path / "buildings.parquet", tmp_path / "sites.parquet"),
        ),
    }

    for function, (name, result) in stages.items():
        monkeypatch.setattr(pipeline, function, mock_stage(name, result))

    outputs = pipeline.run_full_pipeline(
        country="test_region",
        pbf_path=pbf,
        projected_crs="EPSG:3035",
    )

    assert calls == [
        "extraction", "building_cleaning", "context_mapping", "tag_mapping",
        "stage1", "stage2", "features", "inference", "semi_commercial",
        "industrial_grouping", "final_export",
    ]
    assert outputs["final_buildings"] == tmp_path / "buildings.parquet"
    assert outputs["final_industrial_sites"] == tmp_path / "sites.parquet"


def test_rejects_geographic_crs(tmp_path):
    pbf = tmp_path / "test.osm.pbf"
    pbf.touch()

    with pytest.raises(ValueError, match="not a projected CRS"):
        pipeline.run_full_pipeline(
            country="test_region",
            pbf_path=pbf,
            projected_crs="EPSG:4326",
        )


def test_rejects_missing_pbf(tmp_path):
    with pytest.raises(FileNotFoundError, match="PBF file not found"):
        pipeline.run_full_pipeline(
            country="test_region",
            pbf_path=tmp_path / "missing.osm.pbf",
            projected_crs="EPSG:3035",
        )


def test_run_full_pipeline_with_height(monkeypatch, tmp_path):
    """Height input should run height integration and select height-aware downstream stages."""
    calls = []
    pbf = tmp_path / "test.osm.pbf"
    pbf.touch()

    height_data = tmp_path / "heights.parquet"
    height_data.touch()

    extracted = {
        name: tmp_path / f"{name}.parquet"
        for name in ["buildings", "landuse", "pois", "roads", "railways", "waterways", "manmade"]
    }
    context = {
        name: tmp_path / f"{name}_mapped.parquet"
        for name in ["landuse", "pois", "roads", "railways", "waterways", "manmade"]
    }

    def mock_stage(name, result):
        def run(*args, **kwargs):
            calls.append((name, kwargs))
            return result
        return run

    stages = {
        "run_extraction": ("extraction", extracted),
        "run_building_cleaning": ("building_cleaning", tmp_path / "cleaned.parquet"),
        "run_context_mapping": ("context_mapping", context),
        "run_tag_mapping": ("tag_mapping", tmp_path / "tags.parquet"),
        "run_stage1_classification": ("stage1", tmp_path / "stage1.parquet"),
        "run_stage2_classification": ("stage2", tmp_path / "stage2.parquet"),
        "run_feature_engineering": ("features", tmp_path / "features.parquet"),
        "run_optional_height": ("height", tmp_path / "features_height.parquet"),
        "run_model_inference": ("inference", tmp_path / "classified_height.parquet"),
        "run_semi_commercial_classification": ("semi_commercial", tmp_path / "semi_height.parquet"),
        "run_industrial_grouping": (
            "industrial_grouping",
            (tmp_path / "grouped_height.parquet", tmp_path / "parents_height.parquet"),
        ),
        "run_final_export": (
            "final_export",
            (tmp_path / "buildings_height.parquet", tmp_path / "sites_height.parquet"),
        ),
    }

    for function, (name, result) in stages.items():
        monkeypatch.setattr(pipeline, function, mock_stage(name, result))

    outputs = pipeline.run_full_pipeline(
        country="test_region",
        pbf_path=pbf,
        projected_crs="EPSG:3035",
        height_data=height_data,
        height_column="height_m",
    )

    names = [name for name, _ in calls]

    assert names == [
        "extraction", "building_cleaning", "context_mapping", "tag_mapping",
        "stage1", "stage2", "features", "height", "inference",
        "semi_commercial", "industrial_grouping", "final_export",
    ]

    call_kwargs = {name: kwargs for name, kwargs in calls}

    assert call_kwargs["inference"]["use_height"] is True
    assert call_kwargs["semi_commercial"]["use_height"] is True
    assert call_kwargs["industrial_grouping"]["use_height"] is True
    assert call_kwargs["final_export"]["use_height"] is True

    assert outputs["final_buildings"] == tmp_path / "buildings_height.parquet"
    assert outputs["final_industrial_sites"] == tmp_path / "sites_height.parquet"