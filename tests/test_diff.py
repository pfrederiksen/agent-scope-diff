import unittest

from agent_scope_diff.diff import diff_snapshots
from agent_scope_diff.normalize import normalize_config


def categories(findings):
    return {finding.category for finding in findings}


class DiffTests(unittest.TestCase):
    def test_detects_risk_focused_deltas(self):
        before = normalize_config(
            {
                "model": "gpt-4.1",
                "tools": ["slack.read", "notion.read"],
                "permissions": ["notion.read"],
                "env": {"OPENAI_API_KEY": "${OPENAI_API_KEY}"},
            }
        )
        after = normalize_config(
            {
                "model": "gpt-5",
                "tools": ["notion.read", "gmail.send", "github.write"],
                "permissions": ["notion.read_write", "github.write"],
                "env": {
                    "OPENAI_API_KEY": "${OPENAI_API_KEY}",
                    "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
                },
            }
        )

        findings = diff_snapshots(before, after)
        cats = categories(findings)

        self.assertIn("tool_added", cats)
        self.assertIn("tool_removed", cats)
        self.assertIn("permission_widened", cats)
        self.assertIn("model_changed", cats)
        self.assertIn("env_var_added", cats)
        self.assertTrue(any(f.subject == "notion" and f.severity == "high" for f in findings))
        self.assertTrue(any(f.subject == "gmail.send" and f.severity == "high" for f in findings))

    def test_detects_mcp_and_identity_changes(self):
        before = normalize_config(
            {
                "mcpServers": {"github": {"url": "https://old.example.com/mcp"}},
                "auth": {"provider": "github", "tenant": "engineering"},
            }
        )
        after = normalize_config(
            {
                "mcpServers": {
                    "github": {"url": "https://new.example.com/mcp"},
                    "filesystem": {"command": "npx"},
                },
                "auth": {"provider": "github", "tenant": "platform"},
            }
        )

        findings = diff_snapshots(before, after)
        cats = categories(findings)

        self.assertIn("mcp_server_added", cats)
        self.assertIn("endpoint_changed", cats)
        self.assertIn("identity_auth_changed", cats)


if __name__ == "__main__":
    unittest.main()
