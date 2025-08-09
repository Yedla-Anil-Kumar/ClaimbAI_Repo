#!/usr/bin/env python3
"""Run LLM micro-agents across all local git repos under a base folder, in parallel."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from dotenv import load_dotenv

# ---- Make project root importable (so `micro_agents` resolves when run from scripts/) ----
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------------------------------------------------------------------------

from micro_agents.orchestrator import MicroAgentOrchestrator  # noqa: E402


def find_git_repos(base: Path) -> Iterable[Path]:
    """Yield repo roots that contain a .git directory."""
    for root, dirs, _ in os.walk(base):
        if ".git" in dirs:
            yield Path(root)
            # Do not descend into nested repos beneath this one
            dirs.clear()


def scan_single_repo(
    repo_path: Path,
    model: str,
    temperature: float,
    per_repo_dir: Path,
) -> Tuple[str, Dict]:
    """Scan one repository with a fresh orchestrator instance."""
    orchestrator = MicroAgentOrchestrator(model=model, temperature=temperature)
    result = orchestrator.analyze_repo(str(repo_path))

    # Write per-repo JSON immediately (safe in parallel; unique filenames)
    per_repo_dir.mkdir(parents=True, exist_ok=True)
    out_file = per_repo_dir / f"{repo_path.name}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return repo_path.name, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run LLM micro-agents on all repos in a folder (in parallel)."
    )
    parser.add_argument(
        "--base",
        default="useful_repos",
        help="Folder containing cloned git repos (default: useful_repos).",
    )
    parser.add_argument(
        "--out",
        default="data/micro_agents/all_results.json",
        help="Aggregate JSON output path.",
    )
    parser.add_argument(
        "--per-repo-dir",
        default="data/micro_agents/per_repo",
        help="Directory to store per-repo JSON results.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model; overrides env OPENAI_MODEL if provided.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="LLM sampling temperature.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=min(8, (os.cpu_count() or 4) * 2),
        help="Maximum parallel workers (default: min(8, 2*CPU)).",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()  # picks up OPENAI_API_KEY, OPENAI_MODEL, etc.

    args = parse_args()
    base_dir = Path(args.base).resolve()
    out_path = Path(args.out).resolve()
    per_repo_dir = Path(args.per_repo_dir).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_repo_dir.mkdir(parents=True, exist_ok=True)

    repos: List[Path] = list(find_git_repos(base_dir))
    print(f"🔍 Found {len(repos)} repos under {base_dir}\n")

    aggregate: List[Dict] = []
    errors: List[Tuple[str, str]] = []

    # NOTE: ThreadPoolExecutor is ideal here (I/O-bound LLM calls).
    # If you prefer processes, swap in ProcessPoolExecutor, but keep in mind
    # OpenAI rate limits and process spawn overhead.
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(
                scan_single_repo,
                repo_path,
                args.model,
                args.temperature,
                per_repo_dir,
            ): repo_path
            for repo_path in repos
        }

        for future in as_completed(futures):
            repo_path = futures[future]
            name = repo_path.name
            try:
                repo_name, result = future.result()
                scores = result.get("scores", {})
                print(
                    f"✅ {repo_name:<30} "
                    f"Dev: {scores.get('development_maturity', 0):>4} | "
                    f"Innov: {scores.get('innovation_pipeline', 0):>4}"
                )
                aggregate.append(result)
            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                print(f"❌ Error scanning {name}: {msg}")
                errors.append((name, msg))

    # Write aggregate results
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2)

    print(f"\n📝 Per-repo results written to: {per_repo_dir}")
    print(f"🧾 Aggregate JSON written to : {out_path}")
    if errors:
        print("\n⚠️  Repos with errors:")
        for name, msg in errors:
            print(f"   - {name}: {msg}")


if __name__ == "__main__":
    main()
