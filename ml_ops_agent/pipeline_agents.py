# # ml_ops_agent/pipeline_agents.py
# from __future__ import annotations

# from typing import Any, Dict, List, Optional
# from micro_agents.base_agent import BaseMicroAgent


# class ExperimentTrackingAgent(BaseMicroAgent):
#     """LLM agent: detect general experiment tracking usage and quality."""

#     def evaluate(
#         self, code_snippets: List[str], context: Optional[Dict] = None
#     ) -> Dict[str, Any]:
#         system = (
#             "You are an experiment-tracking analyst. Detect MLflow/W&B/ClearML/"
#             "TensorBoard or custom tracking and judge coverage & quality. STRICT JSON."
#         )
#         prompt = (
#             "From these snippets, infer experiment tracking posture:\n\n"
#             f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
#             "Return JSON with keys:\n"
#             "{\n"
#             '  "tools": [{"name": string, "usage": "light|moderate|heavy"}],\n'
#             '  "metrics_logged": bool,\n'
#             '  "artifacts_logged": bool,\n'
#             '  "runs_structure_quality": float,   // 0..1\n'
#             '  "coverage": float                   // 0..1 perceived percent of training covered\n'
#             "}"
#         )
#         resp = self._call_llm(prompt, system)
#         data = self._parse_json_response(resp)
#         return {
#             "tracking_tools": data.get("tools", []) or [],
#             "tracking_metrics_logged": bool(data.get("metrics_logged", False)),
#             "tracking_artifacts_logged": bool(data.get("artifacts_logged", False)),
#             "tracking_runs_quality": float(data.get("runs_structure_quality", 0.0) or 0.0),
#             "tracking_coverage": float(data.get("coverage", 0.0) or 0.0),
#         }


# class PipelineAutomationAgent(BaseMicroAgent):
#     """LLM agent: detect pipeline automation (KFP, SageMaker/AzureML pipelines, Airflow, GitHub Actions)."""

#     def evaluate(
#         self, code_snippets: List[str], context: Optional[Dict] = None
#     ) -> Dict[str, Any]:
#         system = (
#             "Detect automation of ML pipelines: Kubeflow, SageMaker Pipelines, AzureML Pipelines, "
#             "Airflow/Prefect/Dagster, GitHub Actions, GitLab CI. STRICT JSON."
#         )
#         prompt = (
#             "From these snippets, infer pipeline automation posture:\n\n"
#             f"{chr(10).join(f'--- Snippet {i+1} ---\\n{snip}' for i, snip in enumerate(code_snippets))}\n\n"
#             "Return JSON with keys:\n"
#             "{\n"
#             '  "orchestrators": ["kfp"|"sagemaker_pipelines"|"azureml_pipelines"|"airflow"|"prefect"|"dagster"|"gha"|"gitlab_ci"],\n'
#             '  "pipelines_defined": int,\n'
#             '  "scheduling_present": bool,\n'
#             '  "automation_quality": float\n'
#             "}"
#         )
#         resp = self._call_llm(prompt, system)
#         data = self._parse_json_response(resp)
#         return {
#             "pipeline_orchestrators": data.get("orchestrators", []) or [],
#             "pipeline_pipelines_defined": int(data.get("pipelines_defined", 0) or 0),
#             "pipeline_scheduling_present": bool(data.get("scheduling_present", False)),
#             "pipeline_automation_quality": float(data.get("automation_quality", 0.0) or 0.0),
#         }
