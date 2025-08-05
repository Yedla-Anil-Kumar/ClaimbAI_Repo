import os
from utils.file_utils import list_all_files

def analyze_ml_ops(repo_path: str) -> dict:
    files = list(list_all_files(repo_path))
    signals = {
        "uses_mlflow": any("mlflow" in f.lower() for f in files),
        "uses_dvc": any("dvc.yaml" in f.lower() for f in files),
        "has_ci_cd": any(".github/workflows" in f for f in files),
        "model_folder_exists": any("/model" in f or "/models" in f for f in files),
    }
    return {
        "agent": "ml_ops_agent",
        "repo": os.path.basename(repo_path),
        "signals": signals
    }
