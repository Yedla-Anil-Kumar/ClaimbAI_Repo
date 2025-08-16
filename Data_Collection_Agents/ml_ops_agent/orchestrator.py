# Data_Collection_Agents/ml_ops_agent/orchestrator.py
from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict

from .repo_extractors import scan_repo
from .metrics_engine import (
    mlflow_proxy_metrics, sagemaker_proxy_metrics, azureml_proxy_metrics, kubeflow_proxy_metrics,
    tracking_proxy_metrics, automation_proxy_metrics
)
from .llm_graders import LLMGrader
from .canonical import get_builtin_metric_spec

def _clamp01(x: float) -> float: return max(0.0, min(1.0, float(x)))

def _score_ai_ml_capabilities(signals: Dict[str, Any]) -> float:
    platforms = [
        bool(signals.get("uses_mlflow")),
        bool(signals.get("uses_sagemaker")),
        bool(signals.get("uses_azureml")),
        bool(signals.get("uses_kubeflow")),
    ]
    platform_score = sum(platforms) / 4.0
    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))
    depth_terms = [
        signals.get("mlflow_experiments_count", 0),
        signals.get("mlflow_registered_models_count", 0),
        signals.get("sagemaker_endpoints_count", 0),
        signals.get("azureml_endpoints_count", 0),
        signals.get("kubeflow_pipelines_count", 0),
        signals.get("pipeline_pipelines_defined", 0),
    ]
    depth = 1.0 - math.exp(-0.25 * sum(max(0, int(v)) for v in depth_terms))
    raw = 0.5*platform_score + 0.3*(0.5*tracking_cov + 0.5*tracking_quality) + 0.2*depth
    return round(5.0 * _clamp01(raw), 2)

def _score_operations_maturity(signals: Dict[str, Any]) -> float:
    automation_quality = _clamp01(signals.get("pipeline_automation_quality", 0.0))
    scheduling = 1.0 if signals.get("pipeline_scheduling_present") else 0.0
    registry = any([
        signals.get("sagemaker_registry_usage"),
        signals.get("azureml_registry_usage"),
        (signals.get("mlflow_registered_models_count", 0) or 0) > 0
    ])
    ops_quality = sum(_clamp01(signals.get(k, 0.0)) for k in (
        "mlflow_ops_quality", "sagemaker_ops_quality", "azureml_ops_quality", "kubeflow_ops_quality"
    )) / 4.0
    pipelines_defined = _clamp01(min(1.0, (signals.get("pipeline_pipelines_defined", 0) or 0) / 3.0))
    raw = 0.35*automation_quality + 0.2*scheduling + 0.25*(1.0 if registry else 0.0) + 0.15*ops_quality + 0.05*pipelines_defined
    return round(5.0 * _clamp01(raw), 2)

def _lvl(value: float, bands=(0.25, 0.5, 0.75)) -> int:
    if value <= bands[0]: return 0
    if value <= bands[1]: return 1
    if value <= bands[2]: return 2
    return 3

def _aimri_ops_summary(signals: Dict[str, Any]) -> Dict[str, Any]:
    platforms_used = sum(bool(x) for x in [
        signals.get("uses_mlflow"),
        signals.get("uses_sagemaker"),
        signals.get("uses_azureml"),
        signals.get("uses_kubeflow"),
    ])
    platform_norm = platforms_used / 4.0
    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))
    registered_models = int(signals.get("mlflow_registered_models_count", 0) or 0)
    has_registry = any([signals.get("sagemaker_registry_usage"),
                        signals.get("azureml_registry_usage"),
                        registered_models > 0])
    reg_scale = 1.0 - math.exp(-0.3 * max(0, registered_models))
    total_pipelines = int(signals.get("pipeline_pipelines_defined", 0) or 0) \
                    + int(signals.get("sagemaker_pipelines_count", 0) or 0) \
                    + int(signals.get("azureml_pipelines_count", 0) or 0) \
                    + int(signals.get("kubeflow_pipelines_count", 0) or 0)
    pipelines_norm = 1.0 - math.exp(-0.25 * max(0, total_pipelines))
    total_endpoints = int(signals.get("sagemaker_endpoints_count", 0) or 0) \
                    + int(signals.get("azureml_endpoints_count", 0) or 0)
    endpoints_norm = 1.0 - math.exp(-0.35 * max(0, total_endpoints))

    return {
        "platform_surface_area": {"level": _lvl(platform_norm), "value": platforms_used, "desc": "Distinct MLOps platforms detected (0–4)."},
        "experiment_tracking": {
            "coverage_level": _lvl(tracking_cov), "coverage_value": round(tracking_cov,2),
            "hygiene_level": _lvl(tracking_quality), "hygiene_value": round(tracking_quality,2),
            "tools": signals.get("tracking_tools", []),
            "metrics_logged": bool(signals.get("tracking_metrics_logged")),
            "artifacts_logged": bool(signals.get("tracking_artifacts_logged")),
        },
        "model_registry": {"present": has_registry, "registered_models_level": _lvl(1.0 - math.exp(-0.3 * max(0, registered_models)), (0.1,0.4,0.7)), "registered_models_count": registered_models},
        "pipeline_automation": {
            "orchestrators": signals.get("pipeline_orchestrators", []),
            "automation_level": _lvl(_clamp01(signals.get("pipeline_automation_quality",0.0))),
            "automation_value": round(_clamp01(signals.get("pipeline_automation_quality",0.0)),2),
            "scheduling": bool(signals.get("pipeline_scheduling_present")),
            "pipelines_level": _lvl(pipelines_norm),
            "pipelines_total": total_pipelines,
        },
        "serving_endpoints": {
            "level": _lvl(endpoints_norm,(0.15,0.4,0.7)),
            "total": total_endpoints,
            "sagemaker": int(signals.get("sagemaker_endpoints_count",0) or 0),
            "azureml": int(signals.get("azureml_endpoints_count",0) or 0)
        },
        "experiments_scale": {
            "level": _lvl(1.0 - math.exp(-0.25 * max(0, int(signals.get("mlflow_experiments_count",0) or 0)))),
            "count": int(signals.get("mlflow_experiments_count",0) or 0),
        },
    }


class MLOpsOrchestrator:
    """
    Repo-only pipeline (no CSV I/O):
      Extract → Proxy metrics → One-shot LLM grading (with built-in rubrics) → Scores
    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 512):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.grader = LLMGrader(model=model, temperature=temperature, max_tokens=max_tokens)

    def _grade_with_spec(self, spec_id: str, payload_metrics: Dict[str, Any], stem_override: str | None = None) -> Dict[str, Any]:
        spec = get_builtin_metric_spec(spec_id)
        if not spec:
            return {"band": 3, "rationale": f"Spec {spec_id} not found.", "flags": ["missing_spec"]}

        payload = {
            "metric_id": spec.metric_id,
            "methodology": spec.methodology,
            "return_shape_hint": spec.return_shape_hint,
            "metrics": payload_metrics,
            "rubric": spec.rubric,
        }
        return self.grader.grade(stem_override or spec.stem, payload, max_tokens=self.max_tokens)

    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        root = Path(repo_path)

        # 1) Extract raw signals
        ev = scan_repo(repo_path)

        # 2) Deterministic proxies
        mlflow_m = mlflow_proxy_metrics(ev)
        sm_m     = sagemaker_proxy_metrics(ev)
        aml_m    = azureml_proxy_metrics(ev)
        kfp_m    = kubeflow_proxy_metrics(ev)
        trk_m    = tracking_proxy_metrics(ev)
        auto_m   = automation_proxy_metrics(ev)

        # 3) One-shot grading (built-in rubrics; no CSV)
        mlflow_grade = self._grade_with_spec(
            "mlflow.ops_quality_band",
            {**mlflow_m,
             "tools": [t["name"] for t in trk_m["tools"]],
             "registry_signals": mlflow_m["registered_models_count"] > 0,
             "ci_cd": bool(auto_m["orchestrators"]),
             "serving_signals": bool(ev.serving_signals)}
        )
        sm_grade = self._grade_with_spec("sagemaker.ops_quality_band", sm_m)
        aml_grade = self._grade_with_spec("azureml.ops_quality_band", aml_m)
        kfp_grade = self._grade_with_spec("kubeflow.ops_quality_band", kfp_m)
        cicd_grade = self._grade_with_spec(
            "cicd.policy_gates",
            {"workflows": auto_m["orchestrators"], "scheduling": auto_m["scheduling_present"], "policy_gates": ev.cicd_policy_gates}
        )
        tracking_grade = self._grade_with_spec(
            "tracking.maturity_band",
            trk_m | {"tools_flat": [t["name"] for t in trk_m["tools"]]}
        )

        # 4) Merge signals → scoring
        signals: Dict[str, Any] = {
            # Platforms
            "uses_mlflow": mlflow_m["uses_mlflow"],
            "uses_sagemaker": sm_m["uses_sagemaker"],
            "uses_azureml": aml_m["uses_azureml"],
            "uses_kubeflow": kfp_m["uses_kubeflow"],

            # MLflow specifics
            "mlflow_tracking_endpoints": mlflow_m["tracking_endpoints"],
            "mlflow_experiments_count": mlflow_m["experiments_count"],
            "mlflow_registered_models_count": mlflow_m["registered_models_count"],
            "mlflow_ops_quality": mlflow_grade["band"] / 5.0,

            # SageMaker specifics
            "sagemaker_training_jobs_count": sm_m["training_jobs_count"],
            "sagemaker_endpoints_count": sm_m["endpoints_count"],
            "sagemaker_pipelines_count": sm_m["pipelines_count"],
            "sagemaker_registry_usage": sm_m["registry_usage"],
            "sagemaker_ops_quality": sm_grade["band"] / 5.0,

            # AzureML specifics
            "azureml_jobs_count": aml_m["jobs_count"],
            "azureml_endpoints_count": aml_m["endpoints_count"],
            "azureml_pipelines_count": aml_m["pipelines_count"],
            "azureml_registry_usage": aml_m["registry_usage"],
            "azureml_ops_quality": aml_grade["band"] / 5.0,

            # Kubeflow specifics
            "kubeflow_pipelines_count": kfp_m["pipelines_count"],
            "kubeflow_components_count": kfp_m["components_count"],
            "kubeflow_manifests_present": kfp_m["manifests_present"],
            "kubeflow_ops_quality": kfp_grade["band"] / 5.0,

            # Tracking (deterministic proxies also surfaced)
            "tracking_tools": trk_m["tools"],
            "tracking_metrics_logged": trk_m["metrics_logged"],
            "tracking_artifacts_logged": trk_m["artifacts_logged"],
            "tracking_runs_quality": trk_m["runs_structure_quality"],
            "tracking_coverage": trk_m["coverage"],

            # Automation
            "pipeline_orchestrators": auto_m["orchestrators"],
            "pipeline_pipelines_defined": auto_m["pipelines_defined"],
            "pipeline_scheduling_present": auto_m["scheduling_present"],
            "pipeline_automation_quality": auto_m["automation_quality"],
        }

        scores = {
            "ai_ml_capabilities": _score_ai_ml_capabilities(signals),
            "operations_maturity": _score_operations_maturity(signals),
        }

        return {
            "agent": "ml_ops_monitor",
            "repo": root.name,
            "platforms": {
                "uses_mlflow": bool(signals.get("uses_mlflow")),
                "uses_sagemaker": bool(signals.get("uses_sagemaker")),
                "uses_azureml": bool(signals.get("uses_azureml")),
                "uses_kubeflow": bool(signals.get("uses_kubeflow")),
            },
            "scores": scores,
            "aimri_ops_summary": _aimri_ops_summary(signals),
            "grading_notes": {
                "mlflow": mlflow_grade,
                "sagemaker": sm_grade,
                "azureml": aml_grade,
                "kubeflow": kfp_grade,
                "cicd_policy_gates": cicd_grade,
                "tracking_maturity": tracking_grade,
            },
            "mode": "repo_only_builtins",
        }
