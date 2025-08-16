# Data_Collection_Agents/ml_ops_agent/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ----------------------
# Evidence (repo-only)
# ----------------------
@dataclass
class RepoEvidence:
    # MLflow
    mlflow_hits: List[str] = field(default_factory=list)
    mlflow_registry_hits: List[str] = field(default_factory=list)
    mlflow_tracking_uri_values: List[str] = field(default_factory=list)

    # SageMaker
    sagemaker_hits: List[str] = field(default_factory=list)
    sagemaker_endpoint_hits: List[str] = field(default_factory=list)
    sagemaker_pipeline_hits: List[str] = field(default_factory=list)
    sagemaker_registry_hits: List[str] = field(default_factory=list)

    # AzureML
    azureml_hits: List[str] = field(default_factory=list)
    azureml_endpoint_hits: List[str] = field(default_factory=list)
    azureml_pipeline_hits: List[str] = field(default_factory=list)
    azureml_registry_hits: List[str] = field(default_factory=list)

    # Kubeflow
    kfp_hits: List[str] = field(default_factory=list)
    kfp_compiled_yaml: List[str] = field(default_factory=list)

    # Tracking
    tracking_tools: List[str] = field(default_factory=list)  # ["mlflow","wandb","tensorboard","comet_ml","neptune","custom", ...]
    tracking_metrics_signals: List[str] = field(default_factory=list)
    tracking_artifact_signals: List[str] = field(default_factory=list)

    # CI/CD & scheduling
    cicd_workflows: List[str] = field(default_factory=list)
    cicd_schedules: List[str] = field(default_factory=list)
    cicd_policy_gates: Dict[str, bool] = field(default_factory=dict)  # pytest/bandit/trivy/bias/data_validation

    # Serving & manifests (coarse)
    serving_signals: List[str] = field(default_factory=list)
    endpoint_manifests: List[str] = field(default_factory=list)
    pipeline_manifests: List[str] = field(default_factory=list)

    repo_only_mode: bool = True


# ----------------------
# Built-in rubric specs (CSV-inspired, no CSV I/O)
# ----------------------
@dataclass
class MetricSpec:
    metric_id: str              # e.g., "mlflow.ops_quality_band"
    stem: str                   # few_shot file stem: mlflow|sagemaker|azureml|kubeflow|automation|tracking
    group: str                  # for organization/reporting
    methodology: str            # short human explanation (optional, used in prompt context)
    rubric: Dict[str, str]      # band "5".."1" textual criteria
    return_shape_hint: str      # schema reminder (fed into prompt as guardrail)


BUILTIN_METRIC_SPECS: List[MetricSpec] = [
    MetricSpec(
        metric_id="mlflow.ops_quality_band",
        stem="mlflow",
        group="platform",
        methodology="Grade MLflow operational maturity from repo-only evidence (tracking, registry, CI/CD, serving).",
        rubric={
            "5": "Remote tracking + consistent metrics/artifacts + registry promotion + CI/CD + serving/infra signals.",
            "4": "Remote tracking + artifacts + (registry or CI/CD).",
            "3": "Tracking present (local or remote) but limited artifacts or ops integration.",
            "2": "Minimal/partial evidence (ad hoc references).",
            "1": "No meaningful evidence of MLflow usage.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
    MetricSpec(
        metric_id="sagemaker.ops_quality_band",
        stem="sagemaker",
        group="platform",
        methodology="Grade SageMaker usage (jobs, endpoints, pipelines, registry) from repo-only signals.",
        rubric={
            "5": "Endpoints + pipelines + registry present; CI/CD or IaC shows promotion/deploy.",
            "4": "Endpoints + pipelines present; registry optional.",
            "3": "Some jobs or partial pipelines; no endpoints.",
            "2": "Weak, scattered references only.",
            "1": "No evidence.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
    MetricSpec(
        metric_id="azureml.ops_quality_band",
        stem="azureml",
        group="platform",
        methodology="Grade Azure ML maturity (jobs, pipelines, endpoints, registry) using SDK v2/CLI YAML cues.",
        rubric={
            "5": "Managed endpoints + pipelines + registry present; CI/CD shows automation.",
            "4": "Endpoints + pipelines present; registry optional.",
            "3": "Jobs or partial pipelines only.",
            "2": "Weak, scattered references.",
            "1": "No evidence.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
    MetricSpec(
        metric_id="kubeflow.ops_quality_band",
        stem="kubeflow",
        group="platform",
        methodology="Grade KFP maturity (DSL components/pipelines, compiled manifests, scheduling).",
        rubric={
            "5": "Pipelines + compiled manifests + scheduling/automation.",
            "4": "Pipelines + compiled manifests.",
            "3": "Pipelines only (DSL).",
            "2": "Minimal references.",
            "1": "No evidence.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
    MetricSpec(
        metric_id="cicd.policy_gates",
        stem="automation",
        group="cicd",
        methodology="Grade CI/CD policy gates strength (tests, security scans, data validation, bias checks).",
        rubric={
            "5": "Multiple gates (tests + security + data validation/bias) enforced and scheduled.",
            "4": "Tests plus at least one additional gate; some scheduling.",
            "3": "Basic tests only or ad-hoc gates; little scheduling.",
            "2": "Minimal CI/CD without gates.",
            "1": "No CI/CD evidence.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
    MetricSpec(
        metric_id="tracking.maturity_band",
        stem="tracking",
        group="tracking",
        methodology="Grade experiment tracking maturity (tools, metrics, artifacts, coverage).",
        rubric={
            "5": "Rich metrics + artifacts + structured runs; references from CI/nb; multi-tool okay.",
            "4": "Consistent metrics + artifacts; partial coverage.",
            "3": "Metrics yes, artifacts spotty or vice versa.",
            "2": "Sporadic/basic logging.",
            "1": "No evidence.",
        },
        return_shape_hint='{"band":1..5,"rationale":str,"flags":[]}',
    ),
]


def get_builtin_metric_spec(metric_id: str) -> Optional[MetricSpec]:
    for s in BUILTIN_METRIC_SPECS:
        if s.metric_id == metric_id:
            return s
    return None
