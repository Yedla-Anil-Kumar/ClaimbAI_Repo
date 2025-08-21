# from __future__ import annotations
# import hashlib
# import random
# from datetime import datetime, timedelta, timezone
# from typing import Dict, List, Any, Optional

# def _seed_from_name(name: str) -> int:
#     h = hashlib.sha256(name.encode("utf-8")).hexdigest()
#     return int(h[:8], 16)

# def _today_iso(today_utc: Optional[str] = None) -> str:
#     if today_utc:
#         return today_utc[:10]
#     return datetime.now(timezone.utc).strftime("%Y-%m-%d")

# def build_demo_inputs(seed_name: str = "demo_org", today_utc: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Generates realistic demo inputs for ALL 10 BI metrics. No repo dependency.
#     seed_name: deterministic seed for reproducible runs per 'org'.
#     """
#     rnd = random.Random(_seed_from_name(seed_name))
#     today = _today_iso(today_utc)
#     today_dt = datetime.fromisoformat(today + "T00:00:00+00:00")

#     # --- 1) activity_events (30d)
#     users = [f"u{i}" for i in range(1, rnd.randint(6, 14))]
#     platforms = ["powerbi", "looker", "tableau"]
#     content_ids = [f"d{i}" for i in range(1, rnd.randint(5, 10))]
#     events: List[Dict[str, Any]] = []
#     for d in range(0, 30):
#         day = (today_dt - timedelta(days=d)).strftime("%Y-%m-%d")
#         dau_size = rnd.randint(0, max(1, len(users)-1))
#         day_users = rnd.sample(users, k=min(len(users), max(1, dau_size)))
#         for u in day_users:
#             events.append({
#                 "ts": f"{day}T{rnd.randint(7,18):02d}:{rnd.randint(0,59):02d}:00Z",
#                 "user_id": u,
#                 "action": rnd.choice(["view","view","view","view","edit"]),
#                 "content_id": rnd.choice(content_ids),
#                 "platform": rnd.choice(platforms),
#             })
#     activity_events = sorted(events, key=lambda e: e["ts"])

#     # --- 2) usage_logs (active users & roles)
#     roles = []
#     creator_pool = set(rnd.sample(users, k=max(1, len(users)//5)))
#     for u in users:
#         roles.append({"user": u, "role": "creator" if u in creator_pool else "viewer"})
#     usage_logs = roles

#     # --- 3) session_logs
#     session_logs: List[Dict[str, Any]] = []
#     for u in users:
#         for _ in range(rnd.randint(1, 3)):
#             session_logs.append({
#                 "user": u,
#                 "duration": rnd.randint(60, 900),
#                 "pages": rnd.randint(1, 7)
#             })

#     # --- 4) interaction_logs (drilldown)
#     interaction_logs = []
#     for _ in range(rnd.randint(10, 40)):
#         interaction_logs.append({
#             "user": rnd.choice(users),
#             "action": rnd.choice(["view","view","drill","view","drill","view"])
#         })

#     # --- 5) dashboard_metadata (refresh SLA)
#     dashboards = [f"dash:{i:02d}" for i in range(1, rnd.randint(4, 9))]
#     dashboard_metadata = []
#     for d in dashboards:
#         sla = rnd.choice(["daily","daily","weekly","monthly"])
#         lag_days = rnd.choice([0,1,2,3,7,10,14,30])
#         last = (today_dt - timedelta(days=lag_days)).strftime("%Y-%m-%d")
#         dashboard_metadata.append({"id": d, "last_refresh": last, "sla": sla})

#     # --- 6) dashboard_link_data (cross linking)
#     dashboard_link_data = []
#     for d in dashboards:
#         links = rnd.sample([x for x in dashboards if x != d], k=rnd.randint(0, min(3, max(0,len(dashboards)-1))))
#         link_usage = rnd.randint(0, 40) if links else 0
#         dashboard_link_data.append({"id": d, "links": links, "link_usage": link_usage})

#     # --- 7) governance_data
#     governance_data = []
#     for d in dashboards:
#         governance_data.append({
#             "id": d,
#             "certified": rnd.random() < 0.6,
#             "owner": rnd.choice([None, "teamA", "teamB", "teamC"]),
#             "metadata": rnd.choice([[], ["desc"], ["desc", "refresh_rate"]])
#         })

#     # --- 8) source_catalog (diversity)
#     source_catalog = rnd.sample(
#         ["Snowflake","BigQuery","Redshift","Databricks","Postgres","MySQL","MSSQL","Oracle","Salesforce","Workday","NetSuite","SAP"],
#         k=rnd.randint(2, 6)
#     )

#     # --- 9) user_roles (self service)
#     user_roles = [{"id": u, "role": ("creator" if u in creator_pool else "viewer")} for u in users]

#     # --- 10) decision_logs
#     decision_logs = []
#     for i in range(rnd.randint(2, 6)):
#         decision_logs.append({
#             "id": f"dec{i+1}",
#             "linked_dash": rnd.choice([None] + dashboards),
#             "evidence": rnd.choice([None, "", "screenshot", "doc_link"])
#         })

#     return {
#         "today_utc": today,
#         "activity_events": activity_events,
#         "usage_logs": usage_logs,
#         "session_logs": session_logs,
#         "interaction_logs": interaction_logs,
#         "dashboard_metadata": dashboard_metadata,
#         "dashboard_link_data": dashboard_link_data,
#         "governance_data": governance_data,
#         "source_catalog": source_catalog,
#         "user_roles": user_roles,
#         "decision_logs": decision_logs,
#     }
