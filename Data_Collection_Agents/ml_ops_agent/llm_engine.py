from __future__ import annotations
import json
import time
import random
from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent

"""
MLOps Metric Grader — ONE-SHOT (per metric)

- Universal preamble + per-metric rubric
- Each metric includes: example_input AND example_output (true one-shot)
- build_prompt prints the RESPONSE FORMAT before EXAMPLES to reduce anchoring
- Public API is unchanged: one wrapper method per grading/check function

UPDATE:
- Rubrics consider **all** relevant fields in each metric's evidence.
- Response schema now includes **gaps** explaining what limited the band.
- Each metric includes **input_key_meanings** to make field intent explicit.
"""

# -------------------------
# Universal grading contract
# -------------------------

UNIVERSAL_PREAMBLE = (
    "You are an MLOps Assessor. Grade exactly one metric on a 1–5 band:\n"
    "5 = Excellent\n"
    "4 = Good\n"
    "3 = Fair\n"
    "2 = Poor\n"
    "1 = Critical\n\n"
    "Rules:\n"
    "- Use ONLY the provided JSON evidence/rubric/policy text. Do NOT invent data.\n"
    "- Compare all relevant evidence fields; bands must reflect the combination,\n"
    "  not a single field. If fields conflict, choose the lower band and explain briefly.\n"
    "- The rationale must cite 1–2 strongest positives and the single biggest limiter.\n"
    "- Populate 'gaps' with concrete missing/weak items that (if improved) would raise the band.\n"
    "- Be consistent and conservative when values are borderline.\n"
    "- Keep the rationale clear and short (≤3 sentences).\n"
    "- Return ONLY the specified JSON. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"band":<1-5>,'
    '"rationale":"<1-3 sentences>",'
    '"flags":[],'
    '"gaps":[]}'
)

POLICY_GATES_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"band":<1-5>,'
    '"rationale":"<1-3 sentences>",'
    '"present":[],'
    '"missing":[],'
    '"failing":[],'
    '"gaps":[]}'
)

def _rubric_text(t: str) -> str:
    return f"SYSTEM:\n{UNIVERSAL_PREAMBLE}\n\nRUBRIC:\n{t}"


# -------------------------------------------------------------------------
# Metric definitions (20 LLM-used graders/checkers) — ONE SHOT, all-fields
# Each item includes: system (preamble+rubric), input_key_meanings, example IO,
# and the unified response format (with gaps).
# -------------------------------------------------------------------------

METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # =========================
    # MLflow
    # =========================

    "mlflow.experiment_completeness_band": {
        "system": _rubric_text(
            "Use these fields together: pct_all, pct_params, pct_metrics, pct_tags, pct_artifacts.\n"
            "Band 5: ALL fields ≥ 0.90 AND the lowest of the five ≥ 0.90.\n"
            "Band 4: ALL fields ≥ 0.80 AND at least THREE fields ≥ 0.85; lowest ≥ 0.80.\n"
            "Band 3: ALL fields ≥ 0.70 AND at least TWO fields ≥ 0.80; lowest ≥ 0.70.\n"
            "Band 2: ANY field < 0.70 BUT at least TWO fields ≥ 0.60 AND pct_all ≥ 0.60.\n"
            "Band 1: MOST fields < 0.60 OR pct_all < 0.60 OR evidence is missing."
        ),
        "input_key_meanings": {
            "evidence.pct_all": "Share of runs with params+metrics+tags+artifacts all present",
            "evidence.pct_params": "Runs with parameter logging",
            "evidence.pct_metrics": "Runs with metric logging",
            "evidence.pct_tags": "Runs with tags metadata",
            "evidence.pct_artifacts": "Runs persisting artifacts (models/files)"
        },
        "example_input": {
            "metric_id": "mlflow.experiment_completeness_band",
            "rubric": "See rubric above; consider all five fields together.",
            "evidence": {
                "pct_all": 0.82,
                "pct_params": 0.90,
                "pct_metrics": 0.82,
                "pct_tags": 0.81,
                "pct_artifacts": 0.75
            }
        },
        "example_output": {
            "metric_id": "mlflow.experiment_completeness_band",
            "band": 3,
            "rationale": "Params/metrics strong; artifacts at 0.75 caps to 3.",
            "flags": ["artifacts_low"],
            "gaps": ["Increase artifact persistence to ≥0.80"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "mlflow.lineage_coverage_band": {
        "system": _rubric_text(
            "Use: pct_git_sha, pct_data_ref, pct_env_files.\n"
            "Band 5: ALL ≥ 0.95.\n"
            "Band 4: ALL ≥ 0.85 AND at least TWO ≥ 0.90.\n"
            "Band 3: ALL ≥ 0.70 AND at least ONE ≥ 0.85.\n"
            "Band 2: ANY < 0.70 BUT at least ONE ≥ 0.60.\n"
            "Band 1: MOST < 0.60 or multiple missing."
        ),
        "input_key_meanings": {
            "evidence.pct_git_sha": "Runs with committed Git SHA recorded",
            "evidence.pct_data_ref": "Runs with immutable data reference (path/hash/version)",
            "evidence.pct_env_files": "Runs with environment files recorded (conda/requirements)"
        },
        "example_input": {
            "metric_id": "mlflow.lineage_coverage_band",
            "rubric": "All three fields drive the band per the thresholds above.",
            "evidence": {"pct_git_sha": 0.93, "pct_data_ref": 0.84, "pct_env_files": 0.91}
        },
        "example_output": {
            "metric_id": "mlflow.lineage_coverage_band",
            "band": 3,
            "rationale": "Git/env ≥0.90 but data_ref 0.84 limits to 3.",
            "flags": ["data_ref_coverage"],
            "gaps": ["Raise data reference logging to ≥0.85"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "mlflow.experiment_velocity_band": {
        "system": _rubric_text(
            "Use together: improvement_rate_mom, experiments_per_week.\n"
            "Band 5: rate ≥ 0.05 AND exp/wk ≥ 2.0.\n"
            "Band 4: rate ≥ 0.03 AND exp/wk ≥ 1.5.\n"
            "Band 3: BOTH ≥ 0.01.\n"
            "Band 2: ONE ≥ 0.01 but the other lower.\n"
            "Band 1: BOTH < 0.01."
        ),
        "input_key_meanings": {
            "evidence.improvement_rate_mom": "Monthly improvement rate of best run metric",
            "evidence.experiments_per_week": "Average experiments executed per week"
        },
        "example_input": {
            "metric_id": "mlflow.experiment_velocity_band",
            "rubric": "Both dimensions required for higher bands.",
            "evidence": {"improvement_rate_mom": 0.06, "experiments_per_week": 2.2}
        },
        "example_output": {
            "metric_id": "mlflow.experiment_velocity_band",
            "band": 5,
            "rationale": "Both exceed top thresholds.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "mlflow.registry_hygiene_band": {
        "system": _rubric_text(
            "Use together: pct_staged, pct_with_approver, median_stage_latency_h, rollback_count_30d.\n"
            "Band 5: staged ≥ 0.90 AND approver ≥ 0.90 AND latency < 48h AND rollbacks == 0.\n"
            "Band 4: ALL ≥ 0.80 AND latency < 72h AND rollbacks ≤ 1.\n"
            "Band 3: ALL ≥ 0.70 AND latency < 96h AND rollbacks ≤ 2.\n"
            "Band 2: ANY < 0.70 OR latency 96–119h OR rollbacks 3.\n"
            "Band 1: latency ≥ 120h OR rollbacks > 3 OR evidence missing."
        ),
        "input_key_meanings": {
            "evidence.pct_staged": "Models in registry assigned a stage (Staging/Prod/etc.)",
            "evidence.pct_with_approver": "Stage transitions with approver recorded",
            "evidence.median_stage_latency_h": "Median hours to move from staging to prod",
            "evidence.rollback_count_30d": "Prod rollbacks in the last 30 days"
        },
        "example_input": {
            "metric_id": "mlflow.registry_hygiene_band",
            "policy": "All prod transitions approved; median<72h; minimal rollbacks.",
            "rubric": "All four fields jointly determine the band.",
            "evidence": {"pct_staged": 0.83, "pct_with_approver": 0.88, "median_stage_latency_h": 60, "rollback_count_30d": 1}
        },
        "example_output": {
            "metric_id": "mlflow.registry_hygiene_band",
            "band": 4,
            "rationale": "Approvals and latency within targets; a single rollback observed.",
            "flags": ["rollback_present"],
            "gaps": ["Target zero rollbacks; drive latency <48h"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "mlflow.validation_artifacts_band": {
        "system": _rubric_text(
            "Use: pct_with_shap, pct_with_bias_report, pct_with_validation_json (all three matter).\n"
            "Band 5: ALL ≥ 0.90.\n"
            "Band 4: ALL ≥ 0.80 AND at least TWO ≥ 0.85.\n"
            "Band 3: ALL ≥ 0.70 AND at least ONE ≥ 0.80.\n"
            "Band 2: ANY < 0.70 but at least ONE ≥ 0.60.\n"
            "Band 1: MOST < 0.60 or missing."
        ),
        "input_key_meanings": {
            "evidence.pct_with_shap": "Runs with SHAP or equivalent explainability files",
            "evidence.pct_with_bias_report": "Runs with bias/fairness report",
            "evidence.pct_with_validation_json": "Runs with validation summary JSON"
        },
        "example_input": {
            "metric_id": "mlflow.validation_artifacts_band",
            "rubric": "All three files must be considered jointly.",
            "evidence": {"pct_with_shap": 0.75, "pct_with_bias_report": 0.72, "pct_with_validation_json": 0.84}
        },
        "example_output": {
            "metric_id": "mlflow.validation_artifacts_band",
            "band": 3,
            "rationale": "Validation strong; SHAP/bias below 0.80 keep it at 3.",
            "flags": ["bias_coverage_low", "shap_coverage_low"],
            "gaps": ["Raise bias report and SHAP coverage to ≥0.80"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "mlflow.reproducibility_band": {
        "system": _rubric_text(
            "Use: match_rate and signature_conflicts[].\n"
            "Band 5: match_rate ≥ 0.95 AND no conflicts.\n"
            "Band 4: match_rate ≥ 0.85; minor conflicts allowed (few, small metric_diff).\n"
            "Band 3: match_rate ≥ 0.70; some conflicts present.\n"
            "Band 2: match_rate ≥ 0.50; many/serious conflicts.\n"
            "Band 1: match_rate < 0.50 OR major, repeated conflicts."
        ),
        "input_key_meanings": {
            "evidence.match_rate": "Share of reruns that match previous metrics within tolerance",
            "evidence.signature_conflicts[]": "Conflicting model signatures with metric diffs"
        },
        "example_input": {
            "metric_id": "mlflow.reproducibility_band",
            "rubric": "Consider both match rate and presence/severity of conflicts.",
            "evidence": {"match_rate": 0.88, "signature_conflicts": [{"signature": "abc", "runs": ["r1", "r8"], "metric_diff": 0.025}]}
        },
        "example_output": {
            "metric_id": "mlflow.reproducibility_band",
            "band": 4,
            "rationale": "High match rate; minor conflict recorded.",
            "flags": ["conflicts_present"],
            "gaps": ["Resolve signature 'abc' conflict and document tolerance"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # =========================
    # Azure ML (AML)
    # =========================

    "aml.endpoint_slo_band": {
        "system": _rubric_text(
            "Use declared_slo {availability, p95_ms, error_rate} AND measured {availability_30d, p95_ms, error_rate}.\n"
            "Compute deltas vs declared. Prefer the WORST dimension.\n"
            "Band 5: availability_30d ≥ declared+0.002 AND p95_ms ≤ 0.80*declared AND error_rate ≤ 0.50*declared.\n"
            "Band 4: ALL declared met AND at least TWO exceed by margin (availability ≥ +0.001, p95 ≤ 0.90*declared, error ≤ 0.75*declared).\n"
            "Band 3: At least TWO declared met OR ALL barely met.\n"
            "Band 2: Only ONE declared met OR conflicting trade-offs.\n"
            "Band 1: NONE of declared met OR evidence missing."
        ),
        "input_key_meanings": {
            "declared_slo.availability": "Target availability SLO",
            "declared_slo.p95_ms": "Target p95 latency (ms)",
            "declared_slo.error_rate": "Target error rate",
            "evidence.availability_30d": "Measured 30d availability",
            "evidence.p95_ms": "Measured p95 latency",
            "evidence.error_rate": "Measured error rate"
        },
        "example_input": {
            "metric_id": "aml.endpoint_slo_band",
            "declared_slo": {"availability": 0.995, "p95_ms": 300, "error_rate": 0.01},
            "evidence": {"availability_30d": 0.997, "p95_ms": 215, "error_rate": 0.003}
        },
        "example_output": {
            "metric_id": "aml.endpoint_slo_band",
            "band": 5,
            "rationale": "All three exceed SLO with healthy margin.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "aml.jobs_flow_band": {
        "system": _rubric_text(
            "Use: success_rate, p95_duration_min, lead_time_hours together.\n"
            "Band 5: success_rate ≥ 0.98 AND lead_time ≤ 4h AND p95_duration_min ≤ 30.\n"
            "Band 4: success_rate ≥ 0.95 AND lead_time ≤ 8h AND p95_duration_min ≤ 45.\n"
            "Band 3: success_rate ≥ 0.90 AND lead_time ≤ 24h AND p95_duration_min ≤ 60.\n"
            "Band 2: partial health (one dimension clearly below).\n"
            "Band 1: generally failing."
        ),
        "input_key_meanings": {
            "evidence.success_rate": "Proportion of AML jobs that succeed",
            "evidence.p95_duration_min": "p95 job duration in minutes",
            "evidence.lead_time_hours": "Hours between commit and scheduled run start"
        },
        "example_input": {
            "metric_id": "aml.jobs_flow_band",
            "rubric": "All three fields jointly determine the band.",
            "evidence": {"success_rate": 0.94, "p95_duration_min": 38, "lead_time_hours": 6.4}
        },
        "example_output": {
            "metric_id": "aml.jobs_flow_band",
            "band": 3,
            "rationale": "Success <0.95; lead-time moderate; p95 duration acceptable.",
            "flags": [],
            "gaps": ["Raise success_rate to ≥0.95"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "aml.monitoring_coverage_band": {
        "system": _rubric_text(
            "Use: monitors_enabled (bool), median_time_to_ack_h, drift_alerts_30d.\n"
            "Band 5: monitors_enabled == True AND median_time_to_ack_h < 2h.\n"
            "Band 4: monitors_enabled == True AND median_time_to_ack_h < 6h.\n"
            "Band 3: monitors_enabled == True BUT median_time_to_ack_h ≥ 6h OR no recent alerts to validate process.\n"
            "Band 2: monitors_enabled == False BUT some ad-hoc response evidence.\n"
            "Band 1: monitors disabled and no response process."
        ),
        "input_key_meanings": {
            "evidence.monitors_enabled": "Whether AML data/quality/drift monitors are enabled",
            "evidence.median_time_to_ack_h": "Median hours to acknowledge alerts",
            "evidence.drift_alerts_30d": "Count of drift/quality alerts in 30 days"
        },
        "example_input": {
            "metric_id": "aml.monitoring_coverage_band",
            "rubric": "Ack speed and enablement determine band; alerts give context.",
            "evidence": {"monitors_enabled": True, "drift_alerts_30d": 2, "median_time_to_ack_h": 1.2}
        },
        "example_output": {
            "metric_id": "aml.monitoring_coverage_band",
            "band": 5,
            "rationale": "Enabled with fast <2h acknowledgement.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "aml.registry_governance_band": {
        "system": _rubric_text(
            "Use: pct_staged, pct_with_approvals, median_transition_h.\n"
            "Band 5: staged ≥ 0.90 AND approvals ≥ 0.90 AND median_transition_h < 48.\n"
            "Band 4: ALL ≥ 0.80 AND median_transition_h < 72.\n"
            "Band 3: ALL ≥ 0.70 AND median_transition_h < 96.\n"
            "Band 2: ANY < 0.70 OR median_transition_h 96–119.\n"
            "Band 1: median ≥ 120 OR widespread lack of approvals."
        ),
        "input_key_meanings": {
            "evidence.pct_staged": "Models with a registry stage",
            "evidence.pct_with_approvals": "Stage transitions with approvals",
            "evidence.median_transition_h": "Median hours to transition between stages"
        },
        "example_input": {
            "metric_id": "aml.registry_governance_band",
            "rubric": "All three fields together drive the score.",
            "evidence": {"pct_staged": 0.83, "pct_with_approvals": 0.88, "median_transition_h": 60}
        },
        "example_output": {
            "metric_id": "aml.registry_governance_band",
            "band": 4,
            "rationale": "All ≥0.80 and median <72h.",
            "flags": [],
            "gaps": ["Reduce transition median below 48h for band 5"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "aml.cost_correlation_band": {
        "system": _rubric_text(
            "Use: cost_join_rate and coverage (tags/resourceId/tags+resourceId) and cost_per_1k_requests.\n"
            "Band 5: cost_join_rate ≥ 0.90 AND coverage ∈ {\"tags+resourceId\"} AND stable cost attribution.\n"
            "Band 4: cost_join_rate ≥ 0.80 AND coverage includes at least one of tags or resourceId.\n"
            "Band 3: cost_join_rate ≥ 0.60 with partial coverage OR inconsistent attribution.\n"
            "Band 2: cost_join_rate ≥ 0.40 with weak coverage.\n"
            "Band 1: cost_join_rate < 0.40 OR no usable attribution."
        ),
        "input_key_meanings": {
            "evidence.cost_join_rate": "Share of requests/cost rows that can be joined to endpoints",
            "evidence.coverage": "Attribution strategy depth (tags/resourceId/both)",
            "evidence.cost_per_1k_requests": "USD cost per 1000 endpoint requests"
        },
        "example_input": {
            "metric_id": "aml.cost_correlation_band",
            "rubric": "Attribution depth and join quality matter together.",
            "evidence": {"cost_join_rate": 0.93, "cost_per_1k_requests": 0.087, "coverage": "tags+resourceId"}
        },
        "example_output": {
            "metric_id": "aml.cost_correlation_band",
            "band": 5,
            "rationale": "High join quality with fine-grained coverage.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # =========================
    # SageMaker (SM)
    # =========================

    "sm.endpoint_slo_scaling_band": {
        "system": _rubric_text(
            "Use: availability_30d, error_rate, p95_ms, median_reaction_s (autoscaling), max_rps_at_slo.\n"
            "Band 5: availability ≥ 0.999 AND p95_ms ≤ 200 AND error_rate ≤ 0.003 AND reaction ≤ 60s AND max_rps_at_slo ≥ 800.\n"
            "Band 4: availability ≥ 0.997 AND p95_ms ≤ 250 AND error_rate ≤ 0.005 AND reaction ≤ 120s AND max_rps_at_slo ≥ 400.\n"
            "Band 3: availability ≥ 0.995 AND p95_ms ≤ 300 AND error_rate ≤ 0.010.\n"
            "Band 2: meets only ONE–TWO of the above; reaction > 180s OR max_rps_at_slo < 200.\n"
            "Band 1: fails most thresholds OR evidence missing."
        ),
        "input_key_meanings": {
            "evidence.availability_30d": "Measured 30d availability",
            "evidence.error_rate": "Endpoint error rate",
            "evidence.p95_ms": "Endpoint p95 latency (ms)",
            "evidence.median_reaction_s": "Autoscaling median reaction time (seconds)",
            "evidence.max_rps_at_slo": "Sustained RPS while still meeting SLO"
        },
        "example_input": {
            "metric_id": "sm.endpoint_slo_scaling_band",
            "rubric": "All five dimensions jointly determine the band.",
            "evidence": {"availability_30d": 0.999, "error_rate": 0.002, "p95_ms": 180, "median_reaction_s": 55, "max_rps_at_slo": 950}
        },
        "example_output": {
            "metric_id": "sm.endpoint_slo_scaling_band",
            "band": 5,
            "rationale": "Elite availability/latency/errors; fast scaling; high headroom.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "sm.pipeline_flow_band": {
        "system": _rubric_text(
            "Use: success_rate, p95_duration_min, retry_rate, promotion_time_h together.\n"
            "Band 5: success ≥ 0.98 AND promotion ≤ 8h AND p95 ≤ 30 AND retry_rate ≤ 0.03.\n"
            "Band 4: success ≥ 0.95 AND promotion ≤ 12h AND p95 ≤ 45 AND retry_rate ≤ 0.06.\n"
            "Band 3: success ≥ 0.90 AND promotion ≤ 24h AND p95 ≤ 60.\n"
            "Band 2: partial health (one or two pass, others weak).\n"
            "Band 1: generally failing."
        ),
        "input_key_meanings": {
            "evidence.success_rate": "Proportion of SM pipeline executions that succeed",
            "evidence.p95_duration_min": "p95 pipeline duration (minutes)",
            "evidence.retry_rate": "Share of runs that retried due to failures",
            "evidence.promotion_time_h": "Hours from successful run to promoted model"
        },
        "example_input": {
            "metric_id": "sm.pipeline_flow_band",
            "rubric": "All four fields considered jointly.",
            "evidence": {"success_rate": 0.96, "p95_duration_min": 42, "retry_rate": 0.03, "promotion_time_h": 12.0}
        },
        "example_output": {
            "metric_id": "sm.pipeline_flow_band",
            "band": 4,
            "rationale": "Success high; promotion 12h; p95 42; retries low.",
            "flags": [],
            "gaps": ["Reduce promotion_time_h to ≤8h for band 5"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "sm.experiments_lineage_band": {
        "system": _rubric_text(
            "Use: pct_code_ref, pct_data_ref, pct_env (all three together).\n"
            "Band 5: ALL ≥ 0.95.\n"
            "Band 4: ALL ≥ 0.85 AND at least TWO ≥ 0.90.\n"
            "Band 3: ALL ≥ 0.70 AND at least ONE ≥ 0.85.\n"
            "Band 2: ANY < 0.70 but at least ONE ≥ 0.60.\n"
            "Band 1: MOST < 0.60 or missing."
        ),
        "input_key_meanings": {
            "evidence.pct_code_ref": "Experiments with code references recorded",
            "evidence.pct_data_ref": "Experiments with data references recorded",
            "evidence.pct_env": "Experiments with environment references recorded"
        },
        "example_input": {
            "metric_id": "sm.experiments_lineage_band",
            "rubric": "All three lineage dimensions considered together.",
            "evidence": {"pct_code_ref": 0.90, "pct_data_ref": 0.86, "pct_env": 0.92}
        },
        "example_output": {
            "metric_id": "sm.experiments_lineage_band",
            "band": 4,
            "rationale": "All ≥0.85 with two ≥0.90.",
            "flags": [],
            "gaps": ["Improve data_ref to ≥0.90 for band 5"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "sm.clarify_coverage_band": {
        "system": _rubric_text(
            "Use: pct_with_bias_report AND pct_with_explainability.\n"
            "Band 5: BOTH ≥ 0.90.\n"
            "Band 4: BOTH ≥ 0.80.\n"
            "Band 3: BOTH ≥ 0.70 OR one ≥ 0.85 while the other ≥ 0.70.\n"
            "Band 2: ONE ≥ 0.60 but the other < 0.70.\n"
            "Band 1: BOTH < 0.60 or missing."
        ),
        "input_key_meanings": {
            "evidence.pct_with_bias_report": "Experiments/models with bias/fairness reports",
            "evidence.pct_with_explainability": "Experiments/models with explainability outputs"
        },
        "example_input": {
            "metric_id": "sm.clarify_coverage_band",
            "rubric": "Both dimensions must be considered.",
            "evidence": {"pct_with_bias_report": 0.78, "pct_with_explainability": 0.81}
        },
        "example_output": {
            "metric_id": "sm.clarify_coverage_band",
            "band": 3,
            "rationale": "Both ≥0.70; bias <0.80 caps at 3.",
            "flags": ["bias_coverage_low"],
            "gaps": ["Raise bias_report coverage to ≥0.80"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "sm.cost_efficiency_band": {
        "system": _rubric_text(
            "Use together: per_1k_inferences_usd, per_training_hour_usd, gpu_mem_headroom_pct, idle_vs_active_ratio.\n"
            "Heuristics target cost-efficiency + healthy utilization (not too low headroom, not too idle).\n"
            "Band 5: per_1k ≤ 0.08 AND train_hour ≤ 4 AND headroom in [10,40] AND idle_ratio < 0.20.\n"
            "Band 4: per_1k ≤ 0.10 AND train_hour ≤ 6 AND headroom in [8,45] AND idle_ratio < 0.30.\n"
            "Band 3: mixed signals (some strong, some weak) but no severe waste; idle_ratio < 0.45.\n"
            "Band 2: evident inefficiency (per_1k > 0.12 OR train_hour > 8 OR headroom < 5 or > 55 OR idle_ratio ≥ 0.45).\n"
            "Band 1: heavy waste across several dimensions."
        ),
        "input_key_meanings": {
            "evidence.per_1k_inferences_usd": "Serving cost per 1k inferences (USD)",
            "evidence.per_training_hour_usd": "Training cost per compute hour (USD)",
            "evidence.gpu_mem_headroom_pct": "Available GPU memory during peak usage (%)",
            "evidence.idle_vs_active_ratio": "Idle time ÷ active time over the window"
        },
        "example_input": {
            "metric_id": "sm.cost_efficiency_band",
            "rubric": "All four fields jointly determine the band.",
            "evidence": {"per_1k_inferences_usd": 0.065, "per_training_hour_usd": 3.2, "gpu_mem_headroom_pct": 28, "idle_vs_active_ratio": 0.18}
        },
        "example_output": {
            "metric_id": "sm.cost_efficiency_band",
            "band": 5,
            "rationale": "Low costs, healthy headroom, low idle.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # =========================
    # CI/CD (DORA + policy)
    # =========================

    "cicd.deploy_frequency_band": {
        "system": _rubric_text(
            "Use: freq_per_week and service_count together; approx per-service rate = freq_per_week / max(service_count,1).\n"
            "Band 5: per-service ≳ 1/day (≥ 5 per week per service) OR freq_per_week ≥ 5 with ≤ 7 services.\n"
            "Band 4: per-service weekly+ (≥ 1 per week per service) OR freq_per_week ≥ 3.\n"
            "Band 3: monthly-ish cadence across services (≥ 0.25 per week per service) OR freq_per_week ≥ 1.\n"
            "Band 2: sporadic (< monthly per service) but some activity.\n"
            "Band 1: rare or no deployments."
        ),
        "input_key_meanings": {
            "evidence.freq_per_week": "Total deployments per week across ML services",
            "evidence.service_count": "Number of ML services managed"
        },
        "example_input": {
            "metric_id": "cicd.deploy_frequency_band",
            "context": "ML services in consulting org",
            "rubric": "Both overall and per-service cadence matter.",
            "evidence": {"freq_per_week": 5.2, "service_count": 7}
        },
        "example_output": {
            "metric_id": "cicd.deploy_frequency_band",
            "band": 5,
            "rationale": "≈daily overall with moderate number of services.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "cicd.lead_time_band": {
        "system": _rubric_text(
            "Use: p50_hours and p95_hours (both must be met for higher bands).\n"
            "Band 5: p50 ≤ 4h AND p95 ≤ 24h.\n"
            "Band 4: p50 ≤ 8h AND p95 ≤ 48h.\n"
            "Band 3: p50 ≤ 24h AND p95 ≤ 72h.\n"
            "Band 2: partial (one passes but not the other) OR p95 ≤ 96h with weak p50.\n"
            "Band 1: slower than those thresholds."
        ),
        "input_key_meanings": {
            "evidence.p50_hours": "Median (p50) lead time from commit to prod",
            "evidence.p95_hours": "p95 lead time from commit to prod"
        },
        "example_input": {
            "metric_id": "cicd.lead_time_band",
            "rubric": "Both p50 and p95 matter together.",
            "evidence": {"p50_hours": 6.8, "p95_hours": 18.2}
        },
        "example_output": {
            "metric_id": "cicd.lead_time_band",
            "band": 4,
            "rationale": "p50 <8h and p95 <24h fits band 4.",
            "flags": [],
            "gaps": ["Lower p50 to ≤4h for band 5"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "cicd.change_failure_rate_band": {
        "system": _rubric_text(
            "Use together: cfr and rollbacks_30d. Prefer the worse dimension.\n"
            "Band 5: cfr < 0.15 AND rollbacks_30d ≤ 3.\n"
            "Band 4: cfr < 0.20 AND rollbacks_30d ≤ 5.\n"
            "Band 3: cfr < 0.30 AND rollbacks_30d ≤ 8.\n"
            "Band 2: cfr < 0.40 OR rollbacks_30d ≤ 12.\n"
            "Band 1: worse than those."
        ),
        "input_key_meanings": {
            "evidence.cfr": "Change failure rate for prod deployments",
            "evidence.rollbacks_30d": "Rollback count over the last 30 days"
        },
        "example_input": {
            "metric_id": "cicd.change_failure_rate_band",
            "rubric": "CFR and rollbacks jointly determine the band.",
            "evidence": {"cfr": 0.11, "rollbacks_30d": 3}
        },
        "example_output": {
            "metric_id": "cicd.change_failure_rate_band",
            "band": 5,
            "rationale": "Low CFR with limited rollbacks.",
            "flags": [],
            "gaps": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    "cicd.policy_gates_band": {
        "system": _rubric_text(
            "Inputs: required_checks[], workflow_yaml (text), logs_snippets[].\n"
            "Check presence of each required check in the YAML and whether logs_snippets show it passed.\n"
            "Populate arrays: present, missing, failing.\n"
            "Band 5: ALL required checks present AND passing before deploy.\n"
            "Band 4: ALL present, but ≤1 failing/flaky indicated in logs.\n"
            "Band 3: ≥50% present/passing; some missing or failing.\n"
            "Band 2: <50% present/passing; many missing/failing.\n"
            "Band 1: Most missing with no evidence of enforcement."
        ),
        "input_key_meanings": {
            "required_checks[]": "List of mandatory CI gates (e.g., pytest, bandit, trivy, ...)",
            "workflow_yaml": "CI workflow text used to infer which checks exist and when they run",
            "logs_snippets[]": "Build/deploy log lines used to infer pass/fail"
        },
        "example_input": {
            "metric_id": "cicd.policy_gates_band",
            "required_checks": ["pytest", "integration-tests", "bandit", "trivy", "bias_check", "data_validation"],
            "workflow_yaml": "jobs:\n  build:\n    steps:\n      - run: pytest\n      - run: bandit -r .\n      - run: trivy fs .\n      - run: make data_validation\n      - run: make bias_check\n  deploy:\n    needs: build\n    steps:\n      - run: ./deploy.sh",
            "logs_snippets": ["pytest passed", "bandit 0 issues", "trivy no HIGH|CRITICAL", "data_validation ok", "bias_check ok", "integration-tests flaky"],
            "rubric": "Band by presence+passing per the scheme above."
        },
        "example_output": {
            "metric_id": "cicd.policy_gates_band",
            "band": 4,
            "rationale": "All present; integration-tests flaky in logs.",
            "present": ["pytest", "bandit", "trivy", "bias_check", "data_validation", "integration-tests"],
            "missing": [],
            "failing": ["integration-tests"],
            "gaps": ["Deflake integration-tests or make it blocking pre-deploy"]
        },
        "response_format": POLICY_GATES_RESPONSE_FORMAT,
    },
}


# -----------------------
# Prompt builder and LLM
# -----------------------

def build_prompt(metric_id: str, task_input: dict) -> str:
    meta = METRIC_PROMPTS.get(metric_id)
    if not meta:
        raise ValueError(f"Unknown metric_id: {metric_id}")
    key_meanings = meta.get("input_key_meanings", {})
    key_lines = [f"- {k}: {v}" for k, v in key_meanings.items()]
    meanings_block = "INPUT KEY MEANINGS:\n" + "\n".join(key_lines) + "\n\n" if key_lines else ""
    return (
        f"{meta['system']}\n\n"
        f"{meanings_block}"
        f"RESPONSE FORMAT (JSON only):\n{meta['response_format']}\n\n"
        f"EVIDENCE (USER):\n{json.dumps(task_input, indent=2)}\n\n"
        f"EXAMPLE INPUT:\n{json.dumps(meta.get('example_input', {}), indent=2)}\n\n"
        f"EXAMPLE OUTPUT:\n{json.dumps(meta.get('example_output', {}), indent=2)}"
    )


class MLOpsLLM(BaseMicroAgent):
    def grade_metric(self, metric_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        _ = METRIC_PROMPTS[metric_id]  # fail fast if unknown
        prompt = build_prompt(metric_id, evidence)
        return self._ask(metric_id=metric_id, user_prompt=prompt)

    def _ask(self, *, metric_id: str, user_prompt: str, max_tokens: int = 700) -> Dict[str, Any]:
        time.sleep(random.uniform(0.02, 0.07))
        raw = self._call_llm(system_prompt="", prompt=user_prompt, max_tokens=max_tokens)
        try:
            out = self._parse_json_response(raw) or {}
        except Exception:
            out = {}

        # Always stamp the metric_id
        out["metric_id"] = metric_id

        # Coerce to the expected band (1–5). Accept "band" or fallback to "score".
        try:
            band_val = int(out.get("band", out.get("score", 3)))
        except Exception:
            band_val = 3
        out["band"] = max(1, min(5, band_val))

        # Remove any accidental BI-style fields but KEEP gaps now
        out.pop("score", None)
        out.pop("evidence", None)
        out.pop("actions", None)
        out.pop("confidence", None)

        # Ensure schema-specific fields
        if metric_id == "cicd.policy_gates_band":
            out.setdefault("rationale", "No rationale.")
            out.setdefault("present", [])
            out.setdefault("missing", [])
            out.setdefault("failing", [])
            out.setdefault("gaps", [])
            out.pop("flags", None)
        else:
            out.setdefault("rationale", "No rationale.")
            out.setdefault("flags", [])
            out.setdefault("gaps", [])

        return out

    # ---- Wrapper methods (1:1 with your LLM-used functions) ----
    def grade_mlflow_experiment_completeness(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.experiment_completeness_band", evidence)

    def grade_mlflow_lineage_coverage(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.lineage_coverage_band", evidence)

    def grade_mlflow_experiment_velocity(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.experiment_velocity_band", evidence)

    def grade_mlflow_registry_governance(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.registry_hygiene_band", evidence)

    def grade_mlflow_validation_artifacts(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.validation_artifacts_band", evidence)

    def grade_mlflow_reproducibility(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mlflow.reproducibility_band", evidence)

    def grade_aml_endpoint_slo(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("aml.endpoint_slo_band", evidence)

    def grade_aml_jobs_flow(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("aml.jobs_flow_band", evidence)

    def grade_aml_monitoring_coverage(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("aml.monitoring_coverage_band", evidence)

    def grade_aml_registry_governance(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("aml.registry_governance_band", evidence)

    def grade_aml_cost_correlation(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("aml.cost_correlation_band", evidence)

    def grade_sm_endpoint_slo_scaling(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sm.endpoint_slo_scaling_band", evidence)

    def grade_sm_pipeline_flow(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sm.pipeline_flow_band", evidence)

    def grade_sm_experiments_lineage(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sm.experiments_lineage_band", evidence)

    def grade_sm_clarify_coverage(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sm.clarify_coverage_band", evidence)

    def grade_sm_cost_efficiency(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sm.cost_efficiency_band", evidence)

    def grade_cicd_deploy_frequency(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("cicd.deploy_frequency_band", evidence)

    def grade_cicd_lead_time(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("cicd.lead_time_band", evidence)

    def grade_cicd_change_failure_rate(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("cicd.change_failure_rate_band", evidence)

    def check_cicd_policy_gates(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("cicd.policy_gates_band", evidence)

    # Parity with your BI engine
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"status": "ok"}