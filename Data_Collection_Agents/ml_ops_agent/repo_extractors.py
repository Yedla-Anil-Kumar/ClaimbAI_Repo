# Data_Collection_Agents/ml_ops_agent/repo_extractors.py
from __future__ import annotations
import re
from pathlib import Path
from typing import List
from utils.file_utils import list_all_files
from .canonical import RepoEvidence

ALLOWED_EXTS = (".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".txt", ".md")

RE = {
    # MLflow
    "mlflow": re.compile(r"\bmlflow\b|\bMLproject\b|\bMLmodel\b|\bmlruns\b|MlflowClient", re.I),
    "mlflow_uri": re.compile(r"mlflow\.set_tracking_uri\(['\"]([^'\"]+)['\"]\)", re.I),
    "mlflow_registry": re.compile(r"register_model\(|model[-_ ]registry|mlflow\.models", re.I),

    # SageMaker
    "sm": re.compile(r"\bsagemaker\b|boto3\.client\(['\"]sagemaker['\"]\)", re.I),
    "sm_endpoint": re.compile(r"create_endpoint|Model\s*\.\s*deploy|sage.*endpoint", re.I),
    "sm_pipeline": re.compile(r"sagemaker\.workflow\.Pipeline|step functions", re.I),
    "sm_registry": re.compile(r"ModelPackage|ModelPackageGroup|create_model_package", re.I),

    # AzureML
    "aml": re.compile(r"\bazure\.ai\.ml\b|mlclient|azureml:", re.I),
    "aml_endpoint": re.compile(r"ManagedOnlineEndpoint|online-endpoint|endpoint:.*azureml", re.I),
    "aml_pipeline": re.compile(r"@dsl\.pipeline|pipeline:|ml\s+pipeline\s+create", re.I),
    "aml_registry": re.compile(r"\bregistry\b.*(model|environment)|register.*azureml", re.I),

    # Kubeflow
    "kfp": re.compile(r"\bkfp\b|@dsl\.pipeline|@dsl\.component|kfp\.dsl", re.I),
    "kfp_yaml": re.compile(r"apiVersion:\s*(argoproj\.io|tekton.dev)/", re.I),

    # Tracking
    "wandb": re.compile(r"\bwandb\b", re.I),
    "tb": re.compile(r"(tensorboard|SummaryWriter)", re.I),
    "comet": re.compile(r"\bcomet_ml\b", re.I),
    "neptune": re.compile(r"\bneptune\b", re.I),
    "metrics_generic": re.compile(r"log_metric|log_metrics|\bmetrics\.json\b|\bmetrics\.csv\b", re.I),
    "artifacts_generic": re.compile(r"log_artifact|artifacts?/|MLmodel|model\.pkl|model\.pt|conda\.yaml|requirements\.txt", re.I),

    # CI/CD
    "gha": re.compile(r"\.github/workflows/.*\.(yml|yaml)$", re.I),
    "gitlab": re.compile(r"\.gitlab-ci\.yml$", re.I),
    "ado": re.compile(r"azure-pipelines\.(yml|yaml)$", re.I),
    "jenkins": re.compile(r"jenkinsfile$", re.I),
    "circle": re.compile(r"\.circleci/config\.(yml|yaml)$", re.I),
    "cron": re.compile(r"cron:\s*['\"][^'\"]+['\"]|schedule_interval\s*=\s*['\"][^'\"]+['\"]|@daily|@hourly", re.I),

    # Serving
    "serve": re.compile(r"\b(kserve|inference|serve|serving|endpoint)\b", re.I),
    "fastapi": re.compile(r"\bFastAPI\(|\bfastapi\b", re.I),
    "flask": re.compile(r"\bFlask\(|\bflask\b", re.I),
}

POLICY_GATES = ["pytest", "integration", "bandit", "trivy", "bias", "data_validation"]


def _read_text(path: Path, max_bytes: int = 100_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
    except Exception:
        return ""


def scan_repo(repo_path: str) -> RepoEvidence:
    ev = RepoEvidence()
    files: List[str] = list(list_all_files(repo_path))

    for f in files:
        p = Path(f)
        name = str(p).replace("\\", "/")
        if p.suffix.lower() not in ALLOWED_EXTS and p.name.lower() != "jenkinsfile":
            continue

        text = _read_text(p)

        # MLflow
        if RE["mlflow"].search(text) or "MLproject" in name or "MLmodel" in name or "mlruns" in name:
            ev.mlflow_hits.append(name)
        for m in RE["mlflow_uri"].finditer(text):
            ev.mlflow_tracking_uri_values.append(m.group(1))
        if RE["mlflow_registry"].search(text):
            ev.mlflow_registry_hits.append(name)

        # SageMaker
        if RE["sm"].search(text):
            ev.sagemaker_hits.append(name)
        if RE["sm_endpoint"].search(text):
            ev.sagemaker_endpoint_hits.append(name)
        if RE["sm_pipeline"].search(text):
            ev.sagemaker_pipeline_hits.append(name)
        if RE["sm_registry"].search(text):
            ev.sagemaker_registry_hits.append(name)

        # AzureML
        if RE["aml"].search(text) or "azureml:" in text:
            ev.azureml_hits.append(name)
        if RE["aml_endpoint"].search(text):
            ev.azureml_endpoint_hits.append(name)
        if RE["aml_pipeline"].search(text):
            ev.azureml_pipeline_hits.append(name)
        if RE["aml_registry"].search(text):
            ev.azureml_registry_hits.append(name)

        # Kubeflow
        if RE["kfp"].search(text):
            ev.kfp_hits.append(name)
        if p.suffix.lower() in (".yml", ".yaml") and RE["kfp_yaml"].search(text):
            ev.kfp_compiled_yaml.append(name)

        # Tracking tools / signals
        if RE["wandb"].search(text): ev.tracking_tools.append("wandb")
        if RE["tb"].search(text): ev.tracking_tools.append("tensorboard")
        if RE["comet"].search(text): ev.tracking_tools.append("comet_ml")
        if RE["neptune"].search(text): ev.tracking_tools.append("neptune")
        if "mlflow" in text.lower(): ev.tracking_tools.append("mlflow")

        if RE["metrics_generic"].search(text): ev.tracking_metrics_signals.append(name)
        if RE["artifacts_generic"].search(text): ev.tracking_artifact_signals.append(name)

        # CI/CD workflows & schedules
        if RE["gha"].search(name) or RE["gitlab"].search(name) or RE["ado"].search(name) or RE["jenkins"].search(name) or RE["circle"].search(name):
            ev.cicd_workflows.append(name)
            low = text.lower()
            ev.cicd_policy_gates.update({
                "pytest": ("pytest" in low),
                "integration": ("integration" in low),
                "bandit": ("bandit" in low),
                "trivy": ("trivy" in low),
                "bias": ("bias" in low),
                "data_validation": ("great_expectations" in low or "evidently" in low or "pandera" in low or "data_validation" in low),
            })
            m = RE["cron"].search(text)
            if m:
                ev.cicd_schedules.append(m.group(0))

        # Serving & manifests
        if RE["serve"].search(text) or RE["fastapi"].search(text) or RE["flask"].search(text):
            ev.serving_signals.append(name)

        if "endpoint" in name.lower(): ev.endpoint_manifests.append(name)
        if "pipeline" in name.lower() or "/pipelines/" in name.lower(): ev.pipeline_manifests.append(name)

    ev.tracking_tools = sorted(set(ev.tracking_tools))
    return ev
