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

from Data_Collection_Agents.enterprise_agent.canonical import (  # noqa: E402
    EnterpriseInputs,
)
from Data_Collection_Agents.enterprise_agent.orchestrator import (  # noqa: E402
    EnterpriseOrchestrator,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Enterprise Systems agent on JSON input(s)."
    )
    parser.add_argument(
        "--inputs",
        default="data/enterprise_agent/sample_inputs",
        help="Path to a single JSON file OR a directory of JSON files.",
    )
    parser.add_argument(
        "--per-input-dir",
        default="data/enterprise_agent/Output",
        help="Directory to write per-input result JSONs.",
    )
    parser.add_argument(
        "--out",
        default="data/enterprise_agent/Output/aggregate_results.json",
        help="Aggregate JSON output path.",
    )
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


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
    files = list(iter_json(inputs_path))
    if not files:
        print(f"⚠️  No JSON files found under {inputs_path}")
        return

    for f in files:
        name = f.stem
        payload = json.loads(f.read_text(encoding="utf-8"))
        ent = EnterpriseInputs.from_dict(payload)
        result = orch.analyze_inputs(ent)

        per_file = per_dir / f"{name}_result.json"
        per_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

        aggregate.append(result)
        print(f"✅ {name:<24} → {per_file.relative_to(per_dir.parent)}")

    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(f"\n📝 Per-input results written to: {per_dir}")
    print(f"🧾 Aggregate JSON written to : {out_path}")


if __name__ == "__main__":
    main()
