"""
JSON report export — complete structured forensic report bundle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def export_json(bundle: Dict[str, Any], output_path: Path) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, default=str),
        encoding="utf-8",
    )
    return str(output_path)
