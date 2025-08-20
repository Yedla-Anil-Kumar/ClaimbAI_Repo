# Data_Collection_Agents/bi_tracker/repo_extractors.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List
from utils.file_utils import list_all_files
from .canonical import BIEvidence

ALLOWED_EXTS = (".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".txt", ".md", ".sql")
SPECIAL_FILES = {"Dockerfile", "Jenkinsfile", "CODEOWNERS", "Chart.yaml", "Makefile", ".gitlab-ci.yml"}
MAX_BYTES_PER_TEXT = 100_000

def _read_text(path: Path, max_bytes: int = MAX_BYTES_PER_TEXT) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
    except Exception:
        return ""

def _norm(p: Path) -> str:
    return str(p).replace("\\", "/")

RE = {
    # Footprints
    "tableau_ext": re.compile(r"\.(twb|twbx)$", re.I),
    "powerbi_ext": re.compile(r"\.(pbix)$", re.I),
    "looker_ext":  re.compile(r"\.lookml$", re.I),

    "tableau_dir": re.compile(r"/(tableau|dashboards)/", re.I),
    "powerbi_dir": re.compile(r"/(powerbi|bi)/", re.I),
    "looker_dir":  re.compile(r"/(looker|lookml)/", re.I),

    # Publishing/CLI commands inside scripts/CI
    "tabcmd": re.compile(r"\btabcmd\b|\btsm\b|tableau_tools", re.I),
    "powerbi_cli": re.compile(r"\bpowerbi\b|\bpbi-tools\b|\bpowerbi-cli\b", re.I),
    "looker_deploy": re.compile(r"\blooker\b.*(deploy|content|validator)", re.I),

    # CI file paths
    "gha_path": re.compile(r"\.github/workflows/.*\.(yml|yaml)$", re.I),
    "gitlab_path": re.compile(r"\.gitlab-ci\.yml$", re.I),
    "ado_path": re.compile(r"azure-pipelines\.(yml|yaml)$", re.I),
    "jenkins": re.compile(r"(?i)jenkinsfile$"),

    # Scheduling / reviews
    "cron": re.compile(r"cron:\s*['\"][^'\"]+['\"]|on:\s*schedule|schedule_interval\s*=\s*['\"][^'\"]+['\"]|@daily|@hourly", re.I),
    "review_gate": re.compile(r"(required_approving_review|CODEOWNERS|pull_request_review|require-review)", re.I),

    # Data quality & validation
    "ge": re.compile(r"great_expectations", re.I),
    "pandera": re.compile(r"\bpandera\b", re.I),
    "dbt_test": re.compile(r"(?m)^\s*tests\s*:\s*\n", re.I),  # dbt schema tests section
    "validation_file": re.compile(r"validation\.(ya?ml|json)$", re.I),
    "dbt_metrics": re.compile(r"(?m)^\s*metrics\s*:\s*\n", re.I),

    # KPI catalogs
    "kpi_catalog": re.compile(r"kpis?\.(ya?ml|json)$", re.I),
    "lookml_measure": re.compile(r"(?m)^\s*measure:\s*[\w_]+\s*$", re.I),

    # Ownership/docs
    "owner_line": re.compile(r"(owner|owned_by|contact)\s*[:=]\s*.+", re.I),

    # Access/privacy
    "role_map": re.compile(r"(roles|permissions|acl)s?\.(ya?ml|json)$", re.I),
    "pii_tag": re.compile(r"\bPII\b|\b(personal|sensitive)\b.*\bdata\b", re.I),
    "privacy_doc": re.compile(r"privacy(\.md|\.rst)?$", re.I),
}

def scan_repo(repo_path: str) -> BIEvidence:
    ev = BIEvidence()
    files: List[str] = list(list_all_files(repo_path))

    for f in files:
        p = Path(f)
        name = _norm(p)
        base = p.name

        if (p.suffix.lower() not in ALLOWED_EXTS) and (base not in SPECIAL_FILES) and not RE["tableau_ext"].search(base) and not RE["powerbi_ext"].search(base) and not RE["looker_ext"].search(base):
            continue

        text = _read_text(p)

        # ---- Tool footprints ----
        if RE["tableau_ext"].search(base) or RE["tableau_dir"].search(name):
            ev.tableau_files.append(name)
        if RE["powerbi_ext"].search(base) or RE["powerbi_dir"].search(name) or RE["powerbi_cli"].search(text):
            ev.powerbi_files.append(name)
        if RE["looker_ext"].search(base) or RE["looker_dir"].search(name):
            ev.looker_files.append(name)

        # ---- CI/CD ----
        is_ci = any(RE[k].search(name) for k in ("gha_path", "gitlab_path", "ado_path", "jenkins"))
        if is_ci:
            ev.cicd_workflows.append(name)
            ev.cicd_workflow_texts[name] = text
            # find publish commands
            if RE["tabcmd"].search(text):
                ev.deploy_commands.append("tableau:tabcmd")
            if RE["powerbi_cli"].search(text):
                ev.deploy_commands.append("powerbi:cli")
            if RE["looker_deploy"].search(text):
                ev.deploy_commands.append("looker:deploy")
            # schedules
            for m in RE["cron"].finditer(text):
                ev.schedules.append(m.group(0))
            if RE["review_gate"].search(text):
                ev.reviewers_required_hint = True

        if base == "CODEOWNERS":
            ev.codeowners_present = True

        # ---- Data quality / validation ----
        if RE["ge"].search(text): ev.data_quality_tools.append("great_expectations")
        if RE["pandera"].search(text): ev.data_quality_tools.append("pandera")
        if RE["dbt_test"].search(text): ev.dbt_test_files.append(name)
        if RE["validation_file"].search(base): ev.validation_schemas.append(name)
        if RE["dbt_metrics"].search(text): ev.dbt_metrics_files.append(name)

        # ---- KPI / semantic layer ----
        if RE["kpi_catalog"].search(base): ev.kpi_catalogs.append(name)
        ev.lookml_measures += len(RE["lookml_measure"].findall(text)) if base.endswith(".lookml") else 0

        # ---- Ownership / docs ----
        if base.lower() == "readme.md" and ("/dashboards/" in name or "/bi/" in name or "/tableau/" in name or "/looker/" in name or "/powerbi/" in name):
            ev.dashboard_readmes.append(name)
        for m in RE["owner_line"].finditer(text):
            ev.ownership_lines.append(m.group(0).strip())

        # ---- Access / privacy ----
        if RE["role_map"].search(base): ev.role_maps.append(name)
        if RE["pii_tag"].search(text): ev.pii_tags.append(name)
        if RE["privacy_doc"].search(base.lower()): ev.privacy_docs.append(name)

    # dedupe / tidy
    ev.data_quality_tools = sorted(set(ev.data_quality_tools))
    ev.deploy_commands = sorted(set(ev.deploy_commands))
    ev.schedules = sorted(set(ev.schedules))
    return ev