# Contributing

Thanks for improving `agent-scope-diff`.

## Local Setup

```bash
python3 -m pip install -e ".[dev]"
python3 -m unittest discover -s tests -t .
```

## Development Guidelines

- Keep the CLI focused on agent capability and risk posture changes.
- Prefer compact findings over raw structural dumps.
- Add tests for new normalizers, severity behavior, and output modes.
- Do not commit generated build artifacts or secrets.

## Release Changes

For release changes, update both:

- `pyproject.toml`
- `src/agent_scope_diff/__init__.py`

Then run:

```bash
scripts/release-check.sh
```

