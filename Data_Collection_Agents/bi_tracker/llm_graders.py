# Data_Collection_Agents/bi_tracker/llm_graders.py
from __future__ import annotations
import json
import time
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
from Data_Collection_Agents.base_agent import BaseMicroAgent

def _load_few_shot_pair(stem: str) -> tuple[str, str]:
    root = Path(__file__).resolve().parent / "few_shot"
    txt = root / f"{stem}_example.txt"
    jsn = root / f"{stem}_example.json"
    ex_text = txt.read_text(encoding="utf-8") if txt.exists() else ""
    ex_json = ""
    if jsn.exists():
        try:
            ex_json = json.dumps(json.loads(jsn.read_text(encoding="utf-8")), indent=2)
        except Exception:
            ex_json = ""
    return ex_text, ex_json

def _strict_json_parse(s: str) -> Dict[str, Any]:
    try:
        if "```json" in s:
            ss = s.split("```json",1)[1].split("```",1)[0]
            return json.loads(ss.strip())
        if "```" in s:
            ss = s.split("```",1)[1].split("```",1)[0]
            return json.loads(ss.strip())
        return json.loads(s)
    except Exception:
        try:
            i, j = s.find("{"), s.rfind("}")
            if i >= 0 and j > i:
                return json.loads(s[i:j+1])
        except Exception:
            pass
        return {}

class BIUsageLLM(BaseMicroAgent):
    """
    Function-specific one-shot prompts for BI metrics.
    Each method prepares its own SYSTEM and USER content, and (optionally) includes a few-shot example.
    All methods return: {"score": <0..1>, "rationale": "..."}.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 512):
        super().__init__(model=model, temperature=temperature)
        self.max_tokens = max_tokens

    # ---- 1) DAU/MAU ----
    def grade_dau_mau_stickiness(self, activity_events: List[Dict[str,Any]], today_utc: str) -> Dict[str,Any]:
        stem = "dau_mau_stickiness"
        ex_text, ex_json = _load_few_shot_pair(stem)
        system = (
            "You are a BI usage assessor. Compute DAU/MAU stickiness and score 0–1.\n"
            "Weight factors:\n- DAU/MAU ratio (60%)\n- Consistency of DAU across past 7 days (20%)\n- Trend over last 7 days (20%)."
        )
        user = ""
        if ex_text and ex_json:
            user += f"{ex_text}\n\nEXAMPLE OUTPUT:\n{ex_json}\n\n"
        user += "TASK INPUT:\n" + json.dumps({"events": activity_events, "today": today_utc}, indent=2) + \
                '\n\nRESPONSE FORMAT:\n{"score":<0..1>, "rationale":"detailed explanation with weights"}'

        time.sleep(random.uniform(0.02,0.08))
        resp = self._call_llm(user, system_prompt=system, max_tokens=self.max_tokens)
        out = _strict_json_parse(resp)
        # Fallback if model fails: compute plain DAU/MAU only
        if "score" not in out:
            try:
                dau = len({e["user_id"] for e in activity_events if e["ts"][:10] == today_utc})
                mau = len({e["user_id"] for e in activity_events}) or 1
                stickiness = dau/mau
                out = {"score": min(stickiness/0.60, 1.0), "rationale": "Fallback: DAU/MAU vs 0.60 target."}
            except Exception:
                out = {"score": 0.0, "rationale": "Fallback: unable to compute."}
        return out

    # ---- shared builder for remaining metrics ----
    def _generic_score(self, stem: str, system: str, task_payload: Dict[str,Any], response_schema: str = '{"score":<0..1>,"rationale":"..."}') -> Dict[str,Any]:
        ex_text, ex_json = _load_few_shot_pair(stem)
        user = ""
        if ex_text and ex_json:
            user += f"{ex_text}\n\nEXAMPLE OUTPUT:\n{ex_json}\n\n"
        user += "TASK INPUT:\n" + json.dumps(task_payload, indent=2) + f"\n\nRESPONSE FORMAT:\n{response_schema}"
        time.sleep(random.uniform(0.02,0.08))
        resp = self._call_llm(user, system_prompt=system, max_tokens=self.max_tokens)
        out = _strict_json_parse(resp)
        if "score" not in out:
            out = {"score": task_payload.get("baseline_score", 0.0), "rationale": "Fallback: used baseline_score."}
        return out

    # 2) creators ratio
    def grade_creators_ratio(self, activity_events, user_directory, baseline_score: float) -> Dict[str,Any]:
        system = ("You are a BI adoption assessor. Explain whether the active creator share is healthy for a governed self-service model. "
                  "Return score 0–1 using baseline as a prior; move toward 1.0 if near ~15% creators, penalize large deviations.")
        return self._generic_score("creators_ratio", system,
            {"activity_events": activity_events, "user_directory": user_directory, "baseline_score": baseline_score})

    # 3) session depth
    def grade_session_depth(self, activity_events, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess analysis depth. Use median pages and total duration per session. Target: 4 pages, 600s. "
                  "Produce a clear rationale and score 0–1 around those targets.")
        return self._generic_score("session_depth", system, {"activity_events": activity_events, "baseline_score": baseline_score})

    # 4) reach
    def grade_reach(self, activity_events, user_directory, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess org reach of BI. ≥60% of users should view ≥1 dashboard in window. "
                  "Return 0–1 and a concise rationale.")
        return self._generic_score("reach", system,
            {"activity_events": activity_events, "user_directory": user_directory, "baseline_score": baseline_score})

    # 5) certified coverage
    def grade_certified_coverage(self, activity_events, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You evaluate trust/governance coverage. More certified views → higher trust. Target ≥80% certified views.")
        return self._generic_score("certified_coverage", system,
            {"activity_events": activity_events, "content_catalog": content_catalog, "baseline_score": baseline_score})

    # 6) content health
    def grade_content_health(self, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess content hygiene. Penalize stale (≥90d), orphaned owners, and duplicates (same field set). "
                  "Explain the biggest drivers.")
        return self._generic_score("content_health", system,
            {"content_catalog": content_catalog, "baseline_score": baseline_score})

    # 7) lineage
    def grade_lineage(self, lineage_edges, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess lineage completeness for dashboards. Target 90% of dashboards with upstream lineage.")
        return self._generic_score("lineage", system,
            {"lineage_edges": lineage_edges, "content_catalog": content_catalog, "baseline_score": baseline_score})

    # 8) permission hygiene
    def grade_permission_hygiene(self, permissions, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess access risk. Penalize org-wide access on non-low-sensitivity assets. "
                  "Goal is 0% overbroad.")
        return self._generic_score("permission_hygiene", system,
            {"permissions": permissions, "content_catalog": content_catalog, "baseline_score": baseline_score})

    # 9) refresh reliability
    def grade_refresh(self, refresh_logs, freshness_sla_hours: int, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess refresh reliability and freshness SLA attainment. Combine success rate and freshness≤SLA.")
        return self._generic_score("refresh", system,
            {"refresh_logs": refresh_logs, "freshness_sla_hours": freshness_sla_hours, "baseline_score": baseline_score})

    # 10) performance
    def grade_performance(self, performance_logs, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess query/render performance. p95 ≤ 2000ms is on target; cache hit ≥0.60 improves score.")
        return self._generic_score("performance", system,
            {"performance_logs": performance_logs, "baseline_score": baseline_score})

    # 11) self-service
    def grade_self_service(self, activity_events, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess self-service balance. Target explore:canned ≈ 0.3. Penalize extreme deviations.")
        return self._generic_score("self_service", system,
            {"activity_events": activity_events, "baseline_score": baseline_score})

    # 12) NLQ
    def grade_nlq(self, nlq_logs, user_directory, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess NLQ adoption, accuracy, and speed. Weight adoption 40%, success 40%, latency 20%.")
        return self._generic_score("nlq", system,
            {"nlq_logs": nlq_logs, "user_directory": user_directory, "baseline_score": baseline_score})

    # 13) catalog
    def grade_catalog(self, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess metadata completeness: descriptions (90%) and glossary terms (70%). Provide concise rationale.")
        return self._generic_score("catalog", system,
            {"content_catalog": content_catalog, "baseline_score": baseline_score})

    # 14) equity
    def grade_equity(self, activity_events, user_directory, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess access equity for certified dashboards across departments. Penalize large coverage gaps.")
        return self._generic_score("equity", system,
            {"activity_events": activity_events, "user_directory": user_directory, "content_catalog": content_catalog, "baseline_score": baseline_score})

    # 15) alert→action
    def grade_alert_action(self, alerts_subscriptions, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess whether alerts drive actions (e.g., tickets). Target ≥60% of alerts result in an action.")
        return self._generic_score("alert_action", system,
            {"alerts_subscriptions": alerts_subscriptions, "baseline_score": baseline_score})

    # 16) annotations
    def grade_annotation_density(self, comment_events, activity_events, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess in-product collaboration density (comments per 100 views). Target ≈5 per 100 views.")
        return self._generic_score("annotation_density", system,
            {"comment_events": comment_events, "activity_events": activity_events, "baseline_score": baseline_score})

    # 17) export→action
    def grade_export_action(self, export_events, downstream_actions, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess whether exports result in downstream tracked work. Target ≥30% of exports lead to actions.")
        return self._generic_score("export_action", system,
            {"export_events": export_events, "downstream_actions": downstream_actions, "baseline_score": baseline_score})

    # 18) decision linkage
    def grade_decision_log_linkage(self, content_catalog, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess traceability: % of assets with linked issues/OKRs. Higher is better; target ≥60%.")
        return self._generic_score("decision_log_linkage", system,
            {"content_catalog": content_catalog, "baseline_score": baseline_score})

    # 19) cycle time
    def grade_cycle_time(self, alerts_subscriptions, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess time from signal to action. Faster median and p90 improve the score.")
        return self._generic_score("cycle_time", system,
            {"alerts_subscriptions": alerts_subscriptions, "baseline_score": baseline_score})

    # 20) cost efficiency
    def grade_cost_efficiency(self, cost_usage, activity_events, baseline_score: float) -> Dict[str,Any]:
        system = ("You assess BI cost efficiency using cost per active user and per 1k queries. "
                  "Explain drivers succinctly and return 0–1.")
        return self._generic_score("cost_efficiency", system,
            {"cost_usage": cost_usage, "activity_events": activity_events, "baseline_score": baseline_score})
    

    def evaluate(self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compatibility method to satisfy BaseMicroAgent ABC.
        Primary API remains the grade_* methods; this provides a generic one-shot
        call path if you pass {"system": "...", "prompt": "..."} in context.
        """
        ctx = context or {}
        prompt = ctx.get("prompt")
        system = ctx.get("system", "")
        if prompt:
            raw = self._call_llm(prompt, system_prompt=system, max_tokens=self.max_tokens)
            parsed = self._parse_json_response(raw)
            return parsed or {"raw": raw}
        # Not used by orchestrator; just return a benign ack
        return {"ok": True, "message": "Use the grade_* methods for BI scoring."}