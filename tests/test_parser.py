import unittest

from agent_scope_diff.parser import load_config


class ParserTests(unittest.TestCase):
    def test_load_json_fixture(self):
        data = load_config("fixtures/simple-before.json")
        self.assertEqual(data["model"], "gpt-4.1")

    def test_load_yaml_fixture(self):
        data = load_config("fixtures/mcp-before.yaml")
        self.assertIn("mcpServers", data)


if __name__ == "__main__":
    unittest.main()
