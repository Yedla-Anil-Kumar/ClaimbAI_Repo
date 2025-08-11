#!/usr/bin/env python3
# scripts/run_ml_ops_agent.py
"""Run MLOps LLM micro-agents across repos (parallel), optionally on an interval."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from dotenv import load_dotenv

# Allow `ml_ops_agent` imports when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_ops_agent.orchestrator import MLOpsOrchestrator  # noqa: E402


def find_git_repos(base: Path) -> Iterable[Path]:
    for root, dirs, _ in os.walk(base):
        if ".git" in dirs:
            yield Path(root)
            dirs.clear()


def scan_single_repo(
    repo_path: Path, model: str, temperature: float, per_repo_dir: Path
) -> Tuple[str, Dict]:
    orch = MLOpsOrchestrator(model=model, temperature=temperature)
    result = orch.analyze_repo(str(repo_path))

    per_repo_dir.mkdir(parents=True, exist_ok=True)
    out_file = per_repo_dir / f"{repo_path.name}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    scores = result.get("scores", {})
    print(
        f"✅ {repo_path.name:<30} "
        f"AI/ML: {scores.get('ai_ml_capabilities', 0):>4} | "
        f"Ops: {scores.get('operations_maturity', 0):>4}"
    )
    return repo_path.name, result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run MLOps LLM micro-agents on all repos in a folder."
    )
    p.add_argument("--base", default="useful_repos", help="Folder with repos.")
    p.add_argument(
        "--out",
        default="data/ml_ops/all_results.json",
        help="Aggregate JSON output path.",
    )
    p.add_argument(
        "--per-repo-dir",
        default="data/ml_ops/per_repo",
        help="Directory for per-repo JSON.",
    )
    p.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model ID.",
    )
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument(
        "--max-workers",
        type=int,
        default=min(6, (os.cpu_count() or 4) * 2),
        help="Parallel threads (LLM is I/O-bound).",
    )
    p.add_argument(
        "--interval-hours",
        type=float,
        default=0.0,
        help="If > 0, loop and rescan every N hours (e.g., 4.0).",
    )
    return p.parse_args()


def run_once(args: argparse.Namespace) -> None:
    base_dir = Path(args.base).resolve()
    out_path = Path(args.out).resolve()
    per_repo_dir = Path(args.per_repo_dir).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_repo_dir.mkdir(parents=True, exist_ok=True)

    repos: List[Path] = list(find_git_repos(base_dir))
    print(f"🔍 Found {len(repos)} repos under {base_dir}\n")

    aggregate: List[Dict] = []
    errors: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futures = {
            ex.submit(scan_single_repo, repo, args.model, args.temperature, per_repo_dir): repo
            for repo in repos
        }
        for fut in as_completed(futures):
            repo = futures[fut]
            try:
                _, result = fut.result()
                aggregate.append(result)
            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                print(f"❌ {repo.name}: {msg}")
                errors.append((repo.name, msg))

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2)

    print(f"\n📝 Per-repo results written to: {per_repo_dir}")
    print(f"🧾 Aggregate JSON written to : {out_path}")
    if errors:
        print("\n⚠️  Errors:")
        for name, msg in errors:
            print(f"   - {name}: {msg}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    if args.interval_hours > 0:
        while True:
            run_once(args)
            sleep_s = max(60.0, args.interval_hours * 3600.0)
            print(f"\n⏳ Sleeping {int(sleep_s)}s before next collection...")
            time.sleep(sleep_s)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
