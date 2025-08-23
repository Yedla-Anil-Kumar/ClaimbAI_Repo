# import os
# import json
# from typing import Dict, Any
# from google import genai
# from dotenv import load_dotenv

# load_dotenv()

# KEY = os.getenv("GOOGLE_API_KEY")
# if not KEY:
#     raise ValueError("Missing GOOGLE_API_KEY in .env file")


# client = genai.Client(api_key=KEY)

# def check_schema_consistency(
#     table_schemas: Dict[str, list], baseline_schema: Dict[str, list]) -> Dict[str, Any]:

#     task_input = {
#         "baseline_schema": baseline_schema,
#         "actual_schema": table_schemas
#     }
#     task_input_json = json.dumps(task_input, ensure_ascii=False)

#     prompt = (
#         "SYSTEM:\n"
#         "You are a Data Platform Health evaluator. Score schema consistency (1–5).\n\n"
#         "RUBRIC:\n"
#         "- 5: 100% schemas consistent.\n"
#         "- 4: Minor mismatches <5%.\n"
#         "- 3: Some inconsistencies 5–15%.\n"
#         "- 2: Frequent schema drift 15–30%.\n"
#         "- 1: Severe inconsistency >30%.\n\n"
#         "EXAMPLE INPUT:\n"
#         '{"baseline_schema":{"users":["id","email","created_at"]},"actual_schema":{"users":["id","email"]}}\n\n'
#         "EXAMPLE OUTPUT:\n"
#         '{"metric_id":"schema.consistency","score":3,"rationale":"Missing \'created_at\' in users; ~33% of required fields absent for this table."}\n\n'
#         "TASK INPUT:\n"
#         + task_input_json
#         + "\n\nRESPONSE FORMAT (JSON only):\n"
#         '{"metric_id":"schema.consistency","score":<1-5>,"rationale":"..."}\n'
#        'Please respond ONLY with the JSON object, no Markdown or code fences.'
#     )

#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt,
#     )
#     try:
#         raw = response.candidates[0].content.parts[0].text
#         return json.loads(raw)
#     except Exception as e:
#         print("DEBUG RAW:", response)
#         raise e


# def main():
#     baseline_schema = {
#         "users": ["id","name", "email", "created_at"],
#         "orders": ["id", "user_id", "amount", "created_at"]
#     }

#     table_schemas = {
#         "users": ["id", "email"], 
#         "orders": ["id", "user_id", "amount", "created_at"]
#     }

#     try:
#         result = check_schema_consistency(table_schemas, baseline_schema)
#         print("Model response:")
#         print(json.dumps(result, indent=2, ensure_ascii=False))
#     except Exception as e:
#         print("Error calling check_schema_consistency():", repr(e))


# if __name__ == "__main__":
#     main()


import os
import json
import yaml
from typing import Dict, Any
from google import genai
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("GOOGLE_API_KEY")
if not KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

client = genai.Client(api_key=KEY)


def _load_json(path: str) -> str:
    """Helper: read JSON file and return raw JSON string."""
    with open(path, "r", encoding="utf-8") as f:
        return json.dumps(json.load(f), ensure_ascii=False)


def check_schema_consistency(
    baseline_schema_json: str, table_schemas_json: str
) -> Dict[str, Any]:
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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    try:
        raw = response.candidates[0].content.parts[0].text
        return json.loads(raw)
    except Exception as e:
        print("DEBUG RAW:", response)
        raise e


def main():
    # Load config
    with open("config/data_platform_analyzer.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    baseline_path = config["BASELINE_PATH"]
    tables_path = config["TABLES_PATH"]
    output_path = config["OUTPUT_PATH"]

    # Read baseline and actual schema JSONs
    baseline_schema_json = _load_json(baseline_path)
    table_schemas_json = _load_json(tables_path)

    # Run evaluation
    try:
        result = check_schema_consistency(baseline_schema_json, table_schemas_json)

        # Write output.json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Schema consistency check complete. Results stored in {output_path}")

    except Exception as e:
        print("❌ Error:", repr(e))


if __name__ == "__main__":
    main()
