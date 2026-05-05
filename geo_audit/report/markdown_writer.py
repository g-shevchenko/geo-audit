"""Markdown report writers: report.md (full) + actions.md (P0–P3 only)."""
from __future__ import annotations

from pathlib import Path

from geo_audit.orchestrator import AuditReport
from geo_audit.modules.base import Finding


def _priority_emoji(p: str) -> str:
    return {"P0": "🚨", "P1": "🔴", "P2": "🟡", "P3": "🟢"}.get(p, "•")


def _render_finding(f: dict | Finding) -> str:
    if isinstance(f, dict):
        priority = f.get("priority", "P3")
        title = f.get("title", "")
        evidence = f.get("evidence", "")
        fix_url = f.get("fix_url", "")
    else:
        priority = f.priority
        title = f.title
        evidence = f.evidence
        fix_url = f.fix_url
    line = f"- {_priority_emoji(priority)} **{priority}** {title}"
    if evidence:
        line += f"\n  - _{evidence}_"
    if fix_url:
        line += f"\n  - [docs]({fix_url})"
    return line


def write_actions_md(report: AuditReport, path: Path) -> None:
    """Action plan grouped by priority. Concise, client-shareable."""
    by_pri: dict[str, list] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for m in report.modules:
        for a in m.actions:
            row = a.to_dict() if hasattr(a, "to_dict") else a
            row["_module"] = m.name
            by_pri.setdefault(row.get("priority", "P3"), []).append(row)

    lines: list[str] = []
    lines.append(f"# GEO Audit — Action Plan")
    lines.append(f"")
    lines.append(f"**URL:** {report.url}")
    lines.append(f"**Composite Score:** {report.composite.score}/100")
    lines.append(f"**Started:** {report.started_at}")
    lines.append(f"**geo-audit version:** {report.geo_audit_version} (methodology v{report.methodology_version})")
    lines.append(f"")

    if report.composite.modules_skipped:
        lines.append(f"> ⚠️  Modules skipped (missing keys / failed): "
                     f"{', '.join(report.composite.modules_skipped)}")
        lines.append(f"")

    for pri in ["P0", "P1", "P2", "P3"]:
        items = by_pri.get(pri, [])
        if not items:
            continue
        label = {
            "P0": "🚨 P0 — Critical (fix this week)",
            "P1": "🔴 P1 — High (fix this month)",
            "P2": "🟡 P2 — Medium (this quarter)",
            "P3": "🟢 P3 — Note / observation",
        }[pri]
        lines.append(f"## {label}")
        lines.append("")
        for it in items:
            lines.append(f"- **[{it['_module']}]** {it.get('title', '')}")
            if it.get("evidence"):
                lines.append(f"  - _{it['evidence']}_")
            if it.get("fix_url"):
                lines.append(f"  - [docs]({it['fix_url']})")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report_md(report: AuditReport, path: Path) -> None:
    """Full per-module report."""
    lines: list[str] = []
    lines.append(f"# GEO Audit Report — {report.url}")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Composite Score | **{report.composite.score}/100** |")
    lines.append(f"| Started | {report.started_at} |")
    lines.append(f"| Duration | {report.duration_ms}ms |")
    lines.append(f"| Methodology version | {report.methodology_version} |")
    lines.append(f"| Modules used | {', '.join(report.composite.modules_used) or '—'} |")
    lines.append(f"| Modules skipped | {', '.join(report.composite.modules_skipped) or '—'} |")
    lines.append("")

    for m in report.modules:
        weight = report.composite.weights_used.get(m.name)
        score_repr = f"{m.score}/100" if m.score is not None else "—"
        weight_repr = f" (weight {weight})" if weight else ""
        lines.append(f"## {m.name} — {score_repr}{weight_repr}")
        lines.append("")
        if m.ran_in_degraded_mode:
            lines.append(f"> _Degraded:_ {m.skip_reason or '—'}")
            if m.what_youd_get:
                lines.append(f">")
                lines.append(f"> {m.what_youd_get}")
            lines.append("")
        if m.findings:
            lines.append("### Findings")
            lines.append("")
            for f in m.findings:
                lines.append(_render_finding(f))
            lines.append("")
        if m.actions:
            lines.append("### Actions")
            lines.append("")
            for a in m.actions:
                lines.append(_render_finding(a))
            lines.append("")
        lines.append(f"_Took {m.duration_ms}ms._")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
