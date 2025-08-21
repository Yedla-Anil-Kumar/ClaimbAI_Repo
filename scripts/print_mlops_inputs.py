#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow Data_Collection_Agents imports when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Data_Collection_Agents.ml_ops_agent.repo_extractors import scan_repo  # noqa: E402
from Data_Collection_Agents.ml_ops_agent.metrics_engine import (          # noqa: E402
    payload_cicd_policy_gates,
    payload_registry_governance_readiness,
    payload_artifact_lineage_readiness,
    payload_monitoring_readiness,
    payload_validation_readiness,
    payload_lineage_practices,
    payload_dora_readiness,
    payload_cost_attribution,
    payload_slo_declared,
)

def find_git_repos(base: Path):
    for root, dirs, _ in os.walk(base):
        if ".git" in dirs:
            yield Path(root)
            dirs.clear()

def safe_repo_dir(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._@" else "_" for ch in name)

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser("Dump MLOps LLM inputs per repo into data/ml_ops/inputs/<repo>/")
    ap.add_argument("--base", default="useful_repos", help="Folder containing git repos (walks for .git)")
    ap.add_argument("--out-base", default="data/ml_ops/inputs", help="Output base directory")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    out_base = Path(args.out_base).resolve()
    repos = list(find_git_repos(base))
    print(f"🔎 Found {len(repos)} repos under {base}")

    for repo in repos:
        print(f"➡️  {repo.name}")
        ev = scan_repo(str(repo))

        repo_dir = out_base / safe_repo_dir(repo.name)
        # Trimmed evidence snapshot (what you may want to show)
        evidence_trimmed = {
            "cicd_workflows": ev.cicd_workflows,
            "cicd_policy_gates": ev.cicd_policy_gates,
            "cicd_schedules": ev.cicd_schedules[:10],
            "deploy_jobs": ev.cicd_deploy_job_names[:10],
            "environments": ev.cicd_environments[:10],
            "image_digest_pins": ev.image_digest_pins[:5],
            "unpinned_images": ev.unpinned_images[:5],
            "monitoring_rule_files": ev.monitoring_rule_files[:10],
            "alert_channel_signals": ev.alert_channel_signals[:10],
            "model_card_files": ev.model_card_files[:10],
            "tracking_tools": ev.tracking_tools,
        }
        write_json(repo_dir / "evidence_trimmed.json", evidence_trimmed)

        # Exact payloads fed to the LLM grader
        payloads = {
            "cicd_policy_gates": payload_cicd_policy_gates(ev),
            "registry_governance_readiness": payload_registry_governance_readiness(ev),
            "artifact_lineage_readiness": payload_artifact_lineage_readiness(ev),
            "monitoring_readiness": payload_monitoring_readiness(ev),
            "validation_readiness": payload_validation_readiness(ev),
            "lineage_readiness": payload_lineage_practices(ev),
            "dora_readiness": payload_dora_readiness(ev),
            "cost_attribution_readiness": payload_cost_attribution(ev),
            "slo_declared": payload_slo_declared(ev),
        }
        # One file per payload (easy to open during demo)
        for k, v in payloads.items():
            write_json(repo_dir / f"{k}.json", v)
        # And a combined file
        write_json(repo_dir / "all_payloads.json", payloads)

    print(f"\n✅ Done. Inspect per-repo inputs under: {out_base}")

if __name__ == "__main__":
    main()