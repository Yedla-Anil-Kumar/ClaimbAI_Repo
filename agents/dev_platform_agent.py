from pathlib import Path
from typing import Any, Dict, List

from utils.file_utils    import list_all_files, list_source_files
from utils.code_analysis import (
    ast_metrics,
    detect_tests,
    detect_env,
    detect_ci,
    detect_cd,
    detect_experiments,
    scan_secrets
)
from utils.ml_insights import (
    detect_ml_frameworks,
    detect_data_pipeline_configs,
    detect_experiment_tracking,
    detect_model_training_scripts,
    detect_model_evaluation,
    detect_hyperparameter_configs,
    detect_data_validation,
    detect_feature_engineering,
    detect_model_export,
    detect_inference_endpoints,
    detect_nested_loops,
    detect_parallel_patterns
)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def calculate_scores(signals: Dict[str,Any], py_files: List[Path]) -> Dict[str,float]:
    # ─── Development Maturity ────────────────────────────────────
    s_cc   = clamp01(1 - (min(signals["avg_cyclomatic_complexity"],30)/30)**1.5)
    s_mi   = clamp01(signals["avg_maintainability_index"])
    s_doc  = clamp01(signals["docstring_coverage"])
    tc     = signals["test_file_count"]
    s_tests= clamp01(0.3*min(tc,10)/10 + 0.7*(tc/len(py_files) if py_files else 0))
    s_ci   = 1.0 if signals["ci_workflow_count"]>0 else 0.0
    s_cd   = 1.0 if signals["deploy_script_count"]>0 else 0.0
    env_bits=[signals["has_requirements"],signals["has_pipfile"],signals["has_env_yml"]]
    s_env  = sum(env_bits)/len(env_bits)
    s_sec  = 0.0 if signals["has_secrets"] else 1.0

    w = {"mi":0.25,"doc":0.15,"cc":0.10,"tests":0.20,"ci":0.08,"cd":0.08,"env":0.05,"sec":0.05}
    raw = (w["mi"]*s_mi + w["doc"]*s_doc + w["cc"]*s_cc +
           w["tests"]*s_tests + w["ci"]*s_ci + w["cd"]*s_cd +
           w["env"]*s_env + w["sec"]*s_sec)
    dev = round(raw*5,2)

    # Innovation
    s_exp   = 1.0 if signals["has_experiments"] else 0.0
    track   = sum(signals.get(f"uses_{t}",False) for t in ("mlflow","wandb","clearml"))
    s_track = clamp01(track/3 + (0.5 if track else 0))
    s_hyp   = 1.0 if signals["has_hyperparam_file"] or signals["uses_optuna"] or signals["uses_ray_tune"] else 0.0
    s_val   = 1.0 if any(signals.get(f"uses_{v}",False) for v in ("great_expectations","evidently","pandera")) else 0.0
    s_met   = 1.0 if signals.get("uses_metrics_library") else 0.0

    iw = {"exp":0.25,"track":0.30,"hparams":0.20,"valid":0.15,"metrics":0.10}
    raw2 = (iw["exp"]*s_exp + iw["track"]*s_track + iw["hparams"]*s_hyp +
            iw["valid"]*s_val + iw["metrics"]*s_met)
    innov = round(raw2*5,2)

    return {"development_maturity":dev, "innovation_pipeline":innov}

def analyze_repo(repo_path: str) -> Dict[str,Any]:
    root = Path(repo_path)
    # get only source .py for AST/ML detectors
    source_py = list(list_source_files(repo_path))
    # get all .py for tests, secrets, etc.
    # all_py    = [Path(f) for f in list_all_files(repo_path) if f.endswith(".py")]

    signals: Dict[str,Any] = {}
    # core
    signals.update(ast_metrics(source_py))
    signals.update(detect_tests(root))
    signals.update(detect_env(root))
    signals.update(detect_ci(root))
    signals.update(detect_cd(root))
    signals.update(detect_experiments(root))
    signals.update(scan_secrets(root))
    # ML-insights
    signals.update(detect_ml_frameworks(source_py))
    signals.update(detect_data_pipeline_configs(root, source_py))
    signals.update(detect_experiment_tracking(source_py))
    signals.update(detect_model_training_scripts(source_py))
    signals.update(detect_model_evaluation(source_py))
    signals.update(detect_hyperparameter_configs(root, source_py))
    signals.update(detect_data_validation(source_py))
    signals.update(detect_feature_engineering(source_py))
    signals.update(detect_model_export(source_py, root))
    signals.update(detect_inference_endpoints(source_py))
    signals.update(detect_parallel_patterns(source_py))
    signals.update(detect_nested_loops(source_py))

    scores = calculate_scores(signals, source_py)
    return {
        "agent":  "dev_platform_agent",
        "repo":   root.name,
        "signals":signals,
        "scores": scores
    }
