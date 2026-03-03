import tempfile
import unittest
from pathlib import Path
import socket
from unittest.mock import patch

from blockcheck.strategy_scanner import StrategyScanner


class StrategyScannerUdpSupportTests(unittest.TestCase):
    def test_load_catalog_strategies_uses_discord_voice_for_stun_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ), patch(
            "preset_zapret2.catalog.load_strategies",
            return_value={
                "udp_demo": {
                    "name": "UDP Demo",
                    "args": "--payload=all",
                }
            },
        ) as load_mock:
            scanner = StrategyScanner(target="stun.l.google.com:19302", scan_protocol="stun_voice")
            strategies = scanner._load_catalog_strategies()

        load_mock.assert_called_once_with("discord_voice", "basic")
        self.assertEqual(len(strategies), 1)
        self.assertEqual(strategies[0]["id"], "udp_demo")

    def test_load_catalog_strategies_uses_udp_for_games_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ), patch(
            "preset_zapret2.catalog.load_strategies",
            return_value={"udp_demo": {"name": "UDP Demo", "args": "--payload=all"}},
        ) as load_mock:
            scanner = StrategyScanner(target="stun.cloudflare.com:3478", scan_protocol="udp_games")
            _ = scanner._load_catalog_strategies()

        load_mock.assert_called_once_with("udp", "basic")

    def test_stun_voice_mode_temp_preset_uses_l7_filters(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.l.google.com:19302", scan_protocol="stun_voice")
            preset_path = scanner._write_temp_preset("--payload=all", "stun.l.google.com")

            content = Path(preset_path).read_text(encoding="utf-8")

        self.assertIn("--wf-udp-out=443-65535", content)
        self.assertIn("--filter-l7=stun,discord", content)
        self.assertIn("--payload=stun,discord_ip_discovery", content)
        self.assertNotIn("--filter-tcp=443", content)
        self.assertNotIn("--hostlist=", content)

    def test_udp_games_mode_temp_preset_uses_games_ipset_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ), patch.object(
            StrategyScanner,
            "_build_games_ipset_temp_file",
            return_value=r"C:\Users\Privacy\AppData\Roaming\ZapretTwoDev\lists\ipset-games-udp-autogen.txt",
        ):
            scanner = StrategyScanner(target="stun.cloudflare.com:3478", scan_protocol="udp_games")
            preset_path = scanner._write_temp_preset("--payload=all", "ignored")

            content = Path(preset_path).read_text(encoding="utf-8")

        self.assertIn("--wf-udp-out=443,50000-65535", content)
        self.assertIn("--filter-udp=443,50000-65535", content)
        self.assertIn(r"--ipset=C:\Users\Privacy\AppData\Roaming\ZapretTwoDev\lists\ipset-games-udp-autogen.txt", content)

    def test_resolve_games_ipset_sources_finds_multiple_game_lists(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.cloudflare.com:3478", scan_protocol="udp_games")

            lists_dir = Path(temp_dir) / "lists"
            lists_dir.mkdir(parents=True, exist_ok=True)
            (lists_dir / "ipset-roblox.txt").write_text("1.1.1.0/24\n", encoding="utf-8")
            (lists_dir / "ipset-amazon.txt").write_text("2.2.2.0/24\n", encoding="utf-8")

            sources = scanner._resolve_games_ipset_sources()

        self.assertTrue(any(path.endswith("ipset-roblox.txt") for path in sources))
        self.assertTrue(any(path.endswith("ipset-amazon.txt") for path in sources))

    def test_games_only_scope_skips_unrelated_ipset_files(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(
                target="stun.cloudflare.com:3478",
                scan_protocol="udp_games",
                udp_games_scope="games_only",
            )

            lists_dir = Path(temp_dir) / "lists"
            lists_dir.mkdir(parents=True, exist_ok=True)
            (lists_dir / "ipset-roblox.txt").write_text("1.1.1.0/24\n", encoding="utf-8")
            (lists_dir / "ipset-googlevideo.txt").write_text("3.3.3.0/24\n", encoding="utf-8")

            sources = scanner._resolve_games_ipset_sources()

        self.assertTrue(any(path.endswith("ipset-roblox.txt") for path in sources))
        self.assertFalse(any(path.endswith("ipset-googlevideo.txt") for path in sources))

    def test_all_scope_includes_unrelated_ipset_files(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(
                target="stun.cloudflare.com:3478",
                scan_protocol="udp_games",
                udp_games_scope="all",
            )

            lists_dir = Path(temp_dir) / "lists"
            lists_dir.mkdir(parents=True, exist_ok=True)
            (lists_dir / "ipset-roblox.txt").write_text("1.1.1.0/24\n", encoding="utf-8")
            (lists_dir / "ipset-googlevideo.txt").write_text("3.3.3.0/24\n", encoding="utf-8")

            sources = scanner._resolve_games_ipset_sources()

        self.assertTrue(any(path.endswith("ipset-roblox.txt") for path in sources))
        self.assertTrue(any(path.endswith("ipset-googlevideo.txt") for path in sources))

    def test_build_games_ipset_file_adds_probe_target_ip(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.cloudflare.com:3478", scan_protocol="udp_games")

            lists_dir = Path(temp_dir) / "lists"
            lists_dir.mkdir(parents=True, exist_ok=True)
            (lists_dir / "ipset-roblox.txt").write_text("1.1.1.0/24\n", encoding="utf-8")

            with patch(
                "blockcheck.strategy_scanner.socket.getaddrinfo",
                return_value=[
                    (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("9.9.9.9", 3478)),
                ],
            ):
                path = scanner._build_games_ipset_temp_file()

            content = Path(path).read_text(encoding="utf-8")

        self.assertIn("1.1.1.0/24", content)
        self.assertIn("9.9.9.9", content)

    def test_stun_target_parser_handles_ipv6_brackets(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="[2001:db8::10]:5349", scan_protocol="stun_voice")

        self.assertEqual(scanner._target_host, "2001:db8::10")
        self.assertEqual(scanner._target_port, 5349)
        self.assertEqual(scanner._target, "[2001:db8::10]:5349")

    def test_legacy_udp_stun_alias_maps_to_stun_voice_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.l.google.com:19302", scan_protocol="udp_stun")

        self.assertEqual(scanner._scan_protocol, "stun_voice")

    def test_stun_voice_pool_requires_primary_probe_success(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.l.google.com:19302", scan_protocol="stun_voice")

        pool = [
            {
                "name": "Primary target",
                "kind": "stun",
                "host": "stun.l.google.com",
                "port": 19302,
                "required": True,
            },
            {
                "name": "Canary",
                "kind": "stun",
                "host": "stun.cloudflare.com",
                "port": 3478,
                "required": False,
            },
        ]

        def fake_probe(probe, _af):
            if probe["name"] == "Primary target":
                return False, 12.0, "primary fail"
            return True, 8.0, "ok"

        with patch.object(scanner, "_build_udp_probe_pool", return_value=pool), patch.object(
            scanner,
            "_run_udp_probe_target",
            side_effect=fake_probe,
        ):
            ok, _time_ms, detail, probes = scanner._test_udp_probe_pool(socket.AF_INET)

        self.assertFalse(ok)
        self.assertIn("Primary target", detail)
        self.assertEqual(len(probes), 2)

    def test_udp_games_pool_succeeds_if_any_canary_succeeds(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            StrategyScanner,
            "_find_work_dir",
            return_value=temp_dir,
        ), patch.object(
            StrategyScanner,
            "_find_winws2",
            return_value=str(Path(temp_dir) / "winws2.exe"),
        ):
            scanner = StrategyScanner(target="stun.cloudflare.com:3478", scan_protocol="udp_games")

        pool = [
            {
                "name": "Primary target",
                "kind": "stun",
                "host": "stun.cloudflare.com",
                "port": 3478,
                "required": False,
            },
            {
                "name": "Rust A2S",
                "kind": "source_a2s",
                "host": "205.178.168.170",
                "port": 28015,
                "required": False,
            },
        ]

        def fake_probe(probe, _af):
            if probe["name"] == "Rust A2S":
                return True, 20.0, "A2S reply"
            return False, 30.0, "timeout"

        with patch.object(scanner, "_build_udp_probe_pool", return_value=pool), patch.object(
            scanner,
            "_run_udp_probe_target",
            side_effect=fake_probe,
        ):
            ok, time_ms, detail, probes = scanner._test_udp_probe_pool(socket.AF_INET)

        self.assertTrue(ok)
        self.assertEqual(time_ms, 20.0)
        self.assertIn("pool OK", detail)
        self.assertEqual(len(probes), 2)


if __name__ == "__main__":
    unittest.main()
