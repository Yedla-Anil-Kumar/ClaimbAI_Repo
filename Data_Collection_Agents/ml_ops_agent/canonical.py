# Data_Collection_Agents/ml_ops_agent/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RepoEvidence:
    """
    Canonical evidence collected purely from the repository.
    These are deterministic facts — no LLM here. LLM graders only see structured payloads derived from this.
    """

    # ------- Platform signals (as before) -------
    mlflow_hits: List[str] = field(default_factory=list)
    mlflow_registry_hits: List[str] = field(default_factory=list)
    mlflow_tracking_uri_values: List[str] = field(default_factory=list)

    sagemaker_hits: List[str] = field(default_factory=list)
    sagemaker_endpoint_hits: List[str] = field(default_factory=list)
    sagemaker_pipeline_hits: List[str] = field(default_factory=list)
    sagemaker_registry_hits: List[str] = field(default_factory=list)

    azureml_hits: List[str] = field(default_factory=list)
    azureml_endpoint_hits: List[str] = field(default_factory=list)
    azureml_pipeline_hits: List[str] = field(default_factory=list)
    azureml_registry_hits: List[str] = field(default_factory=list)

    kfp_hits: List[str] = field(default_factory=list)
    kfp_compiled_yaml: List[str] = field(default_factory=list)

    # ------- Experiment tracking (generic) -------
    tracking_tools: List[str] = field(default_factory=list)  # ["mlflow","wandb","tensorboard","comet_ml","neptune",...]
    tracking_metrics_signals: List[str] = field(default_factory=list)   # files or lines
    tracking_artifact_signals: List[str] = field(default_factory=list)

    # ------- CI/CD (workflows + raw content) -------
    cicd_workflows: List[str] = field(default_factory=list)                # workflow file paths
    cicd_workflow_texts: Dict[str, str] = field(default_factory=dict)      # path -> truncated text
    cicd_schedules: List[str] = field(default_factory=list)                # cron strings
    cicd_policy_gates: Dict[str, bool] = field(default_factory=dict)       # pytest/bandit/trivy/... booleans
    cicd_deploy_job_names: List[str] = field(default_factory=list)         # job names likely to deploy/promote
    cicd_environments: List[str] = field(default_factory=list)             # e.g., ["staging","production"]
    cicd_concurrency_signals: List[str] = field(default_factory=list)      # e.g., "concurrency:" lines
    cicd_rollback_signals: List[str] = field(default_factory=list)         # "rollback", "rollout undo", "canary" etc.
    cicd_healthcheck_signals: List[str] = field(default_factory=list)      # health checks / smoke tests before deploy
    codeowners_present: bool = False

    # ------- Serving / deployment signals -------
    serving_signals: List[str] = field(default_factory=list)               # kserve, endpoint, FastAPI/Flask, inference

    # ------- Manifests (rough) -------
    endpoint_manifests: List[str] = field(default_factory=list)
    pipeline_manifests: List[str] = field(default_factory=list)

    # ------- Artifact lineage / integrity readiness -------
    image_digest_pins: List[str] = field(default_factory=list)             # image@sha256:...
    unpinned_images: List[str] = field(default_factory=list)               # image:tag (no digest)
    sbom_signals: List[str] = field(default_factory=list)                  # sbom generation/upload steps
    signing_signals: List[str] = field(default_factory=list)               # cosign/sigstore/attestation
    k8s_probe_signals: List[str] = field(default_factory=list)             # readinessProbe/livenessProbe

    # ------- Monitoring / alerting readiness -------
    monitoring_rule_files: List[str] = field(default_factory=list)
    monitoring_rule_texts: Dict[str, str] = field(default_factory=dict)    # path -> truncated text
    alert_channel_signals: List[str] = field(default_factory=list)         # slack/webhook/email in CI

    # ------- Validation / explainability / bias readiness -------
    explainability_signals: List[str] = field(default_factory=list)        # shap, lime, captum
    bias_signals: List[str] = field(default_factory=list)                  # clarify, fairness
    validation_schema_files: List[str] = field(default_factory=list)       # validation.json/yaml, pandera, GE suites
    model_card_files: List[str] = field(default_factory=list)              # model_card.md/.mdx
    data_validation_libs: List[str] = field(default_factory=list)          # great_expectations, evidently, pandera

    # ------- Lineage practices readiness -------
    lineage_code_signals: List[str] = field(default_factory=list)          # git sha logging/tagging patterns
    data_ref_signals: List[str] = field(default_factory=list)              # dataset/feature-store refs tagging
    env_lock_signals: List[str] = field(default_factory=list)              # conda.yaml/requirements.txt lock & logging

    # ------- Cost tagging / attribution readiness -------
    iac_tag_lines: List[str] = field(default_factory=list)                 # terraform/helm tags & labels
    iac_tag_keys_detected: List[str] = field(default_factory=list)         # flattened tag keys

    # ------- SLO declaration readiness -------
    slo_docs: List[str] = field(default_factory=list)                      # slo.yaml, docs with SLO tables
    slo_env_vars: List[str] = field(default_factory=list)                  # AVAILABILITY_SLO/P95_MS_SLO from CI/env
    slo_texts: Dict[str, str] = field(default_factory=dict)                # path -> truncated text

    # repo-only flag
    repo_only_mode: bool = True
