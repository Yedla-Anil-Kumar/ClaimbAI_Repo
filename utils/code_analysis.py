# import os
# import fnmatch
# import ast
# import re
# from pathlib import Path
# from typing import List, Dict
# from radon.complexity import cc_visit
# from radon.metrics import mi_visit
# from utils.file_utils import list_all_files

# SECRET_PATTERN = re.compile(r"(?:api_key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]+")

# def ast_metrics(py_files: List[Path]) -> Dict[str, float]:
#     """
#     Compute:
#       - avg_cyclomatic_complexity
#       - avg_maintainability_index (0–1)
#       - docstring_coverage (0–1)
#     """
#     total_cc = total_mi = doc_count = func_count = 0

#     for path in py_files:
#         try:
#             src = path.read_text(encoding="utf-8")
#         except Exception:
#             continue

#         # Cyclomatic complexity
#         try:
#             for block in cc_visit(src):
#                 total_cc += block.complexity
#                 func_count += 1
#         except Exception:
#             pass

#         # Maintainability index (0–100 → normalized 0–1)
#         try:
#             mi_scores = mi_visit(src, True)
#             total_mi += sum(mi_scores.values()) / max(1, len(mi_scores))
#         except Exception:
#             pass

#         # Docstring coverage
#         try:
#             tree = ast.parse(src)
#             for node in ast.walk(tree):
#                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
#                     func_count += 1
#                     if ast.get_docstring(node):
#                         doc_count += 1
#         except Exception:
#             pass

#     avg_cc  = (total_cc / func_count) if func_count else 0.0
#     avg_mi  = (total_mi / func_count / 100.0) if func_count else 0.0  # normalizing MI to 0–1
#     doc_cov = (doc_count / func_count) if func_count else 0.0

#     return {
#         "avg_cyclomatic_complexity": avg_cc,
#         "avg_maintainability_index": avg_mi,
#         "docstring_coverage": doc_cov
#     }

# def detect_tests(root: Path) -> Dict[str, int]:
#     """
#     Detect test files and coverage config.
#     - test_file_count: files under 'tests/' or named 'test_*.py'
#     - has_tests: boolean
#     - has_test_coverage_report: True if coverage.xml or .coveragerc present
#     """
#     files = list_all_files(str(root))
#     tests = [
#         f for f in files
#         if "/tests/" in f.lower() or os.path.basename(f).startswith("test_")
#     ]
#     has_cov = (root / "coverage.xml").exists() or (root / ".coveragerc").exists()
#     return {
#         "test_file_count": len(tests),
#         "has_tests": bool(tests),
#         "has_test_coverage_report": has_cov
#     }

# def detect_env(root: Path) -> Dict[str, bool]:
#     """
#     Detect dependency/environment spec files.
#     """
#     return {
#         "has_requirements": (root / "requirements.txt").exists(),
#         "has_pipfile":       (root / "Pipfile").exists(),
#         "has_env_yml":       (root / "environment.yml").exists()
#     }

# def detect_ci(root: Path) -> Dict[str, int]:
#     """
#     Detect CI configurations:
#     - GitHub Actions (.github/workflows/*.yml)
#     - GitLab CI (.gitlab-ci.yml)
#     """
#     cnt = 0
#     gha = root / ".github" / "workflows"
#     if gha.is_dir():
#         cnt += len(fnmatch.filter(os.listdir(gha), "*.yml"))
#     if (root / ".gitlab-ci.yml").exists():
#         cnt += 1
#     return {"ci_workflow_count": cnt, "has_ci": bool(cnt)}

# def detect_cd(root: Path) -> Dict[str, int]:
#     """
#     Detect CD scripts:
#     - deploy.sh, release.sh at repo root or scripts/
#     """
#     scripts = [
#         f for f in list_all_files(str(root))
#         if Path(f).name in ("deploy.sh", "release.sh")
#     ]
#     return {"deploy_script_count": len(scripts), "has_deploy_scripts": bool(scripts)}

# def detect_experiments(root: Path) -> Dict[str, int]:
#     """
#     Detect folders named 'experiment*' at the top level.
#     """
#     dirs = [d for d in os.listdir(root) if "experiment" in d.lower()]
#     return {"experiment_folder_count": len(dirs), "has_experiments": bool(dirs)}

# def scan_secrets(root: Path) -> Dict[str, int]:
#     """
#     Scan for .env files and inline secret patterns.
#     """
#     count = sum(1 for _ in root.rglob(".env"))
#     for path in root.rglob("*.*"):
#         if path.suffix.lower() in {".py", ".yaml", ".yml", ".json", ".txt"}:
#             try:
#                 text = path.read_text(errors="ignore")
#                 if SECRET_PATTERN.search(text):
#                     count += 1
#             except Exception:
#                 pass
#     return {
#         "secret_file_count": count,
#         "has_secrets": bool(count)
#     }