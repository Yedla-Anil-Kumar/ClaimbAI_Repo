# # Data_Collection_Agents/ml_ops_agent/schemas.py
# from __future__ import annotations
# from typing import List, Literal
# from pydantic import BaseModel, Field, ConfigDict, PositiveInt, NonNegativeInt, field_validator

# Percent = Field(ge=0.0, le=1.0)

# # ------------ Shared helpers ------------
# class WindowEpoch(BaseModel):
#     model_config = ConfigDict(extra="forbid", populate_by_name=True)
#     from_: int = Field(alias="from", ge=0)
#     to: int = Field(ge=0)

#     @field_validator("to")
#     @classmethod
#     def _from_lt_to(cls, v, info):
#         frm = info.data.get("from_")
#         if frm is not None and v <= frm:
#             raise ValueError("'to' must be > 'from'")
#         return v

# # ------------ MLflow ------------
# class SampleMissing(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     run_id: str
#     missing: List[str]

# class MLflowExperimentCompleteness(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     window: WindowEpoch
#     pct_params: float = Percent
#     pct_metrics: float = Percent
#     pct_tags: float = Percent
#     pct_artifacts: float = Percent
#     pct_all: float = Percent
#     samples_missing: List[SampleMissing] = Field(default_factory=list)

# class MLflowLineageSample(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     run_id: str
#     git_sha: bool
#     data_ref: bool
#     env_files: List[str] = Field(default_factory=list)

# class MLflowLineageCoverage(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     pct_git_sha: float = Percent
#     pct_data_ref: float = Percent
#     pct_env_files: float = Percent
#     samples: List[MLflowLineageSample] = Field(default_factory=list)

# class WeeklyBest(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     week: str
#     score: float = Percent

# class MLflowBestRunTrend(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     weekly_best: List[WeeklyBest]
#     improvement_rate_mom: float
#     experiments_per_week: float = Field(ge=0.0)
#     direction: Literal["max", "min"]

# class MLflowRegistryHygiene(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     pct_staged: float = Percent
#     median_stage_latency_h: NonNegativeInt
#     rollback_count_30d: NonNegativeInt
#     pct_with_approver: float = Percent

# class MLflowValidationArtifacts(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     pct_with_shap: float = Percent
#     pct_with_bias_report: float = Percent
#     pct_with_validation_json: float = Percent
#     pct_overall: float = Percent

# class SignatureConflict(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     signature: str
#     runs: List[str]
#     metric_diff: float = Field(ge=0.0)

# class MLflowReproducibility(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     match_rate: float = Percent
#     signature_conflicts: List[SignatureConflict] = Field(default_factory=list)

# # ------------ Azure ML (AML) ------------
# class AMLEndpointSLO(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     availability_30d: float = Percent
#     error_rate: float = Percent
#     p95_ms: PositiveInt

# class AMLJobsFlow(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     success_rate: float = Percent
#     p95_duration_min: PositiveInt
#     lead_time_hours: float = Field(gt=0)

# class AMLMonitoringCoverage(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     monitors_enabled: bool
#     drift_alerts_30d: NonNegativeInt
#     median_time_to_ack_h: float = Field(ge=0.0)

# class AMLRegistryGovernance(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     pct_staged: float = Percent
#     pct_with_approvals: float = Percent
#     median_transition_h: NonNegativeInt

# class AMLCostCorrelation(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     cost_join_rate: float = Percent
#     cost_per_1k_requests: float = Field(ge=0.0)
#     coverage: Literal["tags", "resourceId", "tags+resourceId"]

# # ------------ CI/CD ------------
# class CICDDeployFrequency(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     freq_per_week: float = Field(ge=0.0)
#     service_count: PositiveInt

# class CICDLeadTime(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     p50_hours: float = Field(gt=0)
#     p95_hours: float = Field(gt=0)

#     @field_validator("p95_hours")
#     @classmethod
#     def _p95_ge_p50(cls, v, info):
#         p50 = info.data.get("p50_hours")
#         if p50 is not None and v < p50:
#             raise ValueError("p95_hours must be >= p50_hours")
#         return v

# class CICDChangeFailureRate(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     cfr: float = Percent
#     rollbacks_30d: NonNegativeInt

# class CICDPolicyGates(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     required_checks: List[str]
#     workflow_yaml: str
#     logs_snippets: List[str] = Field(default_factory=list)
#     rubric: str

# class CICDArtifactLineage(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     metric_id: str
#     integrity_ok: bool
#     mismatches: List[str] = Field(default_factory=list)

# # ------------ Org-level defaults ------------
# class DeclaredSLO(BaseModel):
#     model_config = ConfigDict(extra="forbid")
#     availability: float = Percent
#     p95_ms: PositiveInt
#     error_rate: float = Percent
