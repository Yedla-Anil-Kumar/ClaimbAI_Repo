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


def check_schema_consistency( baseline_schema_json: str, table_schemas_json: str) -> Dict[str, Any]:
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
        "The final score must have 1 digit after decimal"
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

def evaluate_data_freshness(table_metadata_json: str) -> Dict[str, Any]:
    """Check last-updated timestamps against expected refresh frequency using LLM and return structured JSON evaluation."""

    task_input = json.loads(table_metadata_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Pipeline freshness evaluator. Score data freshness (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: All data <1h delay (meets 100% SLAs).\n"
        "- 4: Mostly fresh (<4h) with minor breaches.\n"
        "- 3: Delays 4–12h common.\n"
        "- 2: Delays >12h frequent.\n"
        "- 1: Data stale >24h.\n\n"
        "EXAMPLE INPUT:\n"
        '{"table":"sales","expected_frequency":"hourly","last_updated":"5h ago"}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.freshness","score":3,"rationale":"Sales updated 5h ago vs hourly SLA; moderate lateness."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"data.freshness","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_data_quality(data_quality_report_json: str) -> Dict[str, Any]:
    """Evaluate data quality by combining null%, duplicate%, outlier% into a score."""

    task_input = json.loads(data_quality_report_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Quality evaluator. Score overall data quality (1–5).\n\n"
        "RUBRIC (combine issue rates):\n"
        "- 5: <1% total issues.\n"
        "- 4: 1–5%.\n"
        "- 3: 6–15%.\n"
        "- 2: 16–30%.\n"
        "- 1: >30%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"null_pct":0.07,"duplicate_pct":0.05}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.quality","score":3,"rationale":"Nulls ~7% and duplicates ~5% → ~12% issues; noticeable but manageable."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"data.quality","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_governance_compliance(access_logs_json: str) -> Dict[str, Any]:
    """Assess governance compliance by analyzing access logs for violations."""

    task_input = json.loads(access_logs_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Governance evaluator. Score compliance posture (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: 100% compliant (0 violations).\n"
        "- 4: Minor violations <5%.\n"
        "- 3: 5–15% violations.\n"
        "- 2: 16–30%.\n"
        "- 1: >30%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"valid_access":95,"violations":5}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"governance.compliance","score":4,"rationale":"~5% violations; mostly compliant with occasional gaps."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"governance.compliance","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_data_lineage(lineage_json: str) -> Dict[str, Any]:
    """Evaluate data lineage coverage and identify gaps."""

    task_input = json.loads(lineage_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Lineage evaluator. Score lineage completeness (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: ≥95% have lineage.\n"
        "- 4: 85–94%.\n"
        "- 3: 70–84%.\n"
        "- 2: 50–69%.\n"
        "- 1: <50%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"tables_total":100,"tables_with_lineage":85}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"data.lineage","score":3,"rationale":"Lineage exists for 85%, at lower bound of good; gaps remain in 15%."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"data.lineage","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_metadata_coverage(metadata_json: str) -> Dict[str, Any]:
    """Evaluate metadata documentation completeness across catalog entries."""

    task_input = json.loads(metadata_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Metadata evaluator. Score metadata coverage (1–5).\n\n"
        "RUBRIC (percent of datasets with all required fields, calculate it properly):\n"
        "- 5: ≥95%\n"
        "- 4: 85–94%\n"
        "- 3: 70–84%\n"
        "- 2: 50–69%\n"
        "- 1: <50%\n\n"
        "EXAMPLE INPUT:\n"
        '{"catalog_entries":[{"table":"orders","description":"Customer orders","owner":"data-team"},'
        '{"table":"customers","description":"","owner":"data-team"}],"required_fields":["description","owner"]}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"metadata.coverage","score":3,"rationale":"~50% fully documented; missing descriptions pull score down."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"metadata.coverage","score":<1-5>,"rationale":"..."}\n'
        "Calculate the percentage properly by dividing the number of required field present across all entries divided by (total value by number of entries * no of required fieds)"
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

def evaluate_sensitive_tagging(tagging_json: str) -> Dict[str, Any]:
    """Validate PII/PHI sensitive data tagging coverage."""

    task_input = json.loads(tagging_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Privacy evaluator. Score sensitive data tagging (1–5).\n\n"
        "RUBRIC (tagging completeness across sensitive fields):\n"
        "- 5: 100% tagged.\n"
        "- 4: 90–99%.\n"
        "- 3: 75–89%.\n"
        "- 2: 50–74%.\n"
        "- 1: <50%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"sensitive_fields":50,"tagged_fields":40}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"sensitive.tagging","score":3,"rationale":"~80% sensitive fields tagged; critical gaps remain."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"sensitive.tagging","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_duplication(duplication_json: str) -> Dict[str, Any]:
    """Detect redundant datasets by identical hashes and score duplication risk."""

    task_input = json.loads(duplication_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Redundancy evaluator. Score duplication (1–5).\n\n"
        "RUBRIC (share of duplicated datasets):\n"
        "- 5: 0% duplicates.\n"
        "- 4: <5%.\n"
        "- 3: 5–15%.\n"
        "- 2: 16–30%.\n"
        "- 1: >30%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"datasets_total":100,"duplicate_groups":10}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"duplication","score":3,"rationale":"~10% redundancy from duplicate groups; increases cost and confusion."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"duplication","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_backup_recovery(backup_json: str) -> Dict[str, Any]:
    """Assesses backup success and restore readiness against RPO/RTO targets."""

    task_input = json.loads(backup_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Resilience evaluator. Score backup & recovery (1–5).\n\n"
        "RUBRIC:\n"
        "- 5: ≥99% success; RPO≤1h; RTO≤1h.\n"
        "- 4: ≥95% success; RPO≤4h; RTO≤4h.\n"
        "- 3: ≥85% success; RPO≤12h; RTO≤8h.\n"
        "- 2: <85% or RPO 12–24h or RTO 8–24h.\n"
        "- 1: Severe gaps; RPO>24h or frequent failures.\n\n"
        "EXAMPLE INPUT:\n"
        '{"backup_success_rate":0.9,"avg_rpo_hours":6,"avg_rto_hours":5}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"backup.recovery","score":3,"rationale":"90% success but RPO~6h and RTO~5h exceed strict targets."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"backup.recovery","score":<1-5>,"rationale":"..."}\n'
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

def evaluate_security_config(security_json: str) -> Dict[str, Any]:
    """Validates encryption, IAM/RBAC, public access, and control checks against compliance rules."""

    task_input = json.loads(security_json)
    task_input_json = json.dumps(task_input, ensure_ascii=False)

    prompt = (
        "SYSTEM:\n"
        "You are a Data Security evaluator. Score security configurations (1–5).\n\n"
        "RUBRIC (failed checks share):\n"
        "- 5: 0% failed checks.\n"
        "- 4: 1–5%.\n"
        "- 3: 6–15%.\n"
        "- 2: 16–30%.\n"
        "- 1: >30%.\n\n"
        "EXAMPLE INPUT:\n"
        '{"checks_total":100,"failures":10}\n\n'
        "EXAMPLE OUTPUT:\n"
        '{"metric_id":"security.config","score":3,"rationale":"~10% IAM/ACL misconfigurations; encryption OK, no public access."}\n\n'
        "TASK INPUT:\n"
        + task_input_json
        + "\n\nRESPONSE FORMAT (JSON only):\n"
        '{"metric_id":"security.config","score":<1-5>,"rationale":"..."}\n'
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


import yaml
import json

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
        },
        {
            "name": "Data Freshness",
            "input": config["FRESHNESS_INPUT_PATH"],
            "output": config["FRESHNESS_OUTPUT_PATH"],
            "func": lambda: evaluate_data_freshness(_load_json(config["FRESHNESS_INPUT_PATH"]))
        },
        {
            "name": "Data Quality",
            "input": config["QUALITY_INPUT_PATH"],
            "output": config["QUALITY_OUTPUT_PATH"],
            "func": lambda: evaluate_data_quality(_load_json(config["QUALITY_INPUT_PATH"]))
        },
        {
            "name": "Governance Compliance",
            "input": config["GOVERNANCE_INPUT_PATH"],
            "output": config["GOVERNANCE_OUTPUT_PATH"],
            "func": lambda: evaluate_governance_compliance(_load_json(config["GOVERNANCE_INPUT_PATH"]))
        },
        {
            "name": "Data Lineage",
            "input": config["LINEAGE_INPUT_PATH"],
            "output": config["LINEAGE_OUTPUT_PATH"],
            "func": lambda: evaluate_data_lineage(_load_json(config["LINEAGE_INPUT_PATH"]))
        },
        {
            "name": "Metadata Coverage",
            "input": config["METADATA_INPUT_PATH"],
            "output": config["METADATA_OUTPUT_PATH"],
            "func": lambda: evaluate_metadata_coverage(_load_json(config["METADATA_INPUT_PATH"]))
        },
        {
            "name": "Sensitive Tagging",
            "input": config["TAGGING_INPUT_PATH"],
            "output": config["TAGGING_OUTPUT_PATH"],
            "func": lambda: evaluate_sensitive_tagging(_load_json(config["TAGGING_INPUT_PATH"]))
        },
        {
            "name": "Duplication",
            "input": config["DUPLICATION_INPUT_PATH"],
            "output": config["DUPLICATION_OUTPUT_PATH"],
            "func": lambda: evaluate_duplication(_load_json(config["DUPLICATION_INPUT_PATH"]))
        },
        {
            "name": "Backup & Recovery",
            "input": config["BACKUP_INPUT_PATH"],
            "output": config["BACKUP_OUTPUT_PATH"],
            "func": lambda: evaluate_backup_recovery(_load_json(config["BACKUP_INPUT_PATH"]))
        },
        {
            "name": "Security Config",
            "input": config["SECURITY_INPUT_PATH"],
            "output": config["SECURITY_OUTPUT_PATH"],
            "func": lambda: evaluate_security_config(_load_json(config["SECURITY_INPUT_PATH"]))
        },
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
