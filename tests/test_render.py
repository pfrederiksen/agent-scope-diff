import json
import unittest

from agent_scope_diff.diff import diff_snapshots
from agent_scope_diff.normalize import normalize_config
from agent_scope_diff.render import render_github_actions, render_json, render_markdown, render_sarif


class RenderTests(unittest.TestCase):
    def test_json_renderer_has_summary_and_findings(self):
        findings = diff_snapshots(normalize_config({"tools": []}), normalize_config({"tools": ["github.write"]}))
        payload = json.loads(render_json(findings, context="pr-42"))

        self.assertEqual(payload["context"], "pr-42")
        self.assertEqual(payload["summary"]["high"], 1)
        self.assertEqual(payload["findings"][0]["category"], "tool_added")

    def test_markdown_renderer_outputs_table(self):
        findings = diff_snapshots(normalize_config({"model": "a"}), normalize_config({"model": "b"}))
        markdown = render_markdown(findings)

        self.assertIn("# Agent Scope Diff", markdown)
        self.assertIn("| Severity | Category | Subject | Before | After | Why it matters |", markdown)

    def test_sarif_and_github_actions_renderers(self):
        findings = diff_snapshots(normalize_config({"tools": []}), normalize_config({"tools": ["github.write"]}))
        findings[0].source = "agent.json"

        sarif = json.loads(render_sarif(findings, context="ci"))
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertEqual(sarif["runs"][0]["results"][0]["level"], "error")

        gha = render_github_actions(findings)
        self.assertIn("::error", gha)
        self.assertIn("file=agent.json", gha)


if __name__ == "__main__":
    unittest.main()
