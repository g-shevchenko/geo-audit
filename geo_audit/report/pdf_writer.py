"""PDF report writer (optional, requires `pip install geo-audit[pdf]`).

Uses WeasyPrint to render the markdown report to PDF. Imports are
lazy so the module is only required when --output ends in .pdf.
"""
from __future__ import annotations

from pathlib import Path


def write_pdf(report, path: Path) -> None:
    """Render report to PDF. Requires weasyprint + markdown."""
    try:
        import markdown  # type: ignore
        from weasyprint import HTML, CSS  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "PDF output requires extras: pip install 'geo-audit[pdf]' "
            f"(missing: {e.name})"
        ) from e

    from geo_audit.report.markdown_writer import write_report_md
    md_path = path.with_suffix(".md")
    write_report_md(report, md_path)
    md_text = md_path.read_text(encoding="utf-8")
    md_path.unlink(missing_ok=True)

    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    css = """
    @page { size: A4; margin: 1.8cm 2cm; }
    body { font-family: -apple-system, 'Helvetica Neue', sans-serif; font-size: 10.5pt; line-height: 1.5; color: #222; }
    h1 { font-size: 22pt; border-bottom: 2px solid #222; padding-bottom: 0.3em; }
    h2 { font-size: 14pt; margin-top: 1.6em; color: #1a1a1a; }
    h3 { font-size: 11pt; color: #555; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 10pt; }
    th { background: #f5f5f5; font-weight: 600; }
    code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
    blockquote { border-left: 3px solid #ddd; margin: 0.6em 0; padding: 0.4em 0.8em; color: #555; }
    """
    html_doc = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_doc).write_pdf(str(path), stylesheets=[CSS(string=css)])
