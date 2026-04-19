from __future__ import annotations

from typing import Any, Dict, List

from .models import Finding
from .parser import load_config


VALID_SEVERITIES = {"info", "caution", "high"}


def apply_severity_config(findings: List[Finding], path: str) -> List[Finding]:
    config = load_config(path)
    if not isinstance(config, dict):
        raise ValueError("severity config must be a JSON/YAML object")
    return [_apply_to_finding(finding, config) for finding in findings]


def _apply_to_finding(finding: Finding, config: Dict[str, Any]) -> Finding:
    severity = finding.severity
    category_overrides = config.get("category_overrides", {})
    subject_overrides = config.get("subject_overrides", {})
    rules = config.get("rules", [])

    if isinstance(category_overrides, dict) and finding.category in category_overrides:
        severity = _valid_severity(category_overrides[finding.category], severity)

    if isinstance(subject_overrides, dict) and finding.subject in subject_overrides:
        severity = _valid_severity(subject_overrides[finding.subject], severity)

    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict) or not _matches_rule(finding, rule):
                continue
            severity = _valid_severity(rule.get("severity"), severity)

    if severity == finding.severity:
        return finding
    finding.severity = severity
    return finding


def _matches_rule(finding: Finding, rule: Dict[str, Any]) -> bool:
    category = rule.get("category")
    if category and category != finding.category:
        return False
    severity = rule.get("current_severity")
    if severity and severity != finding.severity:
        return False
    source = rule.get("source")
    if source and source != finding.source:
        return False
    subject = rule.get("subject")
    if subject and subject != finding.subject:
        return False
    contains = rule.get("subject_contains")
    if contains and str(contains).lower() not in finding.subject.lower():
        return False
    explanation_contains = rule.get("explanation_contains")
    if explanation_contains and str(explanation_contains).lower() not in finding.explanation.lower():
        return False
    return True


def _valid_severity(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value in VALID_SEVERITIES:
        return value
    return fallback
