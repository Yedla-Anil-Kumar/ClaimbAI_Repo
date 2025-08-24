# scripts/run_enterprise_agent.py
#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data_Collection_Agents.enterprise_agent.canonical import EnterpriseInputs
from Data_Collection_Agents.enterprise_agent.orchestrator import EnterpriseOrchestrator

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Enterprise Systems agent on JSON input(s).")
    p.add_argument("--inputs", default="data/enterprise_agent/sample_inputs", help="File or directory of JSON.")
    p.add_argument("--out", default="data/enterprise_agent/aggregate_results.json", help="Aggregate output path.")
    p.add_argument("--per-input-dir", default="data/enterprise_agent/Output", help="Where to write per-input JSONs.")
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL","gpt-4o-mini"))
    p.add_argument("--temperature", type=float, default=0.0)
    return p.parse_args()

def iter_json(path: Path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.glob("*.json")):
        if p.is_file():
            yield p

def main() -> None:
    load_dotenv()
    args = parse_args()

    inputs_path = Path(args.inputs).resolve()
    out_path = Path(args.out).resolve()
    per_dir = Path(args.per_input_dir).resolve()
    per_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    orch = EnterpriseOrchestrator(model=args.model, temperature=args.temperature)

    aggregate = []
    for f in iter_json(inputs_path):
        name = f.stem
        payload = json.loads(f.read_text(encoding="utf-8"))
        ent = EnterpriseInputs.from_dict(payload)
        result = orch.analyze_inputs(ent)
        (per_dir / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        aggregate.append(result)
        print(f"✅ {name}")

    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(f"🧾 Aggregate → {out_path}")

if __name__ == "__main__":
    main()
