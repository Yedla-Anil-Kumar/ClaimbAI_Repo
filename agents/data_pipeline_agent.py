import os
import json
import yaml
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

KEY = os.getenv("OPENAI_API_KEY")
if not KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

# Initialize OpenAI client
client = OpenAI(api_key=KEY)


def _load_json(path: str) -> str:
    """Helper: read JSON file and return raw JSON string."""
    with open(path, "r", encoding="utf-8") as f:
        return json.dumps(json.load(f), ensure_ascii=False)


def _ask_openai(prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Helper: call OpenAI chat model and return parsed JSON response."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a structured evaluator. Always return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print("DEBUG RAW:", raw)
        raise e


# === Evaluators ===

def check_schema_consistency(baseline_schema_json: str, table_schemas_json: str) -> Dict[str, Any]:
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
        '{"metric_id":"schema.consistency","score":3,"rationale":"Missing \'created_at\' in users; ~33% fields absent."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"schema.consistency","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_data_freshness(table_metadata_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(table_metadata_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Pipeline freshness evaluator. Score data freshness (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: All data <1h delay.\n"
        "- 4: Mostly <4h delay small breaches.\n"
        "- 3: 4–12h common.\n"
        "- 2: >12h frequent.\n"
        "- 1: >24h stale.\n\n"
        "EXAMPLE INPUT:\n"
        '{"table":"sales","expected_frequency":"hourly","last_updated":"5h ago"}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.freshness","score":3,"rationale":"Sales updated 5h ago vs hourly SLA."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"data.freshness","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_data_quality(data_quality_report_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(data_quality_report_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Quality evaluator. Combine null%, duplicate%, outlier% into a score.\n"
        "RUBRIC:\n"
        "- 5: <1% issues.\n"
        "- 4: 1–5%\n"
        "- 3: 6–15%\n"
        "- 2: 16–30%\n"
        "- 1: >30%\n\n"
        "EXAMPLE INPUT:\n"
        '{"null_pct":0.07,"duplicate_pct":0.05}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.quality","score":3,"rationale":"~12% issues (7% null, 5% duplicate)."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"data.quality","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_governance_compliance(access_logs_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(access_logs_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Governance evaluator. Score violations vs compliance.\n"
        "RUBRIC:\n"
        "- 5: 0 violations.\n"
        "- 4: <5%.\n"
        "- 3: 5–15%.\n"
        "- 2: 16–30%.\n"
        "- 1: >30%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"valid_access":95,"violations":5}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"governance.compliance","score":4,"rationale":"~5% violations."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"governance.compliance","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_data_lineage(lineage_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(lineage_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Lineage evaluator. Score completeness.\n"
        "RUBRIC:\n"
        "- 5: ≥95%\n"
        "- 4: 85–94%\n"
        "- 3: 70–84%\n"
        "- 2: 50–69%\n"
        "- 1: <50%\n\n"
        "EXAMPLE INPUT:\n"
        '{"tables_total":100,"tables_with_lineage":85}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.lineage","score":3,"rationale":"Lineage only for 85%"}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"data.lineage","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_metadata_coverage(metadata_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(metadata_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Metadata evaluator. Score metadata documentation.\n"
        "RUBRIC:\n"
        "- 5: ≥95%\n"
        "- 4: 85–94%\n"
        "- 3: 70–84%\n"
        "- 2: 50–69%\n"
        "- 1: <50%\n\n"
        "EXAMPLE INPUT:\n"
        '{"catalog_entries":[{"table":"orders","description":"Customer orders","owner":"data-team"},'
        '{"table":"customers","description":"","owner":"data-team"}],"required_fields":["description","owner"]}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"metadata.coverage","score":3,"rationale":"~50% fully documented."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"metadata.coverage","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_sensitive_tagging(tagging_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(tagging_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Privacy evaluator. Score sensitive field tagging completeness.\n"
        "RUBRIC:\n"
        "- 5: 100% tagged\n"
        "- 4: 90–99%\n"
        "- 3: 75–89%\n"
        "- 2: 50–74%\n"
        "- 1: <50%\n\n"
        "EXAMPLE INPUT:\n"
        '{"sensitive_fields":50,"tagged_fields":40}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"sensitive.tagging","score":3,"rationale":"~80% tagged, gaps remain."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"sensitive.tagging","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_duplication(duplication_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(duplication_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Data Redundancy evaluator. Score based on duplicated groups.\n"
        "RUBRIC:\n"
        "- 5: 0%\n"
        "- 4: <5%\n"
        "- 3: 5–15%\n"
        "- 2: 16–30%\n"
        "- 1: >30%\n\n"
        "EXAMPLE INPUT:\n"
        '{"datasets_total":100,"duplicate_groups":10}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"duplication","score":3,"rationale":"~10% redundancy."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"duplication","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_backup_recovery(backup_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(backup_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Backup & Recovery evaluator. Score based on success, RPO/RTO.\n"
        "RUBRIC:\n"
        "- 5: ≥99% success, RPO ≤1h, RTO ≤1h\n"
        "- 4: ≥95% success, RPO ≤4h, RTO ≤4h\n"
        "- 3: ≥85% success, RPO ≤12h, RTO ≤8h\n"
        "- 2: <85% or RPO/RTO breached up to 24h\n"
        "- 1: Severe >24h or frequent failures\n\n"
        "EXAMPLE INPUT:\n"
        '{"backup_success_rate":0.9,"avg_rpo_hours":6,"avg_rto_hours":5}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"backup.recovery","score":3,"rationale":"90% success, RPO 6h, RTO 5h beyond strict SLA."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"backup.recovery","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


def evaluate_security_config(security_json: str) -> Dict[str, Any]:
    task_input_json = json.dumps(json.loads(security_json), ensure_ascii=False)
    prompt = (
        "SYSTEM:\n"
        "You are a Security evaluator. Score IAM, ACL, encryption misconfigs.\n"
        "RUBRIC:\n"
        "- 5: 0% misconfig\n"
        "- 4: 1–5%\n"
        "- 3: 6–15%\n"
        "- 2: 16–30%\n"
        "- 1: >30%\n\n"
        "EXAMPLE INPUT:\n"
        '{"checks_total":100,"failures":10}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"security.config","score":3,"rationale":"~10% misconfigs (IAM)."}\n\n'
        "TASK INPUT:\n" + task_input_json +
        "\n\nRESPONSE FORMAT:\n"
        '{"metric_id":"security.config","score":<1-5>,"rationale":"..."}'
    )
    return _ask_openai(prompt)


# === MAIN DRIVER ===

def main():
    # Load config file
    with open("config/data_platform_analyzer.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tasks = [
        {
            "name": "Schema Consistency",
            "output": config["OUTPUT_PATH"],
            "func": lambda: check_schema_consistency(
                _load_json(config["BASELINE_PATH"]),
                _load_json(config["TABLES_PATH"])
            )
        },
        {
            "name": "Data Freshness",
            "output": config["FRESHNESS_OUTPUT_PATH"],
            "func": lambda: evaluate_data_freshness(_load_json(config["FRESHNESS_INPUT_PATH"]))
        },
        {
            "name": "Data Quality",
            "output": config["QUALITY_OUTPUT_PATH"],
            "func": lambda: evaluate_data_quality(_load_json(config["QUALITY_INPUT_PATH"]))
        },
        {
            "name": "Governance Compliance",
            "output": config["GOVERNANCE_OUTPUT_PATH"],
            "func": lambda: evaluate_governance_compliance(_load_json(config["GOVERNANCE_INPUT_PATH"]))
        },
        {
            "name": "Data Lineage",
            "output": config["LINEAGE_OUTPUT_PATH"],
            "func": lambda: evaluate_data_lineage(_load_json(config["LINEAGE_INPUT_PATH"]))
        },
        {
            "name": "Metadata Coverage",
            "output": config["METADATA_OUTPUT_PATH"],
            "func": lambda: evaluate_metadata_coverage(_load_json(config["METADATA_INPUT_PATH"]))
        },
        {
            "name": "Sensitive Tagging",
            "output": config["TAGGING_OUTPUT_PATH"],
            "func": lambda: evaluate_sensitive_tagging(_load_json(config["TAGGING_INPUT_PATH"]))
        },
        {
            "name": "Duplication",
            "output": config["DUPLICATION_OUTPUT_PATH"],
            "func": lambda: evaluate_duplication(_load_json(config["DUPLICATION_INPUT_PATH"]))
        },
        {
            "name": "Backup & Recovery",
            "output": config["BACKUP_OUTPUT_PATH"],
            "func": lambda: evaluate_backup_recovery(_load_json(config["BACKUP_INPUT_PATH"]))
        },
        {
            "name": "Security Config",
            "output": config["SECURITY_OUTPUT_PATH"],
            "func": lambda: evaluate_security_config(_load_json(config["SECURITY_INPUT_PATH"]))
        },
    ]

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
