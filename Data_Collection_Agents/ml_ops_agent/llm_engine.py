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
"""

# =========================
# Universal grading contract
# =========================
UNIVERSAL_PREAMBLE = (
    "You are an MLOps Assessor. Grade exactly one metric on a 1–5 band:\n"
    "5 = Excellent\n"
    "4 = Good\n"
    "3 = Fair\n"
    "2 = Poor\n"
    "1 = Critical\n\n"
    "Rules:\n"
    "- Use ONLY the provided JSON evidence/rubric/policy text. Do NOT invent data.\n"
    "- Be consistent and conservative when values are borderline.\n"
    "- Keep the rationale clear and short (≤3 sentences).\n"
    "- Return ONLY the specified JSON. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"band":<1-5>,'
    '"rationale":"<1-3 sentences>",'
    '"flags":[]}'
)

POLICY_GATES_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"band":<1-5>,'
    '"rationale":"<1-3 sentences>",'
    '"present":[],'
    '"missing":[],'
    '"failing":[]}'
)

def _rubric_text(t: str) -> str:
    return f"SYSTEM:\n{UNIVERSAL_PREAMBLE}\n\nRUBRIC:\n{t}"

# =========================
# Metric definitions (20 LLM-used graders/checkers) — ONE SHOT
# =========================
METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # ---- MLflow ----
    "mlflow.experiment_completeness_band": {
        "system": _rubric_text(
            "Bands: 5 if pct_all>=0.90; 4 if >=0.80; 3 if >=0.70; 2 if >=0.50; 1 otherwise."
        ),
        "example_input": {
            "metric_id": "mlflow.experiment_completeness_band",
            "rubric": {"5":"pct_all>=0.9","4":"pct_all>=0.8","3":"pct_all>=0.7","2":"pct_all>=0.5","1":"else"},
            "evidence": {"pct_all":0.82,"pct_params":0.90,"pct_metrics":0.82,"pct_tags":0.81,"pct_artifacts":0.75}
        },
        "example_output": {
            "metric_id": "mlflow.experiment_completeness_band",
            "band": 4,
            "rationale": "~82% of runs meet all criteria; artifacts coverage is lowest.",
            "flags": []
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mlflow.lineage_coverage_band": {
        "system": _rubric_text(
            "Consider pct_git_sha, pct_data_ref, pct_env_files.\n"
            "5 if all>=0.95; 4 if all>=0.85; 3 if all>=0.70; 2 if any<0.70; 1 if all<0.50."
        ),
        "example_input": {
            "metric_id":"mlflow.lineage_coverage_band",
            "rubric":{"5":"all>=0.95","4":"all>=0.85","3":"all>=0.7","2":"any<0.7","1":"all<0.5"},
            "evidence":{"pct_git_sha":0.93,"pct_data_ref":0.84,"pct_env_files":0.91}
        },
        "example_output": {
            "metric_id":"mlflow.lineage_coverage_band",
            "band": 3,
            "rationale":"Data-ref coverage (~0.84) limits the score.",
            "flags":["data_ref_coverage"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mlflow.experiment_velocity_band": {
        "system": _rubric_text(
            "Use improvement_rate_mom and experiments_per_week.\n"
            "5 if rate>=0.05 and exp/wk>=2; 4 if >=0.03 and >=1.5; 3 if >=0.01; else lower."
        ),
        "example_input": {
            "metric_id":"mlflow.experiment_velocity_band",
            "rubric":"5 if improvement_rate_mom>=0.05 and experiments_per_week>=2; 4 if >=0.03 and >=1.5; 3 if >=0.01; else lower.",
            "evidence":{"improvement_rate_mom":0.06,"experiments_per_week":2.2}
        },
        "example_output": {
            "metric_id":"mlflow.experiment_velocity_band",
            "band": 5,
            "rationale":"Strong improvement with healthy cadence.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mlflow.registry_hygiene_band": {
        "system": _rubric_text(
            "Policy: All prod transitions approved; median<72h; minimal rollbacks.\n"
            "5 if staged>=0.9 & approver>=0.9 & latency<48h & rollbacks==0;\n"
            "4 if staged>=0.8 & approver>=0.8 & latency<72h;\n"
            "3 if >=0.7 & >=0.7 & <96h; 2 if >=0.5; else 1."
        ),
        "example_input": {
            "metric_id":"mlflow.registry_hygiene_band",
            "policy":"All prod transitions approved; median<72h; minimal rollbacks.",
            "rubric":{"5":"...","4":"...","3":"...","2":"...","1":"else"},
            "evidence":{"pct_staged":0.83,"pct_with_approver":0.88,"median_stage_latency_h":60,"rollback_count_30d":1}
        },
        "example_output": {
            "metric_id":"mlflow.registry_hygiene_band",
            "band": 4,
            "rationale":"Meets approval and latency; some rollbacks present.",
            "flags":["rollback_present"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mlflow.validation_artifacts_band": {
        "system": _rubric_text(
            "Use coverage of shap/bias/validation.\n"
            "5 if all three >=0.90; 4 if >=0.80; 3 if >=0.70; 2 if >=0.50; 1 else."
        ),
        "example_input": {
            "metric_id":"mlflow.validation_artifacts_band",
            "rubric":"5 if all three >=0.9; 4 if >=0.8; 3 if >=0.7; 2 if >=0.5; 1 else.",
            "evidence":{"pct_with_shap":0.75,"pct_with_bias_report":0.72,"pct_with_validation_json":0.84}
        },
        "example_output": {
            "metric_id":"mlflow.validation_artifacts_band",
            "band": 3,
            "rationale":"Validation files present; bias/SHAP coverage below 0.8 caps score.",
            "flags":["bias_coverage_low","shap_coverage_low"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mlflow.reproducibility_band": {
        "system": _rubric_text(
            "Use match_rate; note signature_conflicts in flags if present.\n"
            "5 if >=0.95; 4 if >=0.85; 3 if >=0.70; 2 if >=0.50; else 1."
        ),
        "example_input": {
            "metric_id":"mlflow.reproducibility_band",
            "rubric":{"5":"match_rate>=0.95","4":">=0.85","3":">=0.7","2":">=0.5","1":"else"},
            "evidence":{"match_rate":0.88,"signature_conflicts":[{"signature":"abc","runs":["r1","r8"],"metric_diff":0.025}]}
        },
        "example_output": {
            "metric_id":"mlflow.reproducibility_band",
            "band": 4,
            "rationale":"High match rate; minor conflicts.",
            "flags":["conflicts_present"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---- Azure ML (AML) ----
    "aml.endpoint_slo_band": {
        "system": _rubric_text(
            "Compare measured vs declared SLO (availability, p95_ms, error_rate). "
            "Higher bands as measured exceeds SLO by larger margins."
        ),
        "example_input": {
            "metric_id":"aml.endpoint_slo_band",
            "declared_slo":{"availability":0.995,"p95_ms":300,"error_rate":0.01},
            "evidence":{"availability_30d":0.997,"p95_ms":215,"error_rate":0.003}
        },
        "example_output": {
            "metric_id":"aml.endpoint_slo_band",
            "band": 5,
            "rationale":"All SLOs exceeded.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "aml.jobs_flow_band": {
        "system": _rubric_text(
            "Use success_rate, p95_duration_min, lead_time_hours.\n"
            "5 if success>=0.98 & lead_time<=4h; 4 if >=0.95 & <=8h; 3 if >=0.90 & <=24h; else lower."
        ),
        "example_input": {
            "metric_id":"aml.jobs_flow_band",
            "rubric":"5 if success>=0.98 and lead_time<=4h; 4 if >=0.95 and <=8h; 3 if >=0.9 and <=24h; else lower.",
            "evidence":{"success_rate":0.94,"p95_duration_min":38,"lead_time_hours":6.4}
        },
        "example_output": {
            "metric_id":"aml.jobs_flow_band",
            "band": 3,
            "rationale":"Success below 0.95; lead-time moderate.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "aml.monitoring_coverage_band": {
        "system": _rubric_text(
            "Use monitors_enabled and median_time_to_ack_h.\n"
            "5 if enabled and ack<2h; 4 if <6h; 3 if enabled but slow; 1 if disabled."
        ),
        "example_input": {
            "metric_id":"aml.monitoring_coverage_band",
            "rubric":"5 if monitors enabled and ack<2h; 4 if ack<6h; 3 if enabled but slow; 1 if disabled.",
            "evidence":{"monitors_enabled":True,"drift_alerts_30d":2,"median_time_to_ack_h":1.2}
        },
        "example_output": {
            "metric_id":"aml.monitoring_coverage_band",
            "band": 5,
            "rationale":"Monitors enabled with fast ack (<2h).",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "aml.registry_governance_band": {
        "system": _rubric_text(
            "Use pct_staged, pct_with_approvals, median_transition_h.\n"
            "5 if staged>=0.9 & approvals>=0.9 & median<48h; 4 if >=0.8 & <72h; 3 next; etc."
        ),
        "example_input": {
            "metric_id":"aml.registry_governance_band",
            "rubric":"5 if pct_staged>=0.9 & pct_with_approvals>=0.9 & median_transition_h<48; 4 if >=0.8 & <72; ...",
            "evidence":{"pct_staged":0.83,"pct_with_approvals":0.88,"median_transition_h":60}
        },
        "example_output": {
            "metric_id":"aml.registry_governance_band",
            "band": 4,
            "rationale":"≥0.8 thresholds met; median <72h.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "aml.cost_correlation_band": {
        "system": _rubric_text(
            "Use cost_join_rate and attribution detail.\n"
            "5 if join_rate>=0.9 and per-endpoint costs tracked; 3 if partial; 1 if none."
        ),
        "example_input": {
            "metric_id":"aml.cost_correlation_band",
            "rubric":"5 if join_rate>=0.9 and per-endpoint costs tracked; 3 if partial; 1 if none.",
            "evidence":{"cost_join_rate":0.93,"cost_per_1k_requests":0.087,"coverage":"tags+resourceId"}
        },
        "example_output": {
            "metric_id":"aml.cost_correlation_band",
            "band": 5,
            "rationale":"High join rate with per-endpoint attribution.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---- SageMaker (SM) ----
    "sm.endpoint_slo_scaling_band": {
        "system": _rubric_text(
            "Use availability, p95_ms, median_reaction_s, max_rps_at_slo.\n"
            "5 if availability>=0.999, p95<=200ms, reaction<=60s; 4 if close; etc."
        ),
        "example_input": {
            "metric_id":"sm.endpoint_slo_scaling_band",
            "rubric":"5 if availability>=0.999, p95<=200ms, reaction<=60s; 4 if close; ...",
            "evidence":{"availability_30d":0.999,"error_rate":0.002,"p95_ms":180,"median_reaction_s":55,"max_rps_at_slo":950}
        },
        "example_output": {
            "metric_id":"sm.endpoint_slo_scaling_band",
            "band": 5,
            "rationale":"Meets elite thresholds (availability, latency, reaction).",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sm.pipeline_flow_band": {
        "system": _rubric_text(
            "Use success_rate, p95_duration_min, retry_rate, promotion_time_h.\n"
            "5 if success>=0.98 and promotion<=8h; 4 if success>=0.95 and <=12h; 3 if >=0.9 and <=24h; ..."
        ),
        "example_input": {
            "metric_id":"sm.pipeline_flow_band",
            "rubric":"5 if success>=0.98 and promotion<=8h; 4 if success>=0.95 and <=12h; 3 if >=0.9 and <=24h; ...",
            "evidence":{"success_rate":0.96,"p95_duration_min":42,"retry_rate":0.03,"promotion_time_h":12.0}
        },
        "example_output": {
            "metric_id":"sm.pipeline_flow_band",
            "band": 4,
            "rationale":"High success; promotion within 12h.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sm.experiments_lineage_band": {
        "system": _rubric_text(
            "Use pct_code_ref, pct_data_ref, pct_env.\n"
            "5 if all>=0.95; 4 if all>=0.85; 3 if all>=0.7; etc."
        ),
        "example_input": {
            "metric_id":"sm.experiments_lineage_band",
            "rubric":"5 if all>=0.95; 4 if all>=0.85; 3 if all>=0.7; ...",
            "evidence":{"pct_code_ref":0.90,"pct_data_ref":0.86,"pct_env":0.92}
        },
        "example_output": {
            "metric_id":"sm.experiments_lineage_band",
            "band": 4,
            "rationale":"All dimensions ≥0.85; data refs ~0.86 cap at 4.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sm.clarify_coverage_band": {
        "system": _rubric_text(
            "Use pct_with_bias_report and pct_with_explainability.\n"
            "5 if both>=0.9; 4 if both>=0.8; 3 if >=0.7; ..."
        ),
        "example_input": {
            "metric_id":"sm.clarify_coverage_band",
            "rubric":"5 if both>=0.9; 4 if both>=0.8; 3 if >=0.7; ...",
            "evidence":{"pct_with_bias_report":0.78,"pct_with_explainability":0.81}
        },
        "example_output": {
            "metric_id":"sm.clarify_coverage_band",
            "band": 3,
            "rationale":"Explainability ~0.81; bias <0.8 keeps score at 3.",
            "flags":["bias_coverage_low"]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sm.cost_efficiency_band": {
        "system": _rubric_text(
            "Use per_1k_inferences_usd, per_training_hour_usd, gpu_mem_headroom_pct, idle_vs_active_ratio.\n"
            "5 if low per-1k and healthy utilization (headroom 10–40%, idle<20%); 3 if mixed; 1 if wasteful."
        ),
        "example_input": {
            "metric_id":"sm.cost_efficiency_band",
            "rubric":"5 if low cost per 1k and good utilization (headroom 10–40%, idle<20%); 3 if mixed; 1 if wasteful.",
            "evidence":{"per_1k_inferences_usd":0.065,"per_training_hour_usd":3.2,"gpu_mem_headroom_pct":28,"idle_vs_active_ratio":0.18}
        },
        "example_output": {
            "metric_id":"sm.cost_efficiency_band",
            "band": 5,
            "rationale":"Low per-1k with healthy headroom and low idle time.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---- CI/CD (DORA + policy) ----
    "cicd.deploy_frequency_band": {
        "system": _rubric_text(
            "Use frequency per week and service_count in context.\n"
            "Elite if ~daily per service; High if weekly; Medium if monthly."
        ),
        "example_input": {
            "metric_id":"cicd.deploy_frequency_band",
            "context":"ML services in consulting org",
            "rubric":"Elite if daily+ per service; High if weekly; Medium if monthly.",
            "evidence":{"freq_per_week":5.2,"service_count":7}
        },
        "example_output": {
            "metric_id":"cicd.deploy_frequency_band",
            "band": 5,
            "rationale":"~daily deploys across services.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "cicd.lead_time_band": {
        "system": _rubric_text(
            "Use p50_hours and p95_hours.\n"
            "5 if p50<=4h & p95<=24h; 4 if p50<=8h & p95<=48h; etc."
        ),
        "example_input": {
            "metric_id":"cicd.lead_time_band",
            "rubric":"5 if p50<=4h & p95<=24h; 4 if p50<=8h & p95<=48h; ...",
            "evidence":{"p50_hours":6.8,"p95_hours":18.2}
        },
        "example_output": {
            "metric_id":"cicd.lead_time_band",
            "band": 4,
            "rationale":"Median <8h and p95 <24h meet band-4.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "cicd.change_failure_rate_band": {
        "system": _rubric_text(
            "Use CFR and rollbacks_30d.\n"
            "5 if CFR<0.15; 4 if <0.20; 3 if <0.30; else lower."
        ),
        "example_input": {
            "metric_id":"cicd.change_failure_rate_band",
            "rubric":"5 if CFR<0.15; 4 if <0.2; 3 if <0.3; else lower.",
            "evidence":{"cfr":0.11,"rollbacks_30d":3}
        },
        "example_output": {
            "metric_id":"cicd.change_failure_rate_band",
            "band": 5,
            "rationale":"CFR below 0.15.",
            "flags":[]
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "cicd.policy_gates_band": {
        "system": _rubric_text(
            "Verify required checks from workflow YAML + logs. Band 5 if all required checks exist and pass before deploy; "
            "3 if partial; 1 if missing most. Populate present/missing/failing arrays explicitly."
        ),
        "example_input": {
            "metric_id":"cicd.policy_gates_band",
            "required_checks":["pytest","integration-tests","bandit","trivy","bias_check","data_validation"],
            "workflow_yaml":"<yaml>",
            "logs_snippets":["..."],
            "rubric":"5 if all required checks exist and pass before deploy; 3 if partial; 1 if missing most."
        },
        "example_output": {
            "metric_id":"cicd.policy_gates_band",
            "band": 4,
            "rationale":"All checks present; integration-tests flaky in logs.",
            "present":["pytest","bandit","trivy","bias_check","data_validation","integration-tests"],
            "missing":[],
            "failing":["integration-tests"]
        },
        "response_format": POLICY_GATES_RESPONSE_FORMAT,
    },
}

def build_prompt(metric_id: str, task_input: dict) -> str:
    meta = METRIC_PROMPTS.get(metric_id)
    if not meta:
        raise ValueError(f"Unknown metric_id: {metric_id}")
    return (
        f"{meta['system']}\n\n"
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

        # Remove any accidental BI-style fields
        out.pop("score", None)
        out.pop("evidence", None)
        out.pop("gaps", None)
        out.pop("actions", None)
        out.pop("confidence", None)

        # Ensure schema-specific fields
        if metric_id == "cicd.policy_gates_band":
            out.setdefault("rationale", "No rationale.")
            out.setdefault("present", [])
            out.setdefault("missing", [])
            out.setdefault("failing", [])
            out.pop("flags", None)
        else:
            out.setdefault("rationale", "No rationale.")
            out.setdefault("flags", [])

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
