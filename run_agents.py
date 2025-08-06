import os
import json
import warnings
from pathlib import Path
from agents.dev_platform_agent import analyze_repo

warnings.filterwarnings("ignore", category=SyntaxWarning)

REPO_BASE = "useful_repos"
OUT_FILE  = "data/dev_platform_outputs.json"

os.makedirs(Path(OUT_FILE).parent, exist_ok=True)

def find_git_repos(base: str):
    for root, dirs, _ in os.walk(base):
        if ".git" in dirs:
            yield root
            dirs.clear()

def main():
    repos = list(find_git_repos(REPO_BASE))
    print(f"🔍 Found {len(repos)} repos.\n")

    results = []
    for p in repos:
        name = Path(p).name
        print(f"→ Scanning {name}")
        results.append(analyze_repo(p))

    with open(OUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Written to {OUT_FILE}")

if __name__ == "__main__":
    main()
