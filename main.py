import json
import yaml
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.data_pipeline_agent import DataManagementMetrics, AnalyticsReadinessMetrics


def run_task(task):
    """Worker function to run each task safely and return status message."""
    try:
        result = task["func"]()
        with open(task["output"], "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return f"{task['name']} evaluation complete → {task['output']}"
    except Exception as e:
        return f"Error in {task['name']}: {repr(e)}"


def main():
    # Load config file (combined config should have all paths)
    with open("config/data_platform_analyzer.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Ensure output directories exist
    for key, path in config.items():
        if "OUTPUT" in key:
            os.makedirs(os.path.dirname(path), exist_ok=True)

    # Instantiate both metrics evaluators
    data_metrics = DataManagementMetrics()
    analytics_metrics = AnalyticsReadinessMetrics()

    # === Data Management Metrics (10) ===
    tasks = [
        {
            "name": "Schema Consistency",
            "output": config["OUTPUT_PATH"],
            "func": lambda: data_metrics.check_schema_consistency(
                data_metrics._load_json(config["BASELINE_PATH"]),
                data_metrics._load_json(config["TABLES_PATH"])
            ),
        },
        {
            "name": "Data Freshness",
            "output": config["FRESHNESS_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_data_freshness(
                data_metrics._load_json(config["FRESHNESS_INPUT_PATH"])
            ),
        },
        {
            "name": "Data Quality",
            "output": config["QUALITY_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_data_quality(
                data_metrics._load_json(config["QUALITY_INPUT_PATH"])
            ),
        },
        {
            "name": "Governance Compliance",
            "output": config["GOVERNANCE_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_governance_compliance(
                data_metrics._load_json(config["GOVERNANCE_INPUT_PATH"])
            ),
        },
        {
            "name": "Data Lineage",
            "output": config["LINEAGE_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_data_lineage(
                data_metrics._load_json(config["LINEAGE_INPUT_PATH"])
            ),
        },
        {
            "name": "Metadata Coverage",
            "output": config["METADATA_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_metadata_coverage(
                data_metrics._load_json(config["METADATA_INPUT_PATH"])
            ),
        },
        {
            "name": "Sensitive Tagging",
            "output": config["TAGGING_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_sensitive_tagging(
                data_metrics._load_json(config["TAGGING_INPUT_PATH"])
            ),
        },
        {
            "name": "Duplication",
            "output": config["DUPLICATION_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_duplication(
                data_metrics._load_json(config["DUPLICATION_INPUT_PATH"])
            ),
        },
        {
            "name": "Backup & Recovery",
            "output": config["BACKUP_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_backup_recovery(
                data_metrics._load_json(config["BACKUP_INPUT_PATH"])
            ),
        },
        {
            "name": "Security Config",
            "output": config["SECURITY_OUTPUT_PATH"],
            "func": lambda: data_metrics.evaluate_security_config(
                data_metrics._load_json(config["SECURITY_INPUT_PATH"])
            ),
        },
    ]

    # === Analytics Readiness Metrics (5) ===
    tasks.extend([
        {
            "name": "Pipeline Success Rate",
            "output": config["PIPELINE_SUCCESS_OUTPUT_PATH"],
            "func": lambda: analytics_metrics.compute_pipeline_success_rate(
                analytics_metrics._load_json(config["PIPELINE_SUCCESS_INPUT_PATH"])
            ),
        },
        {
            "name": "Pipeline Latency & Throughput",
            "output": config["PIPELINE_LATENCY_OUTPUT_PATH"],
            "func": lambda: analytics_metrics.compute_pipeline_latency_throughput(
                analytics_metrics._load_json(config["PIPELINE_LATENCY_INPUT_PATH"])
            ),
        },
        {
            "name": "Resource Utilization Efficiency",
            "output": config["RESOURCE_UTIL_OUTPUT_PATH"],
            "func": lambda: analytics_metrics.evaluate_resource_utilization(
                analytics_metrics._load_json(config["RESOURCE_UTIL_INPUT_PATH"])
            ),
        },
        {
            "name": "User Query Performance",
            "output": config["QUERY_PERFORMANCE_OUTPUT_PATH"],
            "func": lambda: analytics_metrics.assess_query_performance(
                analytics_metrics._load_json(config["QUERY_PERFORMANCE_INPUT_PATH"])
            ),
        },
        {
            "name": "Analytics Adoption",
            "output": config["ANALYTICS_ADOPTION_OUTPUT_PATH"],
            "func": lambda: analytics_metrics.compute_analytics_adoption(
                analytics_metrics._load_json(config["ANALYTICS_ADOPTION_INPUT_PATH"])
            ),
        },
    ])

    # Run all 15 tasks in parallel
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(run_task, task): task for task in tasks}
        for future in as_completed(futures):
            print(future.result())


if __name__ == "__main__":
    main()
