#!/usr/bin/env python3
"""Run BI Tracker on a single input JSON (or generate a demo)."""

from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data_Collection_Agents.bi_tracker.input_loader import load_inputs, write_demo_inputs  # noqa: E402
from Data_Collection_Agents.bi_tracker.canonical import BIInputs  # noqa: E402
from Data_Collection_Agents.bi_tracker.orchestrator import BIOrchestrator  # noqa: E402

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BI Tracker agent on one inputs.json")
    p.add_argument("--inputs", default="data/bi_tracker/inputs.json", help="Path to inputs.json")
    p.add_argument("--out", default="data/bi_tracker/results.json", help="Where to write results")
    p.add_argument("--demo", action="store_true", help="Write a demo inputs.json first")
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    p.add_argument("--temperature", type=float, default=0.0)
    return p.parse_args()

def main() -> None:
    load_dotenv()
    args = parse_args()

    inputs_path = Path(args.inputs).resolve()
    if args.demo:
        inputs_path.parent.mkdir(parents=True, exist_ok=True)
        write_demo_inputs(str(inputs_path))
        print(f"🧪 Demo inputs written to {inputs_path}")

    bi = load_inputs(str(inputs_path))
    orch = BIOrchestrator(model=args.model, temperature=args.temperature)
    result = orch.analyze_inputs(bi)

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"✅ BI Tracker finished.\n🧾 Results: {out_path}")

if __name__ == "__main__":
    main()
