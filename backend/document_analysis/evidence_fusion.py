"""
AI-FORGE Evidence Fusion
------------------------

Centralized evidence fusion and JSON serialization.

Responsibilities:
1. Combine forensic evidence.
2. Call risk intelligence.
3. Convert NumPy / Torch / custom objects to native Python types.
4. Guarantee FastAPI-safe JSON output.

IMPORTANT:
Do NOT import risk_intelligence at module level.
The import is intentionally local to avoid circular imports.
"""

from typing import Any

from backend.utils.safe_mapping import is_mapping, snapshot_items


def make_json_serializable(value: Any, _stack: set | None = None) -> Any:
    """
    Recursively convert values into JSON-safe Python types.

    Snapshot mapping keys before reading values so live EXIF objects and
    dictionaries mutated by background analysis threads cannot raise
    "dictionary changed size during iteration". Circular PDF object graphs
    are replaced with a placeholder instead of overflowing the stack.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if _stack is None:
        _stack = set()

    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, np.ndarray):
            return make_json_serializable(value.tolist(), _stack)

    except ImportError:
        pass

    try:
        import torch

        if isinstance(value, torch.Tensor):
            value = value.detach().cpu()
            if value.numel() == 1:
                return value.item()
            return make_json_serializable(value.tolist(), _stack)

    except ImportError:
        pass

    if is_mapping(value) or isinstance(value, (list, tuple, set)):
        object_id = id(value)
        if object_id in _stack:
            return "<circular>"
        _stack.add(object_id)
        try:
            if is_mapping(value):
                return {
                    str(key): make_json_serializable(val, _stack)
                    for key, val in snapshot_items(value)
                }
            return [
                make_json_serializable(item, _stack)
                for item in value
            ]
        finally:
            _stack.discard(object_id)

    try:
        from dataclasses import is_dataclass, asdict
        if is_dataclass(value) and not isinstance(value, type):
            return make_json_serializable(asdict(value), _stack)
    except Exception:
        pass

    if hasattr(value, "to_dict"):
        try:
            return make_json_serializable(value.to_dict(), _stack)
        except Exception:
            pass

    if hasattr(value, "item"):
        try:
            return make_json_serializable(value.item(), _stack)
        except Exception:
            pass

    if hasattr(value, "tolist"):
        try:
            return make_json_serializable(value.tolist(), _stack)
        except Exception:
            pass

    return str(value)


def fuse_evidence(evidence_list=None):
    """
    Main evidence fusion entry point.

    Parameters
    ----------
    evidence_list : list
        List of forensic evidence results.

    Returns
    -------
    dict
        Fully JSON-safe fused analysis result.
    """

    if evidence_list is None:
        evidence_list = []

    # ---------------------------------------------------------
    # Normalize input first
    # ---------------------------------------------------------

    evidence_list = make_json_serializable(
        evidence_list
    )

    # ---------------------------------------------------------
    # Local import prevents circular dependency
    # ---------------------------------------------------------

    from backend.document_analysis.risk_intelligence import (
        analyze_risk_intelligence
    )

    # ---------------------------------------------------------
    # Run risk intelligence
    # ---------------------------------------------------------

    result = analyze_risk_intelligence(
        evidence_list
    )

    # ---------------------------------------------------------
    # CRITICAL:
    # Sanitize entire result recursively
    # ---------------------------------------------------------

    result = make_json_serializable(
        result
    )

    # ---------------------------------------------------------
    # Guarantee dictionary
    # ---------------------------------------------------------

    if not isinstance(result, dict):

        result = {
            "result": result
        }

    return result


__all__ = [
    "fuse_evidence",
    "make_json_serializable",
]