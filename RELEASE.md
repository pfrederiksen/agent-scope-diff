# Release Process

`agent-scope-diff` uses PyPI versions and Git tags together.

## Versioning

- Package versions live in `pyproject.toml` and `src/agent_scope_diff/__init__.py`.
- Release tags use the format `vMAJOR.MINOR.PATCH`, for example `v0.1.0`.
- The tag version must match the package version without the leading `v`.

## Local Checks

```bash
python3 -m unittest discover -s tests -t .
PYTHONPATH=src python3 -m agent_scope_diff.cli fixtures/simple-before.json fixtures/simple-after.json --no-color
```

## Build

Use Python's standard build frontend:

```bash
python3 -m pip install build twine
python3 -m build
python3 -m twine check dist/*
```

## Publish To PyPI

Set the token in the environment rather than writing it to a file:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_API_TOKEN" python3 -m twine upload dist/*
```

## GitHub Release Tags

Create an annotated tag for each published version:

```bash
git tag -a v0.1.0 -m "agent-scope-diff v0.1.0"
git push origin main
git push origin v0.1.0
```

If a GitHub release page is wanted:

```bash
gh release create v0.1.0 dist/* --title "agent-scope-diff v0.1.0" --notes-file RELEASE_NOTES.md
```

