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


def make_json_serializable(value: Any) -> Any:
    """
    Recursively convert values into JSON-safe Python types.

    Handles:
        - numpy integers
        - numpy floats
        - numpy booleans
        - numpy arrays
        - torch tensors
        - dictionaries
        - lists
        - tuples
        - sets
        - dataclasses
        - objects with item()
        - objects with tolist()

    Returns:
        A structure containing only JSON-compatible values.
    """

    # ---------------------------------------------------------
    # None
    # ---------------------------------------------------------

    if value is None:
        return None

    # ---------------------------------------------------------
    # Native Python JSON types
    # ---------------------------------------------------------

    if isinstance(value, (str, int, float, bool)):
        return value

    # ---------------------------------------------------------
    # NumPy
    # ---------------------------------------------------------

    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, np.ndarray):
            return make_json_serializable(
                value.tolist()
            )

    except ImportError:
        pass

    # ---------------------------------------------------------
    # PyTorch
    # ---------------------------------------------------------

    try:
        import torch

        if isinstance(value, torch.Tensor):

            value = value.detach().cpu()

            if value.numel() == 1:
                return value.item()

            return make_json_serializable(
                value.tolist()
            )

    except ImportError:
        pass

    # ---------------------------------------------------------
    # Dictionary
    # ---------------------------------------------------------

    if isinstance(value, dict):

        return {
            str(key): make_json_serializable(val)
            for key, val in value.items()
        }

    # ---------------------------------------------------------
    # List
    # ---------------------------------------------------------

    if isinstance(value, list):

        return [
            make_json_serializable(item)
            for item in value
        ]

    # ---------------------------------------------------------
    # Tuple
    # ---------------------------------------------------------

    if isinstance(value, tuple):

        return [
            make_json_serializable(item)
            for item in value
        ]

    # ---------------------------------------------------------
    # Set
    # ---------------------------------------------------------

    if isinstance(value, set):

        return [
            make_json_serializable(item)
            for item in value
        ]

    # ---------------------------------------------------------
    # Dataclass
    # ---------------------------------------------------------

    try:

        from dataclasses import is_dataclass, asdict

        if is_dataclass(value):

            return make_json_serializable(
                asdict(value)
            )

    except Exception:
        pass

    # ---------------------------------------------------------
    # Objects with to_dict()
    # ---------------------------------------------------------

    if hasattr(value, "to_dict"):

        try:

            return make_json_serializable(
                value.to_dict()
            )

        except Exception:
            pass

    # ---------------------------------------------------------
    # Objects with item()
    # ---------------------------------------------------------

    if hasattr(value, "item"):

        try:

            return make_json_serializable(
                value.item()
            )

        except Exception:
            pass

    # ---------------------------------------------------------
    # Objects with tolist()
    # ---------------------------------------------------------

    if hasattr(value, "tolist"):

        try:

            return make_json_serializable(
                value.tolist()
            )

        except Exception:
            pass

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------

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