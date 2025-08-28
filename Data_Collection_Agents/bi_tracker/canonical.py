# Data_Collection_Agents/bi_tracker/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, timezone


@dataclass
class BIInputs:
    """
    Canonical, platform-agnostic inputs for BI Tracker (supports 20 metrics).
    """

    # Global
    today_utc: str = ""  # auto-filled to UTC date if blank

    # Usage & Adoption
    activity_events: List[Dict[str, Any]] = field(default_factory=list)     # [{ts, user_id, action, content_id?}]
    user_directory:  List[Dict[str, Any]] = field(default_factory=list)     # [{user_id, department, role?, license?}]
    session_logs:    List[Dict[str, Any]] = field(default_factory=list)     # [{user, duration, pages, repeats_per_week?}]
    usage_logs:      List[Dict[str, Any]] = field(default_factory=list)     # [{user, role}]
    interaction_logs: List[Dict[str, Any]] = field(default_factory=list)    # [{user, action, content_id?, ts?}]

    # Content Health & Governance
    governance_data: List[Dict[str, Any]] = field(default_factory=list)     # [{id, certified, owner, metadata:[] }]

    # Reliability
    dashboard_metadata: List[Dict[str, Any]] = field(default_factory=list)  # [{id, last_refresh, sla, priority?}]

    # Feature / Linking
    dashboard_link_data: List[Dict[str, Any]] = field(default_factory=list) # [{id, links:[...], link_usage:int}]

    # Democratization
    source_catalog: List[str] = field(default_factory=list)                 # ["Snowflake","Postgres","Salesforce",...]
    user_roles: List[Dict[str, Any]] = field(default_factory=list)          # [{id, role}]

    # Decision Support
    decision_logs: List[Dict[str, Any]] = field(default_factory=list)       # [{id, linked_dash, evidence, meeting_date?}]

    # ---- helpers ----
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BIInputs":
        return BIInputs(
            today_utc=d.get("today_utc", ""),
            activity_events=d.get("activity_events", []),
            user_directory=d.get("user_directory", []),
            session_logs=d.get("session_logs", []),
            usage_logs=d.get("usage_logs", []),
            interaction_logs=d.get("interaction_logs", []),
            governance_data=d.get("governance_data", []),
            dashboard_metadata=d.get("dashboard_metadata", []),
            dashboard_link_data=d.get("dashboard_link_data", []),
            source_catalog=d.get("source_catalog", []),
            user_roles=d.get("user_roles", []),
            decision_logs=d.get("decision_logs", []),
        )

    def __post_init__(self) -> None:
        # today_utc default
        if not self.today_utc:
            self.today_utc = datetime.now(timezone.utc).date().isoformat()

        def _fix_ts(v: Any) -> str:
            s = "" if v is None else str(v)
            return s[:25]

        # normalize timestamps if present
        for ev in self.activity_events:
            if "ts" in ev:
                ev["ts"] = _fix_ts(ev["ts"])
        for ev in self.interaction_logs:
            if "ts" in ev:
                ev["ts"] = _fix_ts(ev["ts"])

        # normalize dashboard_metadata
        fixed = []
        for d in self.dashboard_metadata:
            fixed.append({
                "id": d.get("id", "") or "",
                "last_refresh": d.get("last_refresh") or self.today_utc,
                "sla": str(d.get("sla") or "weekly").lower(),
                "priority": d.get("priority"),
            })
        self.dashboard_metadata = fixed