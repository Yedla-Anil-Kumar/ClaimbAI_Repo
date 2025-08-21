from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from .canonical import BIInputs

def load_inputs(path: str) -> BIInputs:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Inputs file not found: {p}")
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return BIInputs(**data)

def make_demo_inputs(today: str = "2025-08-01") -> BIInputs:
    # small, coherent demo that exercises all 10 metrics
    return BIInputs(
        today_utc=today,
        activity_events=[
            {"ts": f"{today}T09:12:00Z","user_id":"u2","action":"view","content_id":"d2"},
            {"ts": f"{today}T11:40:00Z","user_id":"u1","action":"view","content_id":"d1"},
            {"ts": "2025-07-29T11:40:00Z","user_id":"u1","action":"view","content_id":"d3"},
            {"ts": "2025-07-27T10:00:00Z","user_id":"u3","action":"view","content_id":"d3"},
            {"ts": "2025-07-28T12:22:00Z","user_id":"u4","action":"view","content_id":"d4"},
        ],
        user_directory=[
            {"user_id":"u1","department":"Finance"},
            {"user_id":"u2","department":"Ops"},
            {"user_id":"u3","department":"Sales"},
            {"user_id":"u4","department":"HR"},
        ],
        session_logs=[
            {"user":"u1","duration":300,"pages":5,"repeats_per_week":2},
            {"user":"u2","duration":120,"pages":2,"repeats_per_week":1},
        ],
        usage_logs=[  # for Active Viewers vs Creators
            {"user":"u1","role":"viewer"},
            {"user":"u2","role":"creator"},
            {"user":"u3","role":"creator"},
            {"user":"u4","role":"viewer"},
        ],
        interaction_logs=[
            {"user":"u1","action":"drill"},
            {"user":"u2","action":"view"},
            {"user":"u3","action":"drilldown"},
        ],
        governance_data=[
            {"id":"d1","certified":True,"owner":"teamA","metadata":["description","refresh_rate"]},
            {"id":"d2","certified":False,"owner":None,"metadata":[]},
        ],
        dashboard_metadata=[
            {"id":"d1","last_refresh":"2025-07-31","sla":"daily","priority":"high"},
            {"id":"d2","last_refresh":"2025-07-28","sla":"weekly","priority":"normal"},
        ],
        source_catalog=["Snowflake","Postgres","Salesforce"],
        user_roles=[
            {"id":"u1","role":"creator"},
            {"id":"u2","role":"viewer"},
            {"id":"u3","role":"creator"},
            {"id":"u4","role":"viewer"},
        ],
        decision_logs=[
            {"id":"dec1","linked_dash":"sales_forecast","evidence":"screenshot"},
            {"id":"dec2","linked_dash":None,"evidence":None},
        ],
    )

def write_demo_inputs(path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    demo = make_demo_inputs()
    p.write_text(json.dumps(demo.__dict__, indent=2), encoding="utf-8")
    return str(p)
