# Data_Collection_Agents/enterprise_agent/llm_engine.py
from __future__ import annotations
import json
import time
import random
from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent


"""
Enterprise Systems Metric Grader — ONE-SHOT (per metric)

- Universal preamble + per-metric rubric
- Each metric entry includes: example_input AND example_output (true one-shot)
- build prompt prints the RESPONSE FORMAT before EXAMPLES to reduce anchoring
- Public API: one wrapper method per grading/check function (20 total)
"""

# =========================
# Universal grading contract
# =========================
UNIVERSAL_PREAMBLE = (
    "You are an Enterprise Systems Assessor. Grade exactly one metric on a 1–5 band:\n"
    "5 = Excellent\n"
    "4 = Good\n"
    "3 = Fair\n"
    "2 = Poor\n"
    "1 = Critical\n\n"
    "Rules:\n"
    "- Use ONLY the provided JSON evidence/rubric text. Do NOT invent data.\n"
    "- Be conservative when values are borderline.\n"
    "- Keep the rationale clear and short (≤3 sentences).\n"
    "- Return ONLY the specified JSON. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = (
    '{"metric_id":"<id>","band":<1-5>,"rationale":"<1-3 sentences>","flags":[]}'
)


def _rubric_text(text: str) -> str:
    return f"SYSTEM:\n{UNIVERSAL_PREAMBLE}\n\nRUBRIC:\n{text}"


# =========================
# Metric definitions (20 one-shot graders)
# NOTE: For “lower is better” metrics, rubric clarifies the direction.
# =========================
METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # ---------- 1) Business Process & Workflow (1–10) ----------
    "process.automation.coverage": {
        "system": _rubric_text(
            "Band by proportion of core workflows automated across SFDC/SAP/Workday/ServiceNow.\n"
            "5: >=0.80, 4: 0.65–0.79, 3: 0.45–0.64, 2: 0.25–0.44, 1: <0.25."
        ),
        "example_input": {"metric_id": "process.automation.coverage", "value": 0.73, "breakdown": {}},
        "example_output": {
            "metric_id": "process.automation.coverage",
            "band": 4,
            "rationale": "Automation coverage ~0.73 across key platforms.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "workflow.sla.adherence": {
        "system": _rubric_text(
            "Band by SLA hit rate across cases/tasks (higher is better).\n"
            "5: >=0.95, 4: 0.90–0.94, 3: 0.80–0.89, 2: 0.65–0.79, 1: <0.65."
        ),
        "example_input": {"metric_id": "workflow.sla.adherence", "value": 0.91},
        "example_output": {
            "metric_id": "workflow.sla.adherence",
            "band": 4,
            "rationale": "SLA adherence at ~0.91 indicates good operational performance.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sales.lead_to_oppty.cycle_time": {
        "system": _rubric_text(
            "Band by median hours from lead created to opportunity qualified (LOWER is better).\n"
            "5: <=12h, 4: 13–24h, 3: 25–48h, 2: 49–96h, 1: >96h."
        ),
        "example_input": {"metric_id": "sales.lead_to_oppty.cycle_time", "value": 27.5},
        "example_output": {
            "metric_id": "sales.lead_to_oppty.cycle_time",
            "band": 3,
            "rationale": "Median ~28h falls in the 25–48h band.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "service.case_resolution_time": {
        "system": _rubric_text(
            "Band by p50 resolution hours for customer cases (LOWER is better).\n"
            "5: <=8h, 4: 9–16h, 3: 17–36h, 2: 37–72h, 1: >72h."
        ),
        "example_input": {"metric_id": "service.case_resolution_time", "value": 14},
        "example_output": {
            "metric_id": "service.case_resolution_time",
            "band": 4,
            "rationale": "Median resolution ~14h meets the 9–16h band.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "service.incident_reopen_rate": {
        "system": _rubric_text(
            "Band by proportion of incidents reopened within 7d (LOWER is better).\n"
            "5: <0.03, 4: 0.03–0.06, 3: 0.07–0.10, 2: 0.11–0.15, 1: >0.15."
        ),
        "example_input": {"metric_id": "service.incident_reopen_rate", "value": 0.055},
        "example_output": {
            "metric_id": "service.incident_reopen_rate",
            "band": 4,
            "rationale": "Reopen rate ~5.5% is within the 3–6% band.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "hr.onboarding.cycle_time": {
        "system": _rubric_text(
            "Band by days from offer accept to day-1 ready (LOWER is better).\n"
            "5: <=5d, 4: 6–8d, 3: 9–12d, 2: 13–18d, 1: >18d."
        ),
        "example_input": {"metric_id": "hr.onboarding.cycle_time", "value": 7},
        "example_output": {
            "metric_id": "hr.onboarding.cycle_time",
            "band": 4,
            "rationale": "Onboarding cycle ~7 days is good.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "finance.procure_to_pay.cycle_time": {
        "system": _rubric_text(
            "Band by median days from PO to payment (LOWER is better).\n"
            "5: <=10d, 4: 11–15d, 3: 16–25d, 2: 26–40d, 1: >40d."
        ),
        "example_input": {"metric_id": "finance.procure_to_pay.cycle_time", "value": 18},
        "example_output": {
            "metric_id": "finance.procure_to_pay.cycle_time",
            "band": 3,
            "rationale": "Median ~18 days is fair; room to streamline approvals.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "sales.quote_to_cash.throughput": {
        "system": _rubric_text(
            "Band by orders per week per rep normalized (HIGHER is better).\n"
            "5: >=1.8, 4: 1.4–1.79, 3: 1.0–1.39, 2: 0.6–0.99, 1: <0.6."
        ),
        "example_input": {"metric_id": "sales.quote_to_cash.throughput", "value": 1.5},
        "example_output": {
            "metric_id": "sales.quote_to_cash.throughput",
            "band": 4,
            "rationale": "Throughput ~1.5 per rep/week is strong.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "backlog.aging": {
        "system": _rubric_text(
            "Band by share of items older than 30d (LOWER is better).\n"
            "5: <0.05, 4: 0.05–0.10, 3: 0.11–0.18, 2: 0.19–0.30, 1: >0.30."
        ),
        "example_input": {"metric_id": "backlog.aging", "value": 0.12},
        "example_output": {
            "metric_id": "backlog.aging",
            "band": 3,
            "rationale": "Aged backlog ~12% indicates moderate flow constraints.",
            "flags": ["aging_above_0_10"],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "rpa.success_rate": {
        "system": _rubric_text(
            "Band by successful unattended bot runs (HIGHER is better).\n"
            "5: >=0.97, 4: 0.93–0.96, 3: 0.85–0.92, 2: 0.70–0.84, 1: <0.70."
        ),
        "example_input": {"metric_id": "rpa.success_rate", "value": 0.94},
        "example_output": {
            "metric_id": "rpa.success_rate",
            "band": 4,
            "rationale": "RPA success ~94% is good; investigate remaining failure modes.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 2) Integration & Data Health (11–15) ----------
    "integration.data_sync.latency": {
        "system": _rubric_text(
            "Band by p95 minutes between source and target sync (LOWER is better).\n"
            "5: <=5m, 4: 6–10m, 3: 11–30m, 2: 31–90m, 1: >90m."
        ),
        "example_input": {"metric_id": "integration.data_sync.latency", "value": 12},
        "example_output": {
            "metric_id": "integration.data_sync.latency",
            "band": 3,
            "rationale": "p95 sync latency ~12m is acceptable but could improve.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "integration.api.reliability": {
        "system": _rubric_text(
            "Band by 30d success rate of critical APIs (HIGHER is better).\n"
            "5: >=0.999, 4: 0.995–0.998, 3: 0.990–0.994, 2: 0.970–0.989, 1: <0.970."
        ),
        "example_input": {"metric_id": "integration.api.reliability", "value": 0.996},
        "example_output": {
            "metric_id": "integration.api.reliability",
            "band": 4,
            "rationale": "Reliability ~99.6% is strong; near elite.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "integration.topology.health": {
        "system": _rubric_text(
            "Composite band from fan-in/fan-out balance, retry storms, dead-letter rate (HIGHER is better).\n"
            "5: healthy on all, 4: minor issues, 3: mixed, 2: significant hot-spots, 1: frequent failures."
        ),
        "example_input": {"metric_id": "integration.topology.health", "value": 0.7},
        "example_output": {
            "metric_id": "integration.topology.health",
            "band": 4,
            "rationale": "Topology mostly healthy with minor retry pockets.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "data.duplicate_record_rate": {
        "system": _rubric_text(
            "Band by duplicate customer/account/contact rate (LOWER is better).\n"
            "5: <0.01, 4: 0.01–0.02, 3: 0.021–0.04, 2: 0.041–0.08, 1: >0.08."
        ),
        "example_input": {"metric_id": "data.duplicate_record_rate", "value": 0.03},
        "example_output": {
            "metric_id": "data.duplicate_record_rate",
            "band": 3,
            "rationale": "Duplicate rate ~3% requires dedup tuning/merging policies.",
            "flags": ["dedup_improvement"],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "data.dq_exceptions_rate": {
        "system": _rubric_text(
            "Band by proportion of nightly DQ checks that raise exceptions (LOWER is better).\n"
            "5: <0.02, 4: 0.02–0.05, 3: 0.051–0.10, 2: 0.101–0.20, 1: >0.20."
        ),
        "example_input": {"metric_id": "data.dq_exceptions_rate", "value": 0.06},
        "example_output": {
            "metric_id": "data.dq_exceptions_rate",
            "band": 3,
            "rationale": "Exceptions ~6% indicates moderate integrity gaps.",
            "flags": ["dq_followup"],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 3) AI Integration & Outcomes (16–18) ----------
    "ai.integration.penetration": {
        "system": _rubric_text(
            "Band by share of core processes using AI assistance/automation (HIGHER is better).\n"
            "5: >=0.70, 4: 0.50–0.69, 3: 0.30–0.49, 2: 0.15–0.29, 1: <0.15."
        ),
        "example_input": {"metric_id": "ai.integration.penetration", "value": 0.52},
        "example_output": {
            "metric_id": "ai.integration.penetration",
            "band": 4,
            "rationale": "AI present in ~52% of target processes.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "ai.outcome.uplift": {
        "system": _rubric_text(
            "Band by median uplift from AI features (conversion, handle time, accuracy).\n"
            "5: >=0.15, 4: 0.10–0.149, 3: 0.05–0.099, 2: 0.02–0.049, 1: <0.02."
        ),
        "example_input": {"metric_id": "ai.outcome.uplift", "value": 0.11},
        "example_output": {
            "metric_id": "ai.outcome.uplift",
            "band": 4,
            "rationale": "Median uplift ~11% across measured outcomes.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "ai.governance.coverage": {
        "system": _rubric_text(
            "Band by % models/use-cases with risk review, monitoring, and rollback plans.\n"
            "5: >=0.90, 4: 0.80–0.89, 3: 0.65–0.79, 2: 0.40–0.64, 1: <0.40."
        ),
        "example_input": {"metric_id": "ai.governance.coverage", "value": 0.82},
        "example_output": {
            "metric_id": "ai.governance.coverage",
            "band": 4,
            "rationale": "Governance coverage ~82% with formal reviews.",
            "flags": [],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },

    # ---------- 4) Platform Health, Change & Risk (19–20) ----------
    "platform.customization.debt": {
        "system": _rubric_text(
            "Band by normalized customization debt index (LOWER is better).\n"
            "5: <=0.20, 4: 0.21–0.35, 3: 0.36–0.55, 2: 0.56–0.75, 1: >0.75."
        ),
        "example_input": {"metric_id": "platform.customization.debt", "value": 0.42},
        "example_output": {
            "metric_id": "platform.customization.debt",
            "band": 3,
            "rationale": "Debt index ~0.42 is moderate; refactor legacy customizations.",
            "flags": ["custom_code_hotspots"],
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
    },
    "platform.change.failure.rate": {
        "system": _rubric_text(
            "Band by prod change failure rate over 30d (LOWER is better).\n"
            "5: <0.10, 4: 0.10–0.15, 3: 0.16–0.25, 2: 0.26–0.40, 1: >0.40."
        ),
        "example_input": {"metric_id": "platform.change.failure.rate", "value": 0.14},
        "example_output": {
            "metric_id": "platform.change.failure.rate",
            "band": 4,
            "rationale": "CFR ~14% aligns with good release hygiene.",
            "flags": [],
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
        f"EVIDENCE (USER):\n{json.dumps(evidence, indent=2)}\n\n"
        f"EXAMPLE INPUT:\n{json.dumps(meta['example_input'], indent=2)}\n\n"
        f"EXAMPLE OUTPUT:\n{json.dumps(meta['example_output'], indent=2)}"
    )


class EnterpriseLLM(BaseMicroAgent):
    """One-shot JSON-in/JSON-out grader with 20 wrapper methods."""

    def grade_metric(self, metric_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        _ = METRIC_PROMPTS[metric_id]  # fail fast if unknown
        prompt = _build_prompt(metric_id, evidence)
        return self._ask(metric_id=metric_id, user_prompt=prompt)
    
    def _ask(self, *, metric_id: str, user_prompt: str, max_tokens: int = 600) -> Dict[str, Any]:
        time.sleep(random.uniform(0.02, 0.06))
        raw = self._call_llm(system_prompt="", prompt=user_prompt, max_tokens=max_tokens)
        try:
            out = self._parse_json_response(raw) or {}
        except Exception:
            out = {}

        # Stamp and coerce
        out["metric_id"] = metric_id
        try:
            band_val = int(out.get("band", 3))
        except Exception:
            band_val = 3
        out["band"] = max(1, min(5, band_val))
        out.setdefault("rationale", "No rationale.")
        out.setdefault("flags", [])
        # Strip accidental fields (defensive)
        for k in ("score", "evidence", "gaps", "actions", "confidence"):
            out.pop(k, None)
        return out

    # ---- 20 wrappers (1:1) ----
    # 1–10
    def grade_process_automation_coverage(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("process.automation.coverage", e)

    def grade_workflow_sla_adherence(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("workflow.sla.adherence", e)

    def grade_sales_lead_to_oppty_cycle_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sales.lead_to_oppty.cycle_time", e)

    def grade_service_case_resolution_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("service.case_resolution_time", e)

    def grade_service_incident_reopen_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("service.incident_reopen_rate", e)

    def grade_hr_onboarding_cycle_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("hr.onboarding.cycle_time", e)

    def grade_finance_procure_to_pay_cycle_time(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("finance.procure_to_pay.cycle_time", e)

    def grade_sales_quote_to_cash_throughput(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("sales.quote_to_cash.throughput", e)

    def grade_backlog_aging(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("backlog.aging", e)

    def grade_rpa_success_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("rpa.success_rate", e)

    # 11–15
    def grade_integration_data_sync_latency(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("integration.data_sync.latency", e)

    def grade_integration_api_reliability(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("integration.api.reliability", e)

    def grade_integration_topology_health(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("integration.topology.health", e)

    def grade_data_duplicate_record_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("data.duplicate_record_rate", e)

    def grade_data_dq_exceptions_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("data.dq_exceptions_rate", e)

    # 16–18
    def grade_ai_integration_penetration(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.integration.penetration", e)

    def grade_ai_outcome_uplift(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.outcome.uplift", e)

    def grade_ai_governance_coverage(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("ai.governance.coverage", e)

    # 19–20
    def grade_platform_customization_debt(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("platform.customization.debt", e)

    def grade_platform_change_failure_rate(self, e: Dict[str, Any]) -> Dict[str, Any]:
        return self.grade_metric("platform.change.failure.rate", e)
    
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"status": "ok"}