import importlib
import unittest

import config as config_module
import hosts.hosts as hosts_module

reg_module = importlib.import_module("config.reg")


class HostsBootstrapFirstLaunchTests(unittest.TestCase):
    def _run_bootstrap(
        self,
        *,
        initial_content: str,
        initial_signature: str | None = None,
        remove_github: bool = True,
    ) -> dict:
        written_contents: list[str] = []
        counters = {
            "read": 0,
            "write": 0,
            "set_signature": 0,
            "set_legacy": 0,
        }
        signature_state = {"value": initial_signature}
        set_signature_calls: list[str] = []

        def fake_read_hosts_file():
            counters["read"] += 1
            return initial_content

        def fake_write_hosts_file(content: str):
            counters["write"] += 1
            written_contents.append(content)
            return True

        def fake_get_remove_github_api():
            return remove_github

        def fake_get_bootstrap_signature():
            return signature_state["value"]

        def fake_set_bootstrap_signature(signature: str):
            counters["set_signature"] += 1
            set_signature_calls.append(signature)
            signature_state["value"] = signature
            return True

        def fake_set_bootstrap_legacy(_done: bool = True):
            counters["set_legacy"] += 1
            return True

        original_read = hosts_module.safe_read_hosts_file
        original_write = hosts_module.safe_write_hosts_file
        original_get_remove = config_module.get_remove_github_api
        original_get_signature = reg_module.get_hosts_bootstrap_signature
        original_set_signature = reg_module.set_hosts_bootstrap_signature
        original_set_legacy = reg_module.set_hosts_bootstrap_v1_done

        try:
            hosts_module.safe_read_hosts_file = fake_read_hosts_file  # type: ignore[assignment]
            hosts_module.safe_write_hosts_file = fake_write_hosts_file  # type: ignore[assignment]
            config_module.get_remove_github_api = fake_get_remove_github_api  # type: ignore[assignment]
            reg_module.get_hosts_bootstrap_signature = fake_get_bootstrap_signature  # type: ignore[assignment]
            reg_module.set_hosts_bootstrap_signature = fake_set_bootstrap_signature  # type: ignore[assignment]
            reg_module.set_hosts_bootstrap_v1_done = fake_set_bootstrap_legacy  # type: ignore[assignment]

            hosts_module.HostsManager(status_callback=lambda _msg: None)
        finally:
            hosts_module.safe_read_hosts_file = original_read  # type: ignore[assignment]
            hosts_module.safe_write_hosts_file = original_write  # type: ignore[assignment]
            config_module.get_remove_github_api = original_get_remove  # type: ignore[assignment]
            reg_module.get_hosts_bootstrap_signature = original_get_signature  # type: ignore[assignment]
            reg_module.set_hosts_bootstrap_signature = original_set_signature  # type: ignore[assignment]
            reg_module.set_hosts_bootstrap_v1_done = original_set_legacy  # type: ignore[assignment]

        return {
            "written_contents": written_contents,
            "counters": counters,
            "signature": signature_state["value"],
            "set_signature_calls": set_signature_calls,
        }

    def test_first_launch_removes_github_and_adds_tracker(self):
        initial_content = (
            "127.0.0.1 localhost\n"
            "1.1.1.1 api.github.com\n"
            "2.2.2.2 keep.me\n"
        )

        result = self._run_bootstrap(initial_content=initial_content)

        self.assertEqual(result["counters"]["read"], 1)
        self.assertEqual(result["counters"]["write"], 1)
        self.assertEqual(result["counters"]["set_signature"], 1)
        self.assertEqual(result["counters"]["set_legacy"], 1)

        expected_signature = hosts_module._get_hosts_bootstrap_signature()
        self.assertEqual(result["signature"], expected_signature)
        self.assertEqual(result["set_signature_calls"], [expected_signature])

        output = result["written_contents"][0]
        self.assertNotIn("api.github.com", output.lower())
        self.assertIn("2.2.2.2 keep.me", output)
        self.assertIn("88.210.52.47 zapret-tracker.duckdns.org", output)

    def test_first_launch_does_not_duplicate_tracker(self):
        initial_content = (
            "127.0.0.1 localhost\n"
            "88.210.52.47 zapret-tracker.duckdns.org\n"
        )

        result = self._run_bootstrap(initial_content=initial_content)

        self.assertEqual(result["counters"]["read"], 1)
        self.assertEqual(result["counters"]["write"], 0)
        self.assertEqual(result["counters"]["set_signature"], 1)
        self.assertEqual(result["counters"]["set_legacy"], 1)

        expected_signature = hosts_module._get_hosts_bootstrap_signature()
        self.assertEqual(result["signature"], expected_signature)
        self.assertEqual(result["set_signature_calls"], [expected_signature])

    def test_first_launch_replaces_tracker_wrong_ip(self):
        initial_content = (
            "127.0.0.1 localhost\n"
            "0.0.0.0 zapret-tracker.duckdns.org\n"
        )

        result = self._run_bootstrap(initial_content=initial_content)

        self.assertEqual(result["counters"]["read"], 1)
        self.assertEqual(result["counters"]["write"], 1)
        output = result["written_contents"][0]
        self.assertNotIn("0.0.0.0 zapret-tracker.duckdns.org", output)
        self.assertIn("88.210.52.47 zapret-tracker.duckdns.org", output)

    def test_signature_change_replaces_old_tracker_domain(self):
        old_domain = "old-tracker.duckdns.org"
        old_signature = f"v2|{old_domain}|88.210.52.47"
        initial_content = (
            "127.0.0.1 localhost\n"
            f"88.210.52.47 {old_domain}\n"
        )

        result = self._run_bootstrap(initial_content=initial_content, initial_signature=old_signature)

        self.assertEqual(result["counters"]["read"], 1)
        self.assertEqual(result["counters"]["write"], 1)
        output = result["written_contents"][0]
        self.assertNotIn(old_domain, output)
        self.assertIn("88.210.52.47 zapret-tracker.duckdns.org", output)

    def test_skips_when_signature_already_applied(self):
        expected_signature = hosts_module._get_hosts_bootstrap_signature()

        result = self._run_bootstrap(
            initial_content="127.0.0.1 localhost\n",
            initial_signature=expected_signature,
        )

        self.assertEqual(result["counters"]["read"], 0)
        self.assertEqual(result["counters"]["write"], 0)
        self.assertEqual(result["counters"]["set_signature"], 0)
        self.assertEqual(result["counters"]["set_legacy"], 0)


if __name__ == "__main__":
    unittest.main()
