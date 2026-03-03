import tempfile
import unittest
from pathlib import Path

from blockcheck.runner import BlockcheckRunner
from blockcheck.targets import load_domains_with_source, load_tcp_targets_with_source, select_tcp_targets


class TcpTargetsSelectionTests(unittest.TestCase):
    def test_load_domains_reports_file_source_for_explicit_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write("example.com\n")
            temp_path = Path(tmp.name)

        try:
            domains, source = load_domains_with_source(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertEqual(domains, ["example.com"])
        self.assertTrue(source.startswith("file:"))

    def test_load_tcp_targets_reports_fallback_source_when_missing(self):
        missing_path = Path(tempfile.gettempdir()) / "nonexistent_tcp_targets_for_test.json"
        if missing_path.exists():
            missing_path.unlink()

        targets, source = load_tcp_targets_with_source(missing_path)

        self.assertTrue(targets)
        self.assertTrue(source.startswith("fallback:missing:"))

    def test_select_tcp_targets_respects_provider_cap(self):
        targets = [
            {"id": "A-1", "provider": "ProviderA", "url": "https://a1.example"},
            {"id": "A-2", "provider": "ProviderA", "url": "https://a2.example"},
            {"id": "A-3", "provider": "ProviderA", "url": "https://a3.example"},
            {"id": "B-1", "provider": "ProviderB", "url": "https://b1.example"},
            {"id": "B-2", "provider": "ProviderB", "url": "https://b2.example"},
            {"id": "C-1", "provider": "ProviderC", "url": "https://c1.example"},
        ]

        selected = select_tcp_targets(targets, max_count=5, per_provider_cap=2)

        self.assertEqual(len(selected), 5)

        counts: dict[str, int] = {}
        for target in selected:
            provider = target["provider"]
            counts[provider] = counts.get(provider, 0) + 1

        self.assertLessEqual(counts.get("ProviderA", 0), 2)
        self.assertLessEqual(counts.get("ProviderB", 0), 2)
        self.assertLessEqual(counts.get("ProviderC", 0), 2)

    def test_runner_rotation_prefers_healthy_targets_first(self):
        runner = BlockcheckRunner(mode="dpi_only", parallel=1)

        candidates = [
            {"id": "A-dead", "provider": "ProviderA", "url": "https://a-dead.example"},
            {"id": "A-ok", "provider": "ProviderA", "url": "https://a-ok.example"},
            {"id": "B-ok", "provider": "ProviderB", "url": "https://b-ok.example"},
            {"id": "B-dead", "provider": "ProviderB", "url": "https://b-dead.example"},
        ]

        health_map = {
            "A-dead": (False, "timeout", 100.0),
            "A-ok": (True, "HTTP 200", 50.0),
            "B-ok": (True, "HTTP 200", 40.0),
            "B-dead": (False, "reset", 90.0),
        }

        selected = runner._select_rotated_tcp_targets(candidates, health_map)
        selected_ids = [target["id"] for target in selected]

        self.assertIn("A-ok", selected_ids)
        self.assertIn("B-ok", selected_ids)
        self.assertLess(selected_ids.index("A-ok"), selected_ids.index("A-dead"))
        self.assertLess(selected_ids.index("B-ok"), selected_ids.index("B-dead"))


if __name__ == "__main__":
    unittest.main()
