# ml_ops_agent/orchestrator.py
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from micro_agents.base_agent import BaseMicroAgent  # for type hints only
from ml_ops_agent.platform_agents import (
    MLflowOpsAgent,
    SageMakerOpsAgent,
    AzureMLOpsAgent,
    KubeflowOpsAgent,
)
from ml_ops_agent.pipeline_agents import (
    ExperimentTrackingAgent,
    PipelineAutomationAgent,
)
from utils.file_utils import list_source_files, list_all_files


def _read_sampled_texts(
    repo_path: str,
    max_files: int = 24,
    max_bytes: int = 8000,
    include_exts: Tuple[str, ...] = (".py", ".yaml", ".yml", ".json", ".toml"),
) -> List[str]:
    """
    Read up to `max_files` code/config files (by extension) and return
    truncated texts for LLM evaluation.
    """
    root = Path(repo_path)
    texts: List[str] = []
    count = 0
    for f in list_all_files(repo_path):
        path = Path(f)
        if path.suffix.lower() not in include_exts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        texts.append(text[:max_bytes])
        count += 1
        if count >= max_files:
            break

    # Fallback to at least some source if none matched
    if not texts:
        src_files = list(list_source_files(repo_path))
        for p in src_files[:max_files]:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="ignore")[:max_bytes])
            except Exception:
                continue
    return texts


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _score_ai_ml_capabilities(signals: Dict[str, Any]) -> float:
    """
    0–5: breadth/depth of platform usage + tracking coverage/quality.
    """
    platform_flags = [
        signals.get("uses_mlflow"),
        signals.get("uses_sagemaker"),
        signals.get("uses_azureml"),
        signals.get("uses_kubeflow"),
    ]
    platform_score = sum(1 for b in platform_flags if b) / 4.0

    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))

    depth_terms = [
        signals.get("mlflow_experiments_count", 0),
        signals.get("mlflow_registered_models_count", 0),
        signals.get("sagemaker_endpoints_count", 0),
        signals.get("azureml_endpoints_count", 0),
        signals.get("kubeflow_pipelines_count", 0),
    ]
    depth = 1.0 - math.exp(-0.25 * sum(max(0, int(v)) for v in depth_terms))

    raw = (
        0.5 * platform_score
        + 0.3 * (0.5 * tracking_cov + 0.5 * tracking_quality)
        + 0.2 * depth
    )
    return round(5.0 * _clamp01(raw), 2)


def _score_operations_maturity(signals: Dict[str, Any]) -> float:
    """
    0–5: automation, scheduling, registry usage, ops quality averages.
    """
    automation_quality = _clamp01(signals.get("pipeline_automation_quality", 0.0))
    scheduling = 1.0 if signals.get("pipeline_scheduling_present") else 0.0

    registry = any(
        [
            signals.get("sagemaker_registry_usage"),
            signals.get("azureml_registry_usage"),
            signals.get("mlflow_registered_models_count", 0) > 0,
        ]
    )
    registry_score = 1.0 if registry else 0.0

    ops_quals = [
        signals.get("mlflow_ops_quality", 0.0),
        signals.get("sagemaker_ops_quality", 0.0),
        signals.get("azureml_ops_quality", 0.0),
        signals.get("kubeflow_ops_quality", 0.0),
    ]
    ops_quality = sum(_clamp01(x) for x in ops_quals) / 4.0

    pipelines_defined = _clamp01(
        min(1.0, signals.get("pipeline_pipelines_defined", 0) / 3.0)
    )

    raw = (
        0.35 * automation_quality
        + 0.2 * scheduling
        + 0.25 * registry_score
        + 0.15 * ops_quality
        + 0.05 * pipelines_defined
    )
    return round(5.0 * _clamp01(raw), 2)


def _level_from_value(value: float, bands: Tuple[float, float, float]) -> int:
    """
    Map a normalized 0..1 value to level 0..3 using three ascending band edges.
    Example: bands=(0.25, 0.5, 0.75).
    """
    if value <= bands[0]:
        return 0
    if value <= bands[1]:
        return 1
    if value <= bands[2]:
        return 2
    return 3


def _aimri_ops_summary(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compose an AIMRI-aligned summary block (subset of 75 dimensions) focused
    on MLOps. We intentionally select dimensions that can be inferred from
    this agent's signals without hardcoding repository details.
    """
    # Platform surface area
    platforms_used = sum(
        bool(x)
        for x in [
            signals.get("uses_mlflow"),
            signals.get("uses_sagemaker"),
            signals.get("uses_azureml"),
            signals.get("uses_kubeflow"),
        ]
    )
    platform_norm = platforms_used / 4.0
    platform_level = _level_from_value(platform_norm, (0.25, 0.5, 0.75))

    # Experiment tracking
    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))
    tracking_cov_level = _level_from_value(tracking_cov, (0.25, 0.5, 0.75))
    tracking_hygiene_level = _level_from_value(tracking_quality, (0.25, 0.5, 0.75))

    # Registry presence and scale
    registered_models = int(signals.get("mlflow_registered_models_count", 0) or 0)
    has_registry = any(
        [
            signals.get("sagemaker_registry_usage"),
            signals.get("azureml_registry_usage"),
            registered_models > 0,
        ]
    )
    reg_scale = 1.0 - math.exp(-0.3 * max(0, registered_models))
    reg_level = _level_from_value(reg_scale, (0.1, 0.4, 0.7))

    # Pipeline automation
    auto_q = _clamp01(signals.get("pipeline_automation_quality", 0.0))
    auto_level = _level_from_value(auto_q, (0.25, 0.5, 0.75))
    scheduling = bool(signals.get("pipeline_scheduling_present"))

    total_pipelines = (
        int(signals.get("pipeline_pipelines_defined", 0) or 0)
        + int(signals.get("sagemaker_pipelines_count", 0) or 0)
        + int(signals.get("azureml_pipelines_count", 0) or 0)
        + int(signals.get("kubeflow_pipelines_count", 0) or 0)
    )
    pipelines_norm = 1.0 - math.exp(-0.25 * max(0, total_pipelines))
    pipelines_level = _level_from_value(pipelines_norm, (0.25, 0.5, 0.75))

    # Serving endpoints
    total_endpoints = int(signals.get("sagemaker_endpoints_count", 0) or 0) + int(
        signals.get("azureml_endpoints_count", 0) or 0
    )
    endpoints_norm = 1.0 - math.exp(-0.35 * max(0, total_endpoints))
    endpoints_level = _level_from_value(endpoints_norm, (0.15, 0.4, 0.7))

    # Experiments scale
    experiments = int(signals.get("mlflow_experiments_count", 0) or 0)
    experiments_norm = 1.0 - math.exp(-0.25 * max(0, experiments))
    experiments_level = _level_from_value(experiments_norm, (0.2, 0.5, 0.8))

    return {
        "platform_surface_area": {
            "level": platform_level,
            "value": platforms_used,
            "desc": "Distinct MLOps platforms detected (0–4).",
        },
        "experiment_tracking": {
            "coverage_level": tracking_cov_level,
            "coverage_value": round(tracking_cov, 2),
            "hygiene_level": tracking_hygiene_level,
            "hygiene_value": round(tracking_quality, 2),
            "tools": signals.get("tracking_tools", []),
            "metrics_logged": bool(signals.get("tracking_metrics_logged")),
            "artifacts_logged": bool(signals.get("tracking_artifacts_logged")),
        },
        "model_registry": {
            "present": has_registry,
            "registered_models_level": reg_level,
            "registered_models_count": registered_models,
        },
        "pipeline_automation": {
            "orchestrators": signals.get("pipeline_orchestrators", []),
            "automation_level": auto_level,
            "automation_value": round(auto_q, 2),
            "scheduling": scheduling,
            "pipelines_level": pipelines_level,
            "pipelines_total": total_pipelines,
        },
        "serving_endpoints": {
            "level": endpoints_level,
            "total": total_endpoints,
            "sagemaker": int(signals.get("sagemaker_endpoints_count", 0) or 0),
            "azureml": int(signals.get("azureml_endpoints_count", 0) or 0),
        },
        "experiments_scale": {
            "level": experiments_level,
            "count": experiments,
        },
    }


class MLOpsOrchestrator:
    """
    Runs MLOps LLM micro-agents over a repo and returns signals + scores,
    including an AIMRI-aligned summary block (subset of the 75 dimensions).
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self.agents: Dict[str, BaseMicroAgent] = {
            "mlflow": MLflowOpsAgent(model, temperature),
            "sagemaker": SageMakerOpsAgent(model, temperature),
            "azureml": AzureMLOpsAgent(model, temperature),
            "kubeflow": KubeflowOpsAgent(model, temperature),
            "tracking": ExperimentTrackingAgent(model, temperature),
            "automation": PipelineAutomationAgent(model, temperature),
        }

    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        root = Path(repo_path)
        snippets = _read_sampled_texts(repo_path)

        signals: Dict[str, Any] = {}
        order = [
            "mlflow",
            "sagemaker",
            "azureml",
            "kubeflow",
            "tracking",
            "automation",
        ]
        for key in order:
            agent = self.agents[key]
            try:
                res = agent.evaluate(snippets)
                signals.update(res)
                print(f"  ✅ {key}")
            except Exception as exc:
                print(f"  ❌ {key}: {exc}")

        scores = {
            "ai_ml_capabilities": _score_ai_ml_capabilities(signals),
            "operations_maturity": _score_operations_maturity(signals),
        }

        # AIMRI-aligned (subset of the 75 dimensions, Ops-focused)
        aimri_ops_summary = _aimri_ops_summary(signals)

        return {
            "agent": "ml_ops_monitor",
            "repo": root.name,
            "platforms": {
                "uses_mlflow": bool(signals.get("uses_mlflow")),
                "uses_sagemaker": bool(signals.get("uses_sagemaker")),
                "uses_azureml": bool(signals.get("uses_azureml")),
                "uses_kubeflow": bool(signals.get("uses_kubeflow")),
            },
            # "signals": signals,
            "scores": scores,
            "aimri_ops_summary": aimri_ops_summary,
        }
