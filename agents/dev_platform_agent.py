from pathlib import Path
from typing import List

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

# Thresholds for mapping numeric values to a 0–5 scale
CC_THRESHOLDS    = [0,  5, 10, 20, 30]   # cyclomatic complexity (lower is better)
MI_THRESHOLDS    = [100, 80, 60, 40, 20] # maintainability index (higher is better)
COUNT_THRESHOLDS = [0,   1,  5, 10, 20]   # for counts (tests, CI files, etc.)

def score_metric(value: float, thresholds: List[float], invert: bool=False) -> int:
    """
    Map `value` into 0–5 based on `thresholds`.
    If invert=True, higher values yield lower scores.
    """
    for i, t in enumerate(thresholds):
        if (value <= t and not invert) or (value >= t and invert):
            return 5 - i
    return 0

def analyze_repo(repo_path: str) -> dict:
    """
    Scans the given local repo folder and returns:
      - raw `signals` (all eight helpers)
      - `scores`: development_maturity and innovation_pipeline (0–5)
    """
    root = Path(repo_path)
    all_files = list_all_files(repo_path)

    # — Gather file‐lists for helpers
    py_files = [Path(f) for f in all_files if f.endswith(".py")]
    nb_files = [Path(f) for f in all_files if f.endswith(".ipynb")]

    # — Raw signals from your helpers
    signals = {}
    signals.update(ast_metrics(py_files))             # avg_cc, avg_mi, doc_cov
    signals.update(notebook_metrics(nb_files))        # notebook_count
    signals.update(detect_tests(root))                # test_file_count, has_tests, has_test_coverage_report
    signals.update(detect_env(root))                  # has_requirements, has_pipfile, has_env_yml
    signals.update(detect_ci(root))                   # ci_workflow_count, has_ci
    signals.update(detect_cd(root))                   # deploy_script_count, has_deploy_scripts
    signals.update(detect_experiments(root))          # experiment_folder_count, has_experiments
    signals.update(scan_secrets(root))                # secret_file_count, has_secrets

    # — Sub-scores for Development Maturity
    sc_cc    = score_metric(signals["avg_cyclomatic_complexity"], CC_THRESHOLDS, invert=True)
    sc_mi    = score_metric(signals["avg_maintainability_index"],    MI_THRESHOLDS)
    sc_tests = score_metric(signals["test_file_count"],              COUNT_THRESHOLDS)
    sc_ci    = score_metric(signals["ci_workflow_count"],            COUNT_THRESHOLDS)
    sc_cd    = score_metric(signals["deploy_script_count"],          COUNT_THRESHOLDS)
    # environment maturity as fraction of env files present
    env_flags = [
        signals["has_requirements"],
        signals["has_pipfile"],
        signals["has_env_yml"]
    ]
    sc_env   = int(sum(env_flags) / len(env_flags) * 5)
    # penalize secret leaks (if any secrets found, score low)
    sc_sec   = 0 if signals["has_secrets"] else 5

    # Composite Dev Maturity (weighted equally across 7 sub-scores)
    dev_maturity = round(
        (sc_cc + sc_mi + sc_tests + sc_ci + sc_cd + sc_env + sc_sec) / 7, 2
    )

    # — Sub-scores for Innovation Pipeline
    sc_nb   = score_metric(signals["notebook_count"], COUNT_THRESHOLDS)
    sc_exp  = score_metric(signals["experiment_folder_count"], COUNT_THRESHOLDS)
    sc_gov  = score_metric(
        signals.get("has_test_coverage_report", 0) + signals.get("has_tests", 0),
        COUNT_THRESHOLDS
    )  # reuse test/coverage as a proxy for governance

    innovation = round((sc_nb + sc_exp + sc_gov) / 3 * 5, 2)

    return {
        "agent": "dev_platform_agent",
        "repo": root.name,
        "signals": signals,
        "scores": {
            "development_maturity": dev_maturity,
            "innovation_pipeline": innovation
        }
    }
