# # Data_Collection_Agents/bi_tracker/metrics_engine.py
# from __future__ import annotations
# from typing import Dict, List
# from .canonical import BIEvidence

# def _bool(x) -> bool: return bool(x)

# # ---------- Deterministic proxies ----------
# def platform_proxy_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "tableau_present": _bool(ev.tableau_files),
#         "powerbi_present": _bool(ev.powerbi_files),
#         "looker_present": _bool(ev.looker_files),
#         "counts": {
#             "tableau": sum(1 for p in ev.tableau_files if p.endswith((".twb", ".twbx"))),
#             "powerbi": sum(1 for p in ev.powerbi_files if p.endswith(".pbix")),
#             "looker": sum(1 for p in ev.looker_files if p.endswith(".lookml")),
#         }
#     }

# def deploy_automation_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "workflow_files": ev.cicd_workflows,
#         "deploy_commands": ev.deploy_commands,
#         "schedules": ev.schedules,
#         "codeowners_present": ev.codeowners_present,
#         "reviewers_required_hint": ev.reviewers_required_hint,
#         "present": bool(ev.deploy_commands or ev.cicd_workflows),
#     }

# def freshness_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "schedules": ev.schedules,
#         "has_schedule": bool(ev.schedules),
#         "has_quality_tools": bool(ev.data_quality_tools or ev.dbt_test_files or ev.validation_schemas),
#         "quality_tools": sorted(set(ev.data_quality_tools)),
#         "dbt_tests": ev.dbt_test_files,
#         "validation_schemas": ev.validation_schemas,
#     }

# def kpi_semantic_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "kpi_catalogs": ev.kpi_catalogs,
#         "lookml_measures": ev.lookml_measures,
#         "dbt_metrics_files": ev.dbt_metrics_files,
#     }

# def docs_governance_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "dashboard_readmes": ev.dashboard_readmes,
#         "ownership_lines": ev.ownership_lines,
#         "codeowners_present": ev.codeowners_present,
#         "reviewers_required_hint": ev.reviewers_required_hint,
#     }

# def access_privacy_metrics(ev: BIEvidence) -> Dict:
#     return {
#         "role_maps": ev.role_maps,
#         "pii_tags": ev.pii_tags,
#         "privacy_docs": ev.privacy_docs,
#     }

# # ---------- Payload builders for one-shot grading ----------
# def payload_bi_deploy_readiness(ev: BIEvidence) -> Dict:
#     m = deploy_automation_metrics(ev)
#     return {
#         "metric_id": "bi.deploy_readiness_band",
#         "evidence": m,
#         "rubric": {
#             "5": "Automated deploy to BI tool with schedules + review gates (CODEOWNERS or required review).",
#             "4": "Automated deploy present and scheduled; partial review gates.",
#             "3": "Manual or partial scripting; limited schedules.",
#             "2": "Weak hints only.",
#             "1": "No deployment automation evidence."
#         }
#     }

# def payload_bi_data_freshness(ev: BIEvidence) -> Dict:
#     m = freshness_metrics(ev)
#     return {
#         "metric_id": "bi.data_freshness_practices_band",
#         "evidence": m,
#         "rubric": {
#             "5": "Schedules + upstream data quality tests + validation schemas.",
#             "4": "Schedules + some quality tools (GE/Pandera/dbt tests).",
#             "3": "Schedules only.",
#             "2": "Sporadic hints.",
#             "1": "No refresh scheduling."
#         }
#     }

# def payload_bi_kpi_semantics(ev: BIEvidence) -> Dict:
#     m = kpi_semantic_metrics(ev)
#     return {
#         "metric_id": "bi.kpi_semantic_quality_band",
#         "evidence": m,
#         "rubric": {
#             "5": "KPI catalog + LookML measures or dbt metrics are substantial.",
#             "4": "KPI catalog + some semantic layer elements.",
#             "3": "Ad-hoc metrics; partial definitions.",
#             "2": "Minimal definitions.",
#             "1": "No KPI/semantic layer evidence."
#         }
#     }

# def payload_bi_docs_governance(ev: BIEvidence) -> Dict:
#     m = docs_governance_metrics(ev)
#     return {
#         "metric_id": "bi.docs_governance_band",
#         "evidence": m,
#         "rubric": {
#             "5": "Dashboard READMEs + ownership lines + CODEOWNERS + review gates.",
#             "4": "Docs + owners + one gate.",
#             "3": "Docs but limited ownership/gates.",
#             "2": "Sparse docs.",
#             "1": "No docs."
#         }
#     }

# def payload_bi_access_privacy(ev: BIEvidence) -> Dict:
#     m = access_privacy_metrics(ev)
#     return {
#         "metric_id": "bi.access_privacy_readiness_band",
#         "evidence": m,
#         "rubric": {
#             "5": "Role maps present + PII tags + privacy docs.",
#             "4": "Two of three.",
#             "3": "One present.",
#             "2": "Weak hints.",
#             "1": "None."
#         }
#     }