# Data_Collection_Agents/ml_ops_agent/metrics_engine.py
from __future__ import annotations
from typing import Dict
from .canonical import RepoEvidence

def _bool(x) -> bool: return bool(x)

def mlflow_proxy_metrics(ev: RepoEvidence) -> Dict:
    return {
        "uses_mlflow": _bool(ev.mlflow_hits),
        "tracking_endpoints": list(sorted(set(ev.mlflow_tracking_uri_values)))[:3],
        "experiments_count": max(1, len(ev.mlflow_hits)//10) if ev.mlflow_hits else 0,  # conservative proxy
        "registered_models_count": len(ev.mlflow_registry_hits),
    }

def sagemaker_proxy_metrics(ev: RepoEvidence) -> Dict:
    return {
        "uses_sagemaker": _bool(ev.sagemaker_hits),
        "training_jobs_count": max(0, len(ev.sagemaker_hits)//15),
        "endpoints_count": len(ev.sagemaker_endpoint_hits),
        "pipelines_count": len(ev.sagemaker_pipeline_hits),
        "registry_usage": _bool(ev.sagemaker_registry_hits),
    }

def azureml_proxy_metrics(ev: RepoEvidence) -> Dict:
    return {
        "uses_azureml": _bool(ev.azureml_hits),
        "jobs_count": max(0, len(ev.azureml_hits)//15),
        "endpoints_count": len(ev.azureml_endpoint_hits),
        "pipelines_count": len(ev.azureml_pipeline_hits),
        "registry_usage": _bool(ev.azureml_registry_hits),
    }

def kubeflow_proxy_metrics(ev: RepoEvidence) -> Dict:
    return {
        "uses_kubeflow": _bool(ev.kfp_hits),
        "pipelines_count": max(len(ev.kfp_hits)//2, len(ev.kfp_compiled_yaml)),
        "components_count": max(0, len(ev.kfp_hits)),
        "manifests_present": _bool(ev.kfp_compiled_yaml),
    }

def tracking_proxy_metrics(ev: RepoEvidence) -> Dict:
    metrics_logged = bool(ev.tracking_metrics_signals)
    artifacts_logged = bool(ev.tracking_artifact_signals)
    runs_quality = 0.0
    if metrics_logged and artifacts_logged:
        runs_quality = 0.7
    if "mlflow" in ev.tracking_tools and ("wandb" in ev.tracking_tools or "tensorboard" in ev.tracking_tools):
        runs_quality = max(runs_quality, 0.85)
    coverage = 0.0
    if metrics_logged: coverage += 0.4
    if artifacts_logged: coverage += 0.4
    if ev.tracking_tools: coverage += 0.2
    return {
        "tools": [{"name": n, "usage": "moderate"} for n in ev.tracking_tools],
        "metrics_logged": metrics_logged,
        "artifacts_logged": artifacts_logged,
        "runs_structure_quality": round(min(1.0, runs_quality), 2),
        "coverage": round(min(1.0, coverage), 2),
    }

def automation_proxy_metrics(ev: RepoEvidence) -> Dict:
    orchestrators = []
    if any("airflow" in p for p in ev.pipeline_manifests): orchestrators.append("airflow")
    if ev.kfp_hits: orchestrators.append("kfp")
    if ev.azureml_pipeline_hits: orchestrators.append("azureml_pipelines")
    if ev.sagemaker_pipeline_hits: orchestrators.append("sagemaker_pipelines")
    if ev.cicd_workflows:
        orchestrators.append("gha" if any(".github/workflows/" in x for x in ev.cicd_workflows) else "gitlab_ci")

    scheduling_present = bool(ev.cicd_schedules)
    pipelines_defined = len(ev.pipeline_manifests)

    automation_quality = 0.0
    if orchestrators: automation_quality += 0.4
    if scheduling_present: automation_quality += 0.3
    if any(ev.cicd_policy_gates.get(k, False) for k in ("pytest","bandit","trivy","bias","data_validation")):
        automation_quality += 0.2
    if pipelines_defined >= 3: automation_quality += 0.1

    return {
        "orchestrators": sorted(set(orchestrators)),
        "pipelines_defined": pipelines_defined,
        "scheduling_present": scheduling_present,
        "automation_quality": round(min(1.0, automation_quality), 2),
    }
