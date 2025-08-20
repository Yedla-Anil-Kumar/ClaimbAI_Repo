# Data_Collection_Agents/bi_tracker/canonical.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class BIEvidence:
    """
    Canonical evidence collected purely from a source repo.
    No LLM here — only deterministic facts to be graded later.
    """

    # ---- Tool footprints ----
    tableau_files: List[str] = field(default_factory=list)        # *.twb, *.twbx, /tableau/
    powerbi_files: List[str] = field(default_factory=list)        # *.pbix, pbip/, powerbi cli
    looker_files: List[str] = field(default_factory=list)         # *.lookml, /looker/

    # ---- CI/CD & deployment automation (raw workflow texts) ----
    cicd_workflows: List[str] = field(default_factory=list)
    cicd_workflow_texts: Dict[str, str] = field(default_factory=dict)  # path -> truncated text
    deploy_commands: List[str] = field(default_factory=list)           # tabcmd/tsm/powerbi-cli/looker deploy calls
    schedules: List[str] = field(default_factory=list)                 # cron patterns or on:schedule
    codeowners_present: bool = False

    # ---- Data quality / upstream model testing ----
    data_quality_tools: List[str] = field(default_factory=list)        # great_expectations, pandera, dbt tests
    dbt_test_files: List[str] = field(default_factory=list)            # dbt schema.yml with tests
    validation_schemas: List[str] = field(default_factory=list)        # validation.(yml|yaml|json)

    # ---- KPI / semantic layer ----
    kpi_catalogs: List[str] = field(default_factory=list)              # kpis.(yml|yaml|json)
    lookml_measures: int = 0                                          # rough count via regex
    dbt_metrics_files: List[str] = field(default_factory=list)         # metrics.(yml|yaml)

    # ---- Ownership, docs, governance ----
    dashboard_readmes: List[str] = field(default_factory=list)         # README.md near dashboards
    reviewers_required_hint: bool = False                              # inferred from CI keywords
    ownership_lines: List[str] = field(default_factory=list)           # owner:, @team in docs

    # ---- Access / privacy signals ----
    role_maps: List[str] = field(default_factory=list)                 # role map files (yaml/json)
    pii_tags: List[str] = field(default_factory=list)                  # PII tags in SQL/metadata
    privacy_docs: List[str] = field(default_factory=list)              # privacy.md or similar

    # repo-only mode flag
    repo_only_mode: bool = True