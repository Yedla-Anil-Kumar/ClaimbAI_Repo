# utils/aimri_mapping.py
"""
Map raw scanner 'signals' to AIMRI-style maturity levels (0–5).

This module is a pure helper: given a `signals: Dict[str, Any]`, it returns
an `aimri_summary` dict with 12 dimensions, each as:
    {"level": int (0..5), "evidence": {...}}

It is defensive (missing keys default sensibly) and requires no other imports.
"""

from __future__ import annotations

from typing import Any, Dict


def _b(signals: Dict[str, Any], key: str) -> bool:
    return bool(signals.get(key, False))


def _f(signals: Dict[str, Any], key: str, default: float = 0.0) -> float:
    val = signals.get(key, default)
    try:
        return float(val)
    except Exception:
        return default


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _fraction_to_level(x: float) -> int:
    """
    Generic mapping from 0..1 fraction to a 0..5 level.
    Tuned to be readable and reasonably discriminative.
    """
    x = _clip01(x)
    if x < 0.20:
        return 0
    if x < 0.35:
        return 1
    if x < 0.50:
        return 2
    if x < 0.65:
        return 3
    if x < 0.80:
        return 4
    return 5


def compute_aimri_summary(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw signals into a 12-dim AIMRI-style summary.
    Levels are integers 0..5; 'evidence' echoes key facts used.
    """

    # 1) Code Health & Maintainability
    mi = _clip01(_f(signals, "avg_maintainability_index"))
    cc = _f(signals, "avg_cyclomatic_complexity")
    docs = _clip01(_f(signals, "docstring_coverage"))
    # invert complexity: assume CC 0..12+ as typical range
    s_cc = _clip01(1.0 - min(cc, 12.0) / 12.0)
    code_health_score = 0.5 * mi + 0.25 * s_cc + 0.25 * docs
    code_health_level = _fraction_to_level(code_health_score)

    # 2) Testing Rigor
    has_tests = _b(signals, "has_tests")
    test_files = int(signals.get("test_file_count", 0) or 0)
    coverage = _clip01(_f(signals, "test_coverage_estimate"))
    testing_quality = _clip01(_f(signals, "testing_quality"))
    if not has_tests:
        testing_level = 0
    else:
        base = max(coverage, testing_quality)
        lvl = _fraction_to_level(base)
        if test_files >= 5:
            lvl = min(5, lvl + 1)
        testing_level = lvl

    # 3) CI/CD Readiness
    ci_wf = int(signals.get("ci_workflow_count", 0) or 0)
    has_ci = _b(signals, "has_ci")
    deploy_scripts = int(signals.get("deploy_script_count", 0) or 0)
    has_deploy = _b(signals, "has_deploy_scripts") or (deploy_scripts > 0)
    if not has_ci and not has_deploy and ci_wf == 0 and deploy_scripts == 0:
        cicd_level = 0
    else:
        cicd_level = 2
        if has_ci or ci_wf > 0:
            cicd_level += 1
        if has_deploy or deploy_scripts > 0:
            cicd_level += 1
        cicd_level = min(5, cicd_level)

    # 4) Dependency & Environment Reproducibility
    has_req = _b(signals, "has_requirements") or _b(signals, "has_requirements.txt")
    has_pipfile = _b(signals, "has_pipfile")
    has_env = _b(signals, "has_env_yml")
    has_pyproject = _b(signals, "has_pyproject_toml")
    spec_count = sum([has_req, has_pipfile, has_env, has_pyproject])
    dep_quality = _clip01(_f(signals, "dependency_management_quality"))
    env_consistency = _clip01(_f(signals, "environment_consistency"))
    if spec_count == 0:
        env_level = 0
    elif spec_count == 1:
        env_level = 2
    else:
        env_level = 3
    if dep_quality >= 0.7:
        env_level += 1
    if env_consistency >= 0.7:
        env_level += 1
    env_level = min(5, env_level)

    # 5) Secret Hygiene
    has_secrets = _b(signals, "has_secrets")
    sec_score = _clip01(_f(signals, "security_score"))
    if has_secrets:
        secret_level = 0
    else:
        secret_level = 3
        if sec_score >= 0.8:
            secret_level = 5
        elif sec_score >= 0.5:
            secret_level = 4

    # 6) Experiment Tracking
    track_flags = sum(
        int(_b(signals, k))
        for k in ("uses_mlflow", "uses_wandb", "uses_clearml")
    )
    track_level = [0, 3, 4, 5][min(track_flags, 3)]

    # 7) Hyperparameter Optimization
    hpo_flags = sum(
        [
            int(_b(signals, "has_hyperparam_file")),
            int(_b(signals, "uses_optuna")),
            int(_b(signals, "uses_ray_tune")),
        ]
    )
    hpo_level = [0, 3, 4, 5][min(hpo_flags, 3)]

    # 8) Data Validation & Quality
    dv_flags = sum(
        int(_b(signals, k))
        for k in ("uses_great_expectations", "uses_evidently", "uses_pandera")
    )
    dv_level = [0, 3, 4, 5][min(dv_flags, 3)]

    # 9) Training & Evaluation Discipline
    train_scripts = int(signals.get("train_script_count", 0) or 0)
    has_entry = _b(signals, "has_entrypoint_training")
    uses_metrics = _b(signals, "uses_metrics_library")
    eval_scripts = int(signals.get("eval_script_count", 0) or 0)
    te_level = 0
    if train_scripts > 0:
        te_level += 2
    if has_entry:
        te_level += 1
    if uses_metrics:
        te_level += 1
    if eval_scripts > 0:
        te_level += 1
    te_level = min(5, te_level)

    # 10) Serving & Deployment for Inference
    has_api = any(
        _b(signals, k) for k in ("uses_fastapi", "uses_flask", "uses_streamlit")
    )
    has_export = any(
        _b(signals, k) for k in ("exports_torch_model", "exports_sklearn_model")
    )
    serving_level = 0
    if has_api:
        serving_level += 2
    if has_export:
        serving_level += 2
    if has_deploy:
        serving_level += 1
    serving_level = min(5, serving_level)

    # 11) Pipelines & Orchestration
    pipe_flags = sum(
        int(_b(signals, k))
        for k in ("has_airflow", "has_prefect", "has_luigi", "has_argo", "has_kedro")
    )
    pipeline_level = [0, 3, 4, 5][min(pipe_flags, 3)]

    # 12) Parallelism Readiness
    par_count = sum(
        int(_b(signals, k))
        for k in ("uses_threading", "uses_multiprocessing", "uses_concurrent")
    )
    parallel_level = min(5, par_count * 2)  # 0,2,4,6 -> capped at 5
    nested_loops = int(signals.get("nested_loop_files", 0) or 0)
    if nested_loops >= 3:
        parallel_level = max(0, parallel_level - 1)

    return {
        "code_health": {
            "level": code_health_level,
            "evidence": {"mi": mi, "cc": cc, "docs": docs},
        },
        "testing_rigor": {
            "level": testing_level,
            "evidence": {
                "has_tests": has_tests,
                "files": test_files,
                "coverage": coverage,
                "testing_quality": testing_quality,
            },
        },
        "ci_cd": {
            "level": cicd_level,
            "evidence": {
                "ci_workflows": ci_wf,
                "has_ci": has_ci,
                "deploy_scripts": deploy_scripts,
                "has_deploy_scripts": has_deploy,
            },
        },
        "env_reproducibility": {
            "level": env_level,
            "evidence": {
                "requirements": has_req,
                "pipfile": has_pipfile,
                "env_yml": has_env,
                "pyproject": has_pyproject,
                "dep_quality": dep_quality,
                "env_consistency": env_consistency,
            },
        },
        "secret_hygiene": {
            "level": secret_level,
            "evidence": {"has_secrets": has_secrets, "security_score": sec_score},
        },
        "experiment_tracking": {
            "level": track_level,
            "evidence": {
                "mlflow": _b(signals, "uses_mlflow"),
                "wandb": _b(signals, "uses_wandb"),
                "clearml": _b(signals, "uses_clearml"),
            },
        },
        "hpo": {
            "level": hpo_level,
            "evidence": {
                "hparam_file": _b(signals, "has_hyperparam_file"),
                "optuna": _b(signals, "uses_optuna"),
                "ray_tune": _b(signals, "uses_ray_tune"),
            },
        },
        "data_validation": {
            "level": dv_level,
            "evidence": {
                "great_expectations": _b(signals, "uses_great_expectations"),
                "evidently": _b(signals, "uses_evidently"),
                "pandera": _b(signals, "uses_pandera"),
            },
        },
        "training_eval": {
            "level": te_level,
            "evidence": {
                "train_scripts": train_scripts,
                "entrypoint": has_entry,
                "metrics_lib": uses_metrics,
                "eval_scripts": eval_scripts,
            },
        },
        "serving_deploy": {
            "level": serving_level,
            "evidence": {
                "fastapi": _b(signals, "uses_fastapi"),
                "flask": _b(signals, "uses_flask"),
                "streamlit": _b(signals, "uses_streamlit"),
                "export_torch": _b(signals, "exports_torch_model"),
                "export_sklearn": _b(signals, "exports_sklearn_model"),
                "deploy_scripts": has_deploy,
            },
        },
        "pipelines": {
            "level": pipeline_level,
            "evidence": {
                "airflow": _b(signals, "has_airflow"),
                "prefect": _b(signals, "has_prefect"),
                "luigi": _b(signals, "has_luigi"),
                "argo": _b(signals, "has_argo"),
                "kedro": _b(signals, "has_kedro"),
            },
        },
        "parallelism": {
            "level": parallel_level,
            "evidence": {
                "threading": _b(signals, "uses_threading"),
                "multiprocessing": _b(signals, "uses_multiprocessing"),
                "concurrent": _b(signals, "uses_concurrent"),
                "nested_loop_files": nested_loops,
            },
        },
    }
