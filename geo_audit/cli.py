"""geo-audit CLI.

Subcommands:
  audit URL          — run full GEO audit (default if URL is the first arg)
  doctor             — show key status + which modules will run
  version            — print version

Run ``geo-audit --help`` for full flag list.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from geo_audit import __version__, __methodology_version__
from geo_audit.config import KEY_ENV_VARS, KEY_HINTS, MODULE_KEY_MATRIX, CROSS_CUTTING_KEYS, load_config
from geo_audit.modules import registry
from geo_audit.orchestrator import run_audit
from geo_audit.report.json_writer import write_json
from geo_audit.report.markdown_writer import write_actions_md, write_report_md


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m" if sys.stdout.isatty() else s


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m" if sys.stdout.isatty() else s


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m" if sys.stdout.isatty() else s


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config()
    print(f"geo-audit {__version__} (methodology v{__methodology_version__})")
    print(f"cache dir: {cfg.cache_dir}")
    print()

    print("=== API key check ===")
    present = []
    missing = []
    for k in KEY_ENV_VARS:
        if cfg.api_keys.get(k):
            present.append(k)
            print(f"  {_green('✓')} {k}")
        else:
            missing.append(k)
            hint = KEY_HINTS.get(k, {})
            what = hint.get("what", "")
            register = hint.get("register", "")
            free_tier = hint.get("free_tier", "")
            print(f"  {_red('✗')} {k}")
            if what:
                print(f"      what:     {what}")
            if register:
                print(f"      register: {register}")
            if free_tier:
                print(f"      free:     {free_tier}")
    print()

    print("=== Modules ready to run ===")
    ready_full: list[str] = []
    ready_partial: list[str] = []
    skipped: list[str] = []
    for name, matrix in MODULE_KEY_MATRIX.items():
        required = matrix.get("required", [])
        optional_any = matrix.get("optional_any_of", [])
        if required and not all(cfg.api_keys.get(k) for k in required):
            skipped.append(name)
            continue
        if optional_any and not any(cfg.api_keys.get(k) for k in optional_any):
            ready_partial.append(name)
        else:
            ready_full.append(name)

    print(f"  Full: {len(ready_full)}/{len(MODULE_KEY_MATRIX)}  →  {', '.join(ready_full) or '—'}")
    print(f"  Partial / degraded: {len(ready_partial)}  →  {', '.join(ready_partial) or '—'}")
    print(f"  Skipped: {len(skipped)}  →  {', '.join(skipped) or '—'}")
    print()

    if missing:
        print("=== Quick wins (BYOK) ===")
        if "ANTHROPIC_API_KEY" in missing and "OPENAI_API_KEY" in missing:
            print(f"  • ANTHROPIC_API_KEY OR OPENAI_API_KEY        → live brand-mention scan in Claude / ChatGPT (~$0.001/audit)")
        if "PAGESPEED_API_KEY" in missing:
            print(f"  • PAGESPEED_API_KEY (free 25k/day)            → full Core Web Vitals (LCP/INP/CLS)")
        if "PERPLEXITY_API_KEY" in missing:
            print(f"  • PERPLEXITY_API_KEY ($5 free credits)        → live Perplexity brand-mention scan")
        if "GEMINI_API_KEY" in missing:
            print(f"  • GEMINI_API_KEY (free)                       → Gemini brand-mention scan")
        if "FIRECRAWL_API_KEY" in missing:
            print(f"  • FIRECRAWL_API_KEY (free 500/mo)             → audit Cloudflare / SPA / geo-blocked sites that direct httpx can't reach")
        if "TAVILY_API_KEY" in missing:
            print(f"  • TAVILY_API_KEY (free 1000/mo)               → ground Claude/ChatGPT/Gemini brand-scans with live web search (much higher accuracy)")
        print()
        print("Get started: copy .env.example → .env, paste your keys, then re-run `geo-audit doctor`.")
    else:
        print(_green("All keys configured. You can run a full audit."))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.modules:
        modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    else:
        modules = None

    print(f"==> Running audit on: {args.url}")
    print(f"    modules: {modules or 'default (' + ', '.join(registry.DEFAULT_ORDER) + ')'}")
    print(f"    keys present: {', '.join(cfg.keys_present()) or 'none — running in degraded mode for some modules'}")
    print()

    report = run_audit(
        args.url,
        config=cfg,
        modules=modules,
        depth=args.depth,
        lang=args.lang,
        no_cache=args.no_cache,
    )

    if report.composite.modules_used or report.composite.modules_skipped:
        print(f"==> Composite GEO Score: {_green(str(report.composite.score) + '/100')}")
        print(f"    duration: {report.duration_ms}ms  |  modules used: {len(report.composite.modules_used)}/{len(report.composite.modules_used) + len(report.composite.modules_skipped)}")
        if report.composite.modules_skipped:
            print(f"    skipped: {_yellow(', '.join(report.composite.modules_skipped))}")
    else:
        print("==> Composite GEO Score: n/a (selected modules are informational gates)")
        print(f"    duration: {report.duration_ms}ms")
    print()

    print("=== Per-module ===")
    for m in report.modules:
        score_repr = f"{m.score}/100" if m.score is not None else "—"
        flag = " (degraded)" if m.ran_in_degraded_mode else ""
        print(f"  {m.name:20s} {score_repr:>10}{flag}")
        if m.ran_in_degraded_mode and m.what_youd_get:
            print(f"    {_yellow('hint:')} {m.what_youd_get}")
    print()

    # Write outputs.
    out_dir = Path(args.output_dir or "geo-audit-output")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    actions_path = out_dir / "actions.md"
    report_md_path = out_dir / "report.md"

    write_json(report, json_path)
    write_actions_md(report, actions_path)
    write_report_md(report, report_md_path)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {actions_path}")
    print(f"Wrote: {report_md_path}")

    if args.pdf:
        try:
            from geo_audit.report.pdf_writer import write_pdf
            pdf_path = out_dir / "report.pdf"
            write_pdf(report, pdf_path)
            print(f"Wrote: {pdf_path}")
        except RuntimeError as e:
            print(_yellow(f"PDF skipped: {e}"))

    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"geo-audit {__version__}")
    print(f"methodology version: {__methodology_version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geo-audit",
        description="GEO audit toolkit — score URLs for AI search visibility.",
    )
    parser.add_argument("--version", action="version", version=f"geo-audit {__version__}")

    sub = parser.add_subparsers(dest="cmd")

    p_audit = sub.add_parser("audit", help="Run a full GEO audit on a URL.")
    p_audit.add_argument("url", help="URL to audit (https://...)")
    p_audit.add_argument("--modules", default=None,
                         help="Comma-separated module names to run (default: all)")
    p_audit.add_argument("--depth", default="full", choices=["quick", "full"])
    p_audit.add_argument("--lang", default=None, choices=["en", "ru"], help="Language hint (default: auto)")
    p_audit.add_argument("--output-dir", "-o", default="geo-audit-output")
    p_audit.add_argument("--pdf", action="store_true", help="Also write report.pdf (requires extras)")
    p_audit.add_argument("--no-cache", action="store_true", help="Bypass HTTP cache")
    p_audit.set_defaults(func=cmd_audit)

    p_doctor = sub.add_parser("doctor", help="Show key status and ready modules.")
    p_doctor.set_defaults(func=cmd_doctor)

    p_ver = sub.add_parser("version", help="Print version.")
    p_ver.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
