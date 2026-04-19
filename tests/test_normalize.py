import unittest

from agent_scope_diff.normalize import normalize_config


class NormalizeTests(unittest.TestCase):
    def test_normalizes_common_agent_fields(self):
        snapshot = normalize_config(
            {
                "model": "gpt-4.1",
                "tools": ["slack.read", {"name": "github.write"}],
                "permissions": ["notion.read_write"],
                "env": {"AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}"},
                "auth": {"provider": "github", "token": "secret-value"},
            }
        )

        self.assertIn("slack.read", snapshot.tools)
        self.assertIn("github.write", snapshot.tools)
        self.assertEqual(snapshot.permissions["notion"], "write")
        self.assertIn("AWS_ACCESS_KEY_ID", snapshot.env_vars)
        self.assertEqual(snapshot.identity["auth.provider"], "github")
        self.assertEqual(snapshot.identity["auth.token"], "<redacted>")

    def test_normalizes_mcp_servers(self):
        snapshot = normalize_config(
            {
                "mcpServers": {
                    "github": {
                        "url": "https://mcp.example.com/github",
                        "tools": ["github.read"],
                    }
                }
            }
        )

        self.assertEqual(snapshot.mcp_servers["github"]["endpoint"], "mcp.example.com")
        self.assertEqual(snapshot.mcp_servers["github"]["tools"], ["github.read"])

    def test_named_openai_agents_normalizer(self):
        snapshot = normalize_config(
            {
                "agents": [
                    {
                        "name": "reviewer",
                        "model": "gpt-5",
                        "tools": ["github.read"],
                        "handoffs": ["triage_agent"],
                    }
                ]
            },
            normalizer="openai-agents",
        )

        self.assertIn("gpt-5", snapshot.models)
        self.assertIn("github.read", snapshot.tools)
        self.assertIn("triage_agent", snapshot.tools)


if __name__ == "__main__":
    unittest.main()
