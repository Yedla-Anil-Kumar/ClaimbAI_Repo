# ml_ops_agent/platform_agents.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from micro_agents.base_agent import BaseMicroAgent


class MLflowOpsAgent(BaseMicroAgent):
    """LLM agent: infer MLflow usage (tracking, registry, deployments)."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "You are an expert MLOps analyst. Inspect project code/config "
            "and infer MLflow usage (tracking, model registry, deployments). "
            "Reply STRICT JSON."
        )
        prompt = (
            "From the following code/config snippets, infer MLflow usage:\n\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return JSON with keys:\n"
            "{\n"
            '  "uses_mlflow": bool,\n'
            '  "tracking_endpoints": [string],\n'
            '  "experiments_count": int,\n'
            '  "registered_models_count": int,\n'
            '  "deployments": [{"type": "model-serve|docker|k8s|other", "details": string}],\n'
            '  "integration_points": ["airflow"|"kfp"|"github_actions"|...],\n'
            '  "ops_quality": float  // 0..1 judgement of MLflow ops hygiene\n'
            "}"
        )
        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)
        # Normalize defaults
        return {
            "uses_mlflow": bool(data.get("uses_mlflow", False)),
            "mlflow_tracking_endpoints": data.get("tracking_endpoints", []) or [],
            "mlflow_experiments_count": int(data.get("experiments_count", 0) or 0),
            "mlflow_registered_models_count": int(
                data.get("registered_models_count", 0) or 0
            ),
            "mlflow_deployments": data.get("deployments", []) or [],
            "mlflow_integration_points": data.get("integration_points", []) or [],
            "mlflow_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class SageMakerOpsAgent(BaseMicroAgent):
    """LLM agent: infer SageMaker training/deployment/pipelines usage."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "You are an expert in AWS SageMaker MLOps. Detect training jobs, "
            "endpoints, model registry, pipelines. Reply STRICT JSON."
        )
        prompt = (
            "From these snippets, infer SageMaker usage:\n\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return JSON with keys:\n"
            "{\n"
            '  "uses_sagemaker": bool,\n'
            '  "training_jobs_count": int,\n'
            '  "endpoints_count": int,\n'
            '  "pipelines_count": int,\n'
            '  "registry_usage": bool,\n'
            '  "ops_quality": float\n'
            "}"
        )
        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)
        return {
            "uses_sagemaker": bool(data.get("uses_sagemaker", False)),
            "sagemaker_training_jobs_count": int(data.get("training_jobs_count", 0) or 0),
            "sagemaker_endpoints_count": int(data.get("endpoints_count", 0) or 0),
            "sagemaker_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "sagemaker_registry_usage": bool(data.get("registry_usage", False)),
            "sagemaker_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class AzureMLOpsAgent(BaseMicroAgent):
    """LLM agent: infer Azure ML jobs/endpoints/pipelines/registry usage."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "You are an expert in Azure ML MLOps. Detect jobs, pipelines, "
            "managed online/batch endpoints, registries. Reply STRICT JSON."
        )
        prompt = (
            "From these snippets, infer Azure ML usage:\n\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return JSON with keys:\n"
            "{\n"
            '  "uses_azureml": bool,\n'
            '  "jobs_count": int,\n'
            '  "endpoints_count": int,\n'
            '  "pipelines_count": int,\n'
            '  "registry_usage": bool,\n'
            '  "ops_quality": float\n'
            "}"
        )
        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)
        return {
            "uses_azureml": bool(data.get("uses_azureml", False)),
            "azureml_jobs_count": int(data.get("jobs_count", 0) or 0),
            "azureml_endpoints_count": int(data.get("endpoints_count", 0) or 0),
            "azureml_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "azureml_registry_usage": bool(data.get("registry_usage", False)),
            "azureml_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }


class KubeflowOpsAgent(BaseMicroAgent):
    """LLM agent: infer Kubeflow Pipelines usage (components, pipelines)."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "You are an expert in Kubeflow Pipelines. Detect KFP usage "
            "(components, pipelines), Argo/K8s manifests for pipelines. Reply STRICT JSON."
        )
        prompt = (
            "From these snippets, infer Kubeflow Pipelines usage:\n\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return JSON with keys:\n"
            "{\n"
            '  "uses_kubeflow": bool,\n'
            '  "pipelines_count": int,\n'
            '  "components_count": int,\n'
            '  "manifests_present": bool,\n'
            '  "ops_quality": float\n'
            "}"
        )
        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)
        return {
            "uses_kubeflow": bool(data.get("uses_kubeflow", False)),
            "kubeflow_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "kubeflow_components_count": int(data.get("components_count", 0) or 0),
            "kubeflow_manifests_present": bool(data.get("manifests_present", False)),
            "kubeflow_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }
