import os
from datetime import datetime, timedelta
from pathlib import Path
from git import Repo
from typing import Dict, Any

from utils.file_utils import list_all_files

# core static-analysis helpers
from utils.code_analysis import (
    detect_env,
    detect_tests,
    detect_ci,
    detect_cd,
    detect_experiments,
    scan_secrets
)

# AI/ML-specific static-analysis helpers
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
    detect_dependency_files,
    detect_documentation
)

def analyze_dev_and_innovation(repo_path: str) -> Dict[str, Any]:
    root = Path(repo_path)
    all_files = list_all_files(repo_path)
    py_files = [Path(f) for f in all_files if f.endswith(".py")]

    signals: Dict[str, Any] = {}

    # ── Development Maturity ──

    # environment files
    signals.update(detect_env(root))  # has_requirements, has_pipfile, has_env_yml

    # Docker
    signals["has_dockerfile"]       = (root / "Dockerfile").exists()
    signals["has_docker_compose"]   = (root / "docker-compose.yml").exists()

    # CI/CD
    ci = detect_ci(root)
    signals["ci_cd_count"] = ci["ci_workflow_count"]
    signals["has_ci"]      = ci["has_ci"]

    cd = detect_cd(root)
    signals["deploy_script_count"] = cd["deploy_script_count"]
    signals["has_deploy_script"]   = cd["has_deploy_scripts"]

    # Tests
    tests = detect_tests(root)
    signals["has_tests"]                = tests["has_tests"]
    signals["test_count"]               = tests["test_file_count"]
    signals["has_test_coverage_report"] = tests["has_test_coverage_report"]

    # Commit activity
    try:
        repo = Repo(repo_path)
        cutoff = datetime.now() - timedelta(days=30)
        recent = [
            c for c in repo.iter_commits()
            if datetime.fromtimestamp(c.committed_date) >= cutoff
        ]
        signals["commits_last_30d"] = len(recent)
        signals["active_dev"]       = len(recent) >= 5
    except Exception:
        signals["commits_last_30d"] = 0
        signals["active_dev"]       = False

    # Changelog & README
    signals["has_changelog"] = (root / "CHANGELOG.md").exists()
    signals["has_readme"]    = (root / "README.md").exists()

    # ── Innovation Pipeline ──

    # Experiments folder
    exp = detect_experiments(root)
    signals["has_experiments"]         = exp["has_experiments"]
    signals["experiment_folder_count"] = exp["experiment_folder_count"]

    # GitHub templates
    gh = root / ".github"
    signals["has_issue_template"] = (
        (gh / "ISSUE_TEMPLATE").exists() or
        (gh / "ISSUE_TEMPLATE.md").exists()
    )
    signals["has_pr_template"]    = (gh / "PULL_REQUEST_TEMPLATE.md").exists()

    # Feature flags
    flags = [
        f for f in all_files
        if "feature" in os.path.basename(f).lower() and f.endswith((".yml", ".yaml"))
    ]
    signals["feature_flag_count"] = len(flags)

    # Secrets
    secret = scan_secrets(root)
    signals["has_secrets"]       = secret["has_secrets"]
    signals["secret_file_count"] = secret["secret_file_count"]

    # ── AI/ML-Specific Insights ──

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

    # ── Repo-maturity extras ──
    signals.update(detect_dependency_files(root))
    signals.update(detect_documentation(root))

    return {
        "agent":  "dev_quality_agent",
        "repo":   root.name,
        "signals": signals
    }
