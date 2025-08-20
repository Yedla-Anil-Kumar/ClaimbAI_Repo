# from __future__ import annotations
# import os, json, yaml
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Any, Dict, List, Optional

# _DEFAULT_CFG_DIR = Path(__file__).resolve().parent / "config"

# def _load_yaml(path: Path) -> Dict[str, Any]:
#     if not path.exists():
#         return {}
#     with path.open("r", encoding="utf-8") as f:
#         return yaml.safe_load(f) or {}

# def _cfg_dir() -> Path:
#     # allow overrides via env var; else use packaged defaults
#     env = os.getenv("MLOPS_CONFIG_DIR")
#     return Path(env).resolve() if env else _DEFAULT_CFG_DIR

# def load_patterns_config() -> Dict[str, Any]:
#     return _load_yaml(_cfg_dir() / "patterns.yaml")

# def load_metrics_config() -> Dict[str, Any]:
#     return _load_yaml(_cfg_dir() / "metrics.yaml")

# # ---- tiny validators (fail-soft) ----
# def expect_keys(d: Dict[str, Any], keys: List[str], ctx: str) -> None:
#     miss = [k for k in keys if k not in d]
#     if miss:
#         print(f"[mlops-config] {ctx}: missing keys {miss}")

# def get_metric_spec(metrics_cfg: Dict[str, Any], metric_id: str) -> Optional[Dict[str, Any]]:
#     specs = metrics_cfg.get("metric_specs", [])
#     for s in specs:
#         if s.get("metric_id") == metric_id:
#             expect_keys(s, ["metric_id","stem","group","rubric","return_shape_hint"], f"metric_spec:{metric_id}")
#             return s
#     print(f"[mlops-config] metric_spec not found: {metric_id}")
#     return None
