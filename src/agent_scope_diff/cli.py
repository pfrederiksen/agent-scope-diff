from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .baseline import load_baseline, suppress_baseline, write_baseline
from .compare_dir import compare_directories
from .diff import diff_snapshots
from .normalize import list_normalizers, normalize_config
from .parser import ParseError, load_config
from .render import render_github_actions, render_human, render_json, render_markdown, render_sarif
from .severity import apply_severity_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-scope-diff",
        description="Risk-focused diffs for agent manifests, MCP configs, and tool permission snapshots.",
    )
    parser.add_argument("before", nargs="?", help="Path to the before JSON/YAML config")
    parser.add_argument("after", nargs="?", help="Path to the after JSON/YAML config")
    parser.add_argument("--compare-dir", nargs=2, metavar=("BEFORE_DIR", "AFTER_DIR"), help="Compare matching JSON/YAML files across two directories")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    parser.add_argument("--markdown", action="store_true", help="Render a Markdown report")
    parser.add_argument("--sarif", action="store_true", help="Render SARIF 2.1.0 JSON")
    parser.add_argument("--github-actions", action="store_true", help="Render GitHub Actions annotations")
    parser.add_argument("--quiet-high-only", action="store_true", help="Only show high severity findings")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal color")
    parser.add_argument("--summary-only", action="store_true", help="Only print the summary")
    parser.add_argument("--context", help="Optional report label")
    parser.add_argument("--fail-on-high", action="store_true", help="Exit with status 2 when high severity findings exist")
    parser.add_argument("--normalizer", choices=list_normalizers(), default="auto", help="Normalizer profile to use")
    parser.add_argument("--severity-config", help="JSON/YAML file with severity override rules")
    parser.add_argument("--baseline", help="JSON/YAML baseline of accepted findings to suppress")
    parser.add_argument("--write-baseline", help="Write the current findings to a baseline JSON file")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    render_modes = [args.json, args.markdown, args.sarif, args.github_actions]
    if sum(1 for enabled in render_modes if enabled) > 1:
        parser.error("choose only one output mode")

    if args.compare_dir and (args.before or args.after):
        parser.error("use either positional before/after files or --compare-dir, not both")
    if not args.compare_dir and (not args.before or not args.after):
        parser.error("provide before/after files or --compare-dir BEFORE_DIR AFTER_DIR")

    try:
        if args.compare_dir:
            findings = compare_directories(args.compare_dir[0], args.compare_dir[1], normalizer=args.normalizer)
        else:
            before_data = load_config(args.before)
            after_data = load_config(args.after)
            findings = diff_snapshots(
                normalize_config(before_data, normalizer=args.normalizer),
                normalize_config(after_data, normalizer=args.normalizer),
            )
        if args.severity_config:
            findings = apply_severity_config(findings, args.severity_config)
        findings = sorted(findings, key=_finding_sort_key)
        if args.write_baseline:
            write_baseline(args.write_baseline, findings)
        if args.baseline:
            findings = suppress_baseline(findings, load_baseline(args.baseline))
    except ParseError as exc:
        print(f"agent-scope-diff: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"agent-scope-diff: {exc}", file=sys.stderr)
        return 1

    if args.quiet_high_only:
        findings = [finding for finding in findings if finding.severity == "high"]

    if args.json:
        output = render_json(findings, context=args.context)
    elif args.markdown:
        output = render_markdown(findings, context=args.context, summary_only=args.summary_only)
    elif args.sarif:
        output = render_sarif(findings, context=args.context)
    elif args.github_actions:
        output = render_github_actions(findings)
    else:
        output = render_human(
            findings,
            context=args.context,
            no_color=args.no_color,
            summary_only=args.summary_only,
        )
    print(output)

    if args.fail_on_high and any(finding.severity == "high" for finding in findings):
        return 2
    return 0


def _finding_sort_key(finding):
    severity_order = {"high": 0, "caution": 1, "info": 2}
    return (severity_order.get(finding.severity, 9), finding.source or "", finding.category, finding.subject)


if __name__ == "__main__":
    raise SystemExit(main())
