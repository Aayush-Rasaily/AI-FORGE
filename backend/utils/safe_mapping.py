"""Safe mapping iteration — never walk a live dict that may grow.

Pillow EXIF objects and background pipeline threads both mutate mappings
while another caller is iterating them. That raises:

    RuntimeError: dictionary changed size during iteration

Snapshot keys first, then read values. Do not iterate .items() on a live mapping.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable, List, Sequence, Tuple


def snapshot_keys(mapping: Any) -> List[Any]:
    try:
        return list(mapping.keys())
    except Exception:
        return []


def snapshot_items(mapping: Any) -> List[Tuple[Any, Any]]:
    """Return a stable (key, value) list from a mapping that may mutate on access."""
    items: List[Tuple[Any, Any]] = []
    for key in snapshot_keys(mapping):
        try:
            if hasattr(mapping, "get"):
                items.append((key, mapping.get(key)))
            else:
                items.append((key, mapping[key]))
        except Exception:
            continue
    return items


def is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray))


def mapping_to_dict(mapping: Any) -> dict:
    return {key: value for key, value in snapshot_items(mapping)}
