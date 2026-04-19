from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


Severity = str


@dataclass(frozen=True)
class Endpoint:
    owner: str
    value: str

    @property
    def key(self) -> str:
        return self.owner


@dataclass
class Snapshot:
    tools: Set[str] = field(default_factory=set)
    permissions: Dict[str, str] = field(default_factory=dict)
    models: Set[str] = field(default_factory=set)
    env_vars: Set[str] = field(default_factory=set)
    mcp_servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    endpoints: Dict[str, str] = field(default_factory=dict)
    identity: Dict[str, str] = field(default_factory=dict)


@dataclass
class Finding:
    category: str
    severity: Severity
    subject: str
    before: Optional[str]
    after: Optional[str]
    explanation: str
    source: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "category": self.category,
            "severity": self.severity,
            "subject": self.subject,
            "before": self.before,
            "after": self.after,
            "explanation": self.explanation,
            "source": self.source,
        }
