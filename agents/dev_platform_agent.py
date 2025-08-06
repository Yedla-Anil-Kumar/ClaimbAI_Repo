# agents/dev_platform_agent.py

from pathlib import Path
from typing import Any, Dict

from utils.file_utils import list_all_files
from utils.code_analysis import (
    ast_metrics,
    notebook_metrics,      # still collected, but NOT used in scoring as per mentor
    detect_tests,
    detect_env,
    detect_ci,
    detect_cd,
    detect_experiments,
    scan_secrets
)
from utils.ml_insights import (
    detect_ml_frameworks,
    detect_data_pipeline_configs,    # now takes (root, py_files)
    detect_experiment_tracking,
    detect_model_training_scripts,
    detect_model_evaluation,
    detect_hyperparameter_configs,    # now takes (root, py_files)
    detect_data_validation,
    detect_feature_engineering,
    detect_model_export,
    detect_inference_endpoints,
    detect_metric_reporting,
    detect_nested_loops,
    detect_dependency_files,          # new
    detect_documentation             # new
)

# Threshold helpers
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def analyze_repo(repo_path: str) -> Dict[str, Any]:
    root = Path(repo_path)
    # gather every file path once
    all_files = list_all_files(repo_path)
    py_files   = [Path(f) for f in all_files if f.endswith(".py")]
    nb_files   = [Path(f) for f in all_files if f.endswith(".ipynb")]

    # ───── Signals ───────────────────────────────────────────────
    signals: Dict[str, Any] = {}

    # core static analysis
    signals.update(ast_metrics(py_files))             # avg_cc, avg_mi, docstring_coverage
    signals.update(notebook_metrics(nb_files))        # notebook_count (collected, not scored)
    signals.update(detect_tests(root))
    signals.update(detect_env(root))
    signals.update(detect_ci(root))
    signals.update(detect_cd(root))
    signals.update(detect_experiments(root))
    signals.update(scan_secrets(root))

    # AI/ML static analysis
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

    # New repo-maturity checks
    signals.update(detect_dependency_files(root))
    signals.update(detect_documentation(root))

    # ───── Scoring (rebalance) ─────────────────────────────────
    # lower CC better
    s_cc   = clamp01(1.0 - min(signals.get("avg_cyclomatic_complexity", 0.0), 30) / 30.0)
    # MI 20→0.0, 100→1.0
    s_mi   = clamp01((min(signals.get("avg_maintainability_index", 0.0), 100) - 20) / 80.0)
    s_doc  = clamp01(signals.get("docstring_coverage", 0.0))
    # tests capped at 10 files
    s_tests = clamp01(signals.get("test_file_count", 0) / 10.0)
    # CI/CD flags
    s_ci   = 1.0 if signals.get("ci_workflow_count", 0) > 0 else 0.0
    s_cd   = 1.0 if signals.get("deploy_script_count", 0) > 0 else 0.0
    # env files fraction
    env_bits = [
        signals.get("has_requirements", False),
        signals.get("has_pipfile", False),
        signals.get("has_env_yml", False)
    ]
    s_env  = sum(env_bits) / len(env_bits)
    # secret penalty
    s_sec  = 0.0 if signals.get("has_secrets", False) else 1.0
    # nested loops penalty (soft)
    nested_pen = clamp01(min(signals.get("nested_loop_files", 0), 10) / 10.0)
    s_eff  = clamp01(1.0 - 0.5 * nested_pen)

    # weights (sum ≈ 1.0)
    w = {
        "mi":    0.30,
        "doc":   0.20,
        "cc":    0.05,
        "tests": 0.15,
        "ci":    0.10,
        "cd":    0.10,
        "env":   0.07,
        "sec":   0.03,
        "eff":   0.00,   # available if you want to penalize inefficiency later
    }
    dev_maturity = round((
        w["mi"]*s_mi + w["doc"]*s_doc + w["cc"]*s_cc +
        w["tests"]*s_tests + w["ci"]*s_ci + w["cd"]*s_cd +
        w["env"]*s_env + w["sec"]*s_sec + w["eff"]*s_eff
    ) * 5, 2)

    # ─ Innovation Pipeline ────────────────────────────────────────
    # experiments, tracking, hyperparams, validation, metrics
    s_exp     = 1.0 if signals.get("has_experiments") else 0.0
    s_track   = 1.0 if any(signals.get(f"uses_{t}", False) for t in ("mlflow","wandb","clearml")) else 0.0
    s_hparams = 1.0 if (
        signals.get("has_hyperparam_file") or
        signals.get("uses_optuna") or signals.get("uses_ray_tune")
    ) else 0.0
    s_valid   = 1.0 if any(signals.get(f"uses_{v}", False) for v in ("great_expectations","evidently","pandera")) else 0.0
    s_metrics = 1.0 if (
        signals.get("reports_precision_recall_f1") or
        signals.get("reports_regression_metrics")
    ) else 0.0

    iw = {
        "exp":     0.30,
        "track":   0.25,
        "hparams": 0.20,
        "valid":   0.15,
        "metrics": 0.10
    }
    innovation = round((
        iw["exp"]*s_exp + iw["track"]*s_track +
        iw["hparams"]*s_hparams + iw["valid"]*s_valid +
        iw["metrics"]*s_metrics
    ) * 5, 2)

    return {
        "agent": "dev_platform_agent",
        "repo":   root.name,
        "signals": signals,
        "scores": {
            "development_maturity": dev_maturity,
            "innovation_pipeline":  innovation
        }
    }
