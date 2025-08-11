# # micro_agents/file_system_agents.py
# from __future__ import annotations

# from pathlib import Path
# from typing import Any, Dict, List, Optional

# from .base_agent import BaseMicroAgent


# def _join_snippets(snippets: List[str]) -> str:
#     parts = []
#     for i, s in enumerate(snippets, start=1):
#         parts.append(f"--- Snippet {i} ---\n{s}")
#     return "\n\n".join(parts)


# def _join_paths(paths: List[str]) -> str:
#     parts = []
#     for i, p in enumerate(paths, start=1):
#         parts.append(f"--- File {i} ---\n{p}")
#     return "\n\n".join(parts)


# class TestDetectionAgent(BaseMicroAgent):
#     """
#     Micro-agent for detecting test files and testing practices.

#     Produces keys compatible with the static pipeline:
#       - test_file_count (int)
#       - has_tests (bool)
#       - has_test_coverage_report (bool)  [best-effort; defaults to False]
#     Additional (nice to have):
#       - test_frameworks (list[str])
#       - test_coverage_estimate (float 0–1)
#       - testing_quality (float 0–1)
#     """

#     def evaluate(
#         self,
#         code_snippets: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are an expert testing analyst. Identify test files, "
#             "frameworks (pytest/unittest/etc.), and estimate coverage. "
#             "Respond ONLY with JSON."
#         )

#         prompt = (
#             "Analyze these code snippets for tests. Return JSON keys:\n"
#             "- test_file_count: integer\n"
#             "- test_frameworks: array of strings\n"
#             "- test_coverage_estimate: number in [0,1]\n"
#             "- testing_quality: number in [0,1]\n"
#             "- has_test_coverage_report: boolean (true if coverage config/files are present)\n\n"
#             f"{_join_snippets(code_snippets)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         test_count = int(res.get("test_file_count", 0))
#         has_cov_report = bool(res.get("has_test_coverage_report", False))

#         return {
#             "test_file_count": test_count,
#             "has_tests": test_count > 0,
#             "has_test_coverage_report": has_cov_report,
#             "test_frameworks": res.get("test_frameworks", []),
#             "test_coverage_estimate": float(res.get("test_coverage_estimate", 0.0)),
#             "testing_quality": float(res.get("testing_quality", 0.0)),
#         }


# class EnvironmentConfigAgent(BaseMicroAgent):
#     """
#     Micro-agent for detecting environment/dependency configuration files.

#     Normalizes common file types to canonical keys used by your pipeline:
#       - has_requirements, has_pipfile, has_env_yml, has_pyproject_toml, has_setup_py
#     """

#     _CANONICAL_KEYS = {
#         "requirements.txt": "has_requirements",
#         "requirements": "has_requirements",
#         "pipfile": "has_pipfile",
#         "environment.yml": "has_env_yml",
#         "environment.yaml": "has_env_yml",
#         "conda.yml": "has_env_yml",
#         "pyproject.toml": "has_pyproject_toml",
#         "setup.py": "has_setup_py",
#     }

#     def evaluate(
#         self,
#         file_paths: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are a dependency management analyst. Identify dependency/"
#             "environment files. Respond ONLY with JSON."
#         )

#         prompt = (
#             "From these file paths, detect dependency/environment files. "
#             "Return JSON keys:\n"
#             "- dependency_files: object mapping file type to boolean presence\n"
#             "- dependency_management_quality: number in [0,1]\n"
#             "- environment_consistency: number in [0,1]\n"
#             "- best_practices: array of strings\n\n"
#             f"{_join_paths(file_paths)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         raw = res.get("dependency_files", {}) or {}
#         out: Dict[str, Any] = {}
#         # Initialize all canonical keys to False
#         for canon in self._CANONICAL_KEYS.values():
#             out[canon] = False

#         # Normalize whatever the model returns into our canonical keys
#         for key, present in raw.items():
#             k = str(key).strip().lower()
#             canon = self._CANONICAL_KEYS.get(k)
#             if canon:
#                 out[canon] = bool(present)

#         # Back-compat names expected by your scoring
#         # (env score is computed from these three)
#         out.setdefault("has_requirements", False)
#         out.setdefault("has_pipfile", False)
#         out.setdefault("has_env_yml", False)

#         # Pass through a few informative extras (optional)
#         out["dependency_management_quality"] = float(
#             res.get("dependency_management_quality", 0.0)
#         )
#         out["environment_consistency"] = float(
#             res.get("environment_consistency", 0.0)
#         )
#         out["dependency_best_practices"] = res.get("best_practices", [])
#         return out


# class CICDAgent(BaseMicroAgent):
#     """
#     Micro-agent for CI/CD configuration detection.

#     Produces keys compatible with static pipeline:
#       - ci_workflow_count (int)
#       - has_ci (bool)
#       - has_github_actions / has_gitlab_ci / has_jenkins (optional booleans)
#     """

#     def evaluate(
#         self,
#         file_paths: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are a CI/CD analyst. Detect CI systems and workflows. "
#             "Respond ONLY with JSON."
#         )

#         prompt = (
#             "From these file paths, detect CI/CD configuration. Return JSON keys:\n"
#             "- ci_files: object mapping CI system name to count\n"
#             "- ci_workflow_count: integer\n"
#             "- ci_quality: number in [0,1]\n"
#             "- deployment_automation: number in [0,1]\n\n"
#             f"{_join_paths(file_paths)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         ci_files = res.get("ci_files", {}) or {}
#         has_github = ci_files.get("github_actions", 0) > 0 or ci_files.get(
#             "github", 0
#         ) > 0
#         has_gitlab = ci_files.get("gitlab_ci", 0) > 0 or ci_files.get(
#             "gitlab", 0
#         ) > 0
#         has_jenkins = ci_files.get("jenkins", 0) > 0

#         count = int(res.get("ci_workflow_count", 0))
#         out = {
#             "ci_workflow_count": count,
#             "has_ci": count > 0 or has_github or has_gitlab or has_jenkins,
#             "ci_quality": float(res.get("ci_quality", 0.0)),
#             "deployment_automation": float(res.get("deployment_automation", 0.0)),
#             "has_github_actions": bool(has_github),
#             "has_gitlab_ci": bool(has_gitlab),
#             "has_jenkins": bool(has_jenkins),
#         }
#         return out


# class DeploymentAgent(BaseMicroAgent):
#     """
#     Micro-agent for deployment scripts/config detection.

#     Produces keys compatible with static pipeline:
#       - deploy_script_count (int)
#       - has_deploy_scripts (bool)
#     """

#     def evaluate(
#         self,
#         file_paths: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are a deployment analyst. Detect deploy scripts/configs. "
#             "Respond ONLY with JSON."
#         )

#         prompt = (
#             "From these file paths, detect deployment materials. Return JSON keys:\n"
#             "- deployment_files: object mapping type to count\n"
#             "- deploy_script_count: integer\n"
#             "- deployment_automation: number in [0,1]\n"
#             "- deployment_quality: number in [0,1]\n\n"
#             f"{_join_paths(file_paths)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         count = int(res.get("deploy_script_count", 0))
#         out = {
#             "deploy_script_count": count,
#             "has_deploy_scripts": count > 0,
#             "deployment_automation": float(res.get("deployment_automation", 0.0)),
#             "deployment_quality": float(res.get("deployment_quality", 0.0)),
#         }

#         # Optionally expose booleans like has_docker, has_kubernetes, etc.
#         deployment_files = res.get("deployment_files", {}) or {}
#         for dtype, dcount in deployment_files.items():
#             key = f"has_{str(dtype).strip().lower()}"
#             out[key] = bool(dcount)

#         return out


# class ExperimentDetectionAgent(BaseMicroAgent):
#     """
#     Micro-agent for experiment directories and files.

#     Produces:
#       - experiment_folder_count (int)
#       - has_experiments (bool)
#     """

#     def evaluate(
#         self,
#         file_paths: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are an experiment management analyst. Detect experiment dirs. "
#             "Respond ONLY with JSON."
#         )

#         prompt = (
#             "From these file paths, detect experiment-related content. "
#             "Return JSON keys:\n"
#             "- experiment_dirs: array of directory names\n"
#             "- experiment_folder_count: integer\n"
#             "- experiment_management: number in [0,1]\n"
#             "- reproducibility_analysis: array of strings\n\n"
#             f"{_join_paths(file_paths)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         count = int(res.get("experiment_folder_count", 0))
#         return {
#             "experiment_folder_count": count,
#             "has_experiments": count > 0,
#             "experiment_dirs": res.get("experiment_dirs", []),
#             "experiment_management": float(res.get("experiment_management", 0.0)),
#             "reproducibility_analysis": res.get("reproducibility_analysis", []),
#         }


# class ProjectStructureAgent(BaseMicroAgent):
#     """
#     Micro-agent for overall project structure/organization.
#     (Optional signal; not required by your current scoring.)
#     """

#     def evaluate(
#         self,
#         file_paths: List[str],
#         context: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         system_prompt = (
#             "You are a project structure analyst. Assess organization and docs. "
#             "Respond ONLY with JSON."
#         )

#         prompt = (
#             "From these file paths, assess project structure. Return JSON keys:\n"
#             "- structure_quality: number in [0,1]\n"
#             "- organization_patterns: array of strings\n"
#             "- documentation_quality: number in [0,1]\n"
#             "- best_practices_adherence: number in [0,1]\n\n"
#             f"{_join_paths(file_paths)}"
#         )

#         response = self._call_llm(prompt, system_prompt)
#         res = self._parse_json_response(response)

#         return {
#             "structure_quality": float(res.get("structure_quality", 0.0)),
#             "organization_patterns": res.get("organization_patterns", []),
#             "documentation_quality": float(res.get("documentation_quality", 0.0)),
#             "best_practices_adherence": float(
#                 res.get("best_practices_adherence", 0.0)
#             ),
#         }
