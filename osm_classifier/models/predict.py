"""Run hierarchical building-classification inference."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


MODEL_FILES = {
    "l0_res_binary": "l0_res_binary_lgb_PRODUCTION_FINAL.pkl",
    "l1a_res_subtypes": "l1a_res_subtypes_xgb_PRODUCTION_FINAL.pkl",
    "l1b_ind_binary": "l1b_ind_binary_xgb_PRODUCTION_FINAL.pkl",
    "l2a_ind_subtypes": "l2a_ind_subtypes_lgb_PRODUCTION_FINAL.pkl",
    "l2b_comm_binary": "l2b_comm_binary_xgb_PRODUCTION_FINAL.pkl",
    "l3a_comm_subtypes": "l3a_comm_subtypes_lgb_PRODUCTION_FINAL.pkl",
}

ENCODER_FILES = {
    "residential": "label_encoder_res.pkl",
    "industrial": "label_encoder_ind.pkl",
    "commercial": "label_encoder_comm.pkl",
}

RESULT_COLUMNS = ["final_l1", "final_l2", "l1_confidence", "l2_confidence", "label_source",]


def load_prediction_artifacts(model_dir: Path,) -> tuple[dict[str, object], dict[str, object]]:
    """Load the six production models and three subtype encoders."""
    model_dir = Path(model_dir)
    models = {}
    encoders = {}

    for level, filename in MODEL_FILES.items():
        path = model_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)

        models[level] = joblib.load(path)
        print(f"[models] Loaded {level:<22} {type(models[level]).__name__}")

    for label, filename in ENCODER_FILES.items():
        path = model_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)

        encoders[label] = joblib.load(path)
        print(f"[models] Loaded {label:<22} encoder")

    return models, encoders


def _select_features(buildings: pd.DataFrame, ids: pd.Index, feature_columns: list[str],) -> pd.DataFrame:
    """Select exact ordered model features for the requested buildings."""
    missing = [column for column in feature_columns if column not in buildings.columns]
    if missing:
        raise ValueError(f"Missing model features: {missing}")

    X = buildings.loc[ids, feature_columns]
    non_numeric = X.select_dtypes(exclude="number").columns.tolist()

    if non_numeric:
        raise TypeError(f"Non-numeric model features: {non_numeric}")

    return X


def predict_with_proba(model, X: pd.DataFrame, *, binary: bool,
    threshold: float = 0.5,) -> tuple[np.ndarray, np.ndarray]:
    """Return integer predictions and predicted-class confidence."""
    if len(X) == 0:
        return (np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32),)

    # Models were trained using NumPy arrays.
    X_array = X.to_numpy()

    if not hasattr(model, "predict_proba"):
        predictions = np.asarray(model.predict(X_array)).astype(np.int32)
        confidence = np.full(len(predictions), np.nan, dtype=np.float32)
        return predictions, confidence

    probabilities = model.predict_proba(X_array)

    if binary:
        predictions = (probabilities[:, 1] >= threshold).astype(np.int32)
        confidence = np.where(predictions == 1, probabilities[:, 1],
            probabilities[:, 0],).astype(np.float32)

        return predictions, confidence

    predictions = np.asarray(model.predict(X_array)).astype(np.int32)
    confidence = probabilities[np.arange(len(predictions)), predictions,].astype(np.float32)

    return predictions, confidence

def _print_subtype_distribution(labels: np.ndarray) -> None:
    """Print the predicted subtype distribution."""
    print("  Subtype distribution:")
    classes, counts = np.unique(labels, return_counts=True)

    for label, count in zip(classes, counts):
        print(f"    {str(label):<25}: {count:>9,}")

def predict_full_cascade(buildings: pd.DataFrame, predict_mask: pd.Series, models: dict[str, object],
    encoders: dict[str, object], level_features: dict[str, list[str]], thresholds: dict[str, float],) -> pd.DataFrame:
    """Run the complete hierarchy on fully unclassified buildings."""
    predict_ids = buildings.index[predict_mask]

    results = pd.DataFrame(index=predict_ids)
    results["final_l1"] = pd.Series(index=predict_ids, dtype="object")
    results["final_l2"] = pd.Series(index=predict_ids, dtype="object")
    results["l1_confidence"] = np.nan
    results["l2_confidence"] = np.nan
    results["label_source"] = "ml_predicted"

    print(f"[predict] Full cascade: {len(predict_ids):,} buildings")

    # --------------------------------------------------------------
    # L0: residential vs non-residential
    # 0 = residential, 1 = non-residential
    # --------------------------------------------------------------
    X = _select_features(buildings, predict_ids, level_features["l0_res_binary"],)
    predictions, confidence = predict_with_proba(models["l0_res_binary"], X,
        binary=True, threshold=thresholds["l0_res_binary"],)

    residential_ids = predict_ids[predictions == 0]
    nonresidential_ids = predict_ids[predictions == 1]

    results.loc[residential_ids, "final_l1"] = "residential"
    results.loc[nonresidential_ids, "final_l1"] = "non_residential_pending"
    results.loc[predict_ids, "l1_confidence"] = confidence

    print(f"  Residential:     {len(residential_ids):,}")
    print(f"  Non-residential: {len(nonresidential_ids):,}")

    # --------------------------------------------------------------
    # L1a: residential subtypes
    # --------------------------------------------------------------
    if len(residential_ids):
        X = _select_features(buildings, residential_ids, level_features["l1a_res_subtypes"],)
        predictions, confidence = predict_with_proba(models["l1a_res_subtypes"], X, binary=False,)
        labels = encoders["residential"].inverse_transform(predictions)

        results.loc[residential_ids, "final_l2"] = labels
        results.loc[residential_ids, "l2_confidence"] = confidence

        _print_subtype_distribution(labels)

    # --------------------------------------------------------------
    # L1b: industrial vs non-industrial
    # 0 = non-industrial, 1 = industrial
    # --------------------------------------------------------------
    X = _select_features(buildings, nonresidential_ids, level_features["l1b_ind_binary"],)
    predictions, confidence = predict_with_proba(models["l1b_ind_binary"], X,
        binary=True, threshold=thresholds["l1b_ind_binary"],)

    industrial_ids = nonresidential_ids[predictions == 1]
    nonindustrial_ids = nonresidential_ids[predictions == 0]

    results.loc[industrial_ids, "final_l1"] = "industrial"
    results.loc[nonindustrial_ids, "final_l1"] = "non_industrial_pending"
    results.loc[nonresidential_ids, "l1_confidence"] = confidence

    print(f"  Industrial:       {len(industrial_ids):,}")
    print(f"  Non-industrial:   {len(nonindustrial_ids):,}")

    # --------------------------------------------------------------
    # L2a: industrial subtypes
    # --------------------------------------------------------------
    if len(industrial_ids):
        X = _select_features(buildings, industrial_ids, level_features["l2a_ind_subtypes"],)
        predictions, confidence = predict_with_proba(models["l2a_ind_subtypes"], X, binary=False,)
        labels = encoders["industrial"].inverse_transform(predictions)

        results.loc[industrial_ids, "final_l2"] = labels
        results.loc[industrial_ids, "l2_confidence"] = confidence

        _print_subtype_distribution(labels)

    # --------------------------------------------------------------
    # L2b: commercial vs other
    # 0 = other, 1 = commercial
    # --------------------------------------------------------------
    X = _select_features(buildings, nonindustrial_ids, level_features["l2b_comm_binary"],)
    predictions, confidence = predict_with_proba(models["l2b_comm_binary"], X,
        binary=True, threshold=thresholds["l2b_comm_binary"],)

    commercial_ids = nonindustrial_ids[predictions == 1]
    other_ids = nonindustrial_ids[predictions == 0]

    results.loc[commercial_ids, "final_l1"] = "commercial"
    results.loc[other_ids, "final_l1"] = "other"
    results.loc[nonindustrial_ids, "l1_confidence"] = confidence

    print(f"  Commercial:       {len(commercial_ids):,}")
    print(f"  Other:            {len(other_ids):,}")

    # --------------------------------------------------------------
    # L3a: commercial subtypes
    # --------------------------------------------------------------
    if len(commercial_ids):
        X = _select_features(buildings, commercial_ids, level_features["l3a_comm_subtypes"],)
        predictions, confidence = predict_with_proba(models["l3a_comm_subtypes"], X, binary=False,)
        labels = encoders["commercial"].inverse_transform(predictions)

        results.loc[commercial_ids, "final_l2"] = labels
        results.loc[commercial_ids, "l2_confidence"] = confidence

        _print_subtype_distribution(labels)

    pending = results["final_l1"].isin(["non_residential_pending", "non_industrial_pending",])

    if pending.any() or results["final_l1"].isna().any():
        raise RuntimeError("Some buildings did not receive a final L1 prediction.")

    results["l1_confidence"] = results["l1_confidence"].astype(np.float32)
    results["l2_confidence"] = results["l2_confidence"].astype(np.float32)

    print("\n[predict] Final L1 distribution:")
    print(results["final_l1"].value_counts().to_string())

    return results[RESULT_COLUMNS]


def predict_missing_subtypes(buildings: pd.DataFrame, masks: dict[str, pd.Series], models: dict[str, object],
    encoders: dict[str, object], level_features: dict[str, list[str]],) -> pd.DataFrame:
    """Predict L2 where Stage 1 or Stage 2 supplied L1 only."""
    jobs = [
        ("trainpool_res_subtype", "residential", "l1a_res_subtypes", "trainpool residential subtypes",),
        ("trainpool_ind_subtype", "industrial", "l2a_ind_subtypes", "trainpool industrial subtypes",),
        ("trainpool_comm_subtype", "commercial", "l3a_comm_subtypes", "trainpool commercial subtypes",),
        ("stage2_res_subtype", "residential", "l1a_res_subtypes", "stage2 residential subtypes",),
        ("stage2_ind_subtype", "industrial", "l2a_ind_subtypes", "stage2 industrial subtypes",),
        ("stage2_comm_subtype", "commercial", "l3a_comm_subtypes", "stage2 commercial subtypes",),]

    frames = []

    print("\n[predict] Predicting missing subtypes...")

    for mask_name, l1_label, model_level, description in jobs:
        ids = buildings.index[masks[mask_name]]
        if len(ids) == 0:
            print(f"  Skipping {description}: 0 buildings")
            continue

        print(f"\n  {description}: {len(ids):,} buildings")

        X = _select_features(buildings, ids, level_features[model_level],)
        predictions, confidence = predict_with_proba(models[model_level], X, binary=False,)
        labels = encoders[l1_label].inverse_transform(predictions)

        frames.append(pd.DataFrame({"final_l1": l1_label, "final_l2": labels,
                    "l1_confidence": np.nan, "l2_confidence": confidence,
                    "label_source": "ml_predicted_subtype",}, index=ids,))

        _print_subtype_distribution(labels)

    if not frames:
        print("\n[predict] Total subtype-only predictions: 0")
        return pd.DataFrame(columns=RESULT_COLUMNS)

    results = pd.concat(frames)

    if results.index.has_duplicates:
        raise ValueError("Duplicate IDs in subtype predictions.")

    results["l1_confidence"] = results["l1_confidence"].astype(np.float32)
    results["l2_confidence"] = results["l2_confidence"].astype(np.float32)

    print(f"\n[predict] Total subtype-only predictions: {len(results):,}")

    return results[RESULT_COLUMNS]