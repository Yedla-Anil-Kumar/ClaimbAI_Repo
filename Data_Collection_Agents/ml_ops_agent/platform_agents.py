# ml_ops_agent/platform_agents.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
from Data_Collection_Agents.base_agent import BaseMicroAgent

FEW_SHOT_DIR = Path(__file__).resolve().parent / "one_shot"


def _load_few_shot_pair(stem: str) -> Tuple[str, str]:
    """
    Load one-shot example pair for this agent.

    Looks for:
      - <stem>_example.txt   (example code/config snippet)
      - <stem>_example.json  (gold labels matching this agent's schema)

    Returns (example_text, example_json_string). Missing files return ("", "").
    """
    txt_path = FEW_SHOT_DIR / f"{stem}_example.txt"
    json_path = FEW_SHOT_DIR / f"{stem}_example.json"
    try:
        example_txt = txt_path.read_text(encoding="utf-8")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        example_json = json.dumps(data, indent=2)
        return example_txt, example_json
    except Exception:
        return "", ""


class MLflowOpsAgent(BaseMicroAgent):
    """LLM agent: infer MLflow usage (tracking, registry, deployments) using one-shot prompting."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:

        system = (
            "You are an expert MLOps analyst. Inspect project code/config and "
            "infer MLflow usage (tracking endpoints, experiments, registry, deployments). "
            "Reply with STRICT JSON only."
        )
        example_txt, example_json = _load_few_shot_pair("mlflow")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "uses_mlflow": bool,\n'
            '  "tracking_endpoints": [string],\n'
            '  "experiments_count": int,\n'
            '  "registered_models_count": int,\n'
            '  "deployments": [{ "type": "model-serve|docker|k8s|other", "details": string }],\n'
            '  "integration_points": ["airflow"|"kfp"|"github_actions"|...],\n'
            '  "ops_quality": float  // 0..1 judgement of MLflow ops hygiene\n'
            '}'
        )

        few_shot_block = ""
        if example_txt and example_json:
            few_shot_block = (
                "For example, for this {code_snippet_example}, scores are below:\n"
                "--- Example ---\n"
                f"{example_txt}\n\n"
                "Correct JSON:\n"
                f"```json\n{example_json}\n```\n\n"
            )
            
        test_block = (
            "Now for this {code_snippet_test} determine the scores.\n\n"
            "Snippets to analyze:\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return STRICT JSON only."
        )

        prompt = (
            f"{schema_block}\n\n"
            f"{few_shot_block}"
            f"{test_block}"
        )

        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)

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
            "You are an expert in AWS SageMaker MLOps. Detect training jobs, endpoints, "
            "pipelines, and (if obvious) registry usage. Reply with STRICT JSON only."
        )
        example_txt, example_json = _load_few_shot_pair("sagemaker")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "uses_sagemaker": bool,\n'
            '  "training_jobs_count": int,\n'
            '  "endpoints_count": int,\n'
            '  "pipelines_count": int,\n'
            '  "registry_usage": bool,\n'
            '  "ops_quality": float\n'
            '}'
        )
        few_shot_block = ""
        if example_txt and example_json:
            few_shot_block = (
                "For example, for this {code_snippet_example}, scores are below:\n"
                "--- Example ---\n"
                f"{example_txt}\n\n"
                "Correct JSON:\n"
                f"```json\n{example_json}\n```\n\n"
            )

        test_block = (
            "Now for this {code_snippet_test} determine the scores.\n\n"
            "Snippets to analyze:\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return STRICT JSON only."
        )

        prompt = f"{schema_block}\n\n{few_shot_block}{test_block}"
        
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
            "You are an expert in Azure ML MLOps. Detect jobs, pipelines, managed endpoints, "
            "and registry usage. Reply with STRICT JSON only."
        )

        example_txt, example_json = _load_few_shot_pair("azureml")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "uses_azureml": bool,\n'
            '  "jobs_count": int,\n'
            '  "endpoints_count": int,\n'
            '  "pipelines_count": int,\n'
            '  "registry_usage": bool,\n'
            '  "ops_quality": float\n'
            '}'
        )
        few_shot_block = ""
        if example_txt and example_json:
            few_shot_block = (
                "For example, for this {code_snippet_example}, scores are below:\n"
                "--- Example ---\n"
                f"{example_txt}\n\n"
                "Correct JSON:\n"
                f"```json\n{example_json}\n```\n\n"
            )

        test_block = (
            "Now for this {code_snippet_test} determine the scores.\n\n"
            "Snippets to analyze:\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return STRICT JSON only."
        )

        prompt = f"{schema_block}\n\n{few_shot_block}{test_block}"

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
            "You are an expert in Kubeflow Pipelines. Detect components and pipelines "
            "and whether manifests/Argo specs are present. Reply with STRICT JSON only."
        )
        example_txt, example_json = _load_few_shot_pair("kubeflow")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "uses_kubeflow": bool,\n'
            '  "pipelines_count": int,\n'
            '  "components_count": int,\n'
            '  "manifests_present": bool,\n'
            '  "ops_quality": float\n'
            '}'
        )

        few_shot_block = ""
        if example_txt and example_json:
            few_shot_block = (
                "For example, for this {code_snippet_example}, scores are below:\n"
                "--- Example ---\n"
                f"{example_txt}\n\n"
                "Correct JSON:\n"
                f"```json\n{example_json}\n```\n\n"
            )

        test_block = (
            "Now for this {code_snippet_test} determine the scores.\n\n"
            "Snippets to analyze:\n"
            f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
            "Return STRICT JSON only."
        )

        prompt = f"{schema_block}\n\n{few_shot_block}{test_block}"
        resp = self._call_llm(prompt, system)
        data = self._parse_json_response(resp)
        return {
            "uses_kubeflow": bool(data.get("uses_kubeflow", False)),
            "kubeflow_pipelines_count": int(data.get("pipelines_count", 0) or 0),
            "kubeflow_components_count": int(data.get("components_count", 0) or 0),
            "kubeflow_manifests_present": bool(data.get("manifests_present", False)),
            "kubeflow_ops_quality": float(data.get("ops_quality", 0.0) or 0.0),
        }
