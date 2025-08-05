# # run_agents.py

# import os
# import json

# from agents.code_repo_agent import analyze_code_repo
# from agents.ml_ops_agent import analyze_ml_ops
# from agents.documentation_agent import analyze_docs
# from agents.dev_platform_agent import analyze_repo as analyze_dev_env

# REPO_BASE   = "external_repos"
# OUTPUT_FILE = "data/agent_outputs.json"

# os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# all_results = []

# for repo_dir in os.listdir(REPO_BASE):
#     path = os.path.join(REPO_BASE, repo_dir)
#     if not os.path.isdir(path):
#         continue

#     print(f"Scanning repository: {repo_dir}")
#     all_results.append(analyze_code_repo(path))
#     all_results.append(analyze_ml_ops(path))
#     all_results.append(analyze_docs(path))
#     all_results.append(analyze_dev_env(path))

# with open(OUTPUT_FILE, "w") as fp:
#     json.dump(all_results, fp, indent=2)

# print(f"\n✅ Agent scan complete. Results saved to {OUTPUT_FILE}")

#!/usr/bin/env python3
# run_agents.py

import os
import json
import warnings
from pathlib import Path

from agents.dev_platform_agent import analyze_repo as analyze_platform
from agents.dev_quality_agent import analyze_dev_and_innovation

warnings.filterwarnings("ignore", category=SyntaxWarning)

REPO_BASE   = "external_repos"
OUT1        = "data/dev_platform_outputs.json"
OUT2        = "data/dev_quality_outputs.json"

os.makedirs(Path(OUT1).parent, exist_ok=True)
os.makedirs(Path(OUT2).parent, exist_ok=True)

def find_git_repos(base: str):
    for root, dirs, _ in os.walk(base):
        if '.git' in dirs:
            yield root
            dirs.clear()

def main():
    repos = list(find_git_repos(REPO_BASE))
    print(f"🔍 Found {len(repos)} repos.\n")

    plat, qual = [], []
    for path in repos:
        name = Path(path).name
        print(f"→ Scanning {name}")
        plat.append(analyze_platform(path))
        qual.append(analyze_dev_and_innovation(path))

    with open(OUT1, 'w') as f1:
        json.dump(plat, f1, indent=2)
    print(f"✅ Dev-Platform → {OUT1}")

    with open(OUT2, 'w') as f2:
        json.dump(qual, f2, indent=2)
    print(f"✅ Dev-Quality  → {OUT2}")

if __name__ == "__main__":
    main()
