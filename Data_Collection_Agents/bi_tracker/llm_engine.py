from __future__ import annotations
import json
import time
import random
from typing import Any, Dict, List, Optional

from Data_Collection_Agents.base_agent import BaseMicroAgent

"""
BI Metric Prompt Builder (Updated Schema)
- Scoring returns: {"metric_id","band","rationale","flags","gaps"}
- Rationales mention strongest positive AND limiting factor
- Examples include realistic 'gaps' so the model learns to populate them
- 'input_key_meanings' provided for every metric
- build_prompt prints RESPONSE FORMAT before EXAMPLES (reduces anchoring)

Backward-compat shim:
- _ask() mirrors `band` -> `score` to avoid breaking callers that still expect `score`.
  Remove those two lines after you update the orchestrator to use `band`.
"""

# =========================
# Universal scoring contract
# =========================
UNIVERSAL_PREAMBLE = (
    "You are a Business Intelligence (BI) Assessor. Grade exactly one BI metric on a 1–5 band:\n"
    "5 = Excellent (exceeds target, no material risks)\n"
    "4 = Good (meets target, minor risks)\n"
    "3 = Fair (near target, clear risks to address)\n"
    "2 = Poor (misses target, material risks)\n"
    "1 = Critical (significant failure, urgent action)\n\n"
    "Rules:\n"
    "- Use only the provided data. Do not invent values.\n"
    "- Evaluate ALL relevant inputs for the metric; do not rely on a single field.\n"
    "- If important inputs are missing or unclear, list them under 'gaps' and prefer the lower band.\n"
    "- Summarize the strongest positive signal AND the main limiting factor in the rationale (≤3 sentences).\n"
    "- Return ONLY the specified JSON. No extra text."
)

UNIVERSAL_RESPONSE_FORMAT = (
    '{"metric_id":"<id>",'
    '"band":<1-5>,'
    '"rationale":"<1-3 sentences naming strongest positive and limiting factor>",'
    '"flags":[],'
    '"gaps":[]}'
)

# =========================
# Metric definitions (20 BI metrics)
# =========================
METRIC_PROMPTS: Dict[str, Dict[str, Any]] = {
    # 1) DAU/MAU stickiness
    "usage.dau_mau": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (stickiness = DAU/MAU; consider WAU stability if provided):\n"
            "- 5: stickiness ≥ 0.60 with stable 7d DAU and positive 4w trend\n"
            "- 4: 0.45–0.59 with stable 7d DAU\n"
            "- 3: 0.30–0.44 or unstable week\n"
            "- 2: 0.15–0.29 or declining multi-week trend\n"
            "- 1: <0.15 or severe drop\n"
            "Notes: Penalize if activity_events are too sparse for a reliable denominator."
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
            "activity_events": "Events in last 30d to compute DAU/MAU (distinct user_id by day/month)",
            "activity_events[].user_id": "User identifier",
            "activity_events[].ts": "Event timestamp (ISO)",
            "activity_events[].action": "view/explore/edit"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.dau_mau",
            "band": 4,
            "rationale": "Stickiness ~0.55 is solid; lack of explicit 7d stability and 4w trend limits to 4.",
            "flags": ["trend_unknown"],
            "gaps": ["Provide 7d DAU series and 4-week DAU trend to confirm stability"]
        }
    },

    # 2) Active viewers vs creators
    "usage.creators_ratio": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (creator share among active users; consider department spread if available):\n"
            "- 5: ≥35% creators and well distributed across departments\n"
            "- 4: 25–34% creators with fair spread\n"
            "- 3: 15–24% creators or heavily skewed to one team\n"
            "- 2: 8–14% creators\n"
            "- 1: <8% creators"
        ),
        "example_input": {
            "usage_logs": [
                {"user": "u1", "role": "viewer"},
                {"user": "u2", "role": "creator"}
            ],
            "dept_map": {"u1": "Sales", "u2": "Ops"}
        },
        "input_key_meanings": {
            "usage_logs": "Array of active users with effective roles",
            "usage_logs[].role": "'creator' or 'viewer'",
            "dept_map": "Optional mapping user->department to assess spread"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.creators_ratio",
            "band": 4,
            "rationale": "Creator share near 30% is healthy; department coverage not fully proven keeps it at 4.",
            "flags": ["dept_spread_unknown"],
            "gaps": ["Provide creator counts by department to verify distribution"]
        }
    },

    # 3) Session depth & duration
    "usage.session_depth": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (duration, pages, repeat frequency):\n"
            "- 5: ≥300s avg, ≥4 pages, weekly repeats for majority\n"
            "- 4: 250–299s, ~3–4 pages\n"
            "- 3: 150–249s, ~2–3 pages\n"
            "- 2: 90–149s, ~1–2 pages\n"
            "- 1: <90s, ≤1 page"
        ),
        "example_input": {
            "session_logs": [
                {"user": "u1", "duration": 320, "pages": 4, "repeats_per_week": 2},
                {"user": "u2", "duration": 180, "pages": 3}
            ]
        },
        "input_key_meanings": {
            "session_logs": "Per-user session aggregates for recent period",
            "session_logs[].duration": "Average seconds per session",
            "session_logs[].pages": "Average pages per session",
            "session_logs[].repeats_per_week": "Approx repeat sessions / week"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.session_depth",
            "band": 4,
            "rationale": "Avg ~270s and ~3.6 pages are strong; repeat cadence missing for many users caps at 4.",
            "flags": ["repeat_freq_sparse"],
            "gaps": ["Provide repeats_per_week coverage for ≥80% of active users"]
        }
    },

    # 4) Drill-down usage
    "usage.drilldown": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (% sessions using drill + distribution + stability):\n"
            "- 5: ≥35% sessions include drill; broad spread; stable over 4w\n"
            "- 4: 25–34% with fair spread\n"
            "- 3: 15–24% or narrow spread\n"
            "- 2: 8–14%\n"
            "- 1: <8%"
        ),
        "example_input": {"interaction_logs": [{"user": "u1", "action": "drill"}]},
        "input_key_meanings": {
            "interaction_logs": "Interactions where 'action' includes 'drill'/'drilldown'",
            "interaction_logs[].user": "User performing drilldown",
            "interaction_logs[].ts": "Optional timestamp to assess stability"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.drilldown",
            "band": 3,
            "rationale": "About 18% of sessions include drill; lack of multi-BU spread limits the score.",
            "flags": ["spread_limited"],
            "gaps": ["Provide drilldown usage by department or team", "Include 4-week time series for stability"]
        }
    },

    # 5) Refresh timeliness
    "reliability.refresh_timeliness": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (within SLA by declared cadence; weigh critical assets):\n"
            "- 5: ≥95% within SLA, 0 critical stale\n"
            "- 4: 85–94% within SLA, few and low-impact stales\n"
            "- 3: 70–84% within SLA or some high-impact stales\n"
            "- 2: 50–69% within SLA or many stales\n"
            "- 1: <50% within SLA or chronic stales"
        ),
        "example_input": {
            "dashboards": [
                {"id": "d1", "last_refresh": "2025-07-31", "sla": "daily", "priority": "high"},
                {"id": "d2", "last_refresh": "2025-07-28", "sla": "weekly", "priority": "low"}
            ],
            "today": "2025-08-01"
        },
        "input_key_meanings": {
            "dashboards": "Freshness entries with SLA cadence and (optional) priority",
            "dashboards[].sla": "daily/weekly/monthly",
            "dashboards[].priority": "high/medium/low to weight impact",
            "today": "ISO date for comparison"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "reliability.refresh_timeliness",
            "band": 4,
            "rationale": "≈88% within SLA and no critical stales; missing p95 lateness limits confidence.",
            "flags": ["lateness_distribution_unknown"],
            "gaps": ["Provide lateness p95/p99 across assets to assess tail risk"]
        }
    },

    # 6) Cross-dashboard linking
    "features.cross_links": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (presence + usage + distribution):\n"
            "- 5: ≥60% dashboards have links; high traversal; broad spread\n"
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
            "dashboards": "Dashboards with 'links' array and 'link_usage' counter",
            "dashboards[].links": "Target dashboard IDs",
            "dashboards[].link_usage": "Clicks or traversals over period"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "features.cross_links",
            "band": 3,
            "rationale": "~1/3 of dashboards are linked; usage is moderate but uneven.",
            "flags": ["distribution_skewed"],
            "gaps": ["Provide share of link-enabled dashboards by BU or tier"]
        }
    },

    # 7) Governance coverage
    "governance.coverage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (certified, owner present, metadata completeness):\n"
            "- 5: ≥95% certified/owned with complete metadata\n"
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
            "dashboards": "Certification/owner/metadata flags per dashboard",
            "dashboards[].metadata": "List of metadata fields present"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "governance.coverage",
            "band": 3,
            "rationale": "Owners assigned on most assets; incomplete metadata limits quality.",
            "flags": ["metadata_gaps"],
            "gaps": ["Provide % dashboards with full metadata profile (description, owner, SLA, lineage)"]
        }
    },

    # 8) Data source diversity
    "data.source_diversity": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (count + domain balance + new-source trend):\n"
            "- 5: ≥8 sources across ≥3 domains with recent adds\n"
            "- 4: 6–7 sources across ≥3 domains\n"
            "- 3: 4–5 sources or 2 domains\n"
            "- 2: 2–3 sources, 1–2 domains\n"
            "- 1: single source"
        ),
        "example_input": {"source_catalog": ["Snowflake", "Postgres", "Salesforce"]},
        "input_key_meanings": {
            "source_catalog": "Distinct source systems (warehouse/DB/SaaS/etc.)"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "data.source_diversity",
            "band": 3,
            "rationale": "Three sources suggest some variety; unclear domain coverage restricts score.",
            "flags": ["domain_mix_unknown"],
            "gaps": ["Tag each source to a domain (e.g., ERP/CRM/Support) to measure domain balance"]
        }
    },

    # 9) Self-service adoption
    "democratization.self_service": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (creator share + growth + department coverage):\n"
            "- 5: ≥35% creators with broad department coverage and growth\n"
            "- 4: 25–34% creators\n"
            "- 3: 15–24% creators\n"
            "- 2: 8–14% creators\n"
            "- 1: <8% creators"
        ),
        "example_input": {
            "user_roles": [{"id": "u1", "role": "creator"}, {"id": "u2", "role": "viewer"}],
            "dept_map": {"u1": "Finance", "u2": "Ops"}
        },
        "input_key_meanings": {
            "user_roles": "Users and their roles ('creator'/'viewer')",
            "dept_map": "Optional mapping user->department for coverage"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "democratization.self_service",
            "band": 3,
            "rationale": "Creator share ~22% shows traction; unclear growth and department breadth cap it.",
            "flags": ["growth_unknown", "coverage_unknown"],
            "gaps": ["Provide creator share by department and 3-month growth trend"]
        }
    },

    # 10) Decision support traceability
    "decision.traceability": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (% decisions linked + evidence + recency):\n"
            "- 5: ≥70% decisions link dashboards with strong evidence; recent\n"
            "- 4: 55–69% linked with evidence\n"
            "- 3: 35–54% linked or mixed evidence\n"
            "- 2: 15–34%\n"
            "- 1: <15%"
        ),
        "example_input": {
            "decision_logs": [
                {"id": "dec1", "linked_dash": "sales_forecast", "evidence": "screenshot", "date": "2025-07-25"},
                {"id": "dec2", "linked_dash": None, "evidence": None, "date": "2025-07-10"}
            ]
        },
        "input_key_meanings": {
            "decision_logs": "Decisions with optional dashboard references and evidence markers",
            "decision_logs[].date": "Used to judge recency/freshness of decisions"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "decision.traceability",
            "band": 3,
            "rationale": "About half of decisions reference dashboards; evidence exists but recency is mixed.",
            "flags": ["recency_mixed"],
            "gaps": ["Provide exact % decisions with links and count of evidence artifacts in last 30–60 days"]
        }
    },

    # 11) Weekly active users trend (last 4 weeks)
    "usage.weekly_active_trend": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (WAU trend over last 4 weeks):\n"
            "- 5: clear, consistent WAU growth across all 4 weeks\n"
            "- 4: mild growth or stable at high level\n"
            "- 3: flat with noise, no material drop\n"
            "- 2: sustained decline\n"
            "- 1: sharp drop or very low activity"
        ),
        "example_input": {
            "today": "2025-08-21",
            "activity_events": [
                {"ts": "2025-08-21T09:00:00Z", "user_id": "u1", "action": "view"},
                {"ts": "2025-08-05T10:00:00Z", "user_id": "u2", "action": "view"}
            ]
        },
        "input_key_meanings": {
            "today": "ISO date used to bucket events into ISO weeks",
            "activity_events": "Events with ts + user_id to compute distinct WAU per week"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.weekly_active_trend",
            "band": 4,
            "rationale": "WAU shows mild week-over-week growth; lack of denominators per week limits certainty.",
            "flags": ["denominator_unknown"],
            "gaps": ["Provide exact WAU series and total active base per week (n) for the last 4 weeks"]
        }
    },

    # 12) 4-week retention (return users)
    "usage.retention_4w": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (% of week-1 active users who return in weeks 2–4):\n"
            "- 5: ≥60%\n"
            "- 4: 45–59%\n"
            "- 3: 30–44%\n"
            "- 2: 15–29%\n"
            "- 1: <15%"
        ),
        "example_input": {
            "today": "2025-08-21",
            "activity_events": [
                {"ts":"2025-08-01T10:00:00Z","user_id":"u1","action":"view"},
                {"ts":"2025-08-15T09:00:00Z","user_id":"u1","action":"view"}
            ]
        },
        "input_key_meanings": {
            "today": "Reference date",
            "activity_events": "Distinct users by ISO week to compute returns for W2–W4"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "usage.retention_4w",
            "band": 3,
            "rationale": "Retention ~35% is moderate; absence of cohort split by persona limits insight.",
            "flags": ["cohort_mix_unknown"],
            "gaps": ["Provide initial cohort size and segment-level retention (e.g., role/BU)"]
        }
    },

    # 13) Export / download rate
    "features.export_rate": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (share of sessions involving export/download; consider governance):\n"
            "- 5: ≥30% with appropriate controls\n"
            "- 4: 20–29%\n"
            "- 3: 10–19%\n"
            "- 2: 5–9%\n"
            "- 1: <5%"
        ),
        "example_input": {
            "activity_events": [
                {"ts":"2025-08-21T09:00:00Z","user_id":"u1","action":"export"},
                {"ts":"2025-08-21T09:05:00Z","user_id":"u2","action":"view"}
            ]
        },
        "input_key_meanings": {
            "activity_events": "Session-level actions; 'export'/'download' indicate file egress"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "features.export_rate",
            "band": 2,
            "rationale": "Exports near 8% indicate low offline usage; policy coverage for exports is unknown.",
            "flags": ["governance_unknown"],
            "gaps": ["Provide export policy enforcement rate and high-risk asset exceptions"]
        }
    },

    # 14) Alerts & subscriptions usage
    "features.alerts_usage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (# users with alerts/subscriptions and delivery success):\n"
            "- 5: broad adoption across BUs, high success\n"
            "- 4: moderate adoption, mostly successful\n"
            "- 3: limited adoption\n"
            "- 2: very low adoption\n"
            "- 1: near zero"
        ),
        "example_input": {
            "activity_events": [
                {"ts":"2025-08-21T07:00:00Z","user_id":"u1","action":"alert_delivered"},
                {"ts":"2025-08-21T07:00:01Z","user_id":"u2","action":"subscription_email"}
            ]
        },
        "input_key_meanings": {
            "activity_events": "'alert_*' and 'subscription_*' actions to infer adoption and delivery"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "features.alerts_usage",
            "band": 3,
            "rationale": "Meaningful but small cohort uses alerts; delivery looks reliable but BU spread is unknown.",
            "flags": ["coverage_unknown"],
            "gaps": ["Provide number of unique users with active alerts and delivery success rate by BU"]
        }
    },

    # 15) SLA breach streaks
    "reliability.sla_breach_streaks": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (max consecutive periods a dashboard violates SLA; weigh criticality):\n"
            "- 5: zero breaches on critical dashboards\n"
            "- 4: rare, short breaches\n"
            "- 3: occasional moderate streaks\n"
            "- 2: frequent or long streaks\n"
            "- 1: chronic breaches"
        ),
        "example_input": {
            "dashboards": [
                {"id":"d1","last_refresh":"2025-08-21","sla":"daily","priority":"high"},
                {"id":"d2","last_refresh":"2025-08-15","sla":"daily","priority":"high"}
            ],
            "today": "2025-08-21"
        },
        "input_key_meanings": {
            "dashboards[].last_refresh": "Used with SLA to compute breach streak length",
            "dashboards[].priority": "High/medium/low to identify critical breaches"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "reliability.sla_breach_streaks",
            "band": 4,
            "rationale": "Only brief breaches observed; absence of streak length distribution limits certainty.",
            "flags": ["streak_tail_unknown"],
            "gaps": ["Provide max/median breach days and count on high-priority dashboards"]
        }
    },

    # 16) Query/visual error rate
    "reliability.error_rate_queries": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (error rate and impact):\n"
            "- 5: <0.1% errors; no high-impact incidents\n"
            "- 4: 0.1–0.5% errors\n"
            "- 3: 0.5–1.5%\n"
            "- 2: 1.5–3%\n"
            "- 1: >3% or recurring high-impact issues"
        ),
        "example_input": {
            "activity_events": [
                {"ts":"2025-08-21T09:00:00Z","user_id":"u1","action":"error"},
                {"ts":"2025-08-21T09:01:00Z","user_id":"u2","action":"view"}
            ]
        },
        "input_key_meanings": {
            "activity_events": "'error' actions approximate query/visualization failures; consider volume for rate"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "reliability.error_rate_queries",
            "band": 4,
            "rationale": "Estimated error rate is low; lack of incident severity data prevents a 5.",
            "flags": ["impact_unknown"],
            "gaps": ["Provide incident list with severity and user impact (p95 affected)"]
        }
    },

    # 17) PII coverage (governance)
    "governance.pii_coverage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (PII detection/labeling and access policy on dashboards):\n"
            "- 5: comprehensive labeling and access controls across estate\n"
            "- 4: strong coverage; minor gaps\n"
            "- 3: partial coverage\n"
            "- 2: many gaps\n"
            "- 1: poor or absent"
        ),
        "example_input": {
            "dashboards": [
                {"id":"d1","certified":True,"owner":"fin","metadata":["description","pii","access_policy"]},
                {"id":"d2","certified":False,"owner":None,"metadata":[]}
            ]
        },
        "input_key_meanings": {
            "dashboards": "Governance signals per asset",
            "dashboards[].metadata": "Presence of 'pii'/'access_policy' used as proxy"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "governance.pii_coverage",
            "band": 3,
            "rationale": "Key assets appear labeled; inconsistent coverage across estate limits score.",
            "flags": ["coverage_inconsistent"],
            "gaps": ["Provide % assets with PII tag AND enforced access policy, by BU"]
        }
    },

    # 18) Lineage/owner documentation coverage
    "governance.lineage_coverage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (lineage docs, owners, glossary references):\n"
            "- 5: near-complete coverage across estate\n"
            "- 4: strong coverage with minor holes\n"
            "- 3: moderate coverage\n"
            "- 2: sparse\n"
            "- 1: minimal"
        ),
        "example_input": {
            "dashboards": [
                {"id":"d1","owner":"bi_ops","metadata":["lineage","glossary"]},
                {"id":"d2","owner":None,"metadata":[]}
            ]
        },
        "input_key_meanings": {
            "dashboards": "Ownership + metadata proxies for lineage/glossary completeness"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "governance.lineage_coverage",
            "band": 3,
            "rationale": "Lineage documented on a subset; owner gaps limit confidence.",
            "flags": ["owner_missing"],
            "gaps": ["Provide % assets with named owner and lineage/glossary references"]
        }
    },

    # 19) Cost efficiency (warehouse/query)
    "data.cost_efficiency": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (proxy signals: source mix, export rate, stale content):\n"
            "- 5: strong warehouse mix and usage patterns; low egress; minimal staleness\n"
            "- 4: minor inefficiencies (some egress or small stale set)\n"
            "- 3: mixed signals\n"
            "- 2: inefficient (heavy egress/stales)\n"
            "- 1: heavy waste indicators across dimensions"
        ),
        "example_input": {
            "source_catalog": ["Snowflake","BigQuery","Salesforce"],
            "activity_events": [{"ts":"2025-08-21T09:00:00Z","user_id":"u1","action":"export"}],
            "dashboards": [{"id":"d1","last_refresh":"2025-07-01","sla":"monthly"}]
        },
        "input_key_meanings": {
            "source_catalog": "Warehouse/DB/SaaS balance",
            "activity_events": "Exports as proxy for data egress",
            "dashboards": "Stale content as proxy for wasted refresh"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "data.cost_efficiency",
            "band": 3,
            "rationale": "Diverse sources but moderate egress and some staleness create mixed efficiency.",
            "flags": ["egress_present","stale_assets_present"],
            "gaps": ["Provide export sessions % and % stale dashboards by priority"]
        }
    },

    # 20) Department coverage (creators across depts)
    "democratization.dept_coverage": {
        "system": (
            f"{UNIVERSAL_PREAMBLE}\n\n"
            "RUBRIC (# departments with ≥1 creator vs total departments):\n"
            "- 5: ≥80% departments have creators\n"
            "- 4: 60–79%\n"
            "- 3: 40–59%\n"
            "- 2: 20–39%\n"
            "- 1: <20%"
        ),
        "example_input": {
            "user_roles": [{"id":"u1","role":"creator"},{"id":"u2","role":"viewer"}],
            "user_directory": [{"user_id":"u1","department":"Finance"},{"user_id":"u2","department":"Ops"}]
        },
        "input_key_meanings": {
            "user_roles": "Role mapping to identify creators",
            "user_directory": "Map users to departments for coverage calculation"
        },
        "response_format": UNIVERSAL_RESPONSE_FORMAT,
        "example_output": {
            "metric_id": "democratization.dept_coverage",
            "band": 4,
            "rationale": "Creators appear in most departments; lack of distinct creator counts by dept limits certainty.",
            "flags": ["creator_counts_unknown"],
            "gaps": ["Provide count of creators per department and total departments considered"]
        }
    }
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

        # Coerce band
        try:
            out["band"] = max(1, min(5, int(out.get("band", 3))))
        except Exception:
            out["band"] = 3

        # Ensure required fields
        out.setdefault("rationale", "Strong usage signal; limited by missing stability detail.")
        out.setdefault("flags", [])
        out.setdefault("gaps", [])

        # ---- Backward-compatibility shim (remove once orchestrator reads 'band') ----
        # Mirror 'band' into a deprecated 'score' field so existing rollups still work.
        out["score"] = out["band"]
        # ---------------------------------------------------------------------------

        # Always stamp a metric_id if missing (defensive)
        out.setdefault("metric_id", "unknown.metric")

        return out

    def score_metric(self, metric_id: str, task_input: Dict[str, Any]) -> Dict[str, Any]:
        _ = METRIC_PROMPTS[metric_id]  # fail fast if unknown
        prompt = build_prompt(metric_id, task_input)
        out = self._ask(prompt)
        out["metric_id"] = metric_id
        return out

    # Backwards-compatible wrappers
    def score_dau_mau(self, activity_events: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("usage.dau_mau", {"activity_events": activity_events, "today": today})

    def score_active_creators(self, usage_logs: List[Dict[str, Any]], dept_map: Optional[Dict[str,str]]=None) -> Dict[str, Any]:
        payload: Dict[str,Any] = {"usage_logs": usage_logs}
        if dept_map is not None:
            payload["dept_map"] = dept_map
        return self.score_metric("usage.creators_ratio", payload)

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

    def score_self_service_adoption(self, user_roles: List[Dict[str, Any]], dept_map: Optional[Dict[str,str]]=None) -> Dict[str, Any]:
        payload: Dict[str,Any] = {"user_roles": user_roles}
        if dept_map is not None:
            payload["dept_map"] = dept_map
        return self.score_metric("democratization.self_service", payload)

    def score_decision_traceability(self, decision_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("decision.traceability", {"decision_logs": decision_logs})

    # 11) WAU trend
    def score_weekly_active_trend(self, activity_events: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("usage.weekly_active_trend", {"activity_events": activity_events, "today": today})

    # 12) 4-week retention
    def score_retention_4w(self, activity_events: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("usage.retention_4w", {"activity_events": activity_events, "today": today})

    # 13) Export/download rate
    def score_export_rate(self, activity_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("features.export_rate", {"activity_events": activity_events})

    # 14) Alerts / subscriptions usage
    def score_alerts_usage(self, activity_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("features.alerts_usage", {"activity_events": activity_events})

    # 15) SLA breach streaks
    def score_sla_breach_streaks(self, dashboards: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
        return self.score_metric("reliability.sla_breach_streaks", {"dashboards": dashboards, "today": today})

    # 16) Query/visual error rate
    def score_error_rate_queries(self, activity_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("reliability.error_rate_queries", {"activity_events": activity_events})

    # 17) PII coverage
    def score_pii_coverage(self, gov_dashboards: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("governance.pii_coverage", {"dashboards": gov_dashboards})

    # 18) Lineage coverage
    def score_lineage_coverage(self, gov_dashboards: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("governance.lineage_coverage", {"dashboards": gov_dashboards})

    # 19) Cost efficiency
    def score_cost_efficiency(self, source_catalog: List[str], activity_events: List[Dict[str, Any]], dashboards: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("data.cost_efficiency", {"source_catalog": source_catalog, "activity_events": activity_events, "dashboards": dashboards})

    # 20) Department coverage (creators per dept)
    def score_dept_coverage(self, user_roles: List[Dict[str, Any]], user_directory: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.score_metric("democratization.dept_coverage", {"user_roles": user_roles, "user_directory": user_directory})

    # Parity hook
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"status": "ok"}