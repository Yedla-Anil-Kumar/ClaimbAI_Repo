# micro_agents/ml_framework_agents.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent


def _join_snippets(snippets: List[str]) -> str:
    parts = []
    for i, s in enumerate(snippets, start=1):
        parts.append(f"--- Snippet {i} ---\n{s}")
    return "\n\n".join(parts)


class MLFrameworkAgent(BaseMicroAgent):
    """
    Detect and normalize ML framework usage.

    Produces counts compatible with your static signals:
      - framework_torch, framework_tensorflow, framework_sklearn,
        framework_keras, framework_xgboost, framework_lightgbm  (ints)
    """

    _CANON_MAP = {
        "pytorch": "torch",
        "torch": "torch",
        "tf": "tensorflow",
        "tensorflow": "tensorflow",
        "scikit-learn": "sklearn",
        "scikitlearn": "sklearn",
        "sklearn": "sklearn",
        "keras": "keras",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
    }

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert ML framework analyst. Find all ML frameworks "
            "used in the code. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze these code snippets for ML framework usage. Return JSON keys:\n"
            "- framework_usage: object mapping framework name to integer count "
            '(e.g., {"torch": 3, "tensorflow": 1})\n'
            "- primary_framework: string or null\n"
            "- framework_combinations: array of arrays or strings\n"
            "- usage_patterns: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        usage_raw = res.get("framework_usage", {}) or {}
        counts: Dict[str, int] = {
            "framework_torch": 0,
            "framework_tensorflow": 0,
            "framework_sklearn": 0,
            "framework_keras": 0,
            "framework_xgboost": 0,
            "framework_lightgbm": 0,
        }

        for k, v in usage_raw.items():
            name = (k or "").strip().lower()
            canon = self._CANON_MAP.get(name)
            if not canon:
                continue
            if canon == "torch":
                counts["framework_torch"] += int(v or 0)
            elif canon == "tensorflow":
                counts["framework_tensorflow"] += int(v or 0)
            elif canon == "sklearn":
                counts["framework_sklearn"] += int(v or 0)
            elif canon == "keras":
                counts["framework_keras"] += int(v or 0)
            elif canon == "xgboost":
                counts["framework_xgboost"] += int(v or 0)
            elif canon == "lightgbm":
                counts["framework_lightgbm"] += int(v or 0)

        return counts


class ExperimentTrackingAgent(BaseMicroAgent):
    """
    Detect experiment tracking tools.

    Produces booleans compatible with your static signals:
      - uses_mlflow, uses_wandb, uses_clearml
    """

    _CANON_MAP = {
        "mlflow": "uses_mlflow",
        "wandb": "uses_wandb",
        "weights & biases": "uses_wandb",
        "weights and biases": "uses_wandb",
        "clearml": "uses_clearml",
    }

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an experiment tracking analyst. Detect MLflow, W&B, ClearML. "
            "Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the code for experiment tracking. Return JSON keys:\n"
            "- tracking_tools: object mapping tool name to boolean\n"
            "- tracking_patterns: array of strings\n"
            "- best_practices: array of strings\n"
            "- improvement_suggestions: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        tools = {
            str(k).lower(): bool(v)
            for k, v in (res.get("tracking_tools", {}) or {}).items()
        }
        out = {"uses_mlflow": False, "uses_wandb": False, "uses_clearml": False}
        for name, used in tools.items():
            key = self._CANON_MAP.get(name)
            if key:
                out[key] = out.get(key, False) or used
        return out


class HyperparameterOptimizationAgent(BaseMicroAgent):
    """
    Detect HPO tools and hyperparameter config files.

    Produces:
      - has_hyperparam_file (bool)
      - uses_optuna (bool)
      - uses_ray_tune (bool)
    """

    _CANON_MAP = {
        "optuna": "uses_optuna",
        "ray tune": "uses_ray_tune",
        "ray.tune": "uses_ray_tune",
        "ray.tuning": "uses_ray_tune",
        "ray": "uses_ray_tune",
    }

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an HPO analyst. Detect Optuna/Ray Tune and hyperparameter "
            "config files. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the code for hyperparameter optimization. Return JSON keys:\n"
            "- optimization_tools: object mapping tool name to boolean\n"
            "- config_files: boolean indicating hyperparameter config files present\n"
            "- optimization_strategies: array of strings\n"
            "- best_practices: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        tools = {
            str(k).lower(): bool(v)
            for k, v in (res.get("optimization_tools", {}) or {}).items()
        }
        out = {
            "has_hyperparam_file": bool(res.get("config_files", False)),
            "uses_optuna": False,
            "uses_ray_tune": False,
        }
        for name, used in tools.items():
            key = self._CANON_MAP.get(name)
            if key:
                out[key] = out.get(key, False) or used
        return out


class DataValidationAgent(BaseMicroAgent):
    """
    Detect data validation tools.

    Produces:
      - uses_great_expectations, uses_evidently, uses_pandera (booleans)
    """

    _CANON = {
        "great expectations": "uses_great_expectations",
        "greatexpectations": "uses_great_expectations",
        "great_expectations": "uses_great_expectations",
        "evidently": "uses_evidently",
        "pandera": "uses_pandera",
    }

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a data validation analyst. Detect Great Expectations, "
            "Evidently, Pandera. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the code for data validation. Return JSON keys:\n"
            "- validation_tools: object mapping tool name to boolean\n"
            "- validation_patterns: array of strings\n"
            "- data_quality_checks: array of strings\n"
            "- improvement_suggestions: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        tools = {
            str(k).lower(): bool(v)
            for k, v in (res.get("validation_tools", {}) or {}).items()
        }
        out = {
            "uses_great_expectations": False,
            "uses_evidently": False,
            "uses_pandera": False,
        }
        for name, used in tools.items():
            key = self._CANON.get(name)
            if key:
                out[key] = out.get(key, False) or used
        return out


class ModelTrainingAgent(BaseMicroAgent):
    """
    Detect training scripts and entrypoints.

    Produces:
      - train_script_count (int)
      - has_entrypoint_training (bool)
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an ML training analyst. Detect training scripts and main "
            "entrypoints. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the code for training patterns. Return JSON keys:\n"
            "- train_script_count: integer\n"
            "- has_entrypoint_training: boolean\n"
            "- training_patterns: array of strings\n"
            "- training_quality: number in [0,1]\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        return {
            "train_script_count": int(res.get("train_script_count", 0)),
            "has_entrypoint_training": bool(res.get("has_entrypoint_training", False)),
            "training_patterns": res.get("training_patterns", []),
            "training_quality": float(res.get("training_quality", 0.0)),
        }


class ModelEvaluationAgent(BaseMicroAgent):
    """
    Detect evaluation scripts and metrics usage.

    Produces:
      - eval_script_count (int)
      - uses_metrics_library (bool)
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an ML evaluation analyst. Detect evaluation scripts and "
            "metrics libraries. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the code for evaluation. Return JSON keys:\n"
            "- eval_script_count: integer\n"
            "- uses_metrics_library: boolean\n"
            "- evaluation_metrics: array of strings\n"
            "- evaluation_quality: number in [0,1]\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        res = self._parse_json_response(response)

        return {
            "eval_script_count": int(res.get("eval_script_count", 0)),
            "uses_metrics_library": bool(res.get("uses_metrics_library", False)),
            "evaluation_metrics": res.get("evaluation_metrics", []),
            "evaluation_quality": float(res.get("evaluation_quality", 0.0)),
        }
