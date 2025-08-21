from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from .canonical import BIInputs

def load_inputs(path: str) -> BIInputs:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Inputs file not found: {p}")
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return BIInputs.from_dict(data)

def write_inputs(path: str, bi: BIInputs) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(bi.__dict__, indent=2), encoding="utf-8")
    return str(p)