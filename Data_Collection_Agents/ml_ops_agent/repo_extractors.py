# # Data_Collection_Agents/ml_ops_agent/repo_extractors.py
# from __future__ import annotations
# import re
# from pathlib import Path
# from typing import Dict, List
# from utils.file_utils import list_all_files
# from .canonical import RepoEvidence

# # File types we bother to read (plus special names)
# ALLOWED_EXTS = (".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".txt", ".md", ".tf")
# SPECIAL_FILES = {"Dockerfile", "Jenkinsfile", "CODEOWNERS", "Chart.yaml", "Makefile"}

# MAX_BYTES_PER_TEXT = 100_000

# def _read_text(path: Path, max_bytes: int = MAX_BYTES_PER_TEXT) -> str:
#     try:
#         return path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
#     except Exception:
#         return ""

# def _norm(p: Path) -> str:
#     return str(p).replace("\\", "/")

# # --- Regex library (fast + maintainable) ---
# RE = {
#     # MLflow
#     "mlflow": re.compile(r"\bmlflow\b|MLproject|MLmodel|mlruns|MlflowClient", re.I),
#     "mlflow_uri": re.compile(r"mlflow\.set_tracking_uri\(['\"]([^'\"]+)['\"]\)", re.I),
#     "mlflow_registry": re.compile(r"register_model\(|model[-_ ]registry|mlflow\.models", re.I),

#     # SageMaker
#     "sm": re.compile(r"\bsagemaker\b|boto3\.client\(['\"]sagemaker['\"]\)", re.I),
#     "sm_endpoint": re.compile(r"create_endpoint|Model\s*\.\s*deploy|sage.*endpoint", re.I),
#     "sm_pipeline": re.compile(r"sagemaker\.workflow\.Pipeline|step\s*functions", re.I),
#     "sm_registry": re.compile(r"ModelPackage(Group)?|create_model_package", re.I),

#     # AzureML
#     "aml": re.compile(r"\bazure\.ai\.ml\b|mlclient|azureml:", re.I),
#     "aml_endpoint": re.compile(r"ManagedOnlineEndpoint|online-endpoint|endpoint:\s*azureml", re.I),
#     "aml_pipeline": re.compile(r"@dsl\.pipeline|pipeline:|ml\s+pipeline\s+create", re.I),
#     "aml_registry": re.compile(r"\bregistry\b.*(model|environment)|register.*azureml", re.I),

#     # Kubeflow
#     "kfp": re.compile(r"\bkfp\b|@dsl\.pipeline|@dsl\.component|kfp\.dsl", re.I),
#     "kfp_yaml": re.compile(r"apiVersion:\s*(argoproj\.io|tekton.dev)/", re.I),

#     # Tracking ecosystem
#     "wandb": re.compile(r"\bwandb\b", re.I),
#     "tb": re.compile(r"(tensorboard|SummaryWriter)", re.I),
#     "comet": re.compile(r"\bcomet_ml\b", re.I),
#     "neptune": re.compile(r"\bneptune\b", re.I),
#     "metrics_generic": re.compile(r"log_metric|log_metrics|\bmetrics\.json\b|\bmetrics\.csv\b", re.I),
#     "artifacts_generic": re.compile(r"log_artifact|artifacts?/|MLmodel|model\.(pkl|pt)|conda\.yaml|requirements\.txt", re.I),

#     # CI/CD workflow file locations
#     "gha_path": re.compile(r"\.github/workflows/.*\.(yml|yaml)$", re.I),
#     "gitlab_path": re.compile(r"\.gitlab-ci\.yml$", re.I),
#     "ado_path": re.compile(r"azure-pipelines\.(yml|yaml)$", re.I),
#     "circle_path": re.compile(r"\.circleci/config\.(yml|yaml)$", re.I),
#     "jenkins": re.compile(r"(?i)jenkinsfile$"),

#     # Common CI semantics
#     "cron": re.compile(r"cron:\s*['\"][^'\"]+['\"]|schedule_interval\s*=\s*['\"][^'\"]+['\"]|on:\s*schedule|@daily|@hourly", re.I),
#     "deploy_job": re.compile(r"\bdeploy\b|\bpromote\b|\brelease\b|\brollout\b", re.I),
#     "environment": re.compile(r"environment:\s*['\"]?(\w+)['\"]?", re.I),
#     "concurrency": re.compile(r"^\s*concurrency\s*:", re.I | re.M),
#     "rollback": re.compile(r"rollback|rollout\s+undo|canary|blue-?green|shadow", re.I),
#     "health": re.compile(r"health(check)?|smoke|readiness|liveness", re.I),

#     # Serving / endpoints
#     "serve": re.compile(r"\b(kserve|inference|serve|serving|endpoint)\b", re.I),
#     "fastapi": re.compile(r"\bFastAPI\(|\bfastapi\b", re.I),
#     "flask": re.compile(r"\bFlask\(|\bflask\b", re.I),

#     # Artifact lineage / integrity
#     "image_digest": re.compile(r"image:\s*\S+@sha256:[0-9a-f]{20,}", re.I),
#     "image_unpinned": re.compile(r"image:\s*\S+:(?!.*@sha256)[\w\.\-]+", re.I),  # tag without digest
#     "sbom": re.compile(r"\bsbom\b|cyclonedx|syft", re.I),
#     "sign": re.compile(r"\bcosign\b|sigstore|in-toto|attest", re.I),
#     "k8s_probe": re.compile(r"(readinessProbe|livenessProbe):", re.I),

#     # Monitoring / alerts
#     "monitoring_keys": re.compile(r"prometheus|alert(manager)?|azure\s*monitor|log\s*analytics|cloudwatch|alert\s*rule", re.I),
#     "alert_channels": re.compile(r"slack|webhook|pagerduty|ms\-teams|opsgenie", re.I),

#     # Validation / XAI / Bias
#     "shap": re.compile(r"\bshap\b|lime|captum", re.I),
#     "clarify": re.compile(r"\bclarify\b|fairness|bias", re.I),
#     "validation_files": re.compile(r"validation\.(json|ya?ml)|schema\.(json|ya?ml)", re.I),
#     "model_card": re.compile(r"model_card\.(md|mdx)", re.I),
#     "data_validation_libs": re.compile(r"great_expectations|evidently|pandera", re.I),

#     # Lineage practices
#     "git_sha": re.compile(r"(mlflow\.set_tag\(['\"]mlflow\.source\.git\.commit['\"]|git\s+rev-parse|GIT_SHA|mlflow\.log_param\(\s*['\"]git_sha)", re.I),
#     "data_ref": re.compile(r"(feature[_-]?store|data[_-]?ref|dataset[_-]?id|table:\s|s3://|abfs://|gs://)", re.I),
#     "env_lock": re.compile(r"(conda\.yaml|requirements\.txt|pip\-freeze|poetry\.lock)", re.I),

#     # Cost tagging
#     "tags_tf": re.compile(r"tags\s*=\s*{([^}]+)}", re.I | re.S),
#     "labels_yaml": re.compile(r"(labels|tags)\s*:\s*\n(\s+[A-Za-z0-9_\-]+: .+\n)+", re.I),

#     # SLO
#     "slo_doc": re.compile(r"slo\.(ya?ml)$", re.I),
#     "slo_env": re.compile(r"(AVAILABILITY_SLO|P95_MS_SLO|ERROR_RATE_SLO)\s*[:=]\s*[\d\.]+", re.I),
# }

# REQUIRED_POLICY_GATES = ["pytest", "integration", "bandit", "trivy", "bias", "data_validation"]


# def scan_repo(repo_path: str) -> RepoEvidence:
#     ev = RepoEvidence()
#     files: List[str] = list(list_all_files(repo_path))

#     for f in files:
#         p = Path(f)
#         name = _norm(p)
#         base = p.name

#         # Read only relevant files
#         if (p.suffix.lower() not in ALLOWED_EXTS) and (base not in SPECIAL_FILES):
#             continue

#         text = _read_text(p)

#         # ----- MLflow -----
#         if RE["mlflow"].search(text) or "MLproject" in name or "MLmodel" in name or "mlruns" in name:
#             ev.mlflow_hits.append(name)
#         for m in RE["mlflow_uri"].finditer(text):
#             ev.mlflow_tracking_uri_values.append(m.group(1))
#         if RE["mlflow_registry"].search(text):
#             ev.mlflow_registry_hits.append(name)

#         # ----- SageMaker -----
#         if RE["sm"].search(text): ev.sagemaker_hits.append(name)
#         if RE["sm_endpoint"].search(text): ev.sagemaker_endpoint_hits.append(name)
#         if RE["sm_pipeline"].search(text): ev.sagemaker_pipeline_hits.append(name)
#         if RE["sm_registry"].search(text): ev.sagemaker_registry_hits.append(name)

#         # ----- AzureML -----
#         if RE["aml"].search(text) or "azureml:" in text:
#             ev.azureml_hits.append(name)
#         if RE["aml_endpoint"].search(text): ev.azureml_endpoint_hits.append(name)
#         if RE["aml_pipeline"].search(text): ev.azureml_pipeline_hits.append(name)
#         if RE["aml_registry"].search(text): ev.azureml_registry_hits.append(name)

#         # ----- Kubeflow -----
#         if RE["kfp"].search(text): ev.kfp_hits.append(name)
#         if (p.suffix.lower() in (".yml", ".yaml")) and RE["kfp_yaml"].search(text):
#             ev.kfp_compiled_yaml.append(name)

#         # ----- Tracking tools -----
#         if RE["wandb"].search(text): ev.tracking_tools.append("wandb")
#         if RE["tb"].search(text): ev.tracking_tools.append("tensorboard")
#         if RE["comet"].search(text): ev.tracking_tools.append("comet_ml")
#         if RE["neptune"].search(text): ev.tracking_tools.append("neptune")
#         if "mlflow" in text.lower(): ev.tracking_tools.append("mlflow")
#         if RE["metrics_generic"].search(text): ev.tracking_metrics_signals.append(name)
#         if RE["artifacts_generic"].search(text): ev.tracking_artifact_signals.append(name)

#         # ----- CI/CD workflows -----
#         is_ci = any(RE[k].search(name) for k in ("gha_path", "gitlab_path", "ado_path", "circle_path", "jenkins"))
#         if is_ci:
#             ev.cicd_workflows.append(name)
#             ev.cicd_workflow_texts[name] = text
#             if RE["cron"].search(text):
#                 for m in RE["cron"].finditer(text):
#                     ev.cicd_schedules.append(m.group(0))
#             if RE["deploy_job"].search(text):
#                 for m in RE["deploy_job"].finditer(text):
#                     ev.cicd_deploy_job_names.append(m.group(0))
#             for m in RE["environment"].finditer(text):
#                 ev.cicd_environments.append(m.group(1).lower())
#             if RE["concurrency"].search(text): ev.cicd_concurrency_signals.append("concurrency")
#             if RE["rollback"].search(text): ev.cicd_rollback_signals.append("rollback")
#             if RE["health"].search(text): ev.cicd_healthcheck_signals.append("healthcheck")

#             low = text.lower()
#             ev.cicd_policy_gates.update({
#                 "pytest": ("pytest" in low),
#                 "integration": ("integration" in low),
#                 "bandit": ("bandit" in low),
#                 "trivy": ("trivy" in low),
#                 "bias": ("bias" in low or "clarify" in low),
#                 "data_validation": ("great_expectations" in low or "evidently" in low or "pandera" in low or "data_validation" in low),
#             })

#         if base == "CODEOWNERS":
#             ev.codeowners_present = True

#         # ----- Serving signals -----
#         if RE["serve"].search(text) or RE["fastapi"].search(text) or RE["flask"].search(text):
#             ev.serving_signals.append(name)

#         # ----- Manifests, rough heuristics -----
#         if "endpoint" in name.lower(): ev.endpoint_manifests.append(name)
#         if "pipeline" in name.lower() or "/pipelines/" in name.lower(): ev.pipeline_manifests.append(name)

#         # ----- Artifact lineage / integrity -----
#         for m in RE["image_digest"].finditer(text): ev.image_digest_pins.append(m.group(0))
#         for m in RE["image_unpinned"].finditer(text): ev.unpinned_images.append(m.group(0))
#         if RE["sbom"].search(text): ev.sbom_signals.append(name)
#         if RE["sign"].search(text): ev.signing_signals.append(name)
#         if RE["k8s_probe"].search(text): ev.k8s_probe_signals.append(name)

#         # ----- Monitoring / alerts -----
#         if RE["monitoring_keys"].search(text):
#             ev.monitoring_rule_files.append(name)
#             ev.monitoring_rule_texts[name] = text
#         if RE["alert_channels"].search(text):
#             ev.alert_channel_signals.append(name)

#         # ----- Validation / XAI / Bias -----
#         if RE["shap"].search(text): ev.explainability_signals.append(name)
#         if RE["clarify"].search(text): ev.bias_signals.append(name)
#         if RE["validation_files"].search(name) or RE["validation_files"].search(text):
#             ev.validation_schema_files.append(name)
#         if RE["model_card"].search(name) or RE["model_card"].search(text):
#             ev.model_card_files.append(name)
#         if RE["data_validation_libs"].search(text):
#             ev.data_validation_libs.append(name)

#         # ----- Lineage practices -----
#         if RE["git_sha"].search(text): ev.lineage_code_signals.append(name)
#         if RE["data_ref"].search(text): ev.data_ref_signals.append(name)
#         if RE["env_lock"].search(text): ev.env_lock_signals.append(name)

#         # ----- Cost tagging / attribution -----
#         for m in RE["tags_tf"].finditer(text):
#             blob = m.group(1)
#             for line in blob.splitlines():
#                 if "=" in line:
#                     key = line.strip().split("=")[0].strip().strip('"').strip("'")
#                     ev.iac_tag_keys_detected.append(key)
#                     ev.iac_tag_lines.append(line.strip())
#         if RE["labels_yaml"].search(text):
#             for line in text.splitlines():
#                 if ":" in line and (line.strip().startswith(("- ", "#")) is False):
#                     if any(line.strip().startswith(k) for k in ("labels", "tags")):
#                         continue
#                     k = line.strip().split(":")[0].strip()
#                     if len(k) and len(k) < 40:
#                         ev.iac_tag_keys_detected.append(k)

#         # ----- SLO declared -----
#         if RE["slo_doc"].search(name):
#             ev.slo_docs.append(name)
#             ev.slo_texts[name] = text
#         for m in RE["slo_env"].finditer(text):
#             ev.slo_env_vars.append(m.group(0))

#     # De-dup & tidy
#     ev.tracking_tools = sorted(set(ev.tracking_tools))
#     ev.cicd_environments = sorted(set(ev.cicd_environments))
#     ev.iac_tag_keys_detected = sorted(set(ev.iac_tag_keys_detected))
#     return ev
