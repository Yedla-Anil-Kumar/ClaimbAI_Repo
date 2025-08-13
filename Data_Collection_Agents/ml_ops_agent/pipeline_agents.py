# ml_ops_agent/pipeline_agents.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from Data_Collection_Agents.base_agent import BaseMicroAgent

FEW_SHOT_DIR = Path(__file__).resolve().parent / "few_shot"

def _load_few_shot_pair(stem: str) -> Tuple[str, str]:
    """
    Load one-shot example pair for this agent.
    Returns (example_text, example_json_string). Missing files -> ("", "").
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

class ExperimentTrackingAgent(BaseMicroAgent):
    """LLM agent: detect general experiment tracking usage and quality (one-shot)."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "You are an experiment-tracking analyst. Detect MLflow/W&B/ClearML/"
            "TensorBoard or custom tracking and judge coverage & quality. "
            "Reply with STRICT JSON only."
        )

        example_txt, example_json = _load_few_shot_pair("tracking")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "tools": [{"name": string, "usage": "light|moderate|heavy"}],\n'
            '  "metrics_logged": bool,\n'
            '  "artifacts_logged": bool,\n'
            '  "runs_structure_quality": float,   // 0..1\n'
            '  "coverage": float                  // 0..1 perceived percent of training covered\n'
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
            "tracking_tools": data.get("tools", []) or [],
            "tracking_metrics_logged": bool(data.get("metrics_logged", False)),
            "tracking_artifacts_logged": bool(data.get("artifacts_logged", False)),
            "tracking_runs_quality": float(
                data.get("runs_structure_quality", 0.0) or 0.0
            ),
            "tracking_coverage": float(data.get("coverage", 0.0) or 0.0),
        }


class PipelineAutomationAgent(BaseMicroAgent):
    """
    LLM agent: detect pipeline automation (KFP, SageMaker/AzureML pipelines,
    Airflow/Prefect/Dagster, GitHub Actions/GitLab CI). Uses one-shot prompting.
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        system = (
            "Detect automation of ML pipelines: Kubeflow, SageMaker Pipelines, AzureML "
            "Pipelines, Airflow/Prefect/Dagster, GitHub Actions, GitLab CI. "
            "Reply with STRICT JSON only."
        )

        example_txt, example_json = _load_few_shot_pair("automation")

        schema_block = (
            'Return JSON with keys:\n'
            '{\n'
            '  "orchestrators": ["kfp"|"sagemaker_pipelines"|"azureml_pipelines"|\n'
            '                    "airflow"|"prefect"|"dagster"|"gha"|"gitlab_ci"],\n'
            '  "pipelines_defined": int,\n'
            '  "scheduling_present": bool,\n'
            '  "automation_quality": float\n'
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
            "pipeline_orchestrators": data.get("orchestrators", []) or [],
            "pipeline_pipelines_defined": int(data.get("pipelines_defined", 0) or 0),
            "pipeline_scheduling_present": bool(data.get("scheduling_present", False)),
            "pipeline_automation_quality": float(
                data.get("automation_quality", 0.0) or 0.0
            ),
        }
