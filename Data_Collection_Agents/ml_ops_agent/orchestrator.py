from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple
from Data_Collection_Agents.base_agent import BaseMicroAgent
from Data_Collection_Agents.ml_ops_agent.platform_agents import MLflowOpsAgent, SageMakerOpsAgent, AzureMLOpsAgent, KubeflowOpsAgent
from Data_Collection_Agents.ml_ops_agent.pipeline_agents import ExperimentTrackingAgent, PipelineAutomationAgent
from utils.file_utils import list_source_files, list_all_files

MAX_FILES_TOTAL = 60
MAX_BYTES_PER_FILE = 8000
CAP_CICD = 10
CAP_PIPELINES = 12
CAP_INFRA = 10
CAP_DEPLOY_SERVE = 10
CAP_TRACKING = 6
ALLOWED_EXTS = (".py", ".yaml", ".yml", ".json", ".toml")

def _norm(s: str) -> str: return s.replace("\\", "/").lower()

def _pick(files: List[str], pred, cap: int, seen: set) -> List[Path]:
    out: List[Path] = []
    for f in files:
        if len(out) >= cap: break
        if f in seen: continue
        p = Path(f)
        if p.suffix.lower() not in ALLOWED_EXTS and p.name != "Jenkinsfile": continue
        if pred(_norm(str(p))):
            out.append(p); seen.add(f)
    return out

def _read_sampled_texts(repo_path: str, max_files: int = MAX_FILES_TOTAL, max_bytes: int = MAX_BYTES_PER_FILE) -> List[str]:
    files = list(list_all_files(repo_path))
    seen: set = set()
    selected: List[Path] = []

    # 1) CI/CD
    selected += _pick(files, lambda s: (s.startswith(".github/workflows/") or s.endswith("/.gitlab-ci.yml")
                                        or s.endswith("azure-pipelines.yml") or s.endswith("azure-pipelines.yaml")
                                        or s.endswith("/.circleci/config.yml") or s.endswith("/.circleci/config.yaml")
                                        or s.endswith("/bitbucket-pipelines.yml") or s.endswith("/jenkinsfile")), CAP_CICD, seen)
    # 2) Pipelines/Orchestrators
    selected += _pick(files, lambda s: ("/airflow/" in s or "/dags/" in s or "/prefect/" in s or "/flows/" in s
                                        or "/dagster/" in s or "/kfp/" in s or "kubeflow" in s
                                        or "/pipelines/" in s or "/pipeline/" in s or "pipeline" in Path(s).name
                                        or "/components/" in s), CAP_PIPELINES, seen)
    # 3) IaC/Manifests
    selected += _pick(files, lambda s: (s.endswith(".tf") or "/infra/" in s or "/manifests/" in s
                                        or "/k8s/" in s or "/kubernetes/" in s
                                        or "kustomization.yaml" in s or "kustomization.yml" in s
                                        or "chart.yaml" in s or "chart.yml" in s or "/charts/" in s), CAP_INFRA, seen)
    # 4) Deploy/Serve/Endpoints
    selected += _pick(files, lambda s: ("/deploy/" in s or "/deployment/" in s or "endpoint" in s
                                        or "serve" in s or "serving" in s or "inference" in s
                                        or Path(s).name in {"app.py", "main.py"}), CAP_DEPLOY_SERVE, seen)
    # 5) Tracking evidence
    selected += _pick(files, lambda s: ("mlruns" in s or "mlflow" in s or "/wandb" in s
                                        or "tensorboard" in s or "events.out.tfevents" in s
                                        or "comet" in s or "neptune" in s or "mlproject" in s), CAP_TRACKING, seen)
    # 6) Fill remainder by keyword+size
    rest: List[Path] = []
    for f in files:
        if f in seen: continue
        p = Path(f)
        if p.suffix.lower() in ALLOWED_EXTS: rest.append(p)

    def rest_key(p: Path) -> Tuple[int, int]:
        name = p.name.lower()
        hint = any(k in name for k in ("model", "train", "pipeline", "main", "serve", "registry"))
        try: sz = p.stat().st_size
        except Exception: sz = 0
        return (0 if hint else 1, -sz)

    rest.sort(key=rest_key)
    for p in rest:
        if len(selected) >= max_files: break
        selected.append(p)

    if not selected:
        for p in list(list_source_files(repo_path))[:max_files]:
            selected.append(p)

    texts: List[str] = []
    for p in selected[:max_files]:
        try:
            texts.append(p.read_text(encoding="utf-8", errors="ignore")[:max_bytes])
        except Exception:
            continue
    return texts


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _score_ai_ml_capabilities(signals: Dict[str, Any]) -> float:
    base_platforms = [
        bool(signals.get("uses_mlflow")),
        bool(signals.get("uses_sagemaker")),
        bool(signals.get("uses_azureml")),
        bool(signals.get("uses_kubeflow")),
    ]
    orch = [str(x).lower() for x in signals.get("pipeline_orchestrators", [])]
    uses_flyte = any("flyte" in x for x in orch)
    platform_score = (sum(base_platforms) + (1 if uses_flyte else 0)) / 5.0

    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))

    depth_terms = [
        signals.get("mlflow_experiments_count", 0),
        signals.get("mlflow_registered_models_count", 0),
        signals.get("sagemaker_endpoints_count", 0),
        signals.get("azureml_endpoints_count", 0),
        signals.get("kubeflow_pipelines_count", 0),
        signals.get("pipeline_pipelines_defined", 0),  # generic pipeline depth
    ]
    depth = 1.0 - math.exp(-0.25 * sum(max(0, int(v)) for v in depth_terms))

    raw = (
        0.5 * platform_score
        + 0.3 * (0.5 * tracking_cov + 0.5 * tracking_quality)
        + 0.2 * depth
    )
    return round(5.0 * _clamp01(raw), 2)

def _score_operations_maturity(signals: Dict[str, Any]) -> float:
    automation_quality = _clamp01(signals.get("pipeline_automation_quality", 0.0))
    scheduling = 1.0 if signals.get("pipeline_scheduling_present") else 0.0
    registry = any([signals.get("sagemaker_registry_usage"), signals.get("azureml_registry_usage"),
                    (signals.get("mlflow_registered_models_count", 0) or 0) > 0])
    ops_quality = sum(_clamp01(signals.get(k, 0.0)) for k in ("mlflow_ops_quality","sagemaker_ops_quality","azureml_ops_quality","kubeflow_ops_quality")) / 4.0
    pipelines_defined = _clamp01(min(1.0, (signals.get("pipeline_pipelines_defined", 0) or 0) / 3.0))
    raw = 0.35 * automation_quality + 0.2 * scheduling + 0.25 * (1.0 if registry else 0.0) + 0.15 * ops_quality + 0.05 * pipelines_defined
    return round(5.0 * _clamp01(raw), 2)

def _level_from_value(value: float, bands: Tuple[float, float, float]) -> int:
    if value <= bands[0]:
        return 0
    if value <= bands[1]:
        return 1
    if value <= bands[2]:
        return 2
    return 3


def _aimri_ops_summary(signals: Dict[str, Any]) -> Dict[str, Any]:
    platforms_used = sum(
        bool(x)
        for x in [
            signals.get("uses_mlflow"),
            signals.get("uses_sagemaker"),
            signals.get("uses_azureml"),
            signals.get("uses_kubeflow"),
        ]
    )
    if any("flyte" in str(o).lower() for o in signals.get("pipeline_orchestrators", [])):
        platforms_used += 1
    platform_norm = platforms_used / 5.0
    platform_level = _level_from_value(platform_norm, (0.25, 0.5, 0.75))

    tracking_cov = _clamp01(signals.get("tracking_coverage", 0.0))
    tracking_quality = _clamp01(signals.get("tracking_runs_quality", 0.0))
    tracking_cov_level = _level_from_value(tracking_cov, (0.25, 0.5, 0.75))
    tracking_hygiene_level = _level_from_value(tracking_quality, (0.25, 0.5, 0.75))

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

    total_endpoints = int(signals.get("sagemaker_endpoints_count", 0) or 0) + int(
        signals.get("azureml_endpoints_count", 0) or 0
    )
    endpoints_norm = 1.0 - math.exp(-0.35 * max(0, total_endpoints))
    endpoints_level = _level_from_value(endpoints_norm, (0.15, 0.4, 0.7))

    experiments = int(signals.get("mlflow_experiments_count", 0) or 0)
    experiments_norm = 1.0 - math.exp(-0.25 * max(0, experiments))
    experiments_level = _level_from_value(experiments_norm, (0.2, 0.5, 0.8))

    return {
        "platform_surface_area": {
            "level": platform_level,
            "value": platforms_used,
            "desc": "MLflow/SageMaker/AzureML/Kubeflow/Flyte"
        },
        "experiment_tracking": {
            "coverage_level": tracking_cov_level, "coverage_value": round(tracking_cov, 2),
            "hygiene_level": tracking_hygiene_level, "hygiene_value": round(tracking_quality, 2),
            "tools": signals.get("tracking_tools", []),
            "metrics_logged": bool(signals.get("tracking_metrics_logged")),
            "artifacts_logged": bool(signals.get("tracking_artifacts_logged")),
        },
        "model_registry": {"present": has_registry, "registered_models_level": reg_level, "registered_models_count": registered_models},
        "pipeline_automation": {
            "orchestrators": signals.get("pipeline_orchestrators", []),
            "automation_level": auto_level, "automation_value": round(auto_q, 2),
            "scheduling": scheduling, "pipelines_level": pipelines_level, "pipelines_total": total_pipelines,
        },
        "serving_endpoints": {"level": endpoints_level, "total": total_endpoints,
                              "sagemaker": int(signals.get("sagemaker_endpoints_count", 0) or 0),
                              "azureml": int(signals.get("azureml_endpoints_count", 0) or 0)},
        "experiments_scale": {"level": experiments_level, "count": experiments},
    }

class MLOpsOrchestrator:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
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
        for key in ("mlflow", "sagemaker", "azureml", "kubeflow", "tracking", "automation"):
            try:
                signals.update(self.agents[key].evaluate(snippets))
                # print(f"  ✅ {key}")
            except Exception as exc:
                print(f"  ❌ {key}: {exc}")

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
        }
