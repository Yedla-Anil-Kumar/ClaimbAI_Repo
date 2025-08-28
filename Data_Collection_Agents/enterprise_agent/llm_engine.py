# Data_Collection_Agents/enterprise_agent/llm_engine.py
from __future__ import annotations
import json
import random
import time
from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent


"""
Enterprise Systems Metric Grader — ONE-SHOT (per metric)

- Universal preamble + per-metric rubric
- Each metric includes: example_input AND example_output (true one-shot)
- build_prompt prints the RESPONSE FORMAT before EXAMPLES to reduce anchoring
- Public API: one wrapper method per metric (20 total)
"""


# Universal grading contract

UNIVERSAL_PREAMBLE = (
    "You are an Enterprise Systems Assessor. Score exactly one metric on a 1–5 scale:\n"
    "5 = Excellent\n"
    "4 = Good\n"
    "3 = Fair\n"
    "2 = Poor\n"
    "1 = Critical\n\n"
    "Rules:\n"
    "- Use ONLY the provided JSON evidence/rubric. Do NOT invent data.\n"
    "- Be conservative when values are borderline.\n"
    "- Keep rationale <= 3 sentences.\n"
    "- Return ONLY JSON in the specified format. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = '{"Score":<1-5>,"Rationale":"<1-3 sentences>"}'


def _rubric(text: str) -> str:
    return f"SYSTEM:\n{UNIVERSAL_PREAMBLE}\n\nRUBRIC:\n{text}"



# Metric definitions (20 one-shot graders)

METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # ---------- 1) Business Process & Workflow (1–10) ----------
    "process.automation.coverage": {
        "system": _rubric(
            "Coverage ratio of automated objects/workflows across Salesforce, SAP BPM, Workday, ServiceNow.\n"
            "- 5: >=0.85 across ≥3 platforms with regular executions\n"
            "- 4: 0.70–0.84 across ≥2 platforms, moderate execution volume\n"
            "- 3: 0.50–0.69, siloed/patchy automations\n"
            "- 2: 0.30–0.49, sporadic automations\n"
            "- 1: <0.30"
        ),
        "example_input": {
            "computed": {
                "sf_active_flows": 8,
                "sn_active_flows": 4,
                "wd_enabled_bps": 3,
                "sap_bpm_runs_7d": 300,
                "estimated_automated_objects": 22,
                "estimated_total_objects": 25,
                "coverage_ratio": 0.88,
            }
        },
        "example_output": {
            "MetricID": "process.automation.coverage",
            "Score": 5,
            "Rationale": "High coverage across platforms with strong execution volume.",
            "Value": 0.88,
            "Unit": "ratio",
            "Details": {
                "sf_active_flows": 8,
                "sn_active_flows": 4,
                "wd_enabled_bps": 3,
                "sap_bpm_runs_7d": 300,
            },
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "workflow.sla_adherence": {
        "system": _rubric(
            "On-time rate vs SLA for SF Cases, SN Incidents, SAP tickets, Workday tasks.\n"
            "- 5: >=0.95 on-time\n- 4: 0.90–0.94\n- 3: 0.80–0.89\n- 2: 0.60–0.79\n- 1: <0.60"
        ),
        "example_input": {
            "computed": {
                "on_time": 190,
                "total": 200,
                "by_system": {"SF": 0.97, "SN": 0.96, "SAP": 0.93, "WD": 0.95},
            }
        },
        "example_output": {
            "MetricID": "workflow.sla_adherence",
            "Score": 5,
            "Rationale": "Excellent on-time performance across all platforms.",
            "Value": 0.95,
            "Unit": "ratio",
            "Details": {"on_time": 190, "total": 200},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sales.lead_to_oppty_cycle_time": {
        "system": _rubric(
            "Median hours from lead creation to opportunity creation/qualification (lower is better).\n"
            "- 5: <=12h\n- 4: 13–24h\n- 3: 25–48h\n- 2: 49–96h\n- 1: >96h"
        ),
        "example_input": {"computed": {"median_hours": 10, "p90_hours": 20, "sample": 500}},
        "example_output": {
            "MetricID": "sales.lead_to_oppty_cycle_time",
            "Score": 5,
            "Rationale": "Very fast conversion; minimal tail.",
            "Value": 10,
            "Unit": "hours",
            "Details": {"median_hours": 10, "p90_hours": 20, "sample": 500},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "itsm.case_resolution_time": {
        "system": _rubric(
            "Median minutes to resolve incidents/requests in ServiceNow (lower is better).\n"
            "- 5: <=45m\n- 4: 46–90m\n- 3: 91–180m\n- 2: 181–360m\n- 1: >360m"
        ),
        "example_input": {"computed": {"median_minutes": 40, "p90_minutes": 70, "n_resolved": 500}},
        "example_output": {
            "MetricID": "itsm.case_resolution_time",
            "Score": 5,
            "Rationale": "Rapid resolution with minimal tail risk.",
            "Value": 40,
            "Unit": "minutes",
            "Details": {"median_minutes": 40, "p90_minutes": 70, "n_resolved": 500},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "itsm.incident_reopen_rate": {
        "system": _rubric(
            "Share of incidents reopened within 7d of resolution (lower is better).\n"
            "- 5: <=2%\n- 4: 2–7%\n- 3: 8–12%\n- 2: 13–20%\n- 1: >20%"
        ),
        "example_input": {
            "computed": {
                "rate": 0.015,
                "reopened": 9,
                "resolved": 600,
                "by_priority": {"1": 0.02, "2": 0.015, "3": 0.01},
            }
        },
        "example_output": {
            "MetricID": "itsm.incident_reopen_rate",
            "Score": 5,
            "Rationale": "Exceptional first-time fix.",
            "Value": 0.015,
            "Unit": "ratio",
            "Details": {"reopened": 9, "resolved": 600},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "hr.onboarding_cycle_time": {
        "system": _rubric(
            "Workday Hire BP start→complete median hours (lower is better).\n"
            "- 5: <=24h\n- 4: 25–48h\n- 3: 49–72h\n- 2: 73–120h\n- 1: >120h"
        ),
        "example_input": {"computed": {"median_hours": 20, "p90_hours": 36, "n_hires": 60}},
        "example_output": {
            "MetricID": "hr.onboarding_cycle_time",
            "Score": 5,
            "Rationale": "Fast onboarding with streamlined approvals.",
            "Value": 20,
            "Unit": "hours",
            "Details": {"median_hours": 20, "p90_hours": 36, "n_hires": 60},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sap.procure_to_pay_cycle": {
        "system": _rubric(
            "Total days from PO creation → approval → GR → invoice posted (lower is better).\n"
            "- 5: <=5d\n- 4: 6–8d\n- 3: 9–12d\n- 2: 13–20d\n- 1: >20d"
        ),
        "example_input": {
            "computed": {"total_days": 4.5, "approval_days": 0.5, "gr_days": 2.0, "invoice_days": 2.0}
        },
        "example_output": {
            "MetricID": "sap.procure_to_pay_cycle",
            "Score": 5,
            "Rationale": "Very efficient approvals, prompt GR and invoicing.",
            "Value": 4.5,
            "Unit": "days",
            "Details": {"approval_days": 0.5, "gr_days": 2.0, "invoice_days": 2.0},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "q2c.throughput": {
        "system": _rubric(
            "Quote approval → Sales Order → Billing total hours (lower is better for time-to-cash).\n"
            "- 5: <=12h\n- 4: 13–24h\n- 3: 25–48h\n- 2: 49–96h\n- 1: >96h"
        ),
        "example_input": {
            "computed": {"total_hours": 10, "quote_to_so_hours": 4, "so_to_bill_hours": 6}
        },
        "example_output": {
            "MetricID": "q2c.throughput",
            "Score": 5,
            "Rationale": "Extremely fast Q2C.",
            "Value": 10,
            "Unit": "hours",
            "Details": {"quote_to_so_hours": 4, "so_to_bill_hours": 6},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "backlog.aging": {
        "system": _rubric(
            "Median age of open work and tail risk across SN/WD/SAP (lower is better).\n"
            "- 5: p50 <= 1d & p90 <= 3d\n- 4: p50 <= 2d & p90 <= 5d\n- 3: p50 <= 3d & p90 <= 7d\n- 2: p50 <= 5d or p90 <= 10d\n- 1: worse"
        ),
        "example_input": {"computed": {"p50_days": 0.8, "p90_days": 2.5, "open_items": 200}},
        "example_output": {
            "MetricID": "backlog.aging",
            "Score": 5,
            "Rationale": "Backlog turns quickly; minimal tail risk.",
            "Value": 0.8,
            "Unit": "days (p50)",
            "Details": {"p50_days": 0.8, "p90_days": 2.5, "open_items": 200},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "rpa.success_rate": {
        "system": _rubric(
            "Reliability of RPA runs overall and by system (higher is better).\n"
            "- 5: >= 98%\n- 4: 93–97%\n- 3: 85–92%\n- 2: 70–84%\n- 1: <70%"
        ),
        "example_input": {
            "computed": {
                "rate": 0.985,
                "success": 985,
                "failed": 15,
                "by_system": {"SAP": 0.98, "SF": 0.99},
            }
        },
        "example_output": {
            "MetricID": "rpa.success_rate",
            "Score": 5,
            "Rationale": "Exceptional reliability overall and per-system.",
            "Value": 0.985,
            "Unit": "ratio",
            "Details": {"success": 985, "failed": 15},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 2) Integration & Data Health (11–15) ----------
    "integration.data_sync_latency": {
        "system": _rubric(
            "Latency between source and target delivery in iPaaS events (lower is better).\n"
            "- 5: median <=30s & p95 <=60s\n- 4: median <=90s & p95 <=180s\n- 3: median <=300s\n- 2: median <=900s\n- 1: worse"
        ),
        "example_input": {"computed": {"median_sec": 25, "p95_sec": 55, "failed_pct": 0.0}},
        "example_output": {
            "MetricID": "integration.data_sync_latency",
            "Score": 5,
            "Rationale": "Near-real-time sync with tight tail.",
            "Value": 25,
            "Unit": "seconds (median)",
            "Details": {"median_sec": 25, "p95_sec": 55, "failed_pct": 0.0},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "api.reliability": {
        "system": _rubric(
            "API latency vs SLO and error rates across endpoints (higher is better).\n"
            "- 5: p95 within SLO & error_rate <= 0.5%\n- 4: slightly under SLO or 0.5–1%\n"
            "- 3: marginal SLO misses or 1–2%\n- 2: frequent SLO misses or 2–5%\n- 1: severe degradation"
        ),
        "example_input": {"computed": {"p95_ms": 300, "error_rate_pct": 0.1, "rps": 120}},
        "example_output": {
            "MetricID": "api.reliability",
            "Score": 5,
            "Rationale": "Well within SLOs with headroom.",
            "Value": 0.999,
            "Unit": "ratio (proxy)",
            "Details": {"p95_ms": 300, "error_rate_pct": 0.1, "rps": 120},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "integration.topology_health": {
        "system": _rubric(
            "Overall health of integration nodes/edges: uptime, retry storms, dead-letter rate.\n"
            "- 5: >=99.9% uptime across nodes, no critical errors\n- 4: minor instability in ≤1 node\n"
            "- 3: multiple nodes <99.5% or recurring errors\n- 2: frequent outages\n- 1: systemic failures"
        ),
        "example_input": {
            "computed": {"avg_uptime": 99.95, "nodes_healthy": 3, "nodes_total": 3, "critical_errors": 0}
        },
        "example_output": {
            "MetricID": "integration.topology_health",
            "Score": 5,
            "Rationale": "All nodes stable; no critical faults.",
            "Value": 0.9995,
            "Unit": "ratio (uptime avg)",
            "Details": {"nodes_healthy": 3, "nodes_total": 3, "critical_errors": 0},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "mdm.duplicate_rate": {
        "system": _rubric(
            "Duplicate rate across CRM/SAP/MDM matched entities (lower is better).\n"
            "- 5: <=2%\n- 4: 3–5%\n- 3: 6–10%\n- 2: 11–20%\n- 1: >20%"
        ),
        "example_input": {"computed": {"rate": 0.02, "duplicate_groups": 10, "total_entities": 500}},
        "example_output": {
            "MetricID": "mdm.duplicate_rate",
            "Score": 5,
            "Rationale": "Very low duplicates; strong standardization and MDM controls.",
            "Value": 0.02,
            "Unit": "ratio",
            "Details": {"duplicate_groups": 10, "total_entities": 500},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "dq.exceptions_rate": {
        "system": _rubric(
            "Weighted exception rate by rule severity across systems (lower is better).\n"
            "- 5: <=1%\n- 4: 1–3%\n- 3: 3–6%\n- 2: 6–10%\n- 1: >10%"
        ),
        "example_input": {
            "computed": {"rate": 0.008, "failed_checks": 20, "total_checks": 2500, "weighted_severity": 0.8}
        },
        "example_output": {
            "MetricID": "dq.exceptions_rate",
            "Score": 5,
            "Rationale": "Excellent data quality; minimal high-severity breaches.",
            "Value": 0.008,
            "Unit": "ratio",
            "Details": {"failed_checks": 20, "total_checks": 2500, "weighted_severity": 0.8},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 3) AI Integration & Outcomes (16–18) ----------
    "ai.penetration": {
        "system": _rubric(
            "Coverage of workflows using AI features and their execution share (higher is better).\n"
            "- 5: >=75% workflows & >=75% executions\n- 4: 50–74%\n- 3: 30–49%\n- 2: 10–29%\n- 1: <10%"
        ),
        "example_input": {
            "computed": {"workflows_with_ai": 80, "workflows_total": 100, "executions_ai_pct": 0.78}
        },
        "example_output": {
            "MetricID": "ai.penetration",
            "Score": 5,
            "Rationale": "Widespread AI adoption across workflows and runs.",
            "Value": 0.8,
            "Unit": "ratio (coverage)",
            "Details": {"executions_ai_pct": 0.78},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "ai.outcome_uplift": {
        "system": _rubric(
            "Before/after KPI improvement attributable to AI rollout (higher is better).\n"
            "- 5: >=20% uplift with stability\n- 4: 10–19%\n- 3: 5–9%\n- 2: 1–4%\n- 1: <1% or negative"
        ),
        "example_input": {"computed": {"uplift_pct": 0.25, "baseline": 200, "post": 150}},
        "example_output": {
            "MetricID": "ai.outcome_uplift",
            "Score": 5,
            "Rationale": "Substantial improvement attributable to AI with stable trend.",
            "Value": 0.25,
            "Unit": "pct",
            "Details": {"baseline": 200, "post": 150},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "ai.governance_coverage": {
        "system": _rubric(
            "Share of models with required governance controls; alert context (higher is better).\n"
            "- 5: >=90%\n- 4: 75–89%\n- 3: 50–74%\n- 2: 25–49%\n- 1: <25%"
        ),
        "example_input": {
            "computed": {"coverage": 0.92, "models_with_all_controls": 46, "models_total": 50, "alerts_30d": 1}
        },
        "example_output": {
            "MetricID": "ai.governance_coverage",
            "Score": 5,
            "Rationale": "Excellent control coverage; few alerts.",
            "Value": 0.92,
            "Unit": "ratio",
            "Details": {"models_with_all_controls": 46, "models_total": 50, "alerts_30d": 1},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 4) Platform Health, Change & Risk (19–20) ----------
    "platform.customization_debt": {
        "system": _rubric(
            "Composite index from SF Apex/Flows, SN custom records, SAP transports, WD custom steps (lower is better).\n"
            "- 5: low footprint + stable change\n- 4: moderate-low\n- 3: moderate\n- 2: high\n- 1: very high/brittle"
        ),
        "example_input": {
            "computed": {"index": 0.25, "sf_apex": 40, "sn_custom_records": 5, "sap_transports_30d": 3, "wd_custom_steps": 1}
        },
        "example_output": {
            "MetricID": "platform.customization_debt",
            "Score": 5,
            "Rationale": "Lean custom footprint with disciplined change cadence.",
            "Value": 0.25,
            "Unit": "index",
            "Details": {"sf_apex": 40, "sn_custom_records": 5, "sap_transports_30d": 3, "wd_custom_steps": 1},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "change.failure_rate": {
        "system": _rubric(
            "Proportion of failed or rolled-back changes across platforms (lower is better).\n"
            "- 5: <=3%\n- 4: 4–7%\n- 3: 8–12%\n- 2: 13–20%\n- 1: >20%"
        ),
        "example_input": {"computed": {"rate": 0.02, "deploys": 200, "failed_or_rollback": 4}},
        "example_output": {
            "MetricID": "change.failure_rate",
            "Score": 5,
            "Rationale": "Excellent release reliability with robust gating.",
            "Value": 0.02,
            "Unit": "ratio",
            "Details": {"deploys": 200, "failed_or_rollback": 4},
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
}


def _build_prompt(metric_id: str, evidence: Dict[str, Any]) -> str:
    meta = METRIC_PROMPTS.get(metric_id)
    if not meta:
        raise ValueError(f"Unknown metric_id: {metric_id}")
    return (
        f"{meta['system']}\n\n"
        f"RESPONSE FORMAT (JSON only):\n{meta['response_format']}\n\n"
        f"TASK INPUT:\n{json.dumps(evidence, indent=2)}\n\n"
        f"ONE-SHOT EXAMPLE INPUT:\n{json.dumps(meta['example_input'], indent=2)}\n\n"
        f"ONE-SHOT EXAMPLE OUTPUT:\n{json.dumps(meta['example_output'], indent=2)}"
    )


class EnterpriseLLM(BaseMicroAgent):
    """One-shot JSON-in/JSON-out grader with 20 wrapper methods."""

    # ---- Internal LLM call ----
    def _ask(self, *, metric_id: str, user_prompt: str, max_tokens: int = 700) -> Dict[str, Any]:
        time.sleep(random.uniform(0.02, 0.06))
        raw = self._call_llm(system_prompt="", prompt=user_prompt, max_tokens=max_tokens)
        try:
            out = self._parse_json_response(raw) or {}
        except Exception:
            out = {}

        # Normalize shape
        metric_key = metric_id  # used to stamp MetricID if missing
        out.setdefault("MetricID", metric_key)
        try:
            score_val = int(out.get("Score", 3))
        except Exception:
            score_val = 3
        out["Score"] = max(1, min(5, score_val))
        out.setdefault("Rationale", "No rationale.")
        out.setdefault("Details", {})
        out.setdefault("Unit", None)
        out.setdefault("Value", None)
        out.setdefault("Window", {"Start": None, "End": None})

        # Strip accidental fields from chatty models
        for k in ("band", "flags", "gaps", "actions", "confidence"):
            out.pop(k, None)

        # Ensure MetricID consistency
        out["MetricID"] = metric_key
        return out

    # ---- Public API ----
    def grade_metric(self, metric_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        _ = METRIC_PROMPTS[metric_id]  # fail fast if unknown
        prompt = _build_prompt(metric_id, evidence)
        return self._ask(metric_id=metric_id, user_prompt=prompt)

    # ---- 20 wrappers (1:1) ----
    # 1–10
    def grade_process_automation_coverage(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("process.automation.coverage", e)

    def grade_workflow_sla_adherence(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("workflow.sla_adherence", e)

    def grade_sales_lead_to_oppty_cycle_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sales.lead_to_oppty_cycle_time", e)

    def grade_itsm_case_resolution_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("itsm.case_resolution_time", e)

    def grade_itsm_incident_reopen_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("itsm.incident_reopen_rate", e)

    def grade_hr_onboarding_cycle_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("hr.onboarding_cycle_time", e)

    def grade_sap_procure_to_pay_cycle(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sap.procure_to_pay_cycle", e)

    def grade_q2c_throughput(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("q2c.throughput", e)

    def grade_backlog_aging(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("backlog.aging", e)

    def grade_rpa_success_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("rpa.success_rate", e)

    # 11–15
    def grade_integration_data_sync_latency(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("integration.data_sync_latency", e)

    def grade_api_reliability(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("api.reliability", e)

    def grade_integration_topology_health(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("integration.topology_health", e)

    def grade_mdm_duplicate_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("mdm.duplicate_rate", e)

    def grade_dq_exceptions_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("dq.exceptions_rate", e)

    # 16–18
    def grade_ai_penetration(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.penetration", e)

    def grade_ai_outcome_uplift(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.outcome_uplift", e)

    def grade_ai_governance_coverage(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.governance_coverage", e)

    # 19–20
    def grade_platform_customization_debt(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("platform.customization_debt", e)

    def grade_change_failure_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("change.failure_rate", e)

    # parity with other agents
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"status": "ok"}
