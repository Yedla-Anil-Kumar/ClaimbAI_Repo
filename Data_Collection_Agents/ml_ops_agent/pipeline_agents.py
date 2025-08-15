from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from Data_Collection_Agents.base_agent import BaseMicroAgent
import json

def _load_few_shot(name: str) -> Tuple[str, str]:
    """
    Load one-shot example pair for this agent.
    Returns (example_text, example_json_string). Missing files -> ("", "").
    """
    root = Path(__file__).resolve().parent / "few_shot"
    txt = (root / f"{name}_example.txt").read_text(encoding="utf-8") if (root / f"{name}_example.txt").exists() else ""
    lab = ""
    jp = root / f"{name}_example.json"
    if jp.exists():
        try:
            lab = json.dumps(json.loads(jp.read_text(encoding="utf-8")), indent=2)
        except Exception:
            lab = ""
    return txt, lab


class ExperimentTrackingAgent(BaseMicroAgent):
    """One-shot tracking posture with equivalence rules (MLflow/W&B/ClearML/TB/Comet/Neptune/custom)."""

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        example_txt, example_json = _load_few_shot("tracking")
        system = (
            "You are an experiment-tracking analyst. Detect experiment tracking across common tools OR custom trackers (JSON/CSV logs, TB event files). "
            "Reward evidence of metrics + artifacts + structured runs. Reply with STRICT JSON only."
        )
        eep = """
            Metrics evidence: tool API calls OR writing metrics to files consumed by dashboards.
            Artifacts evidence: log_artifact(s), 'artifacts/' folders, 'mlruns/', 'wandb/'.
            Coverage: training + eval + artifacts logged (even if distributed).
        """
        schema = (
            'Return JSON with keys:\n'
            '{\n'
            '  "tools": [{"name": string, "usage": "light|moderate|heavy"}],\n'
            '  "metrics_logged": bool,\n'
            '  "artifacts_logged": bool,\n'
            '  "runs_structure_quality": float,   // 0..1\n'
            '  "coverage": float                  // 0..1 perceived percent of training covered\n'
            '}'
        )
        
        few_shot = f"----- EXAMPLE SNIPPET -----\n{example_txt}\n----- EXAMPLE LABELS -----\n{example_json}\n\n" if example_txt and example_json else ""
        prompt = f"{eep}\n{schema}\n{few_shot}Evaluate as one corpus:\n\n" + "\n".join(
            f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets)
        )
        d = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "tracking_tools": d.get("tools", []) or [],
            "tracking_metrics_logged": bool(d.get("metrics_logged", False)),
            "tracking_artifacts_logged": bool(d.get("artifacts_logged", False)),
            "tracking_runs_quality": float(d.get("runs_structure_quality", 0.0) or 0.0),
            "tracking_coverage": float(d.get("coverage", 0.0) or 0.0),
        }


class PipelineAutomationAgent(BaseMicroAgent):
    """One-shot automation detector (Airflow/Prefect/Dagster/KFP/Argo/Tekton + CI/CD schedulers)."""

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        ex_txt, ex_json = _load_few_shot("automation")
        system = "Detect orchestrators + CI/CD + scheduling; count pipelines conservatively. STRICT JSON."
        eep = """
            Orchestrators: Airflow, Prefect, Dagster, KFP, Argo/Tekton, Step Functions.
            CI/CD: GitHub Actions, GitLab CI, Azure DevOps, Jenkins, CircleCI.
            Scheduling: cron in CI or orchestrators, EventBridge/Cloud Scheduler.
        """
        schema = (
            'Return JSON: {"orchestrators":[string], "pipelines_defined":int, '
            '"scheduling_present":bool, "automation_quality":float}'
        )
        few_shot = f"----- EXAMPLE SNIPPET -----\n{ex_txt}\n----- EXAMPLE LABELS -----\n{ex_json}\n\n" if ex_txt and ex_json else ""
        prompt = f"{eep}\n{schema}\n{few_shot}Evaluate as one corpus:\n\n" + "\n".join(
            f"--- Snippet {i+1} ---\n{snip}" for i, snip in enumerate(code_snippets)
        )
        d = self._parse_json_response(self._call_llm(prompt, system))
        return {
            "pipeline_orchestrators": d.get("orchestrators", []) or [],
            "pipeline_pipelines_defined": int(d.get("pipelines_defined", 0) or 0),
            "pipeline_scheduling_present": bool(d.get("scheduling_present", False)),
            "pipeline_automation_quality": float(d.get("automation_quality", 0.0) or 0.0),
        }
