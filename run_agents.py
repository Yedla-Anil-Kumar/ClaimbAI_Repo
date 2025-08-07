#!/usr/bin/env python3
import os
import json
import warnings
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from agents.dev_platform_agent import analyze_repo

warnings.filterwarnings("ignore", category=SyntaxWarning)

REPO_BASE = "useful_repos"
OUT_FILE  = "data/dev_platform_outputs.json"
MAX_WORKERS = os.cpu_count() or 4  # adjust if you want fewer/more processes

def find_git_repos(base: str):
    for root, dirs, _ in os.walk(base):
        if ".git" in dirs:
            yield root
            dirs.clear()

def main():
    os.makedirs(Path(OUT_FILE).parent, exist_ok=True)
    repos = list(find_git_repos(REPO_BASE))
    print(f"🔍 Found {len(repos)} repos.\n")

    results = []
    # Use a process pool to analyze each repo in parallel
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # schedule all jobs
        future_to_repo = {
            executor.submit(analyze_repo, repo_path): repo_path
            for repo_path in repos
        }
        # collect results as they complete
        for future in as_completed(future_to_repo):
            repo_path = future_to_repo[future]
            name = Path(repo_path).name
            try:
                result = future.result()
                print(f"✅ Scanned {name}")
                results.append(result)
            except Exception as e:
                print(f"❌ Error scanning {name}: {e}")

    # write out all results
    with open(OUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Written to {OUT_FILE}")

if __name__ == "__main__":
    main()
