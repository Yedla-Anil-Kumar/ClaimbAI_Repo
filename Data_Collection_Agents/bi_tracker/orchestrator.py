# Data_Collection_Agents/bi_tracker/orchestrator.py
from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict

from .repo_extractors import scan_repo
from .metrics_engine import (
    platform_proxy_metrics,
    payload_bi_deploy_readiness,
    payload_bi_data_freshness,
    payload_bi_kpi_semantics,
    payload_bi_docs_governance,
    payload_bi_access_privacy,
)
# Reuse your existing generic LLMGrader
from Data_Collection_Agents.ml_ops_agent.llm_graders import LLMGrader

def _clamp01(x: float) -> float: return max(0.0, min(1.0, float(x)))
def _band01(band: int) -> float: return max(0.0, min(1.0, (int(band) - 1) / 4.0))

def _score_business_integration(bands: Dict[str, int]) -> float:
    # Emphasize deploy automation + docs/governance; include access/privacy
    comp = [
        _band01(bands.get("deploy_readiness", 1)),
        _band01(bands.get("docs_governance", 1)),
        _band01(bands.get("access_privacy", 1)),
        _band01(bands.get("data_freshness", 1)),
    ]
    # weights sum ~1
    raw = 0.35*comp[0] + 0.25*comp[1] + 0.2*comp[2] + 0.2*comp[3]
    return round(5.0 * _clamp01(raw), 2)

def _score_decision_making(bands: Dict[str, int]) -> float:
    # Emphasize KPI/semantic quality + freshness; governance still matters
    comp = [
        _band01(bands.get("kpi_semantic", 1)),
        _band01(bands.get("data_freshness", 1)),
        _band01(bands.get("docs_governance", 1)),
    ]
    raw = 0.45*comp[0] + 0.35*comp[1] + 0.20*comp[2]
    return round(5.0 * _clamp01(raw), 2)

def _bi_summary(signals: Dict[str, Any]) -> Dict[str, Any]:
    def _lvl(val: float, bands=(0.25, 0.5, 0.75)) -> int:
        if val <= bands[0]: return 0
        if val <= bands[1]: return 1
        if val <= bands[2]: return 2
        return 3

    assets = signals.get("assets", {})
    deploy = signals.get("deploy", {})
    fresh  = signals.get("freshness", {})
    kpi    = signals.get("kpi", {})
    docs   = signals.get("docs", {})
    acc    = signals.get("access_privacy", {})

    return {
        "asset_footprint": assets,
        "deploy_automation": {
            "present": deploy.get("present", False),
            "workflows": deploy.get("workflow_files", [])[:5],
            "commands": deploy.get("deploy_commands", []),
            "schedules": deploy.get("schedules", [])[:3],
        },
        "refresh_scheduling": {
            "present": fresh.get("has_schedule", False),
            "quality_tools": fresh.get("quality_tools", []),
            "validation_schemas": fresh.get("validation_schemas", [])[:5]
        },
        "kpi_semantic": {
            "kpi_catalogs": kpi.get("kpi_catalogs", []),
            "lookml_measures": kpi.get("lookml_measures", 0),
            "dbt_metrics_files": kpi.get("dbt_metrics_files", [])
        },
        "docs_governance": {
            "readmes": docs.get("dashboard_readmes", [])[:8],
            "codeowners": docs.get("codeowners_present", False),
            "review_gates": docs.get("reviewers_required_hint", False)
        },
        "access_privacy": acc
    }

class BIOrchestrator:
    """Repo-only BI pipeline: Extract → Deterministic metrics → One-shot LLM grading → Scores."""
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 512):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.grader = LLMGrader(model=model, temperature=temperature, max_tokens=max_tokens)

    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        root = Path(repo_path)

        # 1) Extract deterministic evidence
        ev = scan_repo(repo_path)

        # 2) Deterministic platform proxies
        plat = platform_proxy_metrics(ev)

        # 3) One-shot grading payloads
        g = self.grader
        gkw = dict(max_tokens=self.max_tokens)
        g_deploy = g.grade("bi_deploy_readiness", payload_bi_deploy_readiness(ev), **gkw)
        g_fresh  = g.grade("bi_data_freshness",  payload_bi_data_freshness(ev), **gkw)
        g_kpi    = g.grade("bi_kpi_semantics",   payload_bi_kpi_semantics(ev), **gkw)
        g_docs   = g.grade("bi_docs_governance", payload_bi_docs_governance(ev), **gkw)
        g_acc    = g.grade("bi_access_privacy",  payload_bi_access_privacy(ev), **gkw)

        # 4) Assemble signals
        bands = {
            "deploy_readiness": g_deploy["band"],
            "data_freshness":   g_fresh["band"],
            "kpi_semantic":     g_kpi["band"],
            "docs_governance":  g_docs["band"],
            "access_privacy":   g_acc["band"],
        }

        signals: Dict[str, Any] = {
            "platforms": {
                "tableau": plat["tableau_present"],
                "powerbi": plat["powerbi_present"],
                "looker":  plat["looker_present"],
            },
            "assets": plat["counts"],
            "deploy": g_deploy["metric_id"] and payload_bi_deploy_readiness(ev)["evidence"],
            "freshness": payload_bi_data_freshness(ev)["evidence"],
            "kpi": payload_bi_kpi_semantics(ev)["evidence"],
            "docs": payload_bi_docs_governance(ev)["evidence"],
            "access_privacy": payload_bi_access_privacy(ev)["evidence"],
        }

        # 5) Scores
        scores = {
            "business_integration": _score_business_integration(bands),
            "decision_making": _score_decision_making(bands),
        }

        return {
            "agent": "bi_tracker",
            "repo": root.name,
            "platforms": signals["platforms"],
            "scores": scores,
            "bi_summary": _bi_summary(signals),
            "grading_notes": {
                "bi_deploy_readiness": g_deploy,
                "bi_data_freshness_practices": g_fresh,
                "bi_kpi_semantic_quality": g_kpi,
                "bi_docs_governance": g_docs,
                "bi_access_privacy_readiness": g_acc,
            },
            "mode": "repo_only",
        }