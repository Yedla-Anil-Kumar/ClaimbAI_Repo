# Data_Collection_Agents/enterprise_agent/orchestrator.py
from __future__ import annotations

from typing import Any, Dict

from .canonical import EnterpriseInputs
from .llm_engine import EnterpriseLLM


def _b(metric: Dict[str, Any]) -> float:
    """Coerce a metric dict's 'band' to float (default 3.0)."""
    try:
        return float(metric.get("band", 3))
    except Exception:
        return 3.0


class EnterpriseOrchestrator:
    """
    Single-file inputs → 20 metric graders → four rollups (1–5 band averages):

      - process_maturity     (process & workflow KPIs)
      - integration_health   (integration & data KPIs)
      - ai_outcomes          (AI penetration & uplift & governance)
      - platform_risk        (customization debt & change failure)

    Usage:
      inputs = EnterpriseInputs.from_dict(json_blob)
      orch = EnterpriseOrchestrator(model="gpt-4o-mini", temperature=0.0)
      out = orch.analyze_inputs(inputs)
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0,  max_tokens: int = 700):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = EnterpriseLLM(model=model, temperature=temperature)

    def analyze_inputs(self, ei: EnterpriseInputs) -> Dict[str, Any]:
        # ---- Call each grader explicitly (no nested loops; 1:1 mapping) ----
        m1 = self.llm.grade_process_automation_coverage(ei.process_automation_coverage)
        m2 = self.llm.grade_workflow_sla_adherence(ei.workflow_sla_adherence)
        m3 = self.llm.grade_sales_lead_to_oppty_cycle_time(ei.lead_to_oppty_cycle_time)
        m4 = self.llm.grade_service_case_resolution_time(ei.case_resolution_time_sn)
        m5 = self.llm.grade_service_incident_reopen_rate(ei.incident_reopen_rate_sn)
        m6 = self.llm.grade_hr_onboarding_cycle_time(ei.hr_onboarding_cycle_time)
        m7 = self.llm.grade_finance_procure_to_pay_cycle_time(ei.procure_to_pay_cycle_time)
        m8 = self.llm.grade_sales_quote_to_cash_throughput(ei.q2c_throughput)
        m9 = self.llm.grade_backlog_aging(ei.backlog_aging)
        m10 = self.llm.grade_rpa_success_rate(ei.rpa_success_rate)

        m11 = self.llm.grade_integration_data_sync_latency(ei.data_sync_latency)
        m12 = self.llm.grade_integration_api_reliability(ei.api_reliability)
        m13 = self.llm.grade_integration_topology_health(ei.integration_topology_health)
        m14 = self.llm.grade_data_duplicate_record_rate(ei.duplicate_record_rate)
        m15 = self.llm.grade_data_dq_exceptions_rate(ei.dq_exceptions_rate)

        m16 = self.llm.grade_ai_integration_penetration(ei.ai_integration_penetration)
        m17 = self.llm.grade_ai_outcome_uplift(ei.ai_outcome_uplift)
        m18 = self.llm.grade_ai_governance_coverage(ei.ai_governance_coverage)

        m19 = self.llm.grade_platform_customization_debt(ei.customization_debt_index)
        m20 = self.llm.grade_platform_change_failure_rate(ei.change_failure_rate)

        # ---- Assemble metric map (explicit keys, clear to read) ----
        metrics = {
            m1["metric_id"]: m1,
            m2["metric_id"]: m2,
            m3["metric_id"]: m3,
            m4["metric_id"]: m4,
            m5["metric_id"]: m5,
            m6["metric_id"]: m6,
            m7["metric_id"]: m7,
            m8["metric_id"]: m8,
            m9["metric_id"]: m9,
            m10["metric_id"]: m10,
            m11["metric_id"]: m11,
            m12["metric_id"]: m12,
            m13["metric_id"]: m13,
            m14["metric_id"]: m14,
            m15["metric_id"]: m15,
            m16["metric_id"]: m16,
            m17["metric_id"]: m17,
            m18["metric_id"]: m18,
            m19["metric_id"]: m19,
            m20["metric_id"]: m20,
        }

        # ---- Rollups (weights sum to ~1 within each family; tune as needed) ----
        process_maturity = round(
            0.12 * _b(metrics.get("process.automation.coverage", {}))
            + 0.10 * _b(metrics.get("workflow.sla.adherence", {}))
            + 0.08 * _b(metrics.get("sales.lead_to_oppty.cycle_time", {}))
            + 0.08 * _b(metrics.get("service.case_resolution_time", {}))
            + 0.08 * _b(metrics.get("service.incident_reopen_rate", {}))
            + 0.10 * _b(metrics.get("hr.onboarding.cycle_time", {}))
            + 0.12 * _b(metrics.get("finance.procure_to_pay.cycle_time", {}))
            + 0.12 * _b(metrics.get("sales.quote_to_cash.throughput", {}))
            + 0.10 * _b(metrics.get("backlog.aging", {}))
            + 0.10 * _b(metrics.get("rpa.success_rate", {})),
            2,
        )

        integration_health = round(
            0.22 * _b(metrics.get("integration.data_sync.latency", {}))
            + 0.22 * _b(metrics.get("integration.api.reliability", {}))
            + 0.22 * _b(metrics.get("integration.topology.health", {}))
            + 0.17 * _b(metrics.get("data.duplicate_record_rate", {}))
            + 0.17 * _b(metrics.get("data.dq_exceptions_rate", {})),
            2,
        )

        ai_outcomes = round(
            0.38 * _b(metrics.get("ai.integration.penetration", {}))
            + 0.34 * _b(metrics.get("ai.outcome.uplift", {}))
            + 0.28 * _b(metrics.get("ai.governance.coverage", {})),
            2,
        )

        platform_risk = round(
            0.50 * _b(metrics.get("platform.customization.debt", {}))
            + 0.50 * _b(metrics.get("platform.change.failure.rate", {})),
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
