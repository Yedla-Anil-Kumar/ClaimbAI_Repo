#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from Data_Collection_Agents.bi_tracker.canonical import BIInputs # noqa: E042
from Data_Collection_Agents.bi_tracker.orchestrator import BIOrchestrator # noqa: E042

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> None:
    load_dotenv()

    sample_path = Path("data/bi_tracker/sample_inputs.json")
    out_dir = Path("data/bi_tracker/samples")
    out_dir.mkdir(parents=True, exist_ok=True)

    arr = json.loads(sample_path.read_text(encoding="utf-8"))
    if not isinstance(arr, list) or not arr:
        raise RuntimeError("sample_inputs.json must be a non-empty array")

    orch = BIOrchestrator(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
    )

    for idx, payload in enumerate(arr, start=1):
        bi = BIInputs.from_dict(payload)
        result = orch.analyze_inputs(bi)
        out_file = out_dir / f"result_{idx}.json"
        out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"✅ Wrote {out_file}")

if __name__ == "__main__":
    main()