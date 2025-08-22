#!/usr/bin/env python3
# scripts/run_ml_ops_agent.py
"""Run the ML Ops agent on one inputs JSON, or on all JSONs in a folder."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from dotenv import load_dotenv

# Allow Data_Collection_Agents imports when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data_Collection_Agents.ml_ops_agent.orchestrator import MLOpsOrchestrator  # noqa: E402
from Data_Collection_Agents.ml_ops_agent.orchestrator import MLOpsInputs       # noqa: E402


def iter_input_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        for p in sorted(path.glob("*.json")):
            if p.is_file():
                yield p
    else:
        raise FileNotFoundError(f"No such file or directory: {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run ML Ops agent on JSON input(s).")
    p.add_argument(
        "--inputs",
        default="data/ml_ops/sample_inputs",
        help="Path to a single JSON file OR a directory of JSON files.",
    )
    p.add_argument(
        "--out",
        default="data/ml_ops/aggregate_results.json",
        help="Aggregate JSON output path.",
    )
    p.add_argument(
        "--per-input-dir",
        default="data/ml_ops/per_input",
        help="Directory to write per-input result JSONs.",
    )
    p.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model ID.",
    )
    p.add_argument("--temperature", type=float, default=0.0)
    return p.parse_args()


def run_once(args: argparse.Namespace) -> None:
    inputs_path = Path(args.inputs).resolve()
    out_path = Path(args.out).resolve()
    per_input_dir = Path(args.per_input_dir).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_input_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = list(iter_input_files(inputs_path))
    if not files:
        print(f"⚠️  No JSON files found under {inputs_path}")
        return

    print(f"🔍 Found {len(files)} input file(s) under {inputs_path}\n")

    aggregate: List[Dict] = []
    errors: List[Tuple[str, str]] = []

    orch = MLOpsOrchestrator(model=args.model, temperature=args.temperature)

    def _fmt(x):
        return f"{x:>4}" if isinstance(x, (int, float)) else "   -"

    for f in files:
        name = f.stem
        try:
            blob = json.loads(f.read_text(encoding="utf-8"))
            ml_inputs = MLOpsInputs.from_json(blob)
            result = orch.analyze_inputs(ml_inputs)

            # write per-input result
            out_file = per_input_dir / f"{name}.json"
            out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

            # AIMRI summary
            aimri = result.get("aimri_scores", {})
            a3 = aimri.get("3_ai_ml_capabilities", {}).get("overall")
            a8 = aimri.get("8_process_maturity", {}).get("overall")

            print(
                f"✅ {name:<24} "
                f"Cat3(AI/ML): {_fmt(a3)} | "
                f"Cat8(Process): {_fmt(a8)}"
            )

            aggregate.append(result)

        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            print(f"❌ {name}: {msg}")
            errors.append((name, msg))

    # write aggregate
    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    print(f"\n📝 Per-input results written to: {per_input_dir}")
    print(f"🧾 Aggregate JSON written to : {out_path}")
    if errors:
        print("\n⚠️  Errors:")
        for name, msg in errors:
            print(f"   - {name}: {msg}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    run_once(args)


if __name__ == "__main__":
    main()
