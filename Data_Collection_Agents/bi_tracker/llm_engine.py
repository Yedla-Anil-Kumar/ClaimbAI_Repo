from __future__ import annotations
import json
import time
import random
from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent

"""
BI Metric Prompt Builder
- Universal preamble & unified response JSON (1–5 scale)
- Each metric has: system rubric, example_input, input_key_meanings, example_output
- build_prompt prints RESPONSE FORMAT before EXAMPLES (reduces anchoring)
- BIUsageLLM wraps build_prompt so existing orchestrator methods still work
"""

# =========================
# Universal scoring contract
# =========================
UNIVERSAL_PREAMBLE = (
    "You are a Business Intelligence (BI) Assessor. Score exactly one BI metric on a 1-5 scale:\n"
    "5 = Excellent (exceeds target, no material risks)\n"
    "4 = Good (meets target, minor risks)\n"
    "3 = Fair (near target, clear risks to address)\n"
    "2 = Poor (misses target, material risks)\n"
    "1 = Critical (significant failure, urgent action)\n\n"
    "Rules:\n"
    "- Use only the provided data. If required inputs are missing, list them under 'gaps', reduce 'confidence', and adjust the score downward.\n"
    "- Prefer normalized rates (0..1), explicit denominators, and p95/p99 where relevant. Put raw numbers under 'evidence'.\n"
    "- Keep actions concrete (≤5), prioritized (P0/P1/P2), and focused on next steps.\n"
    "- Return ONLY the specified JSON. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"score":<1-5>,'
    '"rationale":"<2-4 sentences>",'
    '"evidence":{},'
    '"gaps":[],'
    '"actions":[{"priority":"P0|P1|P2","action":"..."}],'
    '"confidence":<0.0-1.0>'
)

# =========================
# Metric definitions (10 BI metrics)
# =========================
METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # 1) DAU/MAU stickiness
    "usage.dau_mau": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (stickiness = DAU/MAU):\n"
            "- 5: ≥0.60 with stable 7d DAU and positive trend\n"
            "- 4: 0.45–0.59 with stable 7d DAU\n"
            "- 3: 0.30–0.44 or unstable week\n"
            "- 2: 0.15–0.29 or declining trend\n"
            "- 1: <0.15 or severe drop"
        ),
        "example_input": {
            "today": "2025-08-01",
            "activity_events": [
                {"ts": "2025-08-01T10:00:00Z", "user_id": "u1", "action": "view", "content_id": "d1"},
                {"ts": "2025-07-22T10:00:00Z", "user_id": "u2", "action": "view", "content_id": "d2"}
            ]
        },
        "input_key_meanings": {
            "today": "ISO date for 'today' (YYYY-MM-DD)",
            "activity_events": "Array of events in last 30d",
            "activity_events[].user_id": "User identifier",
            "activity_events[].ts": "Event timestamp (ISO)",
            "activity_events[].action": "view/explore/edit"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.dau_mau",
            "score": 4,
            "rationale": "Stickiness near 0.55 with steady 7d activity and no drop-off.",
            "evidence": {"dau": 120, "mau": 220, "stickiness": 0.545},
            "gaps": [],
            "actions": [{"priority": "P2", "action": "Promote weekly digest to sustain DAU"}],
            "confidence": 0.86
        }
    },

    # 2) Active viewers vs creators
    "usage.creators_ratio": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (creator share among actives):\n"
            "- 5: ≥35% creators and well distributed\n"
            "- 4: 25–34% creators with fair spread\n"
            "- 3: 15–24% or skewed to one team\n"
            "- 2: 8–14% creators\n"
            "- 1: <8% creators"
        ),
        "example_input": {
            "usage_logs": [
                {"user": "u1", "role": "viewer"},
                {"user": "u2", "role": "creator"}
            ]
        },
        "input_key_meanings": {
            "usage_logs": "Array of active users with effective roles",
            "usage_logs[].role": "'creator' or 'viewer'"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.creators_ratio",
            "score": 4,
            "rationale": "Creator share around 30% with decent department spread.",
            "evidence": {"creator_share": 0.30, "active_users": 200},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Offer creator training cohorts per BU"}],
            "confidence": 0.84
        }
    },

    # 3) Session depth & duration
    "usage.session_depth": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (duration, pages, repeat):\n"
            "- 5: ≥300s avg, ≥4 pages, weekly repeats\n"
            "- 4: ~250–299s, ~3–4 pages\n"
            "- 3: ~150–249s, ~2–3 pages\n"
            "- 2: ~90–149s, ~1–2 pages\n"
            "- 1: <90s, ≤1 page"
        ),
        "example_input": {
            "session_logs": [
                {"user": "u1", "duration": 320, "pages": 4, "repeats_per_week": 2},
                {"user": "u2", "duration": 180, "pages": 3}
            ]
        },
        "input_key_meanings": {
            "session_logs": "Array of session aggregates per user",
            "session_logs[].duration": "Seconds per session",
            "session_logs[].pages": "Pages per session"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.session_depth",
            "score": 4,
            "rationale": "Average session length and depth meet targets with moderate repeat frequency.",
            "evidence": {"avg_duration_s": 270, "avg_pages": 3.6},
            "gaps": [],
            "actions": [{"priority": "P2", "action": "Add 'related content' panels to increase depth"}],
            "confidence": 0.82
        }
    },

    # 4) Drill-down usage
    "usage.drilldown": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (% sessions using drill + spread + stability):\n"
            "- 5: ≥35% sessions include drill; broad spread; stable\n"
            "- 4: 25–34% with fair spread\n"
            "- 3: 15–24% or narrow spread\n"
            "- 2: 8–14%\n"
            "- 1: <8%"
        ),
        "example_input": {"interaction_logs": [{"user": "u1", "action": "drill"}]},
        "input_key_meanings": {
            "interaction_logs": "Array of interactions; 'action' includes 'drill'/'drilldown'"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.drilldown",
            "score": 3,
            "rationale": "Drill featured in ~18% of sessions with limited distribution.",
            "evidence": {"pct_sessions_with_drilldown": 0.18},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Add guided drill paths on top dashboards"}],
            "confidence": 0.8
        }
    },

    # 5) Refresh timeliness
    "reliability.refresh_timeliness": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (within SLA by cadence):\n"
            "- 5: ≥95% within SLA, 0 critical stale\n"
            "- 4: 85–94% within SLA, few stales\n"
            "- 3: 70–84% within SLA or some high-impact stales\n"
            "- 2: 50–69% within SLA or many stales\n"
            "- 1: <50% within SLA or chronic stales"
        ),
        "example_input": {
            "dashboards": [
                {"id": "d1", "last_refresh": "2025-07-31", "sla": "daily"},
                {"id": "d2", "last_refresh": "2025-07-28", "sla": "weekly"}
            ],
            "today": "2025-08-01"
        },
        "input_key_meanings": {
            "dashboards": "Array of dashboard freshness entries",
            "dashboards[].sla": "daily/weekly/monthly",
            "today": "ISO date for comparison"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "reliability.refresh_timeliness",
            "score": 4,
            "rationale": "Most dashboards meet declared cadence; few stale and low impact.",
            "evidence": {"within_sla_pct": 0.88, "failures": 3},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Add failure alerts for critical dashes"}],
            "confidence": 0.85
        }
    },

    # 6) Cross-dashboard linking
    "features.cross_links": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (presence + usage + distribution):\n"
            "- 5: ≥60% dashes have links; high traversal; broad spread\n"
            "- 4: 45–59% with moderate traversal\n"
            "- 3: 30–44% or limited spread\n"
            "- 2: 15–29%\n"
            "- 1: <15%"
        ),
        "example_input": {
            "dashboards": [
                {"id": "d1", "links": ["d2"], "link_usage": 15},
                {"id": "d2", "links": [], "link_usage": 0}
            ]
        },
        "input_key_meanings": {
            "dashboards": "Array of dashboards with 'links' and 'link_usage' counters"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "features.cross_links",
            "score": 3,
            "rationale": "Roughly one-third of dashboards have links; traversal moderate.",
            "evidence": {"dash_with_links_pct": 0.34, "link_usage_total": 180},
            "gaps": [],
            "actions": [{"priority": "P2", "action": "Add cross-links on top 10 reports"}],
            "confidence": 0.82
        }
    },

    # 7) Governance coverage
    "governance.coverage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (certified, owner, metadata completeness):\n"
            "- 5: ≥95% certified or owned with complete metadata\n"
            "- 4: 85–94% coverage\n"
            "- 3: 70–84% coverage\n"
            "- 2: 50–69% coverage\n"
            "- 1: <50% coverage"
        ),
        "example_input": {
            "dashboards": [
                {"id": "d1", "certified": True, "owner": "teamA", "metadata": ["description", "refresh_rate"]},
                {"id": "d2", "certified": False, "owner": None, "metadata": []}
            ]
        },
        "input_key_meanings": {
            "dashboards": "Array with certification/owner/metadata flags"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "governance.coverage",
            "score": 3,
            "rationale": "Certification improving; owners mostly assigned; metadata moderate.",
            "evidence": {"certified_pct": 0.55, "ownership_pct": 0.78, "metadata_completeness_pct": 0.50},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Complete metadata for top 50 dashboards"}],
            "confidence": 0.83
        }
    },

    # 8) Data source diversity
    "data.source_diversity": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (count + domain balance + new source trend):\n"
            "- 5: ≥8 sources across ≥3 domains with recent adds\n"
            "- 4: 6–7 sources across ≥3 domains\n"
            "- 3: 4–5 sources or 2 domains\n"
            "- 2: 2–3 sources, 1–2 domains\n"
            "- 1: Single source\n"
        ),
        "example_input": {"source_catalog": ["snowflake", "postgres", "salesforce"]},
        "input_key_meanings": {"source_catalog": "Distinct source systems used"},
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "data.source_diversity",
            "score": 3,
            "rationale": "Three sources across two domains; moderate diversity.",
            "evidence": {"distinct_sources": 3, "domain_count": 2},
            "gaps": [],
            "actions": [{"priority": "P2", "action": "Onboard a service desk and HRIS source"}],
            "confidence": 0.8
        }
    },

    # 9) Self-service adoption
    "democratization.self_service": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (creator share + growth + dept coverage):\n"
            "- 5: ≥35% creators with broad department coverage\n"
            "- 4: 25–34% creators\n"
            "- 3: 15–24% creators\n"
            "- 2: 8–14% creators\n"
            "- 1: <8% creators"
        ),
        "example_input": {"user_roles": [{"id": "u1", "role": "creator"}, {"id": "u2", "role": "viewer"}]},
        "input_key_meanings": {"user_roles": "Users and their roles ('creator'/'viewer')"},
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "democratization.self_service",
            "score": 3,
            "rationale": "Creator share around 22% with growing interest across departments.",
            "evidence": {"creator_share": 0.22},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Launch 'builder hour' sessions per BU"}],
            "confidence": 0.8
        }
    },

    # 10) Decision support traceability
    "decision.traceability": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (% decisions linked + evidence + recency):\n"
            "- 5: ≥70% decisions link dashboards with strong evidence, recent\n"
            "- 4: 55–69% with evidence\n"
            "- 3: 35–54% or mixed evidence\n"
            "- 2: 15–34%\n"
            "- 1: <15%"
        ),
        "example_input": {
            "decision_logs": [
                {"id": "dec1", "linked_dash": "sales_forecast", "evidence": "screenshot"},
                {"id": "dec2", "linked_dash": None, "evidence": None}
            ]
        },
        "input_key_meanings": {
            "decision_logs": "Array of decisions with optional dashboard references and evidence"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "decision.traceability",
            "score": 3,
            "rationale": "About half of decisions reference dashboards; evidence present in many cases.",
            "evidence": {"linked_pct": 0.5, "evidence_markers": "7/12"},
            "gaps": [],
            "actions": [{"priority": "P1", "action": "Adopt decision templates with dashboard links"}],
            "confidence": 0.82
        }
    },
}

def build_prompt(metric_id: str, task_input: dict) -> str:
    meta = METRIC_PROMPTS.get(metric_id)
    if not meta:
        raise ValueError(f"Unknown metric_id: {metric_id}")
    meanings = meta.get("input_key_meanings", {})
    key_meanings_str = "\n".join([f"- {k}: {v}" for k, v in meanings.items()]) if meanings else ""
    return (
        f"SYSTEM:\n{meta['system']}\n\n"
        f"INPUT JSON KEYS AND MEANINGS:\n{key_meanings_str}\n\n"
        f"TASK INPUT:\n{json.dumps(task_input, indent=2)}\n\n"
        f"RESPONSE FORMAT (JSON only):\n{meta['response_format']}\n\n"
        f"EXAMPLE INPUT:\n{json.dumps(meta['example_input'], indent=2)}\n\n"
        f"EXAMPLE OUTPUT:\n{json.dumps(meta['example_output'], indent=2)}"
    )

class BIUsageLLM(BaseMicroAgent):
    def _ask(self, user_prompt: str, max_tokens: int = 700) -> Dict[str, Any]:
        time.sleep(random.uniform(0.02, 0.07))
        raw = self._call_llm(system_prompt="", prompt=user_prompt, max_tokens=max_tokens)
        try:
            out = self._parse_json_response(raw) or {}
        except Exception:
            out = {}
        try:
            out["score"] = max(1, min(5, int(out.get("score", 3))))
        except Exception:
            out["score"] = 3
        out.setdefault("rationale", "No rationale.")
        out.setdefault("evidence", {})
        out.setdefault("gaps", [])
        out.setdefault("actions", [])
        out.setdefault("confidence", 0.5)
        return out

    def score_metric(self, metric_id: str, task_input: Dict[str, Any]) -> Dict[str, Any]:
        _ = METRIC_PROMPTS[metric_id]  # fail fast if unknown
        prompt = build_prompt(metric_id, task_input)
        return self._ask(prompt)

    # Backwards-compatible wrappers
    def score_dau_mau(self, activity_events: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("usage.dau_mau", {"activity_events": activity_events, "today": today})

    def score_active_creators(self, usage_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("usage.creators_ratio", {"usage_logs": usage_logs})

    def score_session_depth(self, session_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("usage.session_depth", {"session_logs": session_logs})

    def score_drilldown(self, interaction_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("usage.drilldown", {"interaction_logs": interaction_logs})

    def score_refresh_timeliness(self, dashboards: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("reliability.refresh_timeliness", {"dashboards": dashboards, "today": today})

    def score_cross_links(self, link_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("features.cross_links", {"dashboards": link_data})

    def score_governance_coverage(self, gov: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("governance.coverage", {"dashboards": gov})

    def score_source_diversity(self, sources: List[str]) -> Dict[str, Any]:
        return self.score_metric("data.source_diversity", {"source_catalog": sources})

    def score_self_service_adoption(self, user_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("democratization.self_service", {"user_roles": user_roles})

    def score_decision_traceability(self, decision_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("decision.traceability", {"decision_logs": decision_logs})

    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"status": "ok"}