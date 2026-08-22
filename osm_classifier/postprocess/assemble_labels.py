"""Assemble final building labels from rules and ML predictions."""

from __future__ import annotations

import numpy as np
import pandas as pd


RESULT_COLUMNS = ["final_l1", "final_l2", "l1_confidence", "l2_confidence", "label_source",]
ML_SUBTYPE_CLASSES = {"residential", "industrial", "commercial"}


def _existing_labels(buildings: pd.DataFrame, mask: pd.Series, l1_column: str,
    l2_column: str, source: str,) -> pd.DataFrame:
    """Create final-label rows from existing Stage 1 or Stage 2 labels."""
    ids = buildings.index[mask]

    return pd.DataFrame({
        "final_l1": buildings.loc[ids, l1_column],
        "final_l2": buildings.loc[ids, l2_column],
        "l1_confidence": np.nan,
        "l2_confidence": np.nan,
        "label_source": source,
    }, index=ids)


def assemble_final_labels(
    buildings: pd.DataFrame,
    masks: dict[str, pd.Series],
    cascade_predictions: pd.DataFrame,
    subtype_predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Combine Stage 1, Stage 2, excluded and predicted labels."""
    required = {"stage1_l1", "stage1_l2", "stage2_l1", "stage2_l2"}
    missing = required - set(buildings.columns)

    if missing:
        raise ValueError(f"Missing label columns: {sorted(missing)}")
    if buildings.index.has_duplicates:
        raise ValueError("Building index contains duplicate IDs.")

    stage1_l1 = buildings["stage1_l1"]
    stage1_l2 = buildings["stage1_l2"]
    stage2_l1 = buildings["stage2_l1"]
    stage2_l2 = buildings["stage2_l2"]

    # Fully labelled Stage 1 buildings pass through unchanged.
    trainpool_full_mask = (masks["train_pool"] & stage1_l1.notna() & stage1_l2.notna())
    results_trainpool_full = _existing_labels(buildings, trainpool_full_mask,
        "stage1_l1", "stage1_l2", "stage1_tagged",)

    # Fully labelled Stage 2 buildings pass through unchanged.
    stage2_full_mask = (masks["stage2"] & stage2_l1.notna() & stage2_l2.notna())
    results_stage2_full = _existing_labels(buildings, stage2_full_mask,
        "stage2_l1", "stage2_l2", "stage2_rule",)

    # Known non-ML L1 classes without a subtype remain without L2.
    trainpool_other_mask = (masks["train_pool"] & stage1_l1.notna()
        & ~stage1_l1.isin(ML_SUBTYPE_CLASSES) & stage1_l2.isna())
    results_trainpool_other = _existing_labels(buildings, trainpool_other_mask,
        "stage1_l1", "stage1_l2", "stage1_tagged",)

    stage2_other_mask = (masks["stage2"] & stage2_l1.notna()
        & ~stage2_l1.isin(ML_SUBTYPE_CLASSES) & stage2_l2.isna())
    results_stage2_other = _existing_labels(buildings, stage2_other_mask,
        "stage2_l1", "stage2_l2", "stage2_rule",)

    # Filters, semi-commercial and commercial/other_service retain Stage 1 labels.
    results_excluded = _existing_labels(buildings, masks["excluded"],
        "stage1_l1", "stage1_l2", "stage1_excluded",)

    frames = [
        cascade_predictions,
        subtype_predictions,
        results_trainpool_full,
        results_stage2_full,
        results_trainpool_other,
        results_stage2_other,
        results_excluded,
    ]

    frames = [frame for frame in frames if not frame.empty]
    results = pd.concat(frames, axis=0)

    # --------------------------------------------------------------
    # Integrity checks
    # --------------------------------------------------------------
    duplicates = int(results.index.duplicated().sum())
    if duplicates:
        duplicate_ids = results.index[results.index.duplicated(keep=False)].unique()

        raise ValueError(f"{duplicates:,} duplicate rows in final labels. "
            f"Example IDs: {duplicate_ids[:10].tolist()}")

    missing_ids = buildings.index.difference(results.index)
    extra_ids = results.index.difference(buildings.index)

    if len(missing_ids) or len(extra_ids):
        raise ValueError(f"Final-label coverage error: {len(missing_ids):,} missing "
            f"and {len(extra_ids):,} extra IDs.")

    null_l1 = int(results["final_l1"].isna().sum())
    if null_l1:
        raise ValueError(f"{null_l1:,} buildings have no final L1 classification.")

    # Restore the original building order.
    results = results.reindex(buildings.index)

    results["l1_confidence"] = results["l1_confidence"].astype(np.float32)
    results["l2_confidence"] = results["l2_confidence"].astype(np.float32)

    print("\n" + "=" * 60)
    print("FINAL CLASSIFICATION SUMMARY")
    print("=" * 60)
    print(f"Buildings: {len(results):,}")

    print("\nLabel sources:")
    print(results["label_source"].value_counts().to_string())

    print("\nFinal L1 classes:")
    l1_counts = results["final_l1"].value_counts()
    total = len(results)

    for label, count in l1_counts.items():
        print(f"  {str(label):<25} {count:>12,}  {count / total:>7.2%}")

    print(f"  {'TOTAL':<25} {total:>12,}")

    return results[RESULT_COLUMNS]