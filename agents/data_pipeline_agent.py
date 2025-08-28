import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI


class DataManagementMetrics:
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.key:
            raise ValueError("Missing OPENAI_API_KEY in .env file")

        self.client = OpenAI(api_key=self.key)


    def _load_json(self, path: str) -> str:
        """Helper: read JSON file and return raw JSON string."""
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False)

    def _ask_openai(self, prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
        """Helper: call OpenAI chat model and return parsed JSON response."""
        response = self.client.chat.completions.create(
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

    def check_schema_consistency(self, baseline_schema_json: str, table_schemas_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"schema.consistency","score":3,"rationale":"Missing \'created_at\' in users; ~33% fields absent.","gap":"Implement automated schema validation, add missing fields to actual schema, establish schema versioning process"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT (JSON only):\n"
            "Rationale should be detailed as it will be fed in another LLM"
            "gap should also be meaningful and understandable"
            '{"metric_id":"schema.consistency","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_data_freshness(self, table_metadata_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"data.freshness","score":3,"rationale":"Sales updated 5h ago vs hourly SLA.","gap":"Optimize ETL pipeline scheduling, implement real-time streaming, add data freshness monitoring alerts"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"data.freshness","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_data_quality(self, data_quality_report_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"data.quality","score":3,"rationale":"~12% issues (7% null, 5% duplicate).","gap":"Implement data validation rules, add duplicate detection algorithms, establish data cleansing workflows"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"data.quality","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_governance_compliance(self, access_logs_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"governance.compliance","score":4,"rationale":"~5% violations.","gap":"Strengthen access control policies, implement regular audit reviews, enhance user training on data governance"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"governance.compliance","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_data_lineage(self, lineage_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"data.lineage","score":3,"rationale":"Lineage only for 85%","gap":"Deploy automated lineage tracking tools, document missing table dependencies, implement column-level lineage mapping"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"data.lineage","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_metadata_coverage(self, metadata_json: str) -> Dict[str, Any]:
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
            '{"catalog_entries":[{"table":"orders","description":"Customer orders","owner":"data-team"},{"table":"customers","description":"","owner":"data-team"}],"required_fields":["description","owner"]}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"metadata.coverage","score":3,"rationale":"~50% fully documented.","gap":"Mandate metadata documentation standards, implement automated metadata validation, assign data stewards for incomplete entries"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"metadata.coverage","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_sensitive_tagging(self, tagging_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"sensitive.tagging","score":3,"rationale":"~80% tagged, gaps remain.","gap":"Implement automated PII detection tools, conduct comprehensive data classification audit, establish mandatory tagging workflows"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"sensitive.tagging","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_duplication(self, duplication_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"duplication","score":3,"rationale":"~10% redundancy.","gap":"Implement data deduplication algorithms, establish single source of truth principles, create data consolidation roadmap"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"duplication","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_backup_recovery(self, backup_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"backup.recovery","score":3,"rationale":"90% success, RPO 6h, RTO 5h beyond strict SLA.","gap":"Upgrade backup infrastructure, implement incremental backups, optimize recovery procedures, add backup monitoring alerts"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"backup.recovery","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

    def evaluate_security_config(self, security_json: str) -> Dict[str, Any]:
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
            '{"metric_id":"security.config","score":3,"rationale":"~10% misconfigs (IAM).","gap":"Implement security configuration scanning, remediate IAM policy violations, establish security baseline standards, add automated compliance checks"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"security.config","score":<1-5>,"rationale":"...","gap":"Specific actionable recommendations to improve score"}'
        )
        return self._ask_openai(prompt)

class AnalyticsReadinessMetrics:
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.key:
            raise ValueError("Missing OPENAI_API_KEY in .env file")
        self.client = OpenAI(api_key=self.key)

    # === Internal Helpers ===
    def _load_json(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False)

    def _ask_openai(self, prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an advanced Analytics Readiness evaluator. Always return valid JSON only."},
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

    def compute_pipeline_success_rate(self, pipeline_runs_json: str) -> Dict[str, Any]:
        task_input_json = json.dumps(json.loads(pipeline_runs_json), ensure_ascii=False)

        prompt = (
            "SYSTEM:\n"
            "You are an Analytics Readiness evaluator. Score pipeline success rate (1–5).\n\n"
            "RUBRIC:\n"
            "- 5: ≥99% jobs succeed\n"
            "- 4: 95–98%\n"
            "- 3: 85–94%\n"
            "- 2: 70–84%\n"
            "- 1: <70%\n\n"
            "EXAMPLE INPUT:\n"
            '{"pipeline_runs":[{"id":1,"status":"success"},{"id":2,"status":"failure"},{"id":3,"status":"success"}]}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"pipeline.success_rate","score":3,"rationale":"66% success (2/3). Below SLA.","gap":"Improve retry mechanisms, investigate job failures, add monitoring alerts"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"pipeline.success_rate","score":<1-5>,"rationale":"...","gap":"..."}'
        )
        return self._ask_openai(prompt)

    def compute_pipeline_latency_throughput(self, pipeline_metrics_json: str) -> Dict[str, Any]:
        task_input_json = json.dumps(json.loads(pipeline_metrics_json), ensure_ascii=False)

        prompt = (
            "SYSTEM:\n"
            "You are an Analytics Readiness evaluator. Score based on pipeline latency & throughput.\n\n"
            "RUBRIC:\n"
            "- 5: runtime<10m, throughput>1M rows/job, negligible wait\n"
            "- 4: runtime<30m, throughput>500k rows\n"
            "- 3: runtime<60m common, moderate throughput\n"
            "- 2: runtime<120m, low throughput\n"
            "- 1: >120m or serious delays\n\n"
            "EXAMPLE INPUT:\n"
            '{"avg_runtime_minutes":45,"rows_processed":600000,"queue_wait_minutes":10}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"pipeline.latency_throughput","score":3,"rationale":"45m avg runtime, 600k rows processed.","gap":"Parallelize ETL tasks, optimize queries, improve cluster resources"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"pipeline.latency_throughput","score":<1-5>,"rationale":"...","gap":"..."}'
        )
        return self._ask_openai(prompt)

    def evaluate_resource_utilization(self, resource_usage_json: str, cost_data_json: str) -> Dict[str, Any]:
        task_input = {
            "resource_usage": json.loads(resource_usage_json),
            "cost_data": json.loads(cost_data_json),
        }
        task_input_json = json.dumps(task_input, ensure_ascii=False)

        prompt = (
            "SYSTEM:\n"
            "You are an Analytics Readiness evaluator. Score Resource Utilization Efficiency considering CPU, memory, storage, and cost.\n\n"
            "RUBRIC:\n"
            "- 5: >75% utilization with optimized cost\n"
            "- 4: 60–74%\n"
            "- 3: 40–59%\n"
            "- 2: 20–39%\n"
            "- 1: <20% or overspending\n\n"
            "EXAMPLE INPUT:\n"
            '{"resource_usage":{"cpu":55,"memory":40,"storage":60},"cost_data":{"monthly_cost_usd":12000}}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"resource.utilization","score":3,"rationale":"~50% avg utilization at $12k monthly.","gap":"Right-size clusters, scale dynamically, implement FinOps cost reviews"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"resource.utilization","score":<1-5>,"rationale":"...","gap":"..."}'
        )
        return self._ask_openai(prompt)

    def assess_query_performance(self, query_logs_json: str) -> Dict[str, Any]:
        task_input_json = json.dumps(json.loads(query_logs_json), ensure_ascii=False)

        prompt = (
            "SYSTEM:\n"
            "You are an Analytics Readiness evaluator. Score user query performance (1–5).\n\n"
            "RUBRIC:\n"
            "- 5: Avg runtime <2s\n"
            "- 4: 2–5s\n"
            "- 3: 6–10s\n"
            "- 2: 11–30s\n"
            "- 1: >30s slow queries\n\n"
            "EXAMPLE INPUT:\n"
            '{"query_logs":[{"id":"q1","runtime":4,"user":"alice","success":true},{"id":"q2","runtime":8,"user":"bob","success":true}]}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"query.performance","score":3,"rationale":"Avg query runtime ~6s.","gap":"Add indexes, optimize joins, introduce caching"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"query.performance","score":<1-5>,"rationale":"...","gap":"..."}'
        )
        return self._ask_openai(prompt)

    def compute_analytics_adoption(self, user_activity_json: str) -> Dict[str, Any]:
        task_input_json = json.dumps(json.loads(user_activity_json), ensure_ascii=False)

        prompt = (
            "SYSTEM:\n"
            "You are an Analytics Readiness evaluator. Score analytics adoption (1–5).\n\n"
            "RUBRIC:\n"
            "- 5: >100 active users, >1000 views\n"
            "- 4: 50–100 users\n"
            "- 3: 25–49 users\n"
            "- 2: 10–24 users\n"
            "- 1: <10 users, low adoption\n\n"
            "EXAMPLE INPUT:\n"
            '{"active_users":35,"dashboard_views":500,"queries_executed":2000}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"metric_id":"analytics.adoption","score":3,"rationale":"Moderate adoption (35 active users, 500 views).","gap":"Improve BI training, promote dashboards, ensure tool accessibility"}\n\n'
            "TASK INPUT:\n" + task_input_json +
            "\n\nRESPONSE FORMAT:\n"
            '{"metric_id":"analytics.adoption","score":<1-5>,"rationale":"...","gap":"..."}'
        )
        return self._ask_openai(prompt)