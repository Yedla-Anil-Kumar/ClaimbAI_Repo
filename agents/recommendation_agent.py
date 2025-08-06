# agents/recommendation_agent.py

import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# ── Load env ──
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

# ── LLM client ──
llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=OPENAI_API_KEY
)

ONE_SHOT_EXAMPLE = """Example (style):
Signals: {"avg_maintainability_index": 45.2, "docstring_coverage": 0.18, "test_count": 1, "ci_workflow_count": 0, "has_secrets": false}
Scores: {"development_maturity": 2.1, "innovation_pipeline": 1.3}
Recommendations:
- Add basic unit tests and enable one CI workflow (e.g., GitHub Actions) to run tests on PRs.
- Improve maintainability by refactoring long functions and adding docstrings; target MI > 65 and docstring coverage > 0.5.
- Introduce ML experiment tracking (MLflow or W&B) and store metrics per run to build a repeatable process.
"""

def generate_recommendations(
    signals: Dict[str, Any],
    scores: Dict[str, Any],
    one_shot: bool = False
) -> str:
    """
    Returns a brief, actionable list of improvements based on static-analysis signals & scores.
    Uses zero-shot by default, or one-shot if `one_shot=True`.
    """
    primer = ONE_SHOT_EXAMPLE if one_shot else ""
    prompt = f"""{primer}
You are an engineering coach. Given the repo static-analysis signals and readiness scores, explain the top risks and list the 3–5 most impactful, concrete improvements. Keep it terse and actionable.

Signals:
{signals}

Scores:
{scores}
"""
    # ChatOpenAI.invoke takes a single prompt string and returns a Message object
    resp = llm.invoke(prompt)
    return resp.content.strip()
