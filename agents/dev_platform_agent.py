import os
# import fnmatch
from utils.file_utils import list_all_files
from utils.code_analysis import (
    average_cyclomatic_complexity,
    maintainability_index,
    detect_ml_usage,
    detect_advanced_tech_usage
)

GOVERNANCE_ITEMS = [
    "README.md",
    "CHANGELOG.md",
    ".github/ISSUE_TEMPLATE.md",
    ".github/PULL_REQUEST_TEMPLATE.md"
]

# Threshold arrays for scoring (0–5)
# CC_THRESHOLDS   = [0, 5, 10, 20, 30] 
# MI_THRESHOLDS   = [100, 80, 60, 40, 20] 
# COUNT_THRESHOLDS= [0, 1, 2, 5, 10] 

def score_metric(value, thresholds, invert=False):
    """
    Map `value` into 0–5 based on `thresholds`.
    If invert=True, higher value → lower score.
    """
    for i, t in enumerate(thresholds):
        if (value <= t and not invert) or (value >= t and invert):
            return 5 - i
    return 0

def analyze_repo(repo_path: str) -> dict:
    """
    Scan local `repo_path` and return:
      - signals (raw metrics)
      - development_maturity (0–5)
      - innovation_pipeline (0–5)
    """
    files = list(list_all_files(repo_path))

    # Python files
    py_files = [f for f in files if f.endswith(".py")]

    # Code metrics
    avg_cc   = average_cyclomatic_complexity(py_files)
    avg_mi   = maintainability_index(py_files)
    uses_ml  = detect_ml_usage(py_files)
    adv_ml   = detect_advanced_tech_usage(py_files)

    # CI/CD and pipelines
    yaml_files = [f for f in files if f.endswith((".yml", ".yaml"))]
    ci_files   = [f for f in yaml_files if ".github" in f or "workflow" in os.path.basename(f).lower()]
    pipe_defs  = [f for f in yaml_files if "pipeline" in os.path.basename(f).lower()]

    # Tests
    test_files = [f for f in files if "/tests/" in f.lower() or os.path.basename(f).startswith("test_")]

    # Governance
    gov_count = sum(
        1 for item in GOVERNANCE_ITEMS
        if os.path.exists(os.path.join(repo_path, item))
    )

    # Notebooks & experiments
    nb_files = [f for f in files if f.endswith(".ipynb")]
    exp_dirs = [d for d in os.listdir(repo_path) if "experiment" in d.lower()]

    # Subscores
    # sc_cc    = score_metric(avg_cc, CC_THRESHOLDS, invert=True)
    # sc_mi    = score_metric(avg_mi, MI_THRESHOLDS)
    # sc_ci    = score_metric(len(ci_files), COUNT_THRESHOLDS)
    # sc_pipe  = score_metric(len(pipe_defs), COUNT_THRESHOLDS)
    # sc_gov   = min(gov_count, 5)
    # sc_adv   = 1 if adv_ml else 0

    # Dev Maturity composite: weights 25%,25%,20%,15%,15%
    # dev_maturity = round(
    #     sc_cc    * 0.25 +
    #     sc_mi    * 0.25 +
    #     sc_ci    * 0.20 +
    #     sc_pipe  * 0.15 +
    #     sc_gov   * 0.15,
    #     2
    # )

    # Innovation Pipeline: notebooks, ML usage, experiments
    # sc_nb    = 1 if nb_files else 0
    # sc_ml    = 1 if uses_ml else 0
    # sc_exp   = min(len(exp_dirs), 5)
    #innovation = round((sc_nb + sc_ml + sc_exp) / 3 * 5, 2)

    return {
        "agent": "dev_platform_agent",
        "repo": os.path.basename(repo_path),
        "signals": {
            "avg_cyclomatic_complexity": avg_cc,
            "avg_maintainability_index": avg_mi,
            "ci_cd_file_count": len(ci_files),
            "pipeline_definition_count": len(pipe_defs),
            "test_file_count": len(test_files),
            "governance_item_count": gov_count,
            "uses_standard_ml_frameworks": uses_ml,
            "uses_advanced_ml_tech": adv_ml,
            "notebook_count": len(nb_files),
            "experiment_folder_count": len(exp_dirs)
        },
        # "scores": {
        #     "development_maturity": dev_maturity,
        #     "innovation_pipeline": innovation
        # }
    }
