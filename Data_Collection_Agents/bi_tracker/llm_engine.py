from __future__ import annotations
import json, time, random
from pathlib import Path
from typing import Any, Dict, List, Optional
from Data_Collection_Agents.base_agent import BaseMicroAgent

FEW_SHOT_DIR = Path(__file__).resolve().parent / "few_shot"

def _load_one_shot(stem: str) -> str:
    txt = FEW_SHOT_DIR / f"{stem}_example.txt"
    jsn = FEW_SHOT_DIR / f"{stem}_example.json"
    t = txt.read_text(encoding="utf-8") if txt.exists() else ""
    j = ""
    if jsn.exists():
        try:
            j = json.dumps(json.loads(jsn.read_text(encoding="utf-8")), indent=2)
        except Exception:
            j = ""
    if t and j:
        return "### ONE-SHOT EXAMPLE ###\n" + t + "\n---\n" + j + "\n\n"
    return ""

class LLMBackbone(BaseMicroAgent):
    def ask(self, system_prompt: str, user_prompt: str, max_tokens: int = 700) -> Dict[str, Any]:
        time.sleep(random.uniform(0.02, 0.07))
        raw = self._call_llm(system_prompt=system_prompt, prompt=user_prompt, max_tokens=max_tokens)
        try:
            out = self._parse_json_response(raw) or {}
        except Exception:
            out = {}
        # guards
        try:
            out["score"] = max(0.0, min(1.0, float(out.get("score", 0.0))))
        except Exception:
            out["score"] = 0.0
        out.setdefault("rationale", "No rationale.")
        out.setdefault("details", {})
        return out

class BIUsageLLM(LLMBackbone):
    # 1) DAU / MAU Stickiness
    def score_dau_mau(self, activity_events: List[Dict[str, Any]], today_utc: str) -> Dict[str, Any]:
        fs = _load_one_shot("dau_mau")
        users_today = {e.get("user_id") for e in activity_events if (e.get("ts","")[:10] == today_utc)}
        users_30d   = {e.get("user_id") for e in activity_events}
        dau, mau = len(users_today), max(1, len(users_30d))
        payload = {
            "metric_id":"usage.dau_mau",
            "today": today_utc,
            "precomputed": {"dau": dau, "mau": mau, "stickiness": round(dau/mau, 4)},
            "weights": {"ratio":0.60,"consistency_7d":0.20,"trend_7d":0.20},
            "notes": "If 7d series missing, treat those sub-scores as neutral (mid)."
        }
        system = (
            "You are a BI usage assessor. Terms: DAU = distinct active users today; "
            "MAU = distinct active users in last 30 days; Stickiness = DAU/MAU. "
            "Score 0..1 with weights: ratio(60%), 7d consistency(20%), 7d trend(20%). "
            "Use ONLY the provided JSON; don't invent data. Return STRICT JSON: "
            '{"metric_id","score","rationale","details"}.'
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"activity_events": activity_events, **payload}, indent=2)
        out = self.ask(system, user)
        out.setdefault("metric_id","usage.dau_mau")
        out["details"].update(payload["precomputed"])
        return out

    # 2) Active Viewers vs Creators
    def score_active_creators(self, usage_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("active_creators")
        roles = {u.get("user"): (u.get("role","viewer") or "viewer").lower() for u in usage_logs}
        creators = [u for u,r in roles.items() if r=="creator"]
        payload = {
            "metric_id":"usage.creators_ratio",
            "weights":{"creator_share":0.50,"dept_distribution":0.30,"creator_growth_4w":0.20},
            "details":{"creator_share": round(len(creators)/max(1,len(roles)),4), "active_users": len(roles)}
        }
        system = (
            "You are a BI adoption assessor. 'Creator' = builds/edits/publishes; 'Viewer' = consumes only. "
            "Score 0..1 with weights: %active who create(50%), distribution across departments(30%), "
            "creator growth over last 4 weeks(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"usage_logs": usage_logs, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","usage.creators_ratio"); return out

    # 3) Session Depth & Duration
    def score_session_depth(self, session_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("session_depth")
        if session_logs:
            avg_dur = sum(s.get("duration",0) for s in session_logs)/len(session_logs)
            avg_pages = sum(s.get("pages",0) for s in session_logs)/len(session_logs)
            avg_repeat = sum(s.get("repeats_per_week",0) for s in session_logs)/len(session_logs)
        else:
            avg_dur = avg_pages = avg_repeat = 0.0
        payload = {
            "metric_id":"usage.session_depth",
            "weights":{"duration":0.40,"pages":0.30,"repeat":0.30},
            "benchmarks":{"duration_s":300,"pages":4},
            "details":{"avg_duration_s":avg_dur,"avg_pages":avg_pages,"avg_repeats_per_week":avg_repeat}
        }
        system = (
            "You are a BI engagement assessor. 'Session duration' (seconds) vs 300s benchmark; "
            "'Depth' = pages per session; 'Repeat frequency' = sessions per user per week. "
            "Weights: duration(40%), depth(30%), repeat(30%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"session_logs": session_logs, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","usage.session_depth"); return out

    # 4) Drill-Down Usage
    def score_drilldown_adoption(self, interaction_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("drilldown")
        total = max(1, len(interaction_logs))
        dd = sum(1 for e in interaction_logs if str(e.get("action","")).lower() in ("drill","drilldown","drill_down"))
        payload = {
            "metric_id":"usage.drilldown",
            "weights":{"pct_sessions":0.50,"group_spread":0.30,"trend_stability":0.20},
            "details":{"pct_sessions_with_drilldown": round(dd/total,4)}
        }
        system = (
            "You are a BI feature adoption assessor. 'Drill-down session' = session where drill feature used. "
            "Weights: %sessions with drill-down(50%), spread across groups(30%), trend stability 4w(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"interaction_logs": interaction_logs, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","usage.drilldown"); return out

    # 5) Refresh Timeliness
    def score_refresh_timeliness(self, dashboard_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("refresh_timeliness")
        payload = {
            "metric_id":"reliability.refresh_timeliness",
            "weights":{"within_sla":0.60,"failures":0.20,"impact":0.20},
            "details":{"sla_definition":"daily ≤1d; weekly ≤7d; monthly ≤31d"}
        }
        system = (
            "You are a BI data freshness assessor. 'Within SLA' means last_refresh meets the declared cadence. "
            "Weights: within_sla(60%), failure frequency(20%), impact on key BUs(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"dashboards": dashboard_metadata, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","reliability.refresh_timeliness"); return out

    # 6) Cross-Dashboard Linking
    def score_cross_links(self, link_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("cross_links")
        with_links = sum(1 for d in link_data if d.get("links"))
        total = max(1, len(link_data))
        payload = {
            "metric_id":"features.cross_links",
            "weights":{"has_links":0.40,"usage_freq":0.40,"team_distribution":0.20},
            "details":{"dash_with_links_pct": round(with_links/total,4),
                       "link_usage_total": sum(int(d.get("link_usage",0) or 0) for d in link_data)}
        }
        system = (
            "You are a BI feature adoption assessor. 'Cross-link' = navigable link between dashboards. "
            "Weights: %dashboards with links(40%), traversal frequency(40%), distribution across teams(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"dashboards": link_data, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","features.cross_links"); return out

    # 7) Governance Coverage
    def score_governance_coverage(self, gov: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("governance_coverage")
        total = max(1, len(gov))
        certified = sum(1 for d in gov if bool(d.get("certified")))
        owners    = sum(1 for d in gov if bool(d.get("owner")))
        meta_ok   = sum(1 for d in gov if (d.get("metadata") or []))
        payload = {
            "metric_id":"governance.coverage",
            "weights":{"certified":0.50,"owners":0.30,"metadata":0.20},
            "details":{
                "certified_pct": round(certified/total,4),
                "ownership_pct": round(owners/total,4),
                "metadata_completeness_pct": round(meta_ok/total,4),
            }
        }
        system = (
            "You are a BI governance assessor. 'Certified' = vetted/approved datasets; 'Owner' assigned; "
            "metadata includes description, refresh rate, glossary. Weights: certified(50%), owners(30%), "
            "metadata completeness(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"dashboards": gov, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","governance.coverage"); return out

    # 8) Data Source Diversity
    def score_source_diversity(self, sources: List[str]) -> Dict[str, Any]:
        fs = _load_one_shot("source_diversity")
        payload = {
            "metric_id":"data.source_diversity",
            "weights":{"count":0.40,"domain_balance":0.30,"trend_new":0.30},
            "details":{"sources": sorted({str(s).strip() for s in sources if str(s).strip()})}
        }
        system = (
            "You are a BI data diversity assessor. Score 0..1 for variety of source systems and balance across domains "
            "(e.g., finance/ops/sales). Weights: distinct source count(40%), domain balance(30%), trend of new source "
            "adoption(30%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"source_catalog": sources, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","data.source_diversity"); return out

    # 9) Self-Service Adoption
    def score_self_service_adoption(self, user_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("self_service")
        total = max(1, len(user_roles))
        creators = sum(1 for u in user_roles if (str(u.get("role","")).lower()=="creator"))
        payload = {
            "metric_id":"democratization.self_service",
            "weights":{"creator_share":0.50,"growth_3m":0.30,"dept_coverage":0.20},
            "details":{"creator_share": round(creators/total,4)}
        }
        system = (
            "You are a BI democratization assessor. Self-service means users create their own content. "
            "Weights: %users who are creators(50%), growth of creators over 3 months(30%), dept coverage(20%). STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"user_roles": user_roles, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","democratization.self_service"); return out

    # 10) Decision Support Traceability
    def score_decision_traceability(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        fs = _load_one_shot("decision_traceability")
        total = max(1, len(decisions))
        linked = sum(1 for d in decisions if d.get("linked_dash"))
        evidence = sum(1 for d in decisions if str(d.get("evidence","")).strip())
        payload = {
            "metric_id":"decision.traceability",
            "weights":{"linked":0.50,"evidence_quality":0.30,"recency":0.20},
            "details":{"linked_pct": round(linked/total,4), "evidence_markers": f"{evidence}/{total}"}
        }
        system = (
            "You are a BI decision-support assessor. Traceability = decisions explicitly reference dashboards. "
            "Weights: % decisions linked(50%), evidence quality (records/screenshots)(30%), recency in critical forums(20%). "
            "STRICT JSON."
        )
        user = fs + "TASK INPUT:\n" + json.dumps({"decision_logs": decisions, **payload}, indent=2)
        out = self.ask(system, user); out.setdefault("metric_id","decision.traceability"); return out

    # satisfy abstract method (not used here)
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        return {"ok": True}
