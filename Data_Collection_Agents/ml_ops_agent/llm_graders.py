# Data_Collection_Agents/ml_ops_agent/llm_graders.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from Data_Collection_Agents.base_agent import BaseMicroAgent

# Load one-shot worked example (no CSV; just local few_shot)
def _load_few_shot_pair(stem: str) -> Tuple[str, str]:
    root = Path(__file__).resolve().parent / "few_shot"
    t = root / f"{stem}_example.txt"
    j = root / f"{stem}_example.json"
    ex_text = t.read_text(encoding="utf-8") if t.exists() else ""
    ex_json = ""
    if j.exists():
        try:
            ex_json = json.dumps(json.loads(j.read_text(encoding="utf-8")), indent=2)
        except Exception:
            ex_json = ""
    return ex_text, ex_json


class LLMGrader(BaseMicroAgent):
    """
    Generic one-shot grader:
      - Shows exactly one worked example (few_shot/<stem>_example.{txt,json})
      - Receives a compact JSON payload (metrics + rubric + context)
      - Returns STRICT JSON: {"band": 1..5, "rationale": str, "flags": []}
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 512):
        super().__init__(model=model, temperature=temperature)
        self.max_tokens = max_tokens

    def grade(
        self,
        stem: str,
        payload: Dict[str, Any],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        ex_text, ex_labels = _load_few_shot_pair(stem)
        sys_prompt = system or (
            "You are grading MLOps evidence. Use ONLY the provided JSON and example. "
            "Be conservative; do not infer beyond evidence. "
            "Output STRICT JSON with keys: band (1-5), rationale (<=60 words), flags[]."
        )
        example_block = ""
        if ex_text and ex_labels:
            example_block = (
                "----- EXAMPLE SNIPPET -----\n" + ex_text +
                "\n----- EXAMPLE LABELS -----\n" + ex_labels + "\n\n"
            )
        user = example_block + "GRADE THIS EVIDENCE (JSON):\n" + json.dumps(payload, indent=2) + "\n\nReturn STRICT JSON."

        mtok = max_tokens if max_tokens is not None else self.max_tokens
        resp = self._call_llm(user, sys_prompt, max_tokens=mtok)
        out = self._parse_json_response(resp)
        return {
            "band": int(out.get("band", 3) or 3),
            "rationale": out.get("rationale", "No rationale."),
            "flags": out.get("flags", []),
        }

    # ABC compatibility (unused in orchestrator; provided for completeness)
    def evaluate(self, code_snippets, context=None) -> Dict[str, Any]:
        if not context or "stem" not in context or "payload" not in context:
            return {"band": 3, "rationale": "Missing payload.", "flags": ["missing_payload"]}
        return self.grade(context["stem"], context["payload"], system=context.get("system"))
