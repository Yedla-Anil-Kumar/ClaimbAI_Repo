# # Data_Collection_Agents/ml_ops_agent/metrics_engine.py
# from __future__ import annotations
# from typing import Dict, List
# from .canonical import RepoEvidence

# def _bool(x) -> bool: return bool(x)

# # ---------- Platform proxies (unchanged spirit) ----------
# def mlflow_proxy_metrics(ev: RepoEvidence) -> Dict:
#     return {
#         "uses_mlflow": _bool(ev.mlflow_hits),
#         "tracking_endpoints": list(sorted(set(ev.mlflow_tracking_uri_values)))[:3],
#         "experiments_count": max(1, len(ev.mlflow_hits)//10) if ev.mlflow_hits else 0,   # proxy only
#         "registered_models_count": len(ev.mlflow_registry_hits),
#     }

# def sagemaker_proxy_metrics(ev: RepoEvidence) -> Dict:
#     return {
#         "uses_sagemaker": _bool(ev.sagemaker_hits),
#         "training_jobs_count": max(0, len(ev.sagemaker_hits)//15),
#         "endpoints_count": len(ev.sagemaker_endpoint_hits),
#         "pipelines_count": len(ev.sagemaker_pipeline_hits),
#         "registry_usage": _bool(ev.sagemaker_registry_hits),
#     }

# def azureml_proxy_metrics(ev: RepoEvidence) -> Dict:
#     return {
#         "uses_azureml": _bool(ev.azureml_hits),
#         "jobs_count": max(0, len(ev.azureml_hits)//15),
#         "endpoints_count": len(ev.azureml_endpoint_hits),
#         "pipelines_count": len(ev.azureml_pipeline_hits),
#         "registry_usage": _bool(ev.azureml_registry_hits),
#     }

# def kubeflow_proxy_metrics(ev: RepoEvidence) -> Dict:
#     return {
#         "uses_kubeflow": _bool(ev.kfp_hits),
#         "pipelines_count": max(len(ev.kfp_hits)//2, len(ev.kfp_compiled_yaml)),
#         "components_count": max(0, len(ev.kfp_hits)),
#         "manifests_present": _bool(ev.kfp_compiled_yaml),
#     }

# def tracking_proxy_metrics(ev: RepoEvidence) -> Dict:
#     metrics_logged = bool(ev.tracking_metrics_signals)
#     artifacts_logged = bool(ev.tracking_artifact_signals)
#     runs_quality = 0.0
#     if metrics_logged and artifacts_logged: runs_quality = 0.7
#     if "mlflow" in ev.tracking_tools and any(t in ev.tracking_tools for t in ("wandb","tensorboard")):
#         runs_quality = max(runs_quality, 0.85)
#     coverage = (0.4 if metrics_logged else 0.0) + (0.4 if artifacts_logged else 0.0) + (0.2 if ev.tracking_tools else 0.0)
#     return {
#         "tools": [{"name": n, "usage": "moderate"} for n in sorted(set(ev.tracking_tools))],
#         "metrics_logged": metrics_logged,
#         "artifacts_logged": artifacts_logged,
#         "runs_structure_quality": round(min(1.0, runs_quality), 2),
#         "coverage": round(min(1.0, coverage), 2),
#     }

# def automation_proxy_metrics(ev: RepoEvidence) -> Dict:
#     orchestrators: List[str] = []
#     if any("airflow" in p for p in ev.pipeline_manifests): orchestrators.append("airflow")
#     if ev.kfp_hits: orchestrators.append("kfp")
#     if ev.azureml_pipeline_hits: orchestrators.append("azureml_pipelines")
#     if ev.sagemaker_pipeline_hits: orchestrators.append("sagemaker_pipelines")
#     if ev.cicd_workflows:
#         if any(".github/workflows/" in x for x in ev.cicd_workflows): orchestrators.append("gha")
#         if any(".gitlab-ci.yml" in x for x in ev.cicd_workflows): orchestrators.append("gitlab_ci")

#     scheduling_present = bool(ev.cicd_schedules)
#     pipelines_defined = len(ev.pipeline_manifests)
#     automation_quality = 0.0
#     if orchestrators: automation_quality += 0.4
#     if scheduling_present: automation_quality += 0.3
#     if any(ev.cicd_policy_gates.get(k, False) for k in ("pytest","bandit","trivy","bias","data_validation")):
#         automation_quality += 0.2
#     if pipelines_defined >= 3: automation_quality += 0.1
#     return {
#         "orchestrators": sorted(set(orchestrators)),
#         "pipelines_defined": pipelines_defined,
#         "scheduling_present": scheduling_present,
#         "automation_quality": round(min(1.0, automation_quality), 2),
#     }

# # ---------- Readiness payload builders (repo-only; fed to LLM graders) ----------
# def payload_cicd_policy_gates(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "cicd.policy_gates_band",
#         "required_checks": ["pytest","integration-tests","bandit","trivy","bias_check","data_validation"],
#         "workflow_files": ev.cicd_workflows,
#         "workflow_yaml": [ev.cicd_workflow_texts[p] for p in ev.cicd_workflows if p in ev.cicd_workflow_texts][:4],
#         "evidence": {
#             "present_flags": ev.cicd_policy_gates,
#             "schedules": ev.cicd_schedules,
#             "deploy_jobs": ev.cicd_deploy_job_names,
#             "environments": ev.cicd_environments,
#         },
#         "rubric": (
#             "5 if all required checks exist and run before deploy; 4 if most present; "
#             "3 if partial; 2 minimal; 1 if missing."
#         ),
#     }

# def payload_registry_governance_readiness(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "registry_governance_readiness_band",
#         "evidence": {
#             "codeowners_present": ev.codeowners_present,
#             "deploy_jobs": ev.cicd_deploy_job_names,
#             "environments": ev.cicd_environments,
#             "policy_gates": ev.cicd_policy_gates,
#         },
#         "rubric": {
#             "5": "CODEOWNERS + prod environment gating + security tests + explicit promote steps",
#             "4": "prod env + policy gates present",
#             "3": "some gates or envs",
#             "2": "weak hints only",
#             "1": "no governance indicators",
#         },
#     }

# def payload_artifact_lineage_readiness(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "artifact_lineage_readiness_band",
#         "evidence": {
#             "image_digests": ev.image_digest_pins,
#             "unpinned_images": ev.unpinned_images,
#             "sbom": ev.sbom_signals,
#             "signing": ev.signing_signals,
#             "k8s_probes": ev.k8s_probe_signals,
#         },
#         "rubric": {
#             "5": "images pinned by digest + signing/SBOM + probes",
#             "4": "pinned images + either signing or SBOM",
#             "3": "some pinning, missing supply-chain pieces",
#             "2": "unpinned images dominate",
#             "1": "no integrity signals",
#         },
#     }

# def payload_monitoring_readiness(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "monitoring_coverage_readiness_band",
#         "evidence": {
#             "rule_files": ev.monitoring_rule_files,
#             "rule_snippets": [ev.monitoring_rule_texts[p] for p in ev.monitoring_rule_files if p in ev.monitoring_rule_texts][:4],
#             "alert_channels": ev.alert_channel_signals,
#         },
#         "rubric": {
#             "5": "clear prod alert rules + alert channels configured",
#             "4": "rules present with some channels",
#             "3": "basic rules only",
#             "2": "stubs only",
#             "1": "no monitoring config",
#         },
#     }

# def payload_validation_readiness(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "validation_artifacts_readiness_band",
#         "evidence": {
#             "explainability": ev.explainability_signals,
#             "bias": ev.bias_signals,
#             "validation_schemas": ev.validation_schema_files,
#             "model_cards": ev.model_card_files,
#             "data_validation_libs": ev.data_validation_libs,
#         },
#         "rubric": {
#             "5": "bias + explainability + validation schema + model card",
#             "4": "three of the above",
#             "3": "two of the above",
#             "2": "one present",
#             "1": "none present",
#         },
#     }

# def payload_lineage_practices(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "lineage_practices_readiness_band",
#         "evidence": {
#             "git_sha_logging": ev.lineage_code_signals,
#             "data_refs": ev.data_ref_signals,
#             "env_locks": ev.env_lock_signals,
#         },
#         "rubric": {
#             "5": "git_sha + data_ref + env lock all logged",
#             "4": "two present",
#             "3": "one present",
#             "2": "weak hints",
#             "1": "none",
#         },
#     }

# def payload_dora_readiness(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "dora_readiness_band",
#         "evidence": {
#             "environments": ev.cicd_environments,
#             "concurrency": ev.cicd_concurrency_signals,
#             "rollback": ev.cicd_rollback_signals,
#             "health_checks": ev.cicd_healthcheck_signals,
#             "schedules": ev.cicd_schedules,
#         },
#         "rubric": {
#             "5": "env promotion + concurrency + rollback + health checks + schedules",
#             "4": "envs + two of (concurrency, rollback, health checks)",
#             "3": "envs + one",
#             "2": "weak hints only",
#             "1": "none",
#         },
#     }

# def payload_cost_attribution(ev: RepoEvidence) -> Dict:
#     required_tag_keys = ["service", "env", "owner", "model", "endpoint_id"]
#     present = set(k.lower() for k in ev.iac_tag_keys_detected)
#     missing = [k for k in required_tag_keys if k not in present]
#     return {
#         "metric_id": "cost_attribution_readiness_band",
#         "evidence": {
#             "tag_keys_detected": ev.iac_tag_keys_detected,
#             "missing_required": missing,
#             "sample_lines": ev.iac_tag_lines[:20],
#         },
#         "rubric": {
#             "5": "all required keys present and consistent",
#             "4": "most keys present",
#             "3": "some present",
#             "2": "few present",
#             "1": "none",
#         },
#     }

# def payload_slo_declared(ev: RepoEvidence) -> Dict:
#     return {
#         "metric_id": "slo_declared_band",
#         "evidence": {
#             "slo_docs": ev.slo_docs,
#             "slo_env_vars": ev.slo_env_vars,
#             "samples": [ev.slo_texts[p] for p in ev.slo_docs if p in ev.slo_texts][:3],
#         },
#         "rubric": {
#             "5": "SLO docs + thresholds in env/alerts",
#             "4": "SLO docs only",
#             "3": "scattered thresholds",
#             "2": "mentions only",
#             "1": "none",
#         },
#     }
