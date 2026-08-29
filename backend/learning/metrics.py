"""
Classification metrics for detector and system evaluation.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def confusion_matrix(
    y_true: List[int],
    y_pred: List[int],
) -> Tuple[int, int, int, int]:
    """Return TP, FP, TN, FN for binary labels (1=positive/tampered)."""
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == 1 and p == 1:
            tp += 1
        elif t == 0 and p == 1:
            fp += 1
        elif t == 0 and p == 0:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def compute_metrics(
    y_true: List[int],
    y_pred: List[int],
    *,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """Precision, recall, F1, accuracy, FPR, FNR from binary predictions."""
    if not y_true:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "accuracy": 0.0,
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.0,
            "support": 0,
            "threshold": threshold,
        }

    tp, fp, tn, fn = confusion_matrix(y_true, y_pred)
    n = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / n if n > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "support": n,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "threshold": threshold,
    }


def scores_to_binary(scores: List[float], threshold: float = 0.5) -> List[int]:
    return [1 if float(s) >= threshold else 0 for s in scores]


def compute_roc_curve(
    y_true: List[int],
    y_scores: List[float],
    *,
    steps: int = 21,
) -> Dict[str, object]:
    """ROC points and AUC from continuous scores."""
    if not y_true or len(y_true) != len(y_scores):
        return {"points": [], "auc": 0.0}

    thresholds = [i / (steps - 1) for i in range(steps)]
    points: List[Dict[str, float]] = []
    for thr in thresholds:
        pred = scores_to_binary(y_scores, thr)
        tp, fp, tn, fn = confusion_matrix(y_true, pred)
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        points.append({"threshold": round(thr, 4), "tpr": round(tpr, 4), "fpr": round(fpr, 4)})

    # AUC via trapezoidal rule on sorted FPR
    sorted_pts = sorted(points, key=lambda p: p["fpr"])
    auc = 0.0
    for i in range(1, len(sorted_pts)):
        dx = sorted_pts[i]["fpr"] - sorted_pts[i - 1]["fpr"]
        ay = (sorted_pts[i]["tpr"] + sorted_pts[i - 1]["tpr"]) / 2
        auc += dx * ay

    return {"points": points, "auc": round(min(1.0, max(0.0, auc)), 4)}
