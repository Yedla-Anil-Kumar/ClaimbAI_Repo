# Data_Collection_Agents/enterprise_agent/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass
class EnterpriseInputs:
    """
    Canonical inputs for Enterprise Systems Monitor Agent (Agent 6).
    Each field is the DIRECT output of a deterministic compute_* function
    or a raw dataset used to produce those outputs (your collectors fill these).
    """

    # --- Business Process & Workflow (1–10) ---
    process_automation_coverage: Dict[str, Any] = field(default_factory=dict)   # 1
    workflow_sla_adherence: Dict[str, Any] = field(default_factory=dict)        # 2
    lead_to_oppty_cycle_time: Dict[str, Any] = field(default_factory=dict)      # 3
    case_resolution_time_sn: Dict[str, Any] = field(default_factory=dict)       # 4
    incident_reopen_rate_sn: Dict[str, Any] = field(default_factory=dict)       # 5
    hr_onboarding_cycle_time: Dict[str, Any] = field(default_factory=dict)      # 6
    procure_to_pay_cycle_time: Dict[str, Any] = field(default_factory=dict)     # 7
    q2c_throughput: Dict[str, Any] = field(default_factory=dict)                # 8
    backlog_aging: Dict[str, Any] = field(default_factory=dict)                 # 9
    rpa_success_rate: Dict[str, Any] = field(default_factory=dict)              # 10

    # --- Integration & Data Health (11–15) ---
    data_sync_latency: Dict[str, Any] = field(default_factory=dict)             # 11
    api_reliability: Dict[str, Any] = field(default_factory=dict)               # 12
    integration_topology_health: Dict[str, Any] = field(default_factory=dict)   # 13
    duplicate_record_rate: Dict[str, Any] = field(default_factory=dict)         # 14
    dq_exceptions_rate: Dict[str, Any] = field(default_factory=dict)            # 15

    # --- AI Integration & Outcomes (16–18) ---
    ai_integration_penetration: Dict[str, Any] = field(default_factory=dict)    # 16
    ai_outcome_uplift: Dict[str, Any] = field(default_factory=dict)             # 17
    ai_governance_coverage: Dict[str, Any] = field(default_factory=dict)        # 18

    # --- Platform Health, Change & Risk (19–20) ---
    customization_debt_index: Dict[str, Any] = field(default_factory=dict)      # 19
    change_failure_rate: Dict[str, Any] = field(default_factory=dict)           # 20

    # --- Optional (21–22) ---
    sales_forecast_accuracy: Dict[str, Any] = field(default_factory=dict)       # 21
    functional_adoption: Dict[str, Any] = field(default_factory=dict)           # 22

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(blob: Dict[str, Any]) -> "EnterpriseInputs":
        allowed = {f for f in EnterpriseInputs.__annotations__.keys()}
        filtered = {k: v for k, v in blob.items() if k in allowed}
        return EnterpriseInputs(**filtered)
