from __future__ import annotations
from typing import Any, Dict, List
from Data_Collection_Agents.bi_tracker.llm_agent import BIUsageLLM

# Thin wrappers so orchestrator imports remain simple.

def score_dau_mau(activity_events: List[Dict[str,Any]], today_utc: str, model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_dau_mau(activity_events, today_utc)

def score_active_creators(usage_logs: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_active_creators(usage_logs)

def score_session_depth(session_logs: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_session_depth(session_logs)

def score_drilldown_adoption(interaction_logs: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_drilldown(interaction_logs)

def score_refresh_timeliness(dashboard_metadata: List[Dict[str,Any]], today_utc: str | None = None, model: str = "gpt-4o-mini", temperature: float = 0.0) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    # if today_utc is None, agent will still compute on provided details; pass current date-like string
    today = (today_utc or "2025-08-01")
    return agent.score_refresh_timeliness(dashboard_metadata, today)

def score_cross_links(dashboard_link_data: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_cross_links(dashboard_link_data)

def score_governance_coverage(governance_data: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_governance_coverage(governance_data)

def score_source_diversity(source_catalog: List[str], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_source_diversity(source_catalog)

def score_self_service(user_roles: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_self_service_adoption(user_roles)

def score_decision_traceability(decision_logs: List[Dict[str,Any]], model: str, temperature: float) -> Dict[str,Any]:
    agent = BIUsageLLM(model=model, temperature=temperature)
    return agent.score_decision_traceability(decision_logs)
