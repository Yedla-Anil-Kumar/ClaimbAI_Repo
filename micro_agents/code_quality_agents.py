# micro_agents/code_quality_agents.py
from typing import Any, Dict, List, Optional

from .base_agent import BaseMicroAgent


def _join_snippets(snippets: List[str]) -> str:
    parts = []
    for i, s in enumerate(snippets, start=1):
        parts.append(f"--- Snippet {i} ---\n{s}")
    return "\n\n".join(parts)


class CyclomaticComplexityAgent(BaseMicroAgent):
    """
    Micro-agent for estimating cyclomatic complexity using the LLM.

    Output keys map to the static pipeline:
      - avg_cyclomatic_complexity (float)
      - complexity_distribution (dict)
      - complexity_recommendations (list[str])
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a strict code-quality analyst. Estimate cyclomatic "
            "complexity from code. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze the cyclomatic complexity of these code snippets. "
            "Return JSON with keys:\n"
            "- avg_complexity: number\n"
            "- complexity_distribution: {low: int, medium: int, high: int, very_high: int}\n"
            "- recommendations: list of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        result = self._parse_json_response(response)

        return {
            "avg_cyclomatic_complexity": float(result.get("avg_complexity", 0.0)),
            "complexity_distribution": result.get("complexity_distribution", {}),
            "complexity_recommendations": result.get("recommendations", []),
        }


class MaintainabilityAgent(BaseMicroAgent):
    """
    Micro-agent for maintainability/readability/design. Matches existing fields:
      - avg_maintainability_index (0–1)
    Adds:
      - readability_score (0–1)
      - design_quality  (0–1)
      - maintainability_suggestions (list[str])
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert maintainability reviewer. Score readability, "
            "design, and overall maintainability on 0–1. Respond ONLY with JSON."
        )

        prompt = (
            "Evaluate maintainability for the snippets. Return JSON keys:\n"
            "- maintainability_score: number in [0,1]\n"
            "- readability_score: number in [0,1]\n"
            "- design_quality: number in [0,1]\n"
            "- improvement_suggestions: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        result = self._parse_json_response(response)

        return {
            "avg_maintainability_index": float(
                result.get("maintainability_score", 0.0)
            ),
            "readability_score": float(result.get("readability_score", 0.0)),
            "design_quality": float(result.get("design_quality", 0.0)),
            "maintainability_suggestions": result.get("improvement_suggestions", []),
        }


class DocstringCoverageAgent(BaseMicroAgent):
    """
    Micro-agent for docstring presence/quality. Matches existing field:
      - docstring_coverage (0–1)
    Adds:
      - docstring_quality (0–1)
      - missing_documentation (list[str])
      - documentation_suggestions (list[str])
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a documentation analyst. Estimate docstring coverage and "
            "quality. Respond ONLY with JSON."
        )

        prompt = (
            "Analyze docstring coverage/quality. Return JSON keys:\n"
            "- docstring_coverage: number in [0,1]\n"
            "- docstring_quality: number in [0,1]\n"
            "- missing_documentation: array of strings\n"
            "- quality_improvements: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        result = self._parse_json_response(response)

        return {
            "docstring_coverage": float(result.get("docstring_coverage", 0.0)),
            "docstring_quality": float(result.get("docstring_quality", 0.0)),
            "missing_documentation": result.get("missing_documentation", []),
            "documentation_suggestions": result.get("quality_improvements", []),
        }


class NestedLoopsAgent(BaseMicroAgent):
    """
    Micro-agent for nested loops. Matches the static field:
      - nested_loop_files (int)  — aggregated by orchestrator
    Adds:
      - max_nesting_depth (int)
      - performance_concerns (list[str])
      - loop_optimization_suggestions (list[str])

    NOTE: Orchestrator should call this per file (one snippet per call) and
    then count files with nested loops when aggregating.
    """

    def evaluate(
        self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a loop-complexity analyst. Detect nested loops and "
            "report depth/risks. Respond ONLY with JSON."
        )

        prompt = (
            "Inspect the snippet for nested loops. Return JSON keys:\n"
            "- has_nested_loops: boolean\n"
            "- max_nesting_depth: integer\n"
            "- performance_concerns: array of strings\n"
            "- optimization_suggestions: array of strings\n\n"
            f"{_join_snippets(code_snippets)}"
        )

        response = self._call_llm(prompt, system_prompt)
        result = self._parse_json_response(response)

        has_nested = bool(result.get("has_nested_loops", False))
        return {
            # The orchestrator will sum these booleans across files to produce
            # the repo-level "nested_loop_files" number.
            "has_nested_loops": has_nested,
            "max_nesting_depth": int(result.get("max_nesting_depth", 0)),
            "performance_concerns": result.get("performance_concerns", []),
            "loop_optimization_suggestions": result.get("optimization_suggestions", []),
        }
