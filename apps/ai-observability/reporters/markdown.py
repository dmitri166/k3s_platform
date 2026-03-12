"""Markdown reporter for generating RCA reports."""

from typing import Any, Dict
from pathlib import Path
import json
from datetime import datetime, timezone

def generate_markdown_report(analysis_text: str, metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any], anomalies: Dict[str, Any], config) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = f"""# K3s AI Observability RCA Report
**Date:** {date_str}  
**Model:** {config.GROQ_MODEL}  
**Lookback:** {config.LOOKBACK_HOURS}h  

---

"""
    return header + analysis_text

def save_report(report_content: str, raw_data: Dict[str, Any], config) -> Path:
    report_dir = Path(config.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = report_dir / f"rca-{date_str}.md"
    json_path = report_dir / f"rca-{date_str}.json"
    md_path.write_text(report_content, encoding="utf-8")
    json_path.write_text(json.dumps(raw_data, indent=2, default=str), encoding="utf-8")
    config.log.info("RCA Markdown report saved → %s", md_path)
    config.log.info("Raw JSON saved → %s", json_path)
    return md_path