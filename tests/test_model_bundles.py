"""Tests for packaged OSM-only and height-enhanced model bundles."""

import joblib

from osm_classifier.paths import MODEL_WEIGHTS_DIR


MODEL_COUNTRY = "germany"

MODELS = {
    "l0_res_binary": "lgb",
    "l1a_res_subtypes": "xgb",
    "l1b_ind_binary": "xgb",
    "l2a_ind_subtypes": "lgb",
    "l2b_comm_binary": "xgb",
    "l3a_comm_subtypes": "lgb",
}

OSM_COUNTS = {
    "l0_res_binary": 63,
    "l1a_res_subtypes": 62,
    "l1b_ind_binary": 68,
    "l2a_ind_subtypes": 69,
    "l2b_comm_binary": 70,
    "l3a_comm_subtypes": 89,
}

HEIGHT_COUNTS = {
    "l0_res_binary": 64,
    "l1a_res_subtypes": 63,
    "l1b_ind_binary": 69,
    "l2a_ind_subtypes": 70,
    "l2b_comm_binary": 71,
    "l3a_comm_subtypes": 90,
}


def test_model_bundles_exist():
    """Both production model variants should contain all required artifacts."""
    base = MODEL_WEIGHTS_DIR / MODEL_COUNTRY

    for variant in ["osm_only", "with_height"]:
        model_dir = base / variant

        assert model_dir.is_dir()

        for level, algorithm in MODELS.items():
            assert (model_dir / f"{level}_feature_cols.pkl").is_file()
            assert (model_dir / f"{level}_{algorithm}_PRODUCTION_FINAL.pkl").is_file()

        for encoder in ["res", "ind", "comm"]:
            assert (model_dir / f"label_encoder_{encoder}.pkl").is_file()


def test_feature_lists_match_model_variants():
    """Height should appear only in the height-enhanced feature lists."""
    base = MODEL_WEIGHTS_DIR / MODEL_COUNTRY

    for level in MODELS:
        osm_cols = joblib.load(
            base / "osm_only" / f"{level}_feature_cols.pkl"
        )
        height_cols = joblib.load(
            base / "with_height" / f"{level}_feature_cols.pkl"
        )

        assert len(osm_cols) == OSM_COUNTS[level]
        assert len(height_cols) == HEIGHT_COUNTS[level]

        assert "building_height_m" not in osm_cols
        assert "building_height_m" in height_cols

        assert "lod2_height_m" not in osm_cols
        assert "lod2_height_m" not in height_cols