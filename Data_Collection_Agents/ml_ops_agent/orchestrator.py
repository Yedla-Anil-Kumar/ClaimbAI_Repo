from __future__ import annotations
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict

from .llm_engine import MLOpsLLM
from .canonical import MLOpsInputs

# -------- Utility --------
def _b(m: Dict[str, Any]) -> float:
    """Safely coerce the output band to float on [1..5], default 3.0."""
    try:
        return float(m.get("band", 3))
    except Exception:
        return 3.0


# -------- Orchestrator --------
class MLOpsOrchestrator:
    """
    Single-file inputs → 20 metric graders → AIMRI category rollups.

    Outputs are aligned to the AIMRI Categories in your PDF. Today we compute:
      - Category 3 (AI/ML Capabilities) with 5 sub-scores (3.1 .. 3.5)
      - Category 8 (Process Maturity) partial via CI/CD proxies (8.3, 8.4)
    All other categories are included with overall=None (not enough direct signals yet).
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 550):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = MLOpsLLM(model=model, temperature=temperature)

    def analyze_inputs(self, ml: MLOpsInputs) -> Dict[str, Any]:
        # ---- Build grading payloads (rubrics/policies baked as in your spec) ----

        # MLflow
        m1 = self.llm.grade_mlflow_experiment_completeness({
            "evidence": ml.mlflow_experiment_completeness or {},
            "rubric": {"5":"pct_all>=0.9","4":"pct_all>=0.8","3":"pct_all>=0.7","2":"pct_all>=0.5","1":"else"}
        })
        m2 = self.llm.grade_mlflow_lineage_coverage({
            "evidence": ml.mlflow_lineage_coverage or {},
            "rubric":{"5":"all>=0.95","4":"all>=0.85","3":"all>=0.7","2":"any<0.7","1":"all<0.5"}
        })
        m3 = self.llm.grade_mlflow_experiment_velocity({
            "evidence": ml.mlflow_best_run_trend or {},
            "rubric":"5 if improvement_rate_mom>=0.05 and experiments_per_week>=2; 4 if >=0.03 and >=1.5; 3 if >=0.01; else lower."
        })
        m4 = self.llm.grade_mlflow_registry_governance({
            "evidence": ml.mlflow_registry_hygiene or {},
            "policy":"All prod transitions approved; median<72h; minimal rollbacks.",
            "rubric":{"5":"pct_staged>=0.9 && pct_with_approver>=0.9 && latency<48 && rollbacks==0",
                      "4":"pct_staged>=0.8 && pct_with_approver>=0.8 && latency<72",
                      "3":">=0.7 && >=0.7 && <96","2":">=0.5","1":"else"}
        })
        m5 = self.llm.grade_mlflow_validation_artifacts({
            "evidence": ml.mlflow_validation_artifacts or {},
            "rubric":"5 if all three >=0.9; 4 if >=0.8; 3 if >=0.7; 2 if >=0.5; 1 else."
        })
        m6 = self.llm.grade_mlflow_reproducibility({
            "evidence": ml.mlflow_reproducibility or {},
            "rubric":{"5":"match_rate>=0.95","4":">=0.85","3":">=0.7","2":">=0.5","1":"else"}
        })

        # AML
        m7 = self.llm.grade_aml_endpoint_slo({
            "evidence": {"declared_slo": ml.declared_slo, **(ml.aml_endpoint_slo or {})},
            "rubric": "Higher bands as measured exceeds SLO by larger margins."
        })
        m8 = self.llm.grade_aml_jobs_flow({
            "evidence": ml.aml_jobs_flow or {},
            "rubric":"5 if success>=0.98 and lead_time<=4h; 4 if >=0.95 and <=8h; 3 if >=0.9 and <=24h; else lower."
        })
        m9 = self.llm.grade_aml_monitoring_coverage({
            "evidence": ml.aml_monitoring_coverage or {},
            "rubric":"5 if monitors enabled and ack<2h; 4 if ack<6h; 3 if enabled but slow; 1 if disabled."
        })
        m10 = self.llm.grade_aml_registry_governance({
            "evidence": ml.aml_registry_governance or {},
            "rubric":"5 if pct_staged>=0.9 & pct_with_approvals>=0.9 & median_transition_h<48; 4 if >=0.8 & <72; ..."
        })
        m11 = self.llm.grade_aml_cost_correlation({
            "evidence": ml.aml_cost_correlation or {},
            "rubric":"5 if join_rate>=0.9 and per-endpoint costs tracked; 3 if partial; 1 if none."
        })

        # SageMaker
        m12 = self.llm.grade_sm_endpoint_slo_scaling({
            "evidence": ml.sm_endpoint_slo_scaling or {},
            "rubric":"5 if availability>=0.999, p95<=200ms, reaction<=60s; 4 if close; ..."
        })
        m13 = self.llm.grade_sm_pipeline_flow({
            "evidence": ml.sm_pipeline_stats or {},
            "rubric":"5 if success>=0.98 and promotion<=8h; 4 if success>=0.95 and <=12h; 3 if >=0.9 and <=24h; ..."
        })
        m14 = self.llm.grade_sm_experiments_lineage({
            "evidence": ml.sm_experiments_lineage or {},
            "rubric":"5 if all>=0.95; 4 if all>=0.85; 3 if all>=0.7; ..."
        })
        m15 = self.llm.grade_sm_clarify_coverage({
            "evidence": ml.sm_clarify_coverage or {},
            "rubric":"5 if both>=0.9; 4 if both>=0.8; 3 if >=0.7; ..."
        })
        m16 = self.llm.grade_sm_cost_efficiency({
            "evidence": ml.sm_cost_efficiency or {},
            "rubric":"5 if low cost per 1k and good utilization (headroom 10–40%, idle<20%); 3 if mixed; 1 if wasteful."
        })

        # CI/CD
        m17 = self.llm.grade_cicd_deploy_frequency({
            "evidence": {"context":"ML services", **(ml.cicd_deploy_frequency or {})},
            "rubric":"Elite if daily+ per service; High if weekly; Medium if monthly."
        })
        m18 = self.llm.grade_cicd_lead_time({
            "evidence": ml.cicd_lead_time or {},
            "rubric":"5 if p50<=4h & p95<=24h; 4 if p50<=8h & p95<=48h; ..."
        })
        m19 = self.llm.grade_cicd_change_failure_rate({
            "evidence": ml.cicd_change_failure_rate or {},
            "rubric":"5 if CFR<0.15; 4 if <0.2; 3 if <0.3; else lower."
        })

        # Policy gates: use caller payload if complete; else assemble minimal one
        pg_payload = ml.cicd_policy_gates or {
            "required_checks": ml.policy_required_checks,
            "workflow_yaml": "",
            "logs_snippets": [],
            "rubric":"5 if all required checks exist and pass before deploy; 3 if partial; 1 if missing most."
        }
        m20 = self.llm.check_cicd_policy_gates(pg_payload)

        # Deterministic, no LLM: pass through (included in breakdown)
        artifact_lineage = ml.cicd_artifact_lineage or {
            "metric_id":"cicd.artifact_lineage","integrity_ok": False, "mismatches": []
        }

        metrics = [m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20]
        m = {x["metric_id"]: x for x in metrics}

        # ---- AIMRI Category computations (0–5 levels; using our 1–5 bands as-is) ----
        # Category 3 — AI/ML Capabilities (3.1–3.5)
        # 3.1 Model Development: experiment velocity + validation artifacts
        cat3_1 = round((0.55*_b(m3) + 0.45*_b(m5)), 2)

        # 3.2 Production Deployment: AML+SM endpoint SLO & jobs/pipeline flow
        cat3_2 = round((0.30*_b(m7) + 0.25*_b(m12) + 0.25*_b(m8) + 0.20*_b(m13)), 2)

        # 3.3 MLOps Maturity: lineage, reproducibility, job/pipeline maturity, DORA speed
        cat3_3 = round((0.20*_b(m2) + 0.20*_b(m6) + 0.20*_b(m8) + 0.20*_b(m13) + 0.20*_b(m18)), 2)

        # 3.4 Model Governance: registries + policy gates
        cat3_4 = round((0.45*_b(m4) + 0.35*_b(m10) + 0.20*_b(m20)), 2)

        # 3.5 Advanced Capabilities: explainability/bias & cost efficiency
        cat3_5 = round((0.60*_b(m15) + 0.40*_b(m16)), 2)

        cat3_overall = round((0.20*cat3_1 + 0.25*cat3_2 + 0.20*cat3_3 + 0.20*cat3_4 + 0.15*cat3_5), 2)

        # Category 8 — Process Maturity (8.1–8.5) via CI/CD proxies
        cat8_3 = round((0.65*_b(m19) + 0.35*_b(m20)), 2)  # QA: CFR + policy gates
        cat8_4 = round((0.50*_b(m18) + 0.50*_b(m17)), 2)  # Operational Excellence: lead time + deploy freq
        cat8_overall = round((0.55*cat8_4 + 0.45*cat8_3), 2)

        aimri = {
            "1_technical_infrastructure":       {"overall": None, "subs": {}},
            "2_data_management_quality":        {"overall": None, "subs": {}},
            "3_ai_ml_capabilities":             {
                "overall": cat3_overall,
                "subs": {
                    "3_1_model_development": cat3_1,
                    "3_2_production_deployment": cat3_2,
                    "3_3_mlops_maturity": cat3_3,
                    "3_4_model_governance": cat3_4,
                    "3_5_advanced_capabilities": cat3_5,
                }
            },
            "4_talent_skills":                  {"overall": None, "subs": {}},
            "5_governance_ethics":              {"overall": None, "subs": {}},
            "6_strategic_alignment":            {"overall": None, "subs": {}},
            "7_cultural_readiness":             {"overall": None, "subs": {}},
            "8_process_maturity":               {
                "overall": cat8_overall,
                "subs": {
                    "8_1_project_management": None,
                    "8_2_documentation_practices": None,
                    "8_3_quality_assurance": cat8_3,
                    "8_4_operational_excellence": cat8_4,
                    "8_5_measurement_metrics": None,
                }
            },
            "9_foundation_model_ops":           {"overall": None, "subs": {}},
            "10_generative_ai_capabilities":    {"overall": None, "subs": {}},
            "11_responsible_ai_social_impact":  {"overall": None, "subs": {}},
            "12_ai_business_value_roi":         {"overall": None, "subs": {}},
            "13_ai_risk_resilience":            {"overall": None, "subs": {}},
            "14_ai_ecosystem_external_integration": {"overall": None, "subs": {}},
            "15_ai_leadership_vision":          {"overall": None, "subs": {}},
        }

        return {
            "agent": "ml_ops",
            "inputs_summary": {
                "present": [k for k, v in ml.as_dict().items() if v and k not in ("declared_slo","policy_required_checks")],
                "declared_slo": ml.declared_slo,
                "policy_required_checks": ml.policy_required_checks
            },
            "aimri_scores": aimri,
            "metric_breakdown": {
                **m,
                "cicd.artifact_lineage": artifact_lineage
            },
            "mode": "single_inputs_json",
        }
