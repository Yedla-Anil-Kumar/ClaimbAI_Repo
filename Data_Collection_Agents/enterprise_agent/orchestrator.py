# Data_Collection_Agents/enterprise_agent/orchestrator.py
from __future__ import annotations
from typing import Any, Dict

from .canonical import EnterpriseInputs
from .llm_engine import EnterpriseLLM


def _s(metric: Dict[str, Any]) -> float:
    """Coerce a metric dict's 'Score' to float (default 3.0)."""
    try:
        return float(metric.get("Score", 3))
    except Exception:
        return 3.0


class EnterpriseOrchestrator:
    """
    Single-file inputs → 20 metric graders → four rollups (1–5 average Scores):

      - process_maturity     (process & workflow KPIs)
      - integration_health   (integration & data KPIs)
      - ai_outcomes          (AI penetration & uplift & governance)
      - platform_risk        (customization debt & change failure)

    Usage:
      inputs = EnterpriseInputs.from_dict(json_blob)
      orch = EnterpriseOrchestrator(model="gpt-4o-mini", temperature=0.0)
      out = orch.analyze_inputs(inputs)
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 700):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = EnterpriseLLM(model=model, temperature=temperature)

    def analyze_inputs(self, ei: EnterpriseInputs) -> Dict[str, Any]:
        # ---- 20 explicit calls (no nested loops) ----
        m1 = self.llm.grade_process_automation_coverage(ei.process_automation_coverage)
        m2 = self.llm.grade_workflow_sla_adherence(ei.workflow_sla_adherence)
        m3 = self.llm.grade_sales_lead_to_oppty_cycle_time(ei.lead_to_oppty_cycle_time)
        m4 = self.llm.grade_itsm_case_resolution_time(ei.case_resolution_time_sn)
        m5 = self.llm.grade_itsm_incident_reopen_rate(ei.incident_reopen_rate_sn)
        m6 = self.llm.grade_hr_onboarding_cycle_time(ei.hr_onboarding_cycle_time)
        m7 = self.llm.grade_sap_procure_to_pay_cycle(ei.procure_to_pay_cycle_time)
        m8 = self.llm.grade_q2c_throughput(ei.q2c_throughput)
        m9 = self.llm.grade_backlog_aging(ei.backlog_aging)
        m10 = self.llm.grade_rpa_success_rate(ei.rpa_success_rate)

        m11 = self.llm.grade_integration_data_sync_latency(ei.data_sync_latency)
        m12 = self.llm.grade_api_reliability(ei.api_reliability)
        m13 = self.llm.grade_integration_topology_health(ei.integration_topology_health)
        m14 = self.llm.grade_mdm_duplicate_rate(ei.duplicate_record_rate)
        m15 = self.llm.grade_dq_exceptions_rate(ei.dq_exceptions_rate)

        m16 = self.llm.grade_ai_penetration(ei.ai_integration_penetration)
        m17 = self.llm.grade_ai_outcome_uplift(ei.ai_outcome_uplift)
        m18 = self.llm.grade_ai_governance_coverage(ei.ai_governance_coverage)

        m19 = self.llm.grade_platform_customization_debt(ei.customization_debt_index)
        m20 = self.llm.grade_change_failure_rate(ei.change_failure_rate)

        # ---- Assemble map (explicit keys) ----
        metrics = {
            m1["MetricID"]: m1,
            m2["MetricID"]: m2,
            m3["MetricID"]: m3,
            m4["MetricID"]: m4,
            m5["MetricID"]: m5,
            m6["MetricID"]: m6,
            m7["MetricID"]: m7,
            m8["MetricID"]: m8,
            m9["MetricID"]: m9,
            m10["MetricID"]: m10,
            m11["MetricID"]: m11,
            m12["MetricID"]: m12,
            m13["MetricID"]: m13,
            m14["MetricID"]: m14,
            m15["MetricID"]: m15,
            m16["MetricID"]: m16,
            m17["MetricID"]: m17,
            m18["MetricID"]: m18,
            m19["MetricID"]: m19,
            m20["MetricID"]: m20,
        }

        # ---- Rollups (weights tuned; sum ~1 per family) ----
        process_maturity = round(
            0.12 * _s(metrics.get("process.automation.coverage", {}))
            + 0.10 * _s(metrics.get("workflow.sla_adherence", {}))
            + 0.08 * _s(metrics.get("sales.lead_to_oppty_cycle_time", {}))
            + 0.08 * _s(metrics.get("itsm.case_resolution_time", {}))
            + 0.08 * _s(metrics.get("itsm.incident_reopen_rate", {}))
            + 0.10 * _s(metrics.get("hr.onboarding_cycle_time", {}))
            + 0.12 * _s(metrics.get("sap.procure_to_pay_cycle", {}))
            + 0.12 * _s(metrics.get("q2c.throughput", {}))
            + 0.10 * _s(metrics.get("backlog.aging", {}))
            + 0.10 * _s(metrics.get("rpa.success_rate", {})),
            2,
        )

        integration_health = round(
            0.22 * _s(metrics.get("integration.data_sync_latency", {}))
            + 0.22 * _s(metrics.get("api.reliability", {}))
            + 0.22 * _s(metrics.get("integration.topology_health", {}))
            + 0.17 * _s(metrics.get("mdm.duplicate_rate", {}))
            + 0.17 * _s(metrics.get("dq.exceptions_rate", {})),
            2,
        )

        ai_outcomes = round(
            0.38 * _s(metrics.get("ai.penetration", {}))
            + 0.34 * _s(metrics.get("ai.outcome_uplift", {}))
            + 0.28 * _s(metrics.get("ai.governance_coverage", {})),
            2,
        )

        platform_risk = round(
            0.50 * _s(metrics.get("platform.customization_debt", {}))
            + 0.50 * _s(metrics.get("change.failure_rate", {})),
            2,
        )

        return {
            "agent": "enterprise_systems",
            "scores": {
                "process_maturity": process_maturity,
                "integration_health": integration_health,
                "ai_outcomes": ai_outcomes,
                "platform_risk": platform_risk,
            },
            "metric_breakdown": metrics,
            "mode": "single_inputs_json",
        }