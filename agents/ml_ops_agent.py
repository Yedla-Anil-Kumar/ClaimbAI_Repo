# # agents/ml_ops_agent.py
# """
# ML Ops Agent

# Analyzes a repository for MLOps-readiness indicators:
# - orchestration/workflow tools
# - model serving endpoints
# - containerization and deployment configs
# - infrastructure as code (Terraform/Helm/Kustomize)
# - data versioning
# - experiment tracking / model registry hints
# - cloud integrations and managed ML services
# - monitoring/observability hooks
# - feature stores
# - batch/stream processing frameworks

# Returns a `signals` dictionary and two scores:
# - ml_ops_readiness (0–5)
# - production_deployability (0–5)

# This agent is static (no network/LLM), fast, and conservative:
# it looks for imports and well-known file artifacts.
# """

# from __future__ import annotations

# import ast
# import fnmatch
# from pathlib import Path
# from typing import Any, Dict, Iterable, List, Optional, Set

# from utils.file_utils import list_all_files, list_source_files


# # ──────────────────────────────────────────────────────────────────────────────
# # Configurable catalogs (kept in one place; add to these lists as needed)
# # ──────────────────────────────────────────────────────────────────────────────

# ORCHESTRATORS = {
#     "airflow": {"imports": {"airflow"}, "dirs": {"dags"}, "files": set()},
#     "prefect": {"imports": {"prefect"}, "dirs": {"flows", "src/flows"}, "files": set()},
#     "luigi": {"imports": {"luigi"}, "dirs": {"tasks", "src/tasks"}, "files": set()},
#     "dagster": {"imports": {"dagster"}, "dirs": set(), "files": set()},
#     "flyte": {"imports": {"flytekit"}, "dirs": set(), "files": set()},
#     "kubeflow": {"imports": {"kfp"}, "dirs": set(), "files": {"pipeline.yaml", "pipeline.yml"}},
# }

# SERVING = {
#     "fastapi": {"imports": {"fastapi"}, "files": set()},
#     "flask": {"imports": {"flask"}, "files": set()},
#     "bentoml": {"imports": {"bentoml"}, "files": {"bentofile.yaml", "bentofile.yml"}},
#     "seldon": {"imports": {"seldon_core"}, "files": set()},
#     "kserve": {"imports": {"kserve"}, "files": set()},
#     "ray_serve": {"imports": {"ray"}, "files": set()},
#     "torchserve": {"imports": set(), "files": {"model_store", "config.properties"}},
#     "tf_serving": {"imports": set(), "files": set()},
# }

# FEATURE_STORES = {
#     "feast": {"imports": {"feast"}, "files": {"feature_store.yaml", "feature_store.yml"}},
#     "tecton": {"imports": {"tecton"}, "files": set()},
# }

# EXPERIMENT_TRACKING = {
#     "mlflow": {"imports": {"mlflow"}, "files": {"mlruns"}},
#     "wandb": {"imports": {"wandb"}, "files": {"wandb"}},
#     "clearml": {"imports": {"clearml"}, "files": set()},
#     "tensorboard": {"imports": {"tensorboard"}, "files": set()},
# }

# DATA_VERSIONING = {
#     "dvc": {"imports": {"dvc"}, "files": {"dvc.yaml", "dvc.yml", ".dvc"}},
#     "lakefs": {"imports": {"lakefs"}, "files": set()},
#     "pachyderm": {"imports": {"pachyderm"}, "files": set()},
#     "git_lfs": {"imports": set(), "files": {".gitattributes"}},
# }

# INFRA_AS_CODE = {
#     "terraform": {"glob": "*.tf"},
#     "helm": {"files": {"Chart.yaml", "Chart.yml"}},
#     "kustomize": {"files": {"kustomization.yaml", "kustomization.yml"}},
#     "pulumi": {"imports": {"pulumi"}},
# }

# CONTAINERIZATION = {
#     "dockerfile": {"files": {"Dockerfile", "dockerfile"}},
#     "compose": {"files": {"docker-compose.yml", "docker-compose.yaml"}},
#     "kubernetes": {"dir_hints": {"k8s", "kubernetes", "manifests"}},
# }

# MONITORING = {
#     "prometheus": {"files": {"prometheus.yml", "prometheus.yaml"}, "imports": {"prometheus_client"}},
#     "grafana": {"dir_hints": {"grafana"}},
#     "opentelemetry": {"imports": {"opentelemetry"}},
#     "evidently": {"imports": {"evidently"}},
#     "sentry": {"imports": {"sentry_sdk"}},
# }

# CLOUD = {
#     "aws": {"imports": {"boto3", "sagemaker"}},
#     "gcp": {"imports": {"google.cloud"}},
#     "azure": {"imports": {"azure"}},
# }

# BATCH_STREAM = {
#     "spark": {"imports": {"pyspark"}, "files": set()},
#     "beam": {"imports": {"apache_beam"}, "files": set()},
#     "ray": {"imports": {"ray"}, "files": set()},
# }

# MODEL_REGISTRY_HINTS = {
#     "mlflow_registry": {"imports": {"mlflow"}, "text_hints": {"ModelRegistry", "register_model("}},
#     "sagemaker_registry": {"imports": {"sagemaker"}, "text_hints": {"ModelPackageGroup", "create_model_package("}},
# }

# MODEL_EXPORT = {
#     "torch_save": {"calls": [("torch", "save")]},
#     "sklearn_joblib": {"calls": [("joblib", "dump")]},
#     "pickle": {"calls": [("pickle", "dump")]},
#     "onnx": {"imports": {"onnx"}},
# }


# # ──────────────────────────────────────────────────────────────────────────────
# # AST helpers
# # ──────────────────────────────────────────────────────────────────────────────

# def _safe_parse(path: Path) -> Optional[ast.AST]:
#     """Parse a Python file safely; return None on failure."""
#     try:
#         return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
#     except Exception:
#         return None


# def _detect_imports(tree: ast.AST) -> Dict[str, Set[str]]:
#     """Return {'top_level': {...}, 'full_paths': {...}} imports from AST."""
#     top, full = set(), set()
#     for node in ast.walk(tree):
#         if isinstance(node, ast.Import):
#             for a in node.names:
#                 top.add(a.name.split(".", 1)[0])
#         elif isinstance(node, ast.ImportFrom) and node.module:
#             mod = node.module
#             full.add(mod)
#             top.add(mod.split(".", 1)[0])
#     return {"top_level": top, "full_paths": full}


# # ──────────────────────────────────────────────────────────────────────────────
# # Detectors
# # ──────────────────────────────────────────────────────────────────────────────

# def _file_index(repo_path: str) -> Dict[str, Any]:
#     """Build lightweight file indexes for quick lookups."""
#     root = Path(repo_path)
#     files = list(list_all_files(repo_path))
#     names = {Path(f).name for f in files}
#     dirs = {p.name for p in root.glob("*") if p.is_dir()}
#     lower_dirs = {d.lower() for d in dirs}
#     return {"files": files, "names": names, "dirs": dirs, "lower_dirs": lower_dirs}


# def _scan_ast_signals(py_files: List[Path]) -> Dict[str, Any]:
#     """Collect AST-based signals in one pass."""
#     imports: Set[str] = set()
#     full_imports: Set[str] = set()
#     calls: Set[str] = set()

#     for path in py_files:
#         tree = _safe_parse(path)
#         if not tree:
#             continue
#         imps = _detect_imports(tree)
#         imports |= imps["top_level"]
#         full_imports |= imps["full_paths"]

#         for node in ast.walk(tree):
#             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
#                 if isinstance(node.func.value, ast.Name):
#                     calls.add(f"{node.func.value.id}.{node.func.attr}")
#     return {"imports": imports, "full_imports": full_imports, "calls": calls}


# def _match_catalog_by_imports(
#     catalog: Dict[str, Dict[str, Any]], imports: Set[str], full: Set[str]
# ) -> Dict[str, bool]:
#     found: Dict[str, bool] = {}
#     for key, spec in catalog.items():
#         wanted = spec.get("imports", set())
#         if not wanted:
#             found[key] = False
#             continue
#         present = any(
#             (w in imports) or any(fp.startswith(w) for fp in full) for w in wanted
#         )
#         found[key] = bool(present)
#     return found


# def _match_catalog_by_files(
#     catalog: Dict[str, Dict[str, Any]], idx: Dict[str, Any]
# ) -> Dict[str, bool]:
#     found: Dict[str, bool] = {}
#     names = idx["names"]
#     dirs = idx["dirs"]
#     lower_dirs = idx["lower_dirs"]

#     for key, spec in catalog.items():
#         hit = False
#         for f in spec.get("files", set()):
#             if f in names or f in dirs:
#                 hit = True
#                 break
#         for d in spec.get("dir_hints", set()):
#             if d in lower_dirs:
#                 hit = True
#                 break
#         found[key] = hit
#     return found


# def _count_glob(files: Iterable[str], pattern: str) -> int:
#     return sum(1 for f in files if fnmatch.fnmatch(Path(f).name, pattern))


# def _detect_orchestrators(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, bool]:
#     by_imp = _match_catalog_by_imports(ORCHESTRATORS, asts["imports"], asts["full_imports"])
#     by_fs = _match_catalog_by_files(ORCHESTRATORS, idx)
#     return {f"has_{k}": (by_imp.get(k, False) or by_fs.get(k, False)) for k in ORCHESTRATORS}


# def _detect_serving(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, bool]:
#     by_imp = _match_catalog_by_imports(SERVING, asts["imports"], asts["full_imports"])
#     by_fs = _match_catalog_by_files(SERVING, idx)
#     return {f"uses_{k}": (by_imp.get(k, False) or by_fs.get(k, False)) for k in SERVING}


# def _detect_feature_stores(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, bool]:
#     by_imp = _match_catalog_by_imports(FEATURE_STORES, asts["imports"], asts["full_imports"])
#     by_fs = _match_catalog_by_files(FEATURE_STORES, idx)
#     return {f"uses_{k}": (by_imp.get(k, False) or by_fs.get(k, False)) for k in FEATURE_STORES}


# def _detect_tracking(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, bool]:
#     by_imp = _match_catalog_by_imports(EXPERIMENT_TRACKING, asts["imports"], asts["full_imports"])
#     by_fs = _match_catalog_by_files(EXPERIMENT_TRACKING, idx)
#     return {f"uses_{k}": (by_imp.get(k, False) or by_fs.get(k, False)) for k in EXPERIMENT_TRACKING}


# def _detect_data_versioning(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, bool]:
#     out: Dict[str, bool] = {}
#     by_fs = _match_catalog_by_files(DATA_VERSIONING, idx)
#     by_imp = _match_catalog_by_imports(DATA_VERSIONING, asts["imports"], asts["full_imports"])

#     # git-lfs: detect via .gitattributes filter
#     git_lfs = False
#     if ".gitattributes" in idx["names"]:
#         try:
#             root = Path(next(Path(f).parent for f in idx["files"] if Path(f).name == ".gitattributes"))
#         except StopIteration:
#             root = None
#         for f in idx["files"]:
#             if Path(f).name == ".gitattributes":
#                 try:
#                     txt = Path(f).read_text(encoding="utf-8", errors="ignore")
#                     if "filter=lfs" in txt:
#                         git_lfs = True
#                         break
#                 except Exception:
#                     pass

#     for key in DATA_VERSIONING:
#         if key == "git_lfs":
#             out["uses_git_lfs"] = git_lfs
#         else:
#             out[f"uses_{key}"] = bool(by_fs.get(key, False) or by_imp.get(key, False))
#     return out


# def _detect_infra_as_code(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, Any]:
#     files = idx["files"]
#     tf_count = _count_glob(files, "*.tf")
#     helm = any(n in idx["names"] for n in INFRA_AS_CODE["helm"]["files"])
#     kust = any(n in idx["names"] for n in INFRA_AS_CODE["kustomize"]["files"])
#     pulumi = any(
#         (w in asts["imports"]) or any(fp.startswith(w) for fp in asts["full_imports"])
#         for w in INFRA_AS_CODE["pulumi"]["imports"]
#     )
#     return {
#         "terraform_file_count": tf_count,
#         "has_helm": helm,
#         "has_kustomize": kust,
#         "uses_pulumi": pulumi,
#     }


# def _detect_containerization(idx: Dict[str, Any]) -> Dict[str, Any]:
#     names = idx["names"]
#     dirs = idx["lower_dirs"]
#     return {
#         "has_dockerfile": any(n.lower() in {"dockerfile"} for n in names),
#         "has_docker_compose": any(n in {"docker-compose.yml", "docker-compose.yaml"} for n in names),
#         "has_k8s_manifests": any(h in dirs for h in CONTAINERIZATION["kubernetes"]["dir_hints"]),
#     }


# def _detect_monitoring(idx: Dict[str, Any], asts: Dict[str, Any]) -> Dict[str, Any]:
#     names = idx["names"]
#     dirs = idx["lower_dirs"]
#     prom = any(n in MONITORING["prometheus"]["files"] for n in names) or (
#         "prometheus_client" in asts["imports"]
#     )
#     grafana = any("grafana" in dirs for _ in [0])  # dir hint
#     otel = any(
#         (w in asts["imports"]) or any(fp.startswith(w) for fp in asts["full_imports"])
#         for w in MONITORING["opentelemetry"]["imports"]
#     )
#     evidently = "evidently" in asts["imports"] or any(fp.startswith("evidently") for fp in asts["full_imports"])
#     sentry = "sentry_sdk" in asts["imports"]
#     return {
#         "uses_prometheus": prom,
#         "uses_grafana": grafana,
#         "uses_opentelemetry": otel,
#         "uses_evidently": evidently,
#         "uses_sentry": sentry,
#     }


# def _detect_cloud(asts: Dict[str, Any]) -> Dict[str, bool]:
#     def present(keys: Set[str]) -> bool:
#         return any((k in asts["imports"]) or any(fp.startswith(k) for fp in asts["full_imports"]) for k in keys)

#     return {
#         "uses_aws": present(CLOUD["aws"]["imports"]),
#         "uses_gcp": present(CLOUD["gcp"]["imports"]),
#         "uses_azure": present(CLOUD["azure"]["imports"]),
#         "uses_sagemaker": ("sagemaker" in asts["imports"]),
#     }


# def _detect_batch_stream(asts: Dict[str, Any]) -> Dict[str, bool]:
#     return {
#         "uses_spark": ("pyspark" in asts["imports"]),
#         "uses_beam": ("apache_beam" in asts["imports"]),
#         "uses_ray": ("ray" in asts["imports"]) or any(fp.startswith("ray.") for fp in asts["full_imports"]),
#     }


# def _detect_model_registry_hints(py_files: List[Path]) -> Dict[str, bool]:
#     hints = {"mlflow_model_registry_hints": False, "sagemaker_model_registry_hints": False}
#     for path in py_files:
#         try:
#             txt = path.read_text(encoding="utf-8", errors="ignore")
#         except Exception:
#             continue
#         if any(h in txt for h in MODEL_REGISTRY_HINTS["mlflow_registry"]["text_hints"]):
#             hints["mlflow_model_registry_hints"] = True
#         if any(h in txt for h in MODEL_REGISTRY_HINTS["sagemaker_registry"]["text_hints"]):
#             hints["sagemaker_model_registry_hints"] = True
#         if all(hints.values()):
#             break
#     return hints


# def _detect_model_export(py_files: List[Path], asts: Dict[str, Any]) -> Dict[str, bool]:
#     calls = asts["calls"]
#     onnx = "onnx" in asts["imports"] or any(fp.startswith("onnx") for fp in asts["full_imports"])
#     return {
#         "exports_torch_model": ("torch.save" in calls),
#         "exports_sklearn_model": ("joblib.dump" in calls),
#         "exports_pickle": ("pickle.dump" in calls),
#         "exports_onnx": onnx,
#     }


# # ──────────────────────────────────────────────────────────────────────────────
# # Scoring
# # ──────────────────────────────────────────────────────────────────────────────

# def _clamp01(x: float) -> float:
#     return 0.0 if x < 0 else 1.0 if x > 1 else x


# def _score_ml_ops(signals: Dict[str, Any]) -> Dict[str, float]:
#     """Compute two 0–5 scores."""
#     # Readiness components
#     s_orch = 1.0 if any(signals.get(f"has_{k}") for k in ORCHESTRATORS) else 0.0
#     s_track = 1.0 if any(signals.get(f"uses_{k}") for k in EXPERIMENT_TRACKING) else 0.0
#     s_version = 1.0 if any(v for k, v in signals.items() if k.startswith("uses_dvc") or k.startswith("uses_lakefs")
#                            or k.startswith("uses_pachyderm") or k == "uses_git_lfs") else 0.0
#     s_feat = 1.0 if any(signals.get(f"uses_{k}") for k in FEATURE_STORES) else 0.0
#     s_batch = 1.0 if any(signals.get(k) for k in ("uses_spark", "uses_beam", "uses_ray")) else 0.0

#     # Deployability components
#     s_container = 1.0 if any(signals.get(k) for k in ("has_dockerfile", "has_docker_compose")) else 0.0
#     s_k8s = 1.0 if signals.get("has_k8s_manifests") or signals.get("has_helm") or signals.get("has_kustomize") else 0.0
#     s_serving = 1.0 if any(signals.get(f"uses_{k}") for k in SERVING) else 0.0
#     s_cloud = 1.0 if any(signals.get(k) for k in ("uses_aws", "uses_gcp", "uses_azure", "uses_sagemaker")) else 0.0
#     s_monitor = 1.0 if any(signals.get(k) for k in ("uses_prometheus", "uses_grafana",
#                                                      "uses_opentelemetry", "uses_evidently", "uses_sentry")) else 0.0
#     s_registry = 1.0 if any(signals.get(k) for k in ("mlflow_model_registry_hints",
#                                                       "sagemaker_model_registry_hints")) else 0.0

#     w_ready = {"orch": 0.30, "track": 0.25, "version": 0.20, "feature": 0.15, "batch": 0.10}
#     w_deploy = {"container": 0.25, "k8s": 0.20, "serving": 0.25, "cloud": 0.15, "monitor": 0.10, "registry": 0.05}

#     ml_ops_readiness = 5.0 * (
#         w_ready["orch"] * s_orch +
#         w_ready["track"] * s_track +
#         w_ready["version"] * s_version +
#         w_ready["feature"] * s_feat +
#         w_ready["batch"] * s_batch
#     )

#     production_deployability = 5.0 * (
#         w_deploy["container"] * s_container +
#         w_deploy["k8s"] * s_k8s +
#         w_deploy["serving"] * s_serving +
#         w_deploy["cloud"] * s_cloud +
#         w_deploy["monitor"] * s_monitor +
#         w_deploy["registry"] * s_registry
#     )

#     return {
#         "ml_ops_readiness": round(_clamp01(ml_ops_readiness / 5.0) * 5.0, 2),
#         "production_deployability": round(_clamp01(production_deployability / 5.0) * 5.0, 2),
#     }


# # ──────────────────────────────────────────────────────────────────────────────
# # Public entrypoint
# # ──────────────────────────────────────────────────────────────────────────────

# def analyze_ml_ops(repo_path: str) -> Dict[str, Any]:
#     """
#     Analyze a repository for MLOps signals.

#     Parameters
#     ----------
#     repo_path : str
#         Root of the local git repository.

#     Returns
#     -------
#     Dict[str, Any]
#         {
#           "agent": "ml_ops_agent",
#           "repo": "<name>",
#           "signals": {...},
#           "scores": {
#               "ml_ops_readiness": float,
#               "production_deployability": float
#           }
#         }
#     """
#     root = Path(repo_path)
#     py_files: List[Path] = list(list_source_files(repo_path))
#     idx = _file_index(repo_path)
#     asts = _scan_ast_signals(py_files)

#     signals: Dict[str, Any] = {}
#     # Orchestration / workflows
#     signals.update(_detect_orchestrators(idx, asts))
#     # Serving
#     signals.update(_detect_serving(idx, asts))
#     # Feature store
#     signals.update(_detect_feature_stores(idx, asts))
#     # Experiment tracking
#     signals.update(_detect_tracking(idx, asts))
#     # Data versioning
#     signals.update(_detect_data_versioning(idx, asts))
#     # Infra as code
#     signals.update(_detect_infra_as_code(idx, asts))
#     # Containerization
#     signals.update(_detect_containerization(idx))
#     # Monitoring / observability
#     signals.update(_detect_monitoring(idx, asts))
#     # Cloud integrations
#     signals.update(_detect_cloud(asts))
#     # Batch/stream processing
#     signals.update(_detect_batch_stream(asts))
#     # Model registry hints
#     signals.update(_detect_model_registry_hints(py_files))
#     # Model export patterns
#     signals.update(_detect_model_export(py_files, asts))

#     scores = _score_ml_ops(signals)

#     return {
#         "agent": "ml_ops_agent",
#         "repo": root.name,
#        # "signals": signals,
#         "scores": scores,
#     }


# if __name__ == "__main__":
#     # Tiny manual test:
#     # python -m agents.ml_ops_agent /path/to/repo
#     import sys as _sys

#     if len(_sys.argv) < 2:
#         print("Usage: python -m agents.ml_ops_agent <repo_path>")
#         raise SystemExit(2)

#     result_ = analyze_ml_ops(_sys.argv[1])
#     import json as _json

#     print(_json.dumps(result_, indent=2))
