import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import yaml
import json
load_dotenv()

KEY = os.getenv("OPENAI_API_KEY")
if not KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=KEY)


def _load_json(path: str) -> str:
    """Helper: read JSON file and return raw JSON string."""
    with open(path, "r", encoding="utf-8") as f:
        return json.dumps(json.load(f), ensure_ascii=False)


def check_schema_consistency(baseline_schema_json: str, table_schemas_json: str) -> Dict[str, Any]:
    """Compare baseline and actual schema JSONs using LLM and return structured JSON evaluation."""

    task_input = {
        "baseline_schema": json.loads(baseline_schema_json),
        "actual_schema": json.loads(table_schemas_json),
    }
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Platform Health evaluator. Score schema consistency (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: 100% schemas consistent.\n"
        "- 4: Minor mismatches <5%.\n"
        "- 3: Some inconsistencies 5–15%.\n"
        "- 2: Frequent schema drift 15–30%.\n"
        "- 1: Severe inconsistency >30%.\n\n"
        "The final score must have 1 digit after decimal\n\n"
        "EXAMPLE INPUT:\n"
        '{"baseline_schema":{"users":["id","email","created_at"]},"actual_schema":{"users":["id","email"]}}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"schema.consistency","score":3,"rationale":"Missing \'created_at\' in users; ~33% of required fields absent for this table."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"schema.consistency","score":<1-5>,"rationale":"..."}\n'
        "Please respond ONLY with the JSON object, no Markdown or code fences."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # lightweight + accurate model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,  # deterministic output
    )

    try:
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        print("DEBUG RAW:", response)
        raise e


def main():
    # Load config
    with open("config/data_platform_analyzer.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tasks = [
        {
            "name": "Schema Consistency",
            "input": config["BASELINE_PATH"],
            "input2": config["TABLES_PATH"],  # special case with 2 inputs
            "output": config["OUTPUT_PATH"],
            "func": lambda: check_schema_consistency(
                _load_json(config["BASELINE_PATH"]),
                _load_json(config["TABLES_PATH"])
            )
        }
    ]

    # Run each task
    for task in tasks:
        try:
            result = task["func"]()
            with open(task["output"], "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"{task['name']} evaluation complete. Results stored in {task['output']}")
        except Exception as e:
            print(f"Error in {task['name']}: {repr(e)}")

if __name__ == "__main__":
    main()