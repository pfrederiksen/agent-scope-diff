from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from .models import Finding, Snapshot
from .normalize import permission_rank


WRITE_WORDS = ("write", "send", "create", "update", "edit", "delete", "admin", "manage", "full", "root", "*")
READ_WORDS = ("read", "view", "list", "search")


def diff_snapshots(before: Snapshot, after: Snapshot) -> List[Finding]:
    findings: List[Finding] = []
    findings.extend(_set_findings(before.tools, after.tools, "tool", "tools"))
    findings.extend(_permission_findings(before.permissions, after.permissions))
    findings.extend(_model_findings(before.models, after.models))
    findings.extend(_set_findings(before.env_vars, after.env_vars, "env_var", "environment variables"))
    findings.extend(_server_findings(before, after))
    findings.extend(_map_change_findings(before.identity, after.identity, "identity_auth_changed", "identity/auth config"))
    findings.extend(_map_change_findings(before.endpoints, after.endpoints, "endpoint_changed", "endpoint or host"))
    return sorted(findings, key=_sort_key)


def annotate_findings(findings: List[Finding], source: str) -> List[Finding]:
    for finding in findings:
        finding.source = source
    return findings


def _set_findings(before: Set[str], after: Set[str], category: str, label: str) -> List[Finding]:
    findings: List[Finding] = []
    for item in sorted(after - before):
        findings.append(
            Finding(
                category=f"{category}_added",
                severity=_added_severity(category, item),
                subject=item,
                before=None,
                after=item,
                explanation=f"{label[:-1] if label.endswith('s') else label} added: {item}",
            )
        )
    for item in sorted(before - after):
        findings.append(
            Finding(
                category=f"{category}_removed",
                severity="info",
                subject=item,
                before=item,
                after=None,
                explanation=f"{label[:-1] if label.endswith('s') else label} removed: {item}",
            )
        )
    return findings


def _permission_findings(before: Dict[str, str], after: Dict[str, str]) -> List[Finding]:
    findings: List[Finding] = []
    all_subjects = sorted(set(before) | set(after))
    for subject in all_subjects:
        old = before.get(subject)
        new = after.get(subject)
        if old == new:
            continue
        if old is None:
            findings.append(
                Finding(
                    category="permission_widened",
                    severity=_permission_severity(new),
                    subject=subject,
                    before=None,
                    after=new,
                    explanation=f"new permission scope introduced: {subject}.{new}",
                )
            )
            continue
        if new is None:
            findings.append(
                Finding(
                    category="permission_narrowed",
                    severity="info",
                    subject=subject,
                    before=old,
                    after=None,
                    explanation=f"permission scope removed: {subject}.{old}",
                )
            )
            continue
        old_rank = permission_rank(old)
        new_rank = permission_rank(new)
        if new_rank > old_rank:
            findings.append(
                Finding(
                    category="permission_widened",
                    severity="high",
                    subject=subject,
                    before=old,
                    after=new,
                    explanation=f"permission widened: {subject}.{old} -> {subject}.{new}",
                )
            )
        elif new_rank < old_rank:
            findings.append(
                Finding(
                    category="permission_narrowed",
                    severity="info",
                    subject=subject,
                    before=old,
                    after=new,
                    explanation=f"permission narrowed: {subject}.{old} -> {subject}.{new}",
                )
            )
        else:
            findings.append(
                Finding(
                    category="permission_changed",
                    severity="caution",
                    subject=subject,
                    before=old,
                    after=new,
                    explanation=f"permission changed: {subject}.{old} -> {subject}.{new}",
                )
            )
    return findings


def _model_findings(before: Set[str], after: Set[str]) -> List[Finding]:
    if before == after:
        return []
    before_value = ", ".join(sorted(before)) if before else None
    after_value = ", ".join(sorted(after)) if after else None
    severity = "info" if before and after else "caution"
    return [
        Finding(
            category="model_changed",
            severity=severity,
            subject="model",
            before=before_value,
            after=after_value,
            explanation=f"model changed: {before_value or '<none>'} -> {after_value or '<none>'}",
        )
    ]


def _server_findings(before: Snapshot, after: Snapshot) -> List[Finding]:
    findings: List[Finding] = []
    before_names = set(before.mcp_servers)
    after_names = set(after.mcp_servers)
    for name in sorted(after_names - before_names):
        endpoint = after.mcp_servers[name].get("endpoint")
        findings.append(
            Finding(
                category="mcp_server_added",
                severity="caution",
                subject=name,
                before=None,
                after=endpoint or name,
                explanation=f"MCP server added: {name}",
            )
        )
    for name in sorted(before_names - after_names):
        endpoint = before.mcp_servers[name].get("endpoint")
        findings.append(
            Finding(
                category="mcp_server_removed",
                severity="info",
                subject=name,
                before=endpoint or name,
                after=None,
                explanation=f"MCP server removed: {name}",
            )
        )
    for name in sorted(before_names & after_names):
        old_endpoint = before.mcp_servers[name].get("endpoint")
        new_endpoint = after.mcp_servers[name].get("endpoint")
        if old_endpoint != new_endpoint:
            findings.append(
                Finding(
                    category="endpoint_changed",
                    severity="caution",
                    subject=name,
                    before=old_endpoint,
                    after=new_endpoint,
                    explanation=f"MCP server endpoint changed: {name}: {old_endpoint or '<none>'} -> {new_endpoint or '<none>'}",
                )
            )
    return findings


def _map_change_findings(before: Dict[str, str], after: Dict[str, str], category: str, label: str) -> List[Finding]:
    findings: List[Finding] = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        findings.append(
            Finding(
                category=category,
                severity="caution",
                subject=key,
                before=old,
                after=new,
                explanation=f"{label} changed: {key}: {old or '<none>'} -> {new or '<none>'}",
            )
        )
    return findings


def _added_severity(category: str, item: str) -> str:
    lowered = item.lower()
    if category == "tool":
        if any(word in lowered for word in WRITE_WORDS):
            return "high"
        return "caution"
    if category == "env_var":
        if any(word in lowered for word in ("secret", "token", "key", "credential", "password")):
            return "caution"
        return "info"
    return "caution"


def _permission_severity(level: Optional[str]) -> str:
    if not level:
        return "caution"
    if permission_rank(level) >= 2:
        return "high"
    return "caution"


def _sort_key(finding: Finding) -> tuple:
    severity_order = {"high": 0, "caution": 1, "info": 2}
    return (severity_order.get(finding.severity, 9), finding.source or "", finding.category, finding.subject)
