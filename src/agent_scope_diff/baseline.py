from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Set, Tuple

from .models import Finding
from .parser import load_config


Signature = Tuple[str, str, str, str, str]


def finding_signature(finding: Finding) -> Signature:
    return (
        finding.category,
        finding.subject,
        finding.before or "",
        finding.after or "",
        finding.source or "",
    )


def load_baseline(path: str) -> Set[Signature]:
    data = load_config(path)
    if isinstance(data, dict):
        raw_findings = data.get("findings", [])
    elif isinstance(data, list):
        raw_findings = data
    else:
        raw_findings = []
    signatures: Set[Signature] = set()
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        signatures.add(
            (
                str(item.get("category") or ""),
                str(item.get("subject") or ""),
                str(item.get("before") or ""),
                str(item.get("after") or ""),
                str(item.get("source") or ""),
            )
        )
    return signatures


def suppress_baseline(findings: List[Finding], signatures: Set[Signature]) -> List[Finding]:
    return [finding for finding in findings if finding_signature(finding) not in signatures]


def write_baseline(path: str, findings: List[Finding]) -> None:
    payload = {
        "version": 1,
        "findings": [finding.as_dict() for finding in findings],
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

