from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from dataclasses import asdict


@dataclass
class MLOpsInputs:
    """
    Canonical single-JSON inputs for the ML Ops agent.
    These fields are the DIRECT outputs of your deterministic compute_* functions.
    You can load them from data/ml_ops/sample_inputs/*.json or pipe them from collectors.

    For each evidence blob:
      - It should already look like the examples in your spec (metric_id + evidence fields).
      - The orchestrator will wrap each in the LLM grading request with the correct rubric/policy.
    """

    # ---- MLflow experimentation ----
    mlflow_experiment_completeness: Optional[Dict[str, Any]] = None   # compute_mlflow_experiment_completeness
    mlflow_lineage_coverage: Optional[Dict[str, Any]] = None          # compute_mlflow_lineage_coverage
    mlflow_best_run_trend: Optional[Dict[str, Any]] = None            # compute_mlflow_best_run_trend
    mlflow_registry_hygiene: Optional[Dict[str, Any]] = None          # compute_mlflow_registry_hygiene
    mlflow_validation_artifacts: Optional[Dict[str, Any]] = None      # compute_mlflow_validation_artifact_coverage
    mlflow_reproducibility: Optional[Dict[str, Any]] = None           # compute_mlflow_reproducibility_signature

    # ---- Azure ML (AML) ----
    aml_endpoint_slo: Optional[Dict[str, Any]] = None                 # compute_aml_endpoint_slo
    aml_jobs_flow: Optional[Dict[str, Any]] = None                    # compute_aml_jobs_flow
    aml_monitoring_coverage: Optional[Dict[str, Any]] = None          # compute_aml_monitoring_coverage
    aml_registry_governance: Optional[Dict[str, Any]] = None          # compute_aml_registry_governance
    aml_cost_correlation: Optional[Dict[str, Any]] = None             # compute_aml_cost_correlation

    # ---- SageMaker (SM) ----
    sm_endpoint_slo_scaling: Optional[Dict[str, Any]] = None          # compute_sm_endpoint_slo_scaling
    sm_pipeline_stats: Optional[Dict[str, Any]] = None                # compute_sm_pipeline_stats
    sm_experiments_lineage: Optional[Dict[str, Any]] = None           # compute_sm_experiments_lineage_coverage
    sm_clarify_coverage: Optional[Dict[str, Any]] = None              # compute_sm_clarify_coverage
    sm_cost_efficiency: Optional[Dict[str, Any]] = None               # compute_sm_cost_efficiency

    # ---- CI/CD ----
    cicd_deploy_frequency: Optional[Dict[str, Any]] = None            # compute_cicd_deploy_frequency
    cicd_lead_time: Optional[Dict[str, Any]] = None                   # compute_cicd_lead_time
    cicd_change_failure_rate: Optional[Dict[str, Any]] = None         # compute_cicd_change_failure_rate
    cicd_policy_gates: Optional[Dict[str, Any]] = None                # check_cicd_policy_gates (already LLM-ready-ish)
    cicd_artifact_lineage: Optional[Dict[str, Any]] = None            # compute_cicd_artifact_lineage_integrity (deterministic)

    # ---- Optional knobs (defaults set here; override per org) ----
    declared_slo: Dict[str, Any] = field(default_factory=lambda: {
        "availability": 0.995, "p95_ms": 300, "error_rate": 0.01
    })
    policy_required_checks: List[str] = field(default_factory=lambda: [
        "pytest", "integration-tests", "bandit", "trivy", "bias_check", "data_validation"
    ])

    def as_dict(self) -> Dict[str, Any]:
      return asdict(self)

    @staticmethod
    def from_json(blob: Dict[str, Any]) -> "MLOpsInputs":
        allowed = {f.name for f in MLOpsInputs.__dataclass_fields__.values()}
        filtered = {k: v for k, v in blob.items() if k in allowed}
        return MLOpsInputs(**filtered)
