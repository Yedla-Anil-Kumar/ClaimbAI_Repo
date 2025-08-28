# Data_Collection_Agents/enterprise_agent/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict


@dataclass
class EnterpriseInputs:
    """
    Canonical inputs for Enterprise Systems Monitor Agent (Agent 6).

    Each field should contain the JSON evidence for the corresponding metric. 
    Commonly:
      - Raw system payloads (e.g., SFDC, SAP, SNOW, Workday logs)
      - OR a compact {"computed": {...}} block prepared by your collector

    Metric IDs match the 'MetricID' keys used in prompts and outputs.
    """

    # --- Business Process & Workflow (1–10) ---
    process_automation_coverage: Dict[str, Any] = field(default_factory=dict)   # MetricID: process.automation.coverage
    workflow_sla_adherence: Dict[str, Any] = field(default_factory=dict)        # MetricID: workflow.sla_adherence
    lead_to_oppty_cycle_time: Dict[str, Any] = field(default_factory=dict)      # MetricID: sales.lead_to_oppty_cycle_time
    case_resolution_time_sn: Dict[str, Any] = field(default_factory=dict)       # MetricID: itsm.case_resolution_time
    incident_reopen_rate_sn: Dict[str, Any] = field(default_factory=dict)       # MetricID: itsm.incident_reopen_rate
    hr_onboarding_cycle_time: Dict[str, Any] = field(default_factory=dict)      # MetricID: hr.onboarding_cycle_time
    procure_to_pay_cycle_time: Dict[str, Any] = field(default_factory=dict)     # MetricID: sap.procure_to_pay_cycle
    q2c_throughput: Dict[str, Any] = field(default_factory=dict)                # MetricID: q2c.throughput
    backlog_aging: Dict[str, Any] = field(default_factory=dict)                 # MetricID: backlog.aging
    rpa_success_rate: Dict[str, Any] = field(default_factory=dict)              # MetricID: rpa.success_rate

    # --- Integration & Data Health (11–15) ---
    data_sync_latency: Dict[str, Any] = field(default_factory=dict)             # MetricID: integration.data_sync_latency
    api_reliability: Dict[str, Any] = field(default_factory=dict)               # MetricID: api.reliability
    integration_topology_health: Dict[str, Any] = field(default_factory=dict)   # MetricID: integration.topology_health
    duplicate_record_rate: Dict[str, Any] = field(default_factory=dict)         # MetricID: mdm.duplicate_rate
    dq_exceptions_rate: Dict[str, Any] = field(default_factory=dict)            # MetricID: dq.exceptions_rate

    # --- AI Integration & Outcomes (16–18) ---
    ai_integration_penetration: Dict[str, Any] = field(default_factory=dict)    # MetricID: ai.penetration
    ai_outcome_uplift: Dict[str, Any] = field(default_factory=dict)             # MetricID: ai.outcome_uplift
    ai_governance_coverage: Dict[str, Any] = field(default_factory=dict)        # MetricID: ai.governance_coverage

    # --- Platform Health, Change & Risk (19–20) ---
    customization_debt_index: Dict[str, Any] = field(default_factory=dict)      # MetricID: platform.customization_debt
    change_failure_rate: Dict[str, Any] = field(default_factory=dict)           # MetricID: change.failure_rate

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(blob: Dict[str, Any]) -> "EnterpriseInputs":
        allowed = set(EnterpriseInputs.__annotations__.keys())
        filtered = {k: v for k, v in blob.items() if k in allowed}
        return EnterpriseInputs(**filtered)
