# agents/dev_quality_agent.py

import os
import fnmatch
from datetime import datetime, timedelta
from git import Repo
from utils.file_utils import list_all_files

def analyze_dev_and_innovation(repo_path: str) -> dict:
    signals = {}

    # Development Maturity
    signals["has_requirements"] = os.path.exists(os.path.join(repo_path, "requirements.txt"))
    signals["has_pipfile"] = os.path.exists(os.path.join(repo_path, "Pipfile"))
    signals["has_env_yml"] = os.path.exists(os.path.join(repo_path, "environment.yml"))

    signals["has_dockerfile"] = os.path.exists(os.path.join(repo_path, "Dockerfile"))
    signals["has_docker_compose"] = os.path.exists(os.path.join(repo_path, "docker-compose.yml"))

    ci_dir = os.path.join(repo_path, ".github", "workflows")
    workflows = []
    if os.path.isdir(ci_dir):
        workflows = fnmatch.filter(os.listdir(ci_dir), "*.yml")
    signals["ci_cd_count"] = len(workflows)
    signals["has_release_workflow"] = any("release" in w.lower() for w in workflows)

    all_files = list(list_all_files(repo_path))
    test_files = [f for f in all_files if "/tests/" in f.lower() or os.path.basename(f).startswith("test_")]
    signals["has_tests"] = bool(test_files)
    signals["test_count"] = len(test_files)

    # Commit activity
    try:
        repo = Repo(repo_path)
        cutoff = datetime.now() - timedelta(days=30)
        recent = [c for c in repo.iter_commits() if datetime.fromtimestamp(c.committed_date) >= cutoff]
        signals["commits_last_30d"] = len(recent)
        signals["active_dev"] = len(recent) >= 5
    except Exception:
        signals["commits_last_30d"] = 0
        signals["active_dev"] = False

    signals["has_changelog"] = os.path.exists(os.path.join(repo_path, "CHANGELOG.md"))
    signals["has_readme"] = os.path.exists(os.path.join(repo_path, "README.md"))

    # Innovation Pipeline
    gh = os.path.join(repo_path, ".github")
    signals["has_issue_template"] = os.path.exists(os.path.join(gh, "ISSUE_TEMPLATE")) or \
        os.path.exists(os.path.join(gh, "ISSUE_TEMPLATE.md"))
    signals["has_pr_template"] = os.path.exists(os.path.join(gh, "PULL_REQUEST_TEMPLATE.md"))

    signals["has_experiments"] = os.path.isdir(os.path.join(repo_path, "experiments")) or \
        os.path.isdir(os.path.join(repo_path, "notebooks", "experiments"))

    flags = [f for f in all_files if "feature" in os.path.basename(f).lower() and f.endswith((".yml", ".yaml"))]
    signals["feature_flag_count"] = len(flags)

    signals["has_deploy_script"] = os.path.exists(os.path.join(repo_path, "release.sh")) or \
        os.path.exists(os.path.join(repo_path, "deploy.sh"))

    return {
        "agent": "dev_quality_agent",
        "repo": os.path.basename(repo_path),
        "signals": signals
    }
