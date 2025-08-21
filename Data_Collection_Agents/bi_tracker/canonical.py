from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class BIInputs:
    """
    Normalized, platform-agnostic datasets used by the 10 BI metrics.
    These align to the dataset names in your spec.  # :contentReference[oaicite:1]{index=1}
    """
    today_utc: str = "2025-08-01"

    # Usage & Adoption
    activity_events: List[Dict[str, Any]] = field(default_factory=list)   # view/explore/edit/download events
    user_directory: List[Dict[str, Any]] = field(default_factory=list)    # id, department/region/role/license
    session_logs: List[Dict[str, Any]] = field(default_factory=list)      # session aggregates (duration/pages/repeats)
    usage_logs: List[Dict[str, Any]] = field(default_factory=list)        # active users & their effective role

    interaction_logs: List[Dict[str, Any]] = field(default_factory=list)  # drilldown etc.

    # Content Health & Governance
    governance_data: List[Dict[str, Any]] = field(default_factory=list)   # certified/owner/metadata per dashboard

    # Reliability
    dashboard_metadata: List[Dict[str, Any]] = field(default_factory=list)# id, last_refresh, sla, priority

    # Democratization
    source_catalog: List[str] = field(default_factory=list)               # ["Snowflake","Postgres",...]
    user_roles: List[Dict[str, Any]] = field(default_factory=list)        # for self-service adoption

    # Decision Support
    decision_logs: List[Dict[str, Any]] = field(default_factory=list)     # decision id + linked_dash + evidence
