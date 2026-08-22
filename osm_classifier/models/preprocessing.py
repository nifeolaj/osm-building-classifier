"""Prepare feature-engineered buildings for model inference."""

from __future__ import annotations

from pathlib import Path
import geopandas as gpd
import joblib
import pandas as pd


MODEL_LEVELS = (
    "l0_res_binary",
    "l1a_res_subtypes",
    "l1b_ind_binary",
    "l2a_ind_subtypes",
    "l2b_comm_binary",
    "l3a_comm_subtypes",
)


def load_level_feature_columns(model_dir: Path,) -> dict[str, list[str]]:
    """Load the exact feature columns selected for each trained model."""
    level_features = {}

    for level in MODEL_LEVELS:
        path = model_dir / f"{level}_feature_cols.pkl"

        if not path.exists():
            raise FileNotFoundError(path)

        level_features[level] = list(joblib.load(path))

        print(f"[models] {level:<22} {len(level_features[level]):>3} features")

    return level_features


def prepare_inference_data(buildings: gpd.GeoDataFrame,
    level_features: dict[str, list[str]],) -> tuple[gpd.GeoDataFrame, dict[str, pd.Series]]:
    """Validate the model input and construct inference-population masks."""
    required_labels = {"stage1_l1", "stage1_l2", "stage2_l1", "stage2_l2",}
    missing_labels = required_labels - set(buildings.columns)
    if missing_labels:
        raise ValueError(f"Missing classification columns: {sorted(missing_labels)}")

    buildings = buildings.copy()

    # Building ID is the key used to assemble the final classification.
    if buildings.index.name != "id":
        if "id" not in buildings.columns:
            raise ValueError("Building dataset has no 'id' column.")
        buildings = buildings.set_index("id")

    if buildings.index.has_duplicates:
        raise ValueError("Building dataset contains duplicate IDs.")

    # Validate the union of all selected model features.
    required_features = set().union(*level_features.values())
    missing_features = required_features - set(buildings.columns)

    if missing_features:
        raise ValueError("Features required by the trained models are missing: "
            f"{sorted(missing_features)}")

    stage1_l1 = buildings["stage1_l1"]
    stage1_l2 = buildings["stage1_l2"]
    stage2_l1 = buildings["stage2_l1"]
    stage2_l2 = buildings["stage2_l2"]

    # Same four populations used in the final preprocessing notebook.
    masks = {
        "train_pool": (stage1_l1.notna() & ~stage1_l1.isin(["filter", "semi_commercial"])
                        & ~stage1_l2.eq("other_service")),
        "predict": stage1_l1.isna() & stage2_l1.isna(),
        "stage2": stage1_l1.isna() & stage2_l1.notna(),
        "excluded": (stage1_l1.isin(["filter", "semi_commercial"]) 
                     | stage1_l2.eq("other_service")),}

    # Ensure every building belongs to exactly one population.
    membership = pd.DataFrame(masks).sum(axis=1)
    overlapping = int(membership.gt(1).sum())
    uncovered = int(membership.eq(0).sum())

    if overlapping or uncovered:
        raise ValueError(f"Population error: {overlapping:,} overlapping and "
            f"{uncovered:,} uncovered buildings.")

    # Buildings with a known L1 but missing L2 need subtype prediction.
    masks.update({
        "trainpool_res_subtype": (masks["train_pool"] & stage1_l1.eq("residential") & stage1_l2.isna()),
        "trainpool_ind_subtype": (masks["train_pool"] & stage1_l1.eq("industrial") & stage1_l2.isna()),
        "trainpool_comm_subtype": (masks["train_pool"] & stage1_l1.eq("commercial") & stage1_l2.isna()),
        "stage2_res_subtype": (masks["stage2"] & stage2_l1.eq("residential") & stage2_l2.isna()),
        "stage2_ind_subtype": (masks["stage2"] & stage2_l1.eq("industrial") & stage2_l2.isna()),
        "stage2_comm_subtype": (masks["stage2"] & stage2_l1.eq("commercial") & stage2_l2.isna()),})

    print("\n" + "=" * 60)
    print("INFERENCE POPULATIONS")
    print("=" * 60)

    for name in (
        "train_pool", "predict", "stage2", "excluded",
        "trainpool_res_subtype", "trainpool_ind_subtype",
        "trainpool_comm_subtype", "stage2_res_subtype",
        "stage2_ind_subtype", "stage2_comm_subtype",
    ):
        print(f"{name:<28} {masks[name].sum():>12,}")

    print(f"{'TOTAL':<28} {len(buildings):>12,}")

    return buildings, masks


