# agent-scope-diff

`agent-scope-diff` is a shell-first CLI for comparing agent manifests, MCP configs, tool-permission snapshots, and related JSON/YAML files.

It prints a compact diff focused on agent capability and risk posture changes instead of raw structural changes. Think `git diff`, but for agent access.

```text
+ tool added: gmail.send [high]
+ tool added: github.write [high]
- tool removed: slack.read [info]
! permission widened: notion.read -> notion.write [high]
~ model changed: gpt-4.1 -> gpt-5 [info]
+ environment variable added: AWS_ACCESS_KEY_ID [caution]
```

## Install

From a checkout:

```bash
python3 -m pip install .
```

From PyPI:

```bash
pipx install agent-scope-diff
```

With Homebrew:

```bash
brew tap pfrederiksen/tap
brew install agent-scope-diff
```

For development:

```bash
python3 -m pip install -e ".[dev]"
```

Then run:

```bash
agent-scope-diff before.json after.json
```

You can also run without installing:

```bash
PYTHONPATH=src python3 -m agent_scope_diff.cli before.json after.json
```

## Usage

```bash
agent-scope-diff before.json after.json
agent-scope-diff before.yaml after.yaml --json
agent-scope-diff before.json after.json --markdown
agent-scope-diff before.json after.json --quiet-high-only
agent-scope-diff before.json after.json --fail-on-high
agent-scope-diff --compare-dir configs/before configs/after
```

Useful flags:

```text
--json              render machine-readable JSON
--markdown          render a Markdown report
--quiet-high-only   only show high severity findings
--no-color          disable terminal color
--summary-only      only print the summary
--context NAME      add a label to human/JSON/Markdown output
--fail-on-high      exit with status 2 when high severity findings exist
--compare-dir A B   compare matching JSON/YAML files across two folders
--sarif             render SARIF 2.1.0 JSON
--github-actions    render GitHub Actions workflow annotations
--normalizer NAME   choose auto, generic, openai-agents, claude-desktop, or langgraph
--severity-config   apply JSON/YAML severity override rules
--baseline FILE     suppress accepted findings from a baseline
--write-baseline    write current findings to a baseline JSON file
```

## Supported Inputs

The CLI supports:

- JSON files
- YAML files
- directory comparisons with matching JSON/YAML relative paths

It does not require one fixed schema. The normalizer looks for common agent and MCP patterns, including:

- tools: `tools`, `allowed_tools`, `enabledTools`, `toolDefinitions`
- permissions/scopes: `permissions`, `scopes`, `allowedScopes`, `capabilities`
- models: `model`, `model_name`, `defaultModel`
- environment and secret references: `env`, `environment`, `secrets`, `${AWS_ACCESS_KEY_ID}`
- MCP servers: `mcpServers`, `mcp_servers`, server lists
- identity/auth metadata: `auth`, `identity`, `provider`, `service_account`, `oauth`
- endpoints and hosts: `url`, `endpoint`, `host`, `baseUrl`, `command`

Normalizer profiles:

- `auto`: generic heuristics plus known framework enrichers
- `generic`: schema-agnostic recursive normalization only
- `openai-agents`: recognizes common `agents` lists with `model`, `tools`, and `handoffs`
- `claude-desktop`: emphasizes Claude Desktop-style `mcpServers`
- `langgraph`: recognizes simple LangGraph-style `graph.nodes` tool/model fields

## What It Detects

At minimum, `agent-scope-diff` reports:

- tools added or removed
- permissions widened or narrowed
- model changes
- new or removed environment variables and secret references
- identity/auth config changes
- MCP server additions and removals
- endpoint or host changes where visible

Findings include:

- `category`
- `severity`
- `subject`
- `before`
- `after`
- short explanation

## Severity

Severity is intentionally simple:

- `info`: usually reducing access or changing non-sensitive metadata
- `caution`: read-only access, new secret references, auth/endpoint changes, new MCP servers
- `high`: write/send/delete/admin-like tools or broader permission scopes

This is not a policy engine. It is a review aid that makes access changes obvious.

## Examples

Human-readable output:

```bash
agent-scope-diff fixtures/simple-before.json fixtures/simple-after.json --no-color
```

JSON output:

```bash
agent-scope-diff fixtures/simple-before.json fixtures/simple-after.json --json
```

Markdown report:

```bash
agent-scope-diff fixtures/mcp-before.yaml fixtures/mcp-after.yaml --markdown --context "MCP migration"
```

SARIF output:

```bash
agent-scope-diff fixtures/simple-before.json fixtures/simple-after.json --sarif > agent-scope-diff.sarif
```

GitHub Actions annotations:

```bash
agent-scope-diff fixtures/simple-before.json fixtures/simple-after.json --github-actions
```

Compare directories:

```bash
agent-scope-diff --compare-dir configs/before configs/after --markdown
```

CI gate on high-severity changes:

```bash
agent-scope-diff before.yaml after.yaml --fail-on-high
```

Create and use a baseline of accepted findings:

```bash
agent-scope-diff before.yaml after.yaml --write-baseline agent-scope-baseline.json
agent-scope-diff before.yaml after.yaml --baseline agent-scope-baseline.json
```

Customize severity:

```json
{
  "category_overrides": {
    "model_changed": "caution"
  },
  "subject_overrides": {
    "internal.search.read": "info"
  },
  "rules": [
    {
      "category": "tool_added",
      "subject_contains": ".write",
      "severity": "high"
    }
  ]
}
```

Run with:

```bash
agent-scope-diff before.json after.json --severity-config severity.json
```

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -t .
```

Project layout:

```text
src/agent_scope_diff/
  cli.py         argument parsing and exit behavior
  parser.py      JSON/YAML loading
  normalize.py   heuristic normalization into a common snapshot
  diff.py        risk-focused diff engine
  render.py      human, JSON, and Markdown renderers
  compare_dir.py directory comparison
  baseline.py    accepted finding baselines
  severity.py    severity override rules
fixtures/        sample before/after configs
tests/           parser, normalization, diff, and renderer tests
```

## Releases

Releases are versioned with PyPI package versions and GitHub tags.

```bash
scripts/release-check.sh
git tag -a v0.1.0 -m "agent-scope-diff v0.1.0"
git push origin main
git push origin v0.1.0
```

The `Publish` GitHub Actions workflow publishes tagged releases to PyPI using the `PYPI_API_TOKEN` repository secret.
See [RELEASE.md](RELEASE.md) for the full release checklist.

## Limitations

- Normalization is heuristic and optimized for common config shapes.
- It does not evaluate runtime behavior, code, or dynamic tool registration.
- It masks sensitive identity values by key name, but input files should still be handled as sensitive.
- It is not a replacement for authorization policy, threat modeling, or code review.

## Future Ideas

- More framework-specific normalizers
- Richer SARIF locations when source line mapping is available
- Signed or expiring baselines for stricter review workflows
- Optional organization policy packs while keeping the default CLI lightweight
