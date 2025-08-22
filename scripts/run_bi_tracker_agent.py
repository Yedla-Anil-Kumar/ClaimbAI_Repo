#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data_Collection_Agents.bi_tracker.canonical import BIInputs  # noqa: E402
from Data_Collection_Agents.bi_tracker.orchestrator import BIOrchestrator  # noqa: E402

def main() -> None:
    load_dotenv()

    SAMPLES_DIR = Path("data/bi_tracker/Sample_Inputs")
    OUTPUT_DIR  = Path("data/bi_tracker/Output")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    if not sample_files:
        raise RuntimeError(f"No JSON files found in {SAMPLES_DIR}")

    orch = BIOrchestrator(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
    )

    for sample in sample_files:
        payload = json.loads(sample.read_text(encoding="utf-8"))
        bi = BIInputs.from_dict(payload)
        result = orch.analyze_inputs(bi)
        out_file = OUTPUT_DIR / f"{sample.stem}_result.json"
        out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

        scores = result.get("scores", {})
        print(
            f"✅ {sample.name:<28} "
            f"Business Integration: {scores.get('business_integration', 0):>4} | "
            f"Decision Making: {scores.get('decision_making', 0):>4}"
        )

if __name__ == "__main__":
    main()
