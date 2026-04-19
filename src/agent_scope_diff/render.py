from __future__ import annotations

import json
import os
from typing import Iterable, List, Optional

from .models import Finding


COLORS = {
    "high": "\033[31m",
    "caution": "\033[33m",
    "info": "\033[36m",
    "reset": "\033[0m",
}
SYMBOLS = {
    "config_file_added": "+",
    "config_file_removed": "-",
    "tool_added": "+",
    "tool_removed": "-",
    "permission_widened": "!",
    "permission_narrowed": "~",
    "permission_changed": "~",
    "model_changed": "~",
    "env_var_added": "+",
    "env_var_removed": "-",
    "mcp_server_added": "+",
    "mcp_server_removed": "-",
    "identity_auth_changed": "~",
    "endpoint_changed": "!",
}


def render_human(
    findings: List[Finding],
    *,
    context: Optional[str] = None,
    no_color: bool = False,
    summary_only: bool = False,
) -> str:
    lines: List[str] = []
    if context:
        lines.append(f"agent-scope-diff: {context}")
    if not findings:
        lines.append("No agent capability changes detected.")
        return "\n".join(lines)
    if summary_only:
        lines.append(_summary(findings))
        return "\n".join(lines)
    for finding in findings:
        source = f"[{finding.source}] " if finding.source else ""
        line = f"{SYMBOLS.get(finding.category, '~')} {source}{finding.explanation} [{finding.severity}]"
        lines.append(_colorize(line, finding.severity, no_color))
    lines.append(_summary(findings))
    return "\n".join(lines)


def render_json(findings: List[Finding], *, context: Optional[str] = None) -> str:
    payload = {
        "context": context,
        "summary": _summary_counts(findings),
        "findings": [finding.as_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_markdown(findings: List[Finding], *, context: Optional[str] = None, summary_only: bool = False) -> str:
    lines: List[str] = []
    title = "Agent Scope Diff"
    if context:
        title += f": {context}"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Summary:** {_summary(findings)}")
    if summary_only or not findings:
        return "\n".join(lines)
    lines.append("")
    has_source = any(finding.source for finding in findings)
    if has_source:
        lines.append("| File | Severity | Category | Subject | Before | After | Why it matters |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    else:
        lines.append("| Severity | Category | Subject | Before | After | Why it matters |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
    for finding in findings:
        values = [
            _md(finding.severity),
            _md(finding.category),
            _md(finding.subject),
            _md(finding.before or ""),
            _md(finding.after or ""),
            _md(finding.explanation),
        ]
        if has_source:
            values.insert(0, _md(finding.source or ""))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_sarif(findings: List[Finding], *, context: Optional[str] = None) -> str:
    rules = {}
    results = []
    for finding in findings:
        rule_id = finding.category
        rules[rule_id] = {
            "id": rule_id,
            "name": rule_id.replace("_", " "),
            "shortDescription": {"text": rule_id.replace("_", " ")},
        }
        result = {
            "ruleId": rule_id,
            "level": _sarif_level(finding.severity),
            "message": {"text": finding.explanation},
            "properties": {
                "severity": finding.severity,
                "subject": finding.subject,
                "before": finding.before,
                "after": finding.after,
            },
        }
        if finding.source:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.source}
                    }
                }
            ]
        results.append(result)
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agent-scope-diff",
                        "informationUri": "https://github.com/",
                        "rules": list(rules.values()),
                    }
                },
                "automationDetails": {"id": context} if context else {},
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_github_actions(findings: List[Finding]) -> str:
    if not findings:
        return "agent-scope-diff: no agent capability changes detected"
    lines = []
    for finding in findings:
        command = _github_actions_command(finding.severity)
        title = f"{finding.severity}: {finding.category}"
        file_part = f" file={_gha_escape(finding.source)}," if finding.source else " "
        lines.append(
            f"::{command}{file_part}title={_gha_escape(title)}::{_gha_escape(finding.explanation)}"
        )
    return "\n".join(lines)


def _github_actions_command(severity: str) -> str:
    if severity == "high":
        return "error"
    if severity == "caution":
        return "warning"
    return "notice"


def _sarif_level(severity: str) -> str:
    if severity == "high":
        return "error"
    if severity == "caution":
        return "warning"
    return "note"


def _gha_escape(value: Optional[str]) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _summary(findings: List[Finding]) -> str:
    counts = _summary_counts(findings)
    total = counts["total"]
    return f"{total} finding(s): {counts['high']} high, {counts['caution']} caution, {counts['info']} info"


def _summary_counts(findings: List[Finding]) -> dict:
    return {
        "total": len(findings),
        "high": sum(1 for finding in findings if finding.severity == "high"),
        "caution": sum(1 for finding in findings if finding.severity == "caution"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }


def _colorize(text: str, severity: str, no_color: bool) -> str:
    if no_color or os.environ.get("NO_COLOR"):
        return text
    color = COLORS.get(severity)
    if not color:
        return text
    return f"{color}{text}{COLORS['reset']}"


def _md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
