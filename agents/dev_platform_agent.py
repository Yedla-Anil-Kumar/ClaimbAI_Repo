# agents/dev_platform_agent.py

from pathlib import Path
from typing import Any, Dict, List

from utils.file_utils import list_all_files
from utils.code_analysis import (
    ast_metrics,
    notebook_metrics,
    detect_tests,
    detect_env,
    detect_ci,
    detect_cd,
    detect_experiments,
    scan_secrets
)
from utils.ml_insights import (
    detect_ml_frameworks,
    detect_data_pipeline_configs,
    detect_experiment_tracking,
    detect_model_training_scripts,
    detect_model_evaluation,
    detect_hyperparameter_configs,
    detect_data_validation,
    detect_feature_engineering,
    detect_model_export,
    detect_inference_endpoints,
    detect_metric_reporting,
    detect_nested_loops
)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def calculate_scores(signals: Dict[str, Any], py_files: List[Path]) -> Dict[str, float]:
    # ─── Development Maturity ────────────────────────────────────
    cc = signals.get("avg_cyclomatic_complexity", 0.0)
    s_cc = clamp01(1.0 - (min(cc, 30) / 30) ** 1.5)

    test_count = signals.get("test_file_count", 0)
    test_ratio = test_count / (1 + len(py_files))
    s_tests = clamp01(
        0.3 * min(test_count, 10) / 10 +
        0.7 * min(test_ratio, 0.5) / 0.5
    )

    env_scores = {
        "has_requirements": 0.3,
        "has_pipfile":      0.7,
        "has_env_yml":      0.5,
        "has_poetry":       1.0
    }
    s_env = max(
        (env_scores[k] for k in env_scores if signals.get(k, False)),
        default=0.0
    )

    s_dup = 1.0 - clamp01(signals.get("duplication_score", 0.0))

    w = {
        "mi":    0.25,
        "doc":   0.15,
        "cc":    0.10,
        "tests": 0.20,
        "ci":    0.08,
        "cd":    0.08,
        "env":   0.05,
        "sec":   0.05,
        "dup":   0.04
    }

    dev_raw = (
        w["mi"]    * clamp01((signals.get("avg_maintainability_index", 0.0) - 20) / 80.0) +
        w["doc"]   * clamp01(signals.get("docstring_coverage", 0.0)) +
        w["cc"]    * s_cc +
        w["tests"] * s_tests +
        w["ci"]    * (1.0 if signals.get("ci_workflow_count", 0) > 0 else 0.0) +
        w["cd"]    * (1.0 if signals.get("deploy_script_count", 0) > 0 else 0.0) +
        w["env"]   * s_env +
        w["sec"]   * (0.0 if signals.get("has_secrets", False) else 1.0) +
        w["dup"]   * s_dup
    )
    dev_maturity = round(dev_raw * 5, 2)

    # ─── Innovation Pipeline ─────────────────────────────────────
    tracking_systems = sum(
        1 for t in ("mlflow", "wandb", "clearml")
        if signals.get(f"uses_{t}", False)
    )
    s_track = clamp01((tracking_systems / 3.0) + (0.5 if tracking_systems > 0 else 0.0))

    metrics_score = 0.0
    if signals.get("reports_precision_recall_f1"):
        metrics_score = 0.7
    if signals.get("reports_regression_metrics"):
        metrics_score = max(metrics_score, 0.5)
    if signals.get("uses_custom_metrics"):
        metrics_score = 1.0

    iw = {
        "exp":     0.25,
        "track":   0.30,
        "hparams": 0.20,
        "valid":   0.15,
        "metrics": 0.10
    }

    innovation_raw = (
        iw["exp"]   * (1.0 if signals.get("has_experiments") else 0.0) +
        iw["track"] * s_track +
        iw["hparams"] * (1.0 if (
            signals.get("has_hyperparam_file") or
            signals.get("uses_optuna") or
            signals.get("uses_ray_tune")
        ) else 0.0) +
        iw["valid"] * (1.0 if any(
            signals.get(f"uses_{v}", False)
            for v in ("great_expectations", "evidently", "pandera")
        ) else 0.0) +
        iw["metrics"] * metrics_score
    )
    innovation = round(innovation_raw * 5, 2)

    return {
        "development_maturity": dev_maturity,
        "innovation_pipeline":  innovation
    }


def analyze_repo(repo_path: str) -> Dict[str, Any]:
    root      = Path(repo_path)
    all_files = list_all_files(repo_path)
    py_files  = [Path(f) for f in all_files if f.endswith(".py")]
    nb_files  = [Path(f) for f in all_files if f.endswith(".ipynb")]

    signals: Dict[str, Any] = {}
    # core static checks
    signals.update(ast_metrics(py_files))
    signals.update(notebook_metrics(nb_files))
    signals.update(detect_tests(root))
    signals.update(detect_env(root))
    signals.update(detect_ci(root))
    signals.update(detect_cd(root))
    signals.update(detect_experiments(root))
    signals.update(scan_secrets(root))
    # AI/ML static checks
    signals.update(detect_ml_frameworks(py_files))
    signals.update(detect_data_pipeline_configs(root, py_files))
    signals.update(detect_experiment_tracking(py_files))
    signals.update(detect_model_training_scripts(py_files))
    signals.update(detect_model_evaluation(py_files))
    signals.update(detect_hyperparameter_configs(root, py_files))
    signals.update(detect_data_validation(py_files))
    signals.update(detect_feature_engineering(py_files))
    signals.update(detect_model_export(py_files, root))
    signals.update(detect_inference_endpoints(py_files))
    signals.update(detect_metric_reporting(py_files))
    signals.update(detect_nested_loops(py_files))

    scores = calculate_scores(signals, py_files)

    return {
        "agent":   "dev_platform_agent",
        "repo":    root.name,
        "signals": signals,
        "scores":  scores
    }
