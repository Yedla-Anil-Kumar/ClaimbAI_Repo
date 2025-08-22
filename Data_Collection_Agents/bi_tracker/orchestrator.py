from __future__ import annotations
from typing import Any, Dict
from .canonical import BIInputs
from .llm_engine import BIUsageLLM

def _s(m: Dict[str, Any]) -> float:
    try:
        return float(m.get("score", 3))
    except Exception:
        return 3.0

class BIOrchestrator:
    """
    Single-file inputs → 20 metric graders → two rollups (1–5 scale),
    aligned to the AIMRI PRD for Agent 5 (BI Tracker):

      - business_integration  (usage, adoption, feature use)
      - decision_making       (governance, freshness, traceability)

    The former 'operational_health' rollup has been removed to match the PRD.
    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 700):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = BIUsageLLM(model=model, temperature=temperature)

    def analyze_inputs(self, bi: BIInputs) -> Dict[str, Any]:
        # 20 graders (1–5 scale)
        m1  = self.llm.score_dau_mau(bi.activity_events, bi.today_utc)
        m2  = self.llm.score_active_creators(bi.usage_logs)
        m3  = self.llm.score_session_depth(bi.session_logs)
        m4  = self.llm.score_drilldown(bi.interaction_logs)
        m5  = self.llm.score_refresh_timeliness(bi.dashboard_metadata, bi.today_utc)
        m6  = self.llm.score_cross_links(bi.dashboard_link_data)
        m7  = self.llm.score_governance_coverage(bi.governance_data)
        m8  = self.llm.score_source_diversity(bi.source_catalog)
        m9  = self.llm.score_self_service_adoption(bi.user_roles)
        m10 = self.llm.score_decision_traceability(bi.decision_logs)
        m11 = self.llm.score_weekly_active_trend(bi.activity_events, bi.today_utc)
        m12 = self.llm.score_retention_4w(bi.activity_events, bi.today_utc)
        m13 = self.llm.score_export_rate(bi.activity_events)
        m14 = self.llm.score_alerts_usage(bi.activity_events)
        m15 = self.llm.score_sla_breach_streaks(bi.dashboard_metadata, bi.today_utc)
        m16 = self.llm.score_error_rate_queries(bi.activity_events)
        m17 = self.llm.score_pii_coverage(bi.governance_data)
        m18 = self.llm.score_lineage_coverage(bi.governance_data)
        m19 = self.llm.score_cost_efficiency(bi.source_catalog, bi.activity_events, bi.dashboard_metadata)
        m20 = self.llm.score_dept_coverage(bi.user_roles, bi.user_directory)

        metrics = [m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20]
        m = {x["metric_id"]: x for x in metrics}

        # ---- Rollups (two only, per PRD Agent 5) ----
        # Business Integration: usage/adoption/feature use & growth signals
        business_integration = round((
            0.20*_s(m1) +  # DAU/MAU stickiness
            0.12*_s(m2) +  # creators ratio
            0.12*_s(m3) +  # session depth
            0.08*_s(m4) +  # drilldown usage
            0.10*_s(m6) +  # cross-links
            0.08*_s(m8) +  # source diversity (proxy for breadth)
            0.12*_s(m9) +  # self-service adoption
            0.09*_s(m11) + # WAU trend
            0.09*_s(m12)   # 4w retention
        ), 2)

        # Decision Making: governance + freshness + decision traceability + reliability signals
        decision_making = round((
            0.20*_s(m5)  +  # refresh timeliness
            0.18*_s(m7)  +  # governance coverage
            0.08*_s(m8)  +  # source diversity (access to needed data)
            0.22*_s(m10) +  # decision traceability
            0.10*_s(m17) +  # PII coverage
            0.12*_s(m18) +  # lineage coverage
            0.10*_s(m16)    # query/visual error rate (reliability for decisioning)
        ), 2)

        return {
            "agent": "bi_tracker",
            "inputs_summary": {
                "today_utc": bi.today_utc,
                "counts": {
                    "users": len(bi.user_roles) or len(bi.user_directory),
                    "dashboards": len(bi.governance_data) or len(bi.dashboard_metadata),
                    "activity_events": len(bi.activity_events),
                },
            },
            "scores": {
                "business_integration": business_integration,
                "decision_making": decision_making,
            },
            "metric_breakdown": m,
            "mode": "single_inputs_json",
        }
