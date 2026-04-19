from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise SystemExit("could not find project.version in pyproject.toml")
    return match.group(1)


def read_package_version() -> str:
    text = (ROOT / "src" / "agent_scope_diff" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise SystemExit("could not find __version__ in package")
    return match.group(1)


def main() -> int:
    pyproject_version = read_pyproject_version()
    package_version = read_package_version()
    if pyproject_version != package_version:
        print(
            f"version mismatch: pyproject.toml={pyproject_version}, package={package_version}",
            file=sys.stderr,
        )
        return 1
    print(pyproject_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

