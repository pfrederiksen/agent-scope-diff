import json
import tempfile
import unittest
from pathlib import Path

from agent_scope_diff.baseline import load_baseline, suppress_baseline, write_baseline
from agent_scope_diff.compare_dir import compare_directories
from agent_scope_diff.diff import diff_snapshots
from agent_scope_diff.normalize import normalize_config
from agent_scope_diff.severity import apply_severity_config


class RoadmapFeatureTests(unittest.TestCase):
    def test_compare_directories_adds_source_paths(self):
        with tempfile.TemporaryDirectory() as before_dir, tempfile.TemporaryDirectory() as after_dir:
            Path(before_dir, "agent.json").write_text('{"tools": ["github.read"]}', encoding="utf-8")
            Path(after_dir, "agent.json").write_text('{"tools": ["github.read", "github.write"]}', encoding="utf-8")
            Path(after_dir, "new.yaml").write_text("model: gpt-5\n", encoding="utf-8")

            findings = compare_directories(before_dir, after_dir)

        self.assertTrue(any(f.source == "agent.json" and f.category == "tool_added" for f in findings))
        self.assertTrue(any(f.source == "new.yaml" and f.category == "config_file_added" for f in findings))

    def test_baseline_suppresses_exact_findings(self):
        findings = diff_snapshots(normalize_config({"tools": []}), normalize_config({"tools": ["github.write"]}))
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir, "baseline.json")
            write_baseline(str(baseline_path), findings)
            signatures = load_baseline(str(baseline_path))

        self.assertEqual(suppress_baseline(findings, signatures), [])

    def test_severity_config_overrides_findings(self):
        findings = diff_snapshots(normalize_config({"tools": []}), normalize_config({"tools": ["github.write"]}))
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir, "severity.json")
            config_path.write_text(
                json.dumps({"subject_overrides": {"github.write": "caution"}}),
                encoding="utf-8",
            )
            updated = apply_severity_config(findings, str(config_path))

        self.assertEqual(updated[0].severity, "caution")


if __name__ == "__main__":
    unittest.main()
