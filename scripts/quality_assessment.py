import os
import sys
import json
from pathlib import Path
from agents.dev_platform_agent import analyze_repo

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def assess_all_repos(base_dir: str):
    for entry in os.listdir(base_dir):
        repo_path = os.path.join(base_dir, entry)
        if not os.path.isdir(repo_path):
            continue
        signals = analyze_repo(repo_path)
        print(f"\n--- Assessment for {entry} ---")
        print(json.dumps(signals, indent=2))

if __name__ == "__main__":
    base = Path(__file__).parent.parent / "useful_repos"
    assess_all_repos(str(base))
