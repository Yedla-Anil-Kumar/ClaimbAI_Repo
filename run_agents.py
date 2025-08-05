import os
import json

from agents.code_repo_agent import analyze_code_repo
from agents.ml_ops_agent import analyze_ml_ops
from agents.documentation_agent import analyze_docs
from agents.dev_quality_agent import analyze_dev_and_innovation

REPO_BASE   = "external_repos"
OUTPUT_FILE = "data/agent_outputs.json"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

results = []
for repo in os.listdir(REPO_BASE):
    path = os.path.join(REPO_BASE, repo)
    if not os.path.isdir(path):
        continue
    print(f"Scanning {repo}...")
    results.append(analyze_code_repo(path))
    results.append(analyze_ml_ops(path))
    results.append(analyze_docs(path))
    results.append(analyze_dev_and_innovation(path))

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"Results written to {OUTPUT_FILE}")
