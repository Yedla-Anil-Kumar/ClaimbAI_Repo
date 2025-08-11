from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List
import os

from dotenv import load_dotenv

from .code_quality_agents import (
    CyclomaticComplexityAgent,
    DocstringCoverageAgent,
    MaintainabilityAgent,
    NestedLoopsAgent,
)
from .file_system_agents import (
    CICDAgent,
    DeploymentAgent,
    EnvironmentConfigAgent,
    ExperimentDetectionAgent,
    ProjectStructureAgent,
    TestDetectionAgent,
)
from .infrastructure_agents import (
    DataPipelineAgent,
    FeatureEngineeringAgent,
    InferenceEndpointAgent,
    ModelExportAgent,
    ParallelPatternsAgent,
    SecurityAgent,
)
from .ml_framework_agents import (
    DataValidationAgent,
    ExperimentTrackingAgent,
    HyperparameterOptimizationAgent,
    MLFrameworkAgent,
    ModelEvaluationAgent,
    ModelTrainingAgent,
)
from utils.aimri_mapping import compute_aimri_summary
load_dotenv()

# ---- Budget caps (env-overridable) ----

MAX_FILES_PER_REPO = int(os.getenv("MA_MAX_FILES_PER_REPO", "40"))
MAX_SNIPPET_BYTES = int(os.getenv("MA_MAX_SNIPPET_BYTES", "3000"))
MAX_PATHS_PER_AGENT = int(os.getenv("MA_MAX_PATHS_PER_AGENT", "400"))


class MicroAgentOrchestrator:
    """
    Orchestrates all micro-agents and aggregates per-file LLM evaluations
    into the same signal schema your dev_platform_agent uses.

    IMPORTANT:
    - Calls the LLM for each file individually (per your requirement).
    - Aggregates booleans with OR, counts by summation, and averages
      maintainability/docstring/complexity across files.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

        # Initialize micro-agents
        self.agents_code = [
            CyclomaticComplexityAgent(model, temperature),
            MaintainabilityAgent(model, temperature),
            DocstringCoverageAgent(model, temperature),
            NestedLoopsAgent(model, temperature),
        ]
        self.agents_ml = [
            MLFrameworkAgent(model, temperature),
            ExperimentTrackingAgent(model, temperature),
            HyperparameterOptimizationAgent(model, temperature),
            DataValidationAgent(model, temperature),
            ModelTrainingAgent(model, temperature),
            ModelEvaluationAgent(model, temperature),
        ]
        self.agents_infra = [
            ParallelPatternsAgent(model, temperature),
            InferenceEndpointAgent(model, temperature),
            ModelExportAgent(model, temperature),
            DataPipelineAgent(model, temperature),
            FeatureEngineeringAgent(model, temperature),
            SecurityAgent(model, temperature),
        ]
        self.agents_fs = [
            TestDetectionAgent(model, temperature),
            EnvironmentConfigAgent(model, temperature),
            CICDAgent(model, temperature),
            DeploymentAgent(model, temperature),
            ExperimentDetectionAgent(model, temperature),
            ProjectStructureAgent(model, temperature),
        ]

    # ---------- public API ----------

    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        root = Path(repo_path)

        # Per-file contents (source .py only) → sample + trim
        all_source = self._get_source_files(repo_path)
        picked = self._pick_representative_files(all_source)
        source_texts = self._read_files_snippets(picked)

        # All file paths (for FS-style agents) → trim per agent later
        all_paths = self._get_all_paths(repo_path)

        # Aggregate signals across per-file LLM calls
        signals: Dict[str, Any] = self._aggregate_code_signals(source_texts)
        signals.update(self._aggregate_ml_signals(source_texts))
        signals.update(self._aggregate_infra_signals(source_texts))
        signals.update(self._aggregate_fs_signals(all_paths))

        # Compute scores with your existing function
        scores = self._calculate_scores(signals, len(picked))
        aimri = compute_aimri_summary(signals)

        return {
            "agent": "micro_agent_orchestrator",
            "repo": root.name,
            #"signals": signals,
            "scores": scores,
            "micro_agent_results": {
                "source_files_analyzed": len(picked),
                "total_files_analyzed": len(all_source),
            },
            "aimri_summary": aimri,
        }

    # ---------- file helpers ----------

    def _get_source_files(self, repo_path: str) -> List[Path]:
        from utils.file_utils import list_source_files

        return list(list_source_files(repo_path))

    def _get_all_paths(self, repo_path: str) -> List[str]:
        from utils.file_utils import list_all_files

        return list(list_all_files(repo_path))

    def _pick_representative_files(self, paths: List[Path]) -> List[Path]:
        """Prefer src/* and ML/serving/pipeline names, then cap to budget."""
        keywords = (
            "/src/",
            "train",
            "eval",
            "serve",
            "api",
            "pipeline",
            "dag",
            "flow",
            "inference",
        )
        pri = [p for p in paths if any(k in str(p).lower() for k in keywords)]
        # Deduplicate, preserve order
        seen = set()
        dedup: List[Path] = []
        for p in pri + paths:
            if p not in seen:
                seen.add(p)
                dedup.append(p)
        return dedup[:MAX_FILES_PER_REPO]

    @staticmethod
    def _read_files_snippets(paths: Iterable[Path]) -> List[str]:
        """Return head+tail snippets to keep token usage bounded per call."""
        out: List[str] = []
        half = max(1, MAX_SNIPPET_BYTES // 2)
        for p in paths:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            if len(text) <= MAX_SNIPPET_BYTES:
                out.append(text)
            else:
                head = text[:half]
                tail = text[-half:]
                out.append(head + "\n# ...\n" + tail)
        return out

    # ---------- aggregation per category ----------

    def _aggregate_code_signals(self, code_snippets: List[str]) -> Dict[str, Any]:
        """
        Per-file LLM calls; averages numeric quality metrics and ORs booleans.
        """
        accum: Dict[str, Any] = {
            "avg_cyclomatic_complexity": 0.0,
            "avg_maintainability_index": 0.0,
            "docstring_coverage": 0.0,
            "nested_loop_files": 0,
        }
        n = max(1, len(code_snippets))
        for snippet in code_snippets:
            # each agent sees a single snippet (per-file call)
            cc = self.agents_code[0].evaluate([snippet])
            mi = self.agents_code[1].evaluate([snippet])
            ds = self.agents_code[2].evaluate([snippet])
            nl = self.agents_code[3].evaluate([snippet])

            # averages
            accum["avg_cyclomatic_complexity"] += float(
                cc.get("avg_cyclomatic_complexity", 0.0)
            )
            accum["avg_maintainability_index"] += float(
                mi.get("avg_maintainability_index", 0.0)
            )
            accum["docstring_coverage"] += float(ds.get("docstring_coverage", 0.0))

            # count of files with nested loops (treat >0 depth as 1 file)
            if (
                int(nl.get("max_nesting_depth", 0)) > 1
                or int(nl.get("nested_loop_files", 0)) > 0
            ):
                accum["nested_loop_files"] += 1

        accum["avg_cyclomatic_complexity"] /= n
        accum["avg_maintainability_index"] /= n
        accum["docstring_coverage"] /= n
        return accum

    def _aggregate_ml_signals(self, code_snippets: List[str]) -> Dict[str, Any]:
        """
        Sums counts and ORs booleans for ML-related signals, per file.
        """
        out: Dict[str, Any] = {
            "framework_torch": 0,
            "framework_tensorflow": 0,
            "framework_sklearn": 0,
            "framework_keras": 0,
            "framework_xgboost": 0,
            "framework_lightgbm": 0,
            "uses_mlflow": False,
            "uses_wandb": False,
            "uses_clearml": False,
            "has_hyperparam_file": False,
            "uses_optuna": False,
            "uses_ray_tune": False,
            "train_script_count": 0,
            "has_entrypoint_training": False,
            "eval_script_count": 0,
            "uses_metrics_library": False,
            "uses_great_expectations": False,
            "uses_evidently": False,
            "uses_pandera": False,
        }

        for snippet in code_snippets:
            out = self._sum_dict(out, self.agents_ml[0].evaluate([snippet]))
            out = self._or_bools(out, self.agents_ml[1].evaluate([snippet]))
            out = self._or_bools(out, self.agents_ml[2].evaluate([snippet]))
            out = self._or_bools(out, self.agents_ml[3].evaluate([snippet]))

            tr = self.agents_ml[4].evaluate([snippet])
            out["train_script_count"] += int(tr.get("train_script_count", 0))
            out["has_entrypoint_training"] = out["has_entrypoint_training"] or bool(
                tr.get("has_entrypoint_training", False)
            )

            ev = self.agents_ml[5].evaluate([snippet])
            out["eval_script_count"] += int(ev.get("eval_script_count", 0))
            out["uses_metrics_library"] = out["uses_metrics_library"] or bool(
                ev.get("uses_metrics_library", False)
            )

        return out

    def _aggregate_infra_signals(self, code_snippets: List[str]) -> Dict[str, Any]:
        """
        OR booleans and set flags for infra-related signals, per file.
        """
        out: Dict[str, Any] = {
            "uses_threading": False,
            "uses_multiprocessing": False,
            "uses_concurrent": False,
            "uses_fastapi": False,
            "uses_flask": False,
            "uses_streamlit": False,
            "exports_torch_model": False,
            "exports_sklearn_model": False,
            "has_airflow": False,
            "has_prefect": False,
            "has_luigi": False,
            "has_argo": False,
            "has_kedro": False,
            "uses_sklearn_preprocessing": False,
            "uses_featuretools": False,
            "uses_tsfresh": False,
            "has_secrets": False,
        }

        for snippet in code_snippets:
            out = self._or_bools(out, self.agents_infra[0].evaluate([snippet]))
            out = self._or_bools(out, self.agents_infra[1].evaluate([snippet]))
            out = self._or_bools(out, self.agents_infra[2].evaluate([snippet]))
            out = self._or_bools(out, self.agents_infra[3].evaluate([snippet]))
            out = self._or_bools(out, self.agents_infra[4].evaluate([snippet]))
            out = self._or_bools(out, self.agents_infra[5].evaluate([snippet]))

        return out

    def _aggregate_fs_signals(self, all_paths: List[str]) -> Dict[str, Any]:
        """
        Trim path lists per agent to avoid huge prompts and then call once each.
        """
        out: Dict[str, Any] = {
            "test_file_count": 0,
            "has_tests": False,
            "has_test_coverage_report": False,
            "has_requirements": False,
            "has_pipfile": False,
            "has_env_yml": False,
            "ci_workflow_count": 0,
            "has_ci": False,
            "deploy_script_count": 0,
            "has_deploy_scripts": False,
            "experiment_folder_count": 0,
            "has_experiments": False,
        }

        # Helper to limit paths
        def cap(lst: List[str]) -> List[str]:
            return lst[:MAX_PATHS_PER_AGENT]

        # Test detection: paths are not strictly needed; keep minimal to avoid overflow
        td_paths: List[str] = []
        td = self.agents_fs[0].evaluate([])
        out.update(td)

        # Env config
        env_paths = [
            p
            for p in all_paths
            if any(
                name in p.lower()
                for name in (
                    "requirements",
                    "pipfile",
                    "environment.yml",
                    "environment.yaml",
                    "pyproject.toml",
                    "setup.py",
                )
            )
        ]
        out.update(self.agents_fs[1].evaluate(cap(env_paths or all_paths)))

        # CI/CD
        ci_paths = [
            p
            for p in all_paths
            if any(
                tag in p.lower()
                for tag in (
                    ".github/workflows",
                    ".gitlab-ci",
                    "jenkins",
                    ".circleci",
                    "azure-pipelines",
                    "workflow",
                )
            )
        ]
        out.update(self.agents_fs[2].evaluate(cap(ci_paths or all_paths)))

        # Deploy
        dep_paths = [
            p
            for p in all_paths
            if any(
                tag in p.lower()
                for tag in (
                    "deploy",
                    "release",
                    "docker",
                    "docker-compose",
                    "k8s",
                    "kubernetes",
                    "helm",
                    "chart",
                    "deployment.yaml",
                    "service.yaml",
                )
            )
        ]
        out.update(self.agents_fs[3].evaluate(cap(dep_paths or all_paths)))

        # Experiments
        exp_paths = [
            p
            for p in all_paths
            if any(tag in p.lower() for tag in ("experiment", "/exp/", "experiments"))
        ]
        out.update(self.agents_fs[4].evaluate(cap(exp_paths or all_paths)))

        # Project structure (sample paths)
        out.update(self.agents_fs[5].evaluate(cap(all_paths)))

        return out

    # ---------- generic merging helpers ----------

    @staticmethod
    def _or_bools(base: Dict[str, Any], add: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(base)
        for k, v in add.items():
            if isinstance(v, bool) and k in out and isinstance(out[k], bool):
                out[k] = out[k] or v
        return out

    @staticmethod
    def _sum_dict(base: Dict[str, Any], add: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(base)
        for k, v in add.items():
            if (
                isinstance(v, (int, float))
                and k in out
                and isinstance(out[k], (int, float))
            ):
                out[k] = out[k] + v
        return out

    # ---------- scoring ----------

    @staticmethod
    def _calculate_scores(
        signals: Dict[str, Any], num_py_files: int
    ) -> Dict[str, float]:
        # Reuse your existing scoring implementation
        from agents.dev_platform_agent import calculate_scores

        return calculate_scores(signals, num_py_files)
