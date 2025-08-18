# Data_Collection_Agents/ml_ops_agent/llm_graders.py
from __future__ import annotations
import json
import time
import random
from typing import Any, Dict, Optional
from Data_Collection_Agents.base_agent import BaseMicroAgent
from pathlib import Path


def _load_few_shot_pair(stem: str) -> tuple[str, str]:
    root = Path(__file__).resolve().parent / "few_shot"
    txt = (root / f"{stem}_example.txt")
    jsn = (root / f"{stem}_example.json")
    ex_text = txt.read_text(encoding="utf-8") if txt.exists() else ""
    ex_json = ""
    if jsn.exists():
        try:
            ex_json = json.dumps(json.loads(jsn.read_text(encoding="utf-8")), indent=2)
        except Exception:
            ex_json = ""
    return ex_text, ex_json


class LLMGrader(BaseMicroAgent):
    """
    Generic, reusable one-shot grader.
    - Accepts payloads of the form: {"metric_id": str, "rubric": {..} or str, "evidence": {..}}
    - Loads ONE worked example if present (few_shot/<stem>_example.{txt,json})
    - Returns STRICT JSON: {"metric_id": "...", "band": 1..5, "rationale": str, "flags": [..]}
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
        # Normalize payload: allow "metrics" instead of "evidence"
        if "evidence" not in payload and "metrics" in payload:
            payload = {**payload, "evidence": payload["metrics"]}
            payload.pop("metrics", None)

        ex_text, ex_labels = _load_few_shot_pair(stem)
        sys_prompt = system or (
            "You are grading MLOps evidence. Use ONLY the JSON payload. "
            "Return STRICT JSON with keys: metric_id, band (1-5), rationale, flags[]. "
            "Do not invent any data."
        )

        example = ""
        if ex_text and ex_labels:
            example = (
                "----- EXAMPLE SNIPPET -----\n"
                + ex_text
                + "\n----- EXAMPLE LABELS -----\n"
                + ex_labels
                + "\n\n"
            )

        user = (
            example
            + "Here is the grading payload (JSON):\n"
            + json.dumps(payload, indent=2)
            + "\n\nReturn STRICT JSON now."
        )

        # basic jitter when called from several threads
        time.sleep(random.uniform(0.02, 0.08))
        mtok = max_tokens if max_tokens is not None else self.max_tokens
        resp = self._call_llm(user, sys_prompt, max_tokens=mtok)
        out = self._parse_json_response(resp)

        return {
            "metric_id": payload.get("metric_id", "unknown"),
            "band": int(out.get("band", 3) or 3),
            "rationale": out.get("rationale", "No rationale provided."),
            "flags": out.get("flags", []),
        }

    # Optional interface parity with BaseMicroAgent
    def evaluate(self, code_snippets, context=None):
        return {"band": 3, "rationale": "LLMGrader.evaluate() not used directly.", "flags": ["not_used"]}
