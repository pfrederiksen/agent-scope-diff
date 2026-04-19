from __future__ import annotations

from pathlib import Path
from typing import List, Set

from .diff import annotate_findings, diff_snapshots
from .models import Finding
from .normalize import normalize_config
from .parser import load_config


CONFIG_SUFFIXES = {".json", ".yaml", ".yml"}


def compare_directories(before_dir: str, after_dir: str, *, normalizer: str = "auto") -> List[Finding]:
    before_root = Path(before_dir)
    after_root = Path(after_dir)
    before_files = _config_files(before_root)
    after_files = _config_files(after_root)
    findings: List[Finding] = []

    for rel_path in sorted(set(before_files) | set(after_files)):
        before_path = before_files.get(rel_path)
        after_path = after_files.get(rel_path)
        if before_path is None:
            findings.append(
                Finding(
                    category="config_file_added",
                    severity="caution",
                    subject=rel_path,
                    before=None,
                    after=rel_path,
                    explanation=f"config file added: {rel_path}",
                    source=rel_path,
                )
            )
            continue
        if after_path is None:
            findings.append(
                Finding(
                    category="config_file_removed",
                    severity="info",
                    subject=rel_path,
                    before=rel_path,
                    after=None,
                    explanation=f"config file removed: {rel_path}",
                    source=rel_path,
                )
            )
            continue

        before_snapshot = normalize_config(load_config(str(before_path)), normalizer=normalizer)
        after_snapshot = normalize_config(load_config(str(after_path)), normalizer=normalizer)
        findings.extend(annotate_findings(diff_snapshots(before_snapshot, after_snapshot), rel_path))

    return sorted(findings, key=lambda finding: (finding.source or "", finding.category, finding.subject))


def _config_files(root: Path) -> dict:
    if not root.exists() or not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    files = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in CONFIG_SUFFIXES:
            files[str(path.relative_to(root))] = path
    return files

