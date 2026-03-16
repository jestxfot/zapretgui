import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create spec for {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class PresetParserCustomStrategyDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        log_stub = types.ModuleType("log")
        log_stub.log = lambda *_a, **_kw: None
        sys.modules["log"] = log_stub

        repo_root = Path(__file__).resolve().parents[1]
        pkg_dir = repo_root / "preset_zapret2"

        pkg = types.ModuleType("preset_zapret2")
        pkg.__path__ = [str(pkg_dir)]
        sys.modules["preset_zapret2"] = pkg

        _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
        cls.parser = _load_module("preset_zapret2.txt_preset_parser", pkg_dir / "txt_preset_parser.py")

    def test_first_block_can_start_with_hostlist_before_filter(self):
        content = "\n".join(
            [
                "# Preset: Test",
                "# ActivePreset: Test",
                "",
                "--lua-init=@lua/zapret-lib.lua",
                "",
                "--hostlist=lists/youtube.txt",
                "--filter-tcp=80,443",
                "--lua-desync=multisplit:pos=2",
            ]
        )

        data = self.parser.parse_preset_content(content)

        self.assertEqual(len(data.categories), 1)
        self.assertIn("--lua-init=@lua/zapret-lib.lua", data.base_args)
        self.assertNotIn("--hostlist=lists/youtube.txt", data.base_args)
        self.assertIn("--hostlist=lists/youtube.txt", data.categories[0].args)
        self.assertIn("--lua-desync=multisplit:pos=2", data.categories[0].strategy_args)

    def test_inline_filter_hostlist_and_lua_keeps_lua_strategy(self):
        block_args = "--filter-tcp=443 --hostlist=lists/youtube.txt --lua-desync=multisplit:pos=2,midsld-2"

        extracted = self.parser.extract_strategy_args(block_args)

        self.assertEqual(extracted, "--lua-desync=multisplit:pos=2,midsld-2")

    def test_first_block_can_start_with_ipset_before_filter(self):
        content = "\n".join(
            [
                "# Preset: Test",
                "# ActivePreset: Test",
                "",
                "--lua-init=@lua/zapret-lib.lua",
                "",
                "--ipset=lists/ipset-youtube.txt",
                "--filter-udp=443",
                "--lua-desync=fake:blob=quic1",
            ]
        )

        data = self.parser.parse_preset_content(content)

        self.assertEqual(len(data.categories), 1)
        self.assertNotIn("--ipset=lists/ipset-youtube.txt", data.base_args)
        self.assertIn("--ipset=lists/ipset-youtube.txt", data.categories[0].args)
        self.assertIn("--lua-desync=fake:blob=quic1", data.categories[0].strategy_args)

    def test_single_block_with_many_lists_maps_to_many_categories(self):
        content = "\n".join(
            [
                "# Preset: Test",
                "# ActivePreset: Test",
                "",
                "--filter-tcp=80,443",
                "--hostlist=lists/youtube.txt",
                "--hostlist=lists/discord.txt",
                "--ipset=lists/ipset-twitter.txt",
                "--lua-desync=multisplit:pos=2",
            ]
        )

        data = self.parser.parse_preset_content(content)

        cats = {block.category for block in data.categories}
        self.assertIn("youtube", cats)
        self.assertTrue(any(key in cats for key in ("discord_tcp", "discord")))
        self.assertTrue(any(key in cats for key in ("twitter_tcp", "twitter")))
        for block in data.categories:
            self.assertIn("--lua-desync=multisplit:pos=2", block.strategy_args)

if __name__ == "__main__":
    unittest.main()
