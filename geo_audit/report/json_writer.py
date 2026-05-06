"""JSON report writer — canonical, schema-stable."""
from __future__ import annotations

import json
from pathlib import Path

from geo_audit.orchestrator import AuditReport


def write_json(report: AuditReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def to_json_string(report: AuditReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
