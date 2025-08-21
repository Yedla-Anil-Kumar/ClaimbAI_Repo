from __future__ import annotations
from typing import Any, Dict
from .canonical import BIInputs
from .llm_engine import BIUsageLLM

def _clip01(x: float) -> float:
    try: return max(0.0, min(1.0, float(x)))
    except Exception: return 0.0

class BIOrchestrator:
    """
    Single-file inputs → 10 metric graders → two rollups:
      - business_integration  (usage, adoption, feature use)
      - decision_making       (governance, freshness, traceability)
    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 700):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = BIUsageLLM(model=model, temperature=temperature)

    def analyze_inputs(self, bi: BIInputs) -> Dict[str, Any]:
        # Call 10 graders
        m1 = self.llm.score_dau_mau(bi.activity_events, bi.today_utc)
        m2 = self.llm.score_active_creators(bi.usage_logs)
        m3 = self.llm.score_session_depth(bi.session_logs)
        m4 = self.llm.score_drilldown_adoption(bi.interaction_logs)
        m5 = self.llm.score_refresh_timeliness(bi.dashboard_metadata)
        m6 = self.llm.score_cross_links([])  # if you have link_data, pass it here
        m7 = self.llm.score_governance_coverage(bi.governance_data)
        m8 = self.llm.score_source_diversity(bi.source_catalog)
        m9 = self.llm.score_self_service_adoption(bi.user_roles)
        m10 = self.llm.score_decision_traceability(bi.decision_logs)

        metrics = [m1,m2,m3,m4,m5,m6,m7,m8,m9,m10]
        m = {x["metric_id"]: x for x in metrics}

        # Rollups (0..5 scoring for exec-friendly scale)
        business_integration = 5.0 * (
            0.25*_clip01(m1["score"]) + 0.15*_clip01(m2["score"]) + 0.15*_clip01(m3["score"])
          + 0.10*_clip01(m4["score"]) + 0.10*_clip01(m6["score"]) + 0.10*_clip01(m8["score"])
          + 0.15*_clip01(m9["score"])
        )
        decision_making = 5.0 * (
            0.25*_clip01(m5["score"]) + 0.25*_clip01(m7["score"]) + 0.20*_clip01(m10["score"])
          + 0.15*_clip01(m3["score"]) + 0.15*_clip01(m8["score"])
        )

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
                "business_integration": round(business_integration, 2),
                "decision_making": round(decision_making, 2),
            },
            "metric_breakdown": m,
            "mode": "single_inputs_json",
        }
