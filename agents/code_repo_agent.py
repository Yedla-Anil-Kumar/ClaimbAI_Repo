import os
from git import Repo
from utils.file_utils import list_all_files

def analyze_code_repo(repo_path: str) -> dict:
    signals = {}

    # README presence
    signals["has_readme"] = os.path.exists(os.path.join(repo_path, "README.md"))

    # Test files presence
    signals["has_tests"] = any("test" in f.lower() for f in list_all_files(repo_path))

    # Git commit history
    try:
        repo = Repo(repo_path)
        total_commits = len(list(repo.iter_commits()))
        signals["total_commits"] = total_commits
        signals["active_development"] = total_commits > 50
    except Exception:
        signals["total_commits"] = 0
        signals["active_development"] = False

    return {
        "agent": "code_repo_agent",
        "repo": os.path.basename(repo_path),
        "signals": signals
    }
