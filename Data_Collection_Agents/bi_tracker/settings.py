# from __future__ import annotations
# import os
# import re
# from dataclasses import dataclass
# from typing import Dict, Any

# # --------- IO / limits ----------
# MAX_BYTES_PER_TEXT = int(os.getenv("BI_MAX_BYTES_PER_TEXT", "120000"))

# # --------- Regex patterns (compiled once, imported by repo_extractors) ----------
# RE: Dict[str, Any] = {
#     # BI artifacts
#     "looker": re.compile(r"\.lkml$|\.lookml$|\.dashboard\.lookml$|\.model\.lkml$", re.I),
#     "tableau_twb": re.compile(r"\.twb$", re.I),
#     "tableau_twbx": re.compile(r"\.twbx$", re.I),
#     "pbi_pbix": re.compile(r"\.pbix$", re.I),
#     "pbi_pbit": re.compile(r"\.pbit$", re.I),

#     # Governance / metadata
#     "certified": re.compile(r"\bcertified\s*:\s*true\b|\bCertification\s*:\s*(Yes|True|Certified)\b", re.I),
#     "owner": re.compile(r"\b(owner|steward|assignee)\s*:\s*[\w\-\.\s/]+", re.I),
#     "glossary": re.compile(r"\bglossary\b|\bdata dictionary\b|\bbusiness terms\b", re.I),

#     # Lineage / linking
#     "lineage": re.compile(r"\b(explore:\s|\bdepends_on:\s|\bsources?:\s|\bref\(|from\s+\w+\.)", re.I),
#     "xlinks": re.compile(r"(link:|dashboard:|href=.*dashboard|/dashboards/\w+|/reports/)", re.I),
#     "wide_open": re.compile(r"\b(All authenticated users|Everyone|Public)\b", re.I),
#     "perm_manifest": re.compile(r"(permissions|acl|access)[\s:=]", re.I),

#     # Refresh / reliability / cache
#     "refresh_terms": re.compile(r"refresh|schedule|update|extract\s+refresh|pdt\s+build|publish", re.I),
#     "cron": re.compile(r"cron:\s*['\"][^'\"]+['\"]|schedule:\s*['\"][^'\"]+['\"]|@daily|@hourly", re.I),
#     "cache": re.compile(r"\bcache|persist(ed)?_explores|pdt|materialized\s+view", re.I),

#     # Democratization / self-service
#     "explore": re.compile(r"\bexplore\b|ask\s*data|Q&A|nlq", re.I),
#     "contrib": re.compile(r"contributor|how to build (a )?dashboard|self-service|creator guide", re.I),
#     "usage_instrument": re.compile(r"track\(|analytics|telemetry|event\(", re.I),

#     # Decision support / alerts
#     "decision_refs": re.compile(r"Jira|ServiceNow|OKR|decision\s+log|RFC-\d+", re.I),
#     "alert_sub": re.compile(r"subscription|alert|webhook|slack|ms-?teams|pagerduty", re.I),

#     # Cost tagging (Terraform/ARM)
#     "tags_tf": re.compile(r"tags\s*=\s*{([^}]+)}", re.I | re.S),
#     "tag_line": re.compile(r"([A-Za-z0-9_\-]+)\s*=\s*([\"'][^\"']+[\"']|\w+)", re.I),

#     # Data sources (rough lexicon of common sources)
#     "sources": re.compile(r"snowflake|bigquery|redshift|postgres|mysql|mssql|athena|databricks|salesforce|workday|netsuite|sap", re.I),

#     # CI locations
#     "gha_path": re.compile(r"\.github/workflows/.*\.(yml|yaml)$", re.I),
#     "gitlab_path": re.compile(r"\.gitlab-ci\.yml$", re.I),
#     "ado_path": re.compile(r"azure-pipelines\.(yml|yaml)$", re.I),
#     "jenkins": re.compile(r"(?i)jenkinsfile$"),
# }

# ALLOWED_EXTS = (".lkml", ".lookml", ".twb", ".yml", ".yaml", ".json", ".md", ".sql", ".tf", ".py", ".ini", ".cfg", ".toml", ".sh")
# BINARY_LIST_ONLY = (".pbix", ".pbit", ".twbx")
# SPECIAL_FILES = {"CODEOWNERS", "Makefile", "Chart.yaml", "Dockerfile", "Jenkinsfile"}

# REQUIRED_COST_TAG_KEYS = ["owner", "cost-center", "env", "service"]

# # --------- Scoring weights (centralized; no hard-coded numbers in functions) ----------
# SCORING_WEIGHTS = {
#     "bi_capabilities": {"surface": 0.40, "governance": 0.25, "lineage": 0.15, "democrat": 0.20},
#     "operations_maturity": {"refresh": 0.30, "cost": 0.20, "decision": 0.20, "diversity": 0.15, "perm": 0.15},
# }

# # --------- LLM rubrics (fed into LLM graders via payload builders) ----------
# RUBRICS = {
#     "governance": {
#         "5": "owners_present & certified_flags & metadata_docs all strong; coverage_ratio >= 0.8",
#         "4": "two strong, one moderate; coverage_ratio >= 0.6",
#         "3": "mixed evidence; coverage_ratio >= 0.4",
#         "2": "weak evidence; coverage_ratio >= 0.2",
#         "1": "little to no governance evidence",
#     },
#     "lineage": {
#         "5": "lineage_defs high & cross_links present; no risky permissions",
#         "4": "lineage_defs moderate & some cross_links; risky minimal",
#         "3": "some lineage or links; permissions mixed",
#         "2": "few lineage and links; risky permissions present",
#         "1": "none; wide-open permissions",
#     },
#     "refresh": {
#         "5": "refresh_jobs & schedules & cache_signals all present",
#         "4": "jobs & schedules present",
#         "3": "jobs present only",
#         "2": "only hints",
#         "1": "no refresh evidence",
#     },
#     "democratization": {
#         "5": "explore_or_nlq & contrib_guides & instrumentation present",
#         "4": "two of the three present",
#         "3": "one present",
#         "2": "weak hints",
#         "1": "none",
#     },
#     "decision_support": {
#         "5": "decision_refs & alert_subscriptions strong; jira/servicenow/okr links present",
#         "4": "refs & alerts present; limited external links",
#         "3": "some refs or alerts",
#         "2": "weak hints",
#         "1": "none",
#     },
#     "cost": {
#         "5": "owner, cost-center, env, service tags detected consistently",
#         "4": "most present",
#         "3": "some present",
#         "2": "few present",
#         "1": "none",
#     },
#     "data_diversity": {
#         "5": ">=4 distinct sources across >=2 domains",
#         "4": ">=3 sources across >=2 domains",
#         "3": ">=2 sources in 1 domain",
#         "2": "1 source",
#         "1": "no sources detected",
#     },
# }