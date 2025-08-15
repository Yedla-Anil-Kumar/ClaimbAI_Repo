from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from Data_Collection_Agents.base_agent import BaseMicroAgent
import json

# ---- shared few-shot loader ----
def _load_few_shot(name: str) -> Tuple[str, str]:
    root = Path(__file__).resolve().parent / "one_shot"
    txt = (root / f"{name}_example.txt").read_text(encoding="utf-8") if (root / f"{name}_example.txt").exists() else ""
    lab = ""
    jp = root / f"{name}_example.json"
    if jp.exists():
        try:
            lab = json.dumps(json.loads(jp.read_text(encoding="utf-8")), indent=2)
        except Exception:
            lab = ""
    return txt, lab


class MLflowOpsAgent(BaseMicroAgent):
    """One-shot MLflow detector with equivalence rules."""

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        ex_txt, ex_json = _load_few_shot("mlflow")
        system = (
            "You are an expert MLOps analyst. Infer MLflow usage from code/config/CI/IaC. "
            "Be conservative; do not claim resources without evidence. Reply STRICT JSON."
        )
        eep = """
            Judge MLflow by FUNCTIONAL EQUIVALENCE (SDK, CLI, YAML, MlflowClient, autolog, artifacts in mlruns/).
            Registry evidence includes register_model(), Model Registry mentions, MLmodel flavors, CI promotion.
            Integrations include Airflow/KFP/GitHub Actions/GitLab CI/CDK/Terraform touching MLflow.
            Scoring ops_quality: 0.9–1.0 rich remote tracking + registry + CI/CD + serving; 0.6–0.8 solid tracking + some ops;
            0.3–0.5 basic/local tracking; 0.0–0.2 minimal evidence.
        """
        schema = (
            'Return JSON: {"uses_mlflow": bool, "tracking_endpoints": [string], "experiments_count": int, '
            '"registered_models_count": int, "deployments":[{"type":"model-serve|docker|k8s|other","details":string}], '
            '"integration_points":[string], "ops_quality": float}'
        )
        few_shot = ""
        if ex_txt and ex_json:
            few_shot = f"----- EXAMPLE SNIPPET -----\n{ex_txt}\n----- EXAMPLE LABELS -----\n{ex_json}\n\n"
        prompt = (
            f"{eep}\n{schema}\n{few_shot}"
            "Evaluate these repo snippets as one corpus (accept equivalent patterns; be conservative):\n\n"
            + "\n".join(f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets))
        )
        data = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "uses_mlflow": bool(data.get("uses_mlflow", False)),
            "mlflow_tracking_endpoints": data.get("tracking_endpoints", []) or [],
            "mlflow_experiments_count": int(data.get("experiments_count", 0) or 0),
            "mlflow_registered_models_count": int(data.get("registered_models_count", 0) or 0),
            "mlflow_deployments": data.get("deployments", []) or [],
            "mlflow_integration_points": data.get("integration_points", []) or [],
            "mlflow_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class SageMakerOpsAgent(BaseMicroAgent):
    """One-shot SageMaker detector with equivalence rules."""

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        ex_txt, ex_json = _load_few_shot("sagemaker")
        system = (
            "You are an expert in AWS SageMaker. Detect jobs/endpoints/pipelines/registry from SDK, boto3, CLI, IaC. "
            "Be conservative. STRICT JSON."
        )
        eep = """
            Training: Estimator.fit/Processor.run, boto3 create_training_job, Step Functions.
            Endpoints: Model.deploy/boto3 create_endpoint, endpoint configs in IaC.
            Pipelines: sagemaker.workflow.Pipeline, Step Functions ML, CodePipeline.
            Registry: ModelPackage(Group), CI promotion.
        """
        schema = (
            'Return JSON: {"uses_sagemaker": bool, "training_jobs_count": int, "endpoints_count": int, '
            '"pipelines_count": int, "registry_usage": bool, "ops_quality": float}'
        )
        few_shot = f"----- EXAMPLE SNIPPET -----\n{ex_txt}\n----- EXAMPLE LABELS -----\n{ex_json}\n\n" if ex_txt and ex_json else ""
        prompt = f"{eep}\n{schema}\n{few_shot}Evaluate as one corpus:\n\n" + "\n".join(
            f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets)
        )
        data = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "uses_sagemaker": bool(data.get("uses_sagemaker", False)),
            "sagemaker_training_jobs_count": int(data.get("training_jobs_count", 0) or 0),
            "sagemaker_endpoints_count": int(data.get("endpoints_count", 0) or 0),
            "sagemaker_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "sagemaker_registry_usage": bool(data.get("registry_usage", False)),
            "sagemaker_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class AzureMLOpsAgent(BaseMicroAgent):
    """One-shot AzureML detector with equivalence rules."""

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        ex_txt, ex_json = _load_few_shot("azureml")
        system = (
            "You are an expert in Azure ML. Detect jobs/pipelines/managed endpoints/registry using SDK v2 or CLI v2 YAML. "
            "Be conservative. STRICT JSON."
        )
        eep = """
            Jobs: MLClient.jobs.*, azure.ai.ml.command, 'ml job create -f'.
            Pipelines: @dsl.pipeline or pipeline YAML, components YAML.
            Endpoints: ManagedOnlineEndpoint/Deployment (Python/YAML).
            Registry: model/environment reuse or explicit registration.
        """
        schema = (
            'Return JSON: {"uses_azureml": bool, "jobs_count": int, "endpoints_count": int, '
            '"pipelines_count": int, "registry_usage": bool, "ops_quality": float}'
        )
        few_shot = f"----- EXAMPLE SNIPPET -----\n{ex_txt}\n----- EXAMPLE LABELS -----\n{ex_json}\n\n" if ex_txt and ex_json else ""
        prompt = f"{eep}\n{schema}\n{few_shot}Evaluate as one corpus:\n\n" + "\n".join(
            f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets)
        )
        data = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "uses_azureml": bool(data.get("uses_azureml", False)),
            "azureml_jobs_count": int(data.get("jobs_count", 0) or 0),
            "azureml_endpoints_count": int(data.get("endpoints_count", 0) or 0),
            "azureml_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "azureml_registry_usage": bool(data.get("registry_usage", False)),
            "azureml_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class KubeflowOpsAgent(BaseMicroAgent):
    """One-shot KFP detector with equivalence rules."""

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        ex_txt, ex_json = _load_few_shot("kubeflow")
        system = (
            "You are an expert in Kubeflow Pipelines. Detect DSL components/pipelines, compiled YAML, scheduling. "
            "Be conservative. STRICT JSON."
        )
        eep = """
            Pipelines/Components: @dsl.pipeline/@dsl.component, kfp.dsl.* (v1/v2).
            Manifests: compiled Argo/Tekton YAML present.
            Scheduling: CronWorkflow or external CI schedulers.
        """
        schema = (
            'Return JSON: {"uses_kubeflow": bool, "pipelines_count": int, "components_count": int, '
            '"manifests_present": bool, "ops_quality": float}'
        )
        few_shot = f"----- EXAMPLE SNIPPET -----\n{ex_txt}\n----- EXAMPLE LABELS -----\n{ex_json}\n\n" if ex_txt and ex_json else ""
        prompt = f"{eep}\n{schema}\n{few_shot}Evaluate as one corpus:\n\n" + "\n".join(
            f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets)
        )
        data = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "uses_kubeflow": bool(data.get("uses_kubeflow", False)),
            "kubeflow_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "kubeflow_components_count": int(data.get("components_count", 0) or 0),
            "kubeflow_manifests_present": bool(data.get("manifests_present", False)),
            "kubeflow_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }
