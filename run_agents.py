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


import os
import json
from agents.dev_platform_agent import analyze_repo
from agents.dev_quality_agent import analyze_dev_and_innovation
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

REPO_BASE   = "external_repos"
OUTPUT_FILE = "data/dev_platform_outputs.json"
OUTPUT_FILE2 = "data/dev_quality_outputs.json"


os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def find_git_repos(base_path):
    """
    Recursively find all directories under `base_path` that contain a `.git` subdirectory.
    Returns a list of absolute paths to the repo roots.
    """
    repos = []
    for root, dirs, files in os.walk(base_path):
        if ".git" in dirs:
            repos.append(root)
            dirs.clear()
    return repos

def main():
    repo_paths = find_git_repos(REPO_BASE)
    print(f"🔍 Found {len(repo_paths)} repositories under '{REPO_BASE}'\n")

    results = []
    results2 = []
    for path in repo_paths:
        name = os.path.basename(path)
        print(f"→ Scanning '{name}' at: {path}")
        out = analyze_repo(path)
        out2 = analyze_dev_and_innovation(path)
        results2.append(out2)
        results.append(out)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n Scan complete — results written to '{OUTPUT_FILE}'")

    with open(OUTPUT_FILE2, "w") as f:
        json.dump(results2, f, indent=2)
    print(f"\n Scan complete — results written to '{OUTPUT_FILE2}'")



if __name__ == "__main__":
    main()

