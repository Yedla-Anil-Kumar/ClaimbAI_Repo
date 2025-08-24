from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class MLOpsInputs:
    """
    Canonical single-JSON inputs for the MLOps agent.
    These fields are direct outputs of deterministic compute_* functions
    (collectors/parsers). The orchestrator passes only the relevant 'evidence'
    blob per metric to the LLM engine.

    Do not include rubrics/policies here; they live in the LLM engine.
    """

    # ---- MLflow experimentation ----
    mlflow_experiment_completeness: Optional[Dict[str, Any]] = None 
    mlflow_lineage_coverage: Optional[Dict[str, Any]] = None
    mlflow_best_run_trend: Optional[Dict[str, Any]] = None
    mlflow_registry_hygiene: Optional[Dict[str, Any]] = None
    mlflow_validation_artifacts: Optional[Dict[str, Any]] = None
    mlflow_reproducibility: Optional[Dict[str, Any]] = None

    # ---- Azure ML (AML) ----
    aml_endpoint_slo: Optional[Dict[str, Any]] = None
    aml_jobs_flow: Optional[Dict[str, Any]] = None
    aml_monitoring_coverage: Optional[Dict[str, Any]] = None
    aml_registry_governance: Optional[Dict[str, Any]] = None
    aml_cost_correlation: Optional[Dict[str, Any]] = None

    # ---- SageMaker (SM) ----
    sm_endpoint_slo_scaling: Optional[Dict[str, Any]] = None
    sm_pipeline_stats: Optional[Dict[str, Any]] = None
    sm_experiments_lineage: Optional[Dict[str, Any]] = None
    sm_clarify_coverage: Optional[Dict[str, Any]] = None
    sm_cost_efficiency: Optional[Dict[str, Any]] = None

    # ---- CI/CD ----
    cicd_deploy_frequency: Optional[Dict[str, Any]] = None
    cicd_lead_time: Optional[Dict[str, Any]] = None
    cicd_change_failure_rate: Optional[Dict[str, Any]] = None
    cicd_policy_gates: Optional[Dict[str, Any]] = None
    cicd_artifact_lineage: Optional[Dict[str, Any]] = None  # deterministic

    # ---- Optional knobs (defaults set here; override per org) ----
    declared_slo: Dict[str, Any] = field(
        default_factory=lambda: {
            "availability": 0.995,
            "p95_ms": 300,
            "error_rate": 0.01,
        }
    )
    policy_required_checks: List[str] = field(
        default_factory=lambda: [
            "pytest",
            "integration-tests",
            "bandit",
            "trivy",
            "bias_check",
            "data_validation",
        ]
    )

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(blob: Dict[str, Any]) -> "MLOpsInputs":
        allowed = set(MLOpsInputs.__dataclass_fields__.keys())  # type: ignore[attr-defined]  # noqa: E501
        filtered = {k: v for k, v in blob.items() if k in allowed}
        return MLOpsInputs(**filtered)
