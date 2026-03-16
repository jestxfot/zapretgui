import importlib.util
import os
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create spec for {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_min_categories(categories_file: Path) -> None:
    categories_file.write_text(
        "\n".join(
            [
                "version = 1.0",
                "",
                "[youtube]",
                "base_filter_hostlist = --filter-tcp=80,443 --hostlist=youtube.txt",
                "protocol = TCP",
                "",
                "[discord_tcp]",
                "base_filter_hostlist = --filter-tcp=80,443 --hostlist=discord.txt",
                "protocol = TCP",
                "",
                "[twitter_tcp]",
                "base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-twitter.txt",
                "protocol = TCP",
                "",
                "[twitch_tcp]",
                "base_filter_hostlist = --filter-tcp=443 --hostlist=twitch.txt",
                "protocol = TCP",
            ]
        ),
        encoding="utf-8",
    )


class PresetParserListAliasCanonicalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        log_stub = types.ModuleType("log")
        log_stub.log = lambda *_a, **_kw: None
        sys.modules["log"] = log_stub
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.pkg_dir = cls.repo_root / "preset_zapret2"

    def _load_parser_with_indexjson(self):
        package_name = f"preset_zapret2_alias_test_{uuid.uuid4().hex}"
        pkg = types.ModuleType(package_name)
        pkg.__path__ = [str(self.pkg_dir)]
        sys.modules[package_name] = pkg

        _load_module(f"{package_name}.catalog", self.pkg_dir / "catalog.py")
        return _load_module(
            f"{package_name}.txt_preset_parser",
            self.pkg_dir / "txt_preset_parser.py",
        )

    def test_list_aliases_map_to_canonical_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            indexjson = tmp_path / "json"
            builtin_dir = indexjson / "strategies" / "builtin"
            builtin_dir.mkdir(parents=True, exist_ok=True)
            _write_min_categories(builtin_dir / "categories.txt")

            prev_index = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            try:
                parser = self._load_parser_with_indexjson()
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

                data = parser.parse_preset_content(content)
                cats = {block.category for block in data.categories}
                self.assertIn("youtube", cats)
                self.assertIn("discord_tcp", cats)
                self.assertIn("twitter_tcp", cats)
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index

    def test_twitch_alias_maps_to_twitch_tcp_even_with_broader_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            indexjson = tmp_path / "json"
            builtin_dir = indexjson / "strategies" / "builtin"
            builtin_dir.mkdir(parents=True, exist_ok=True)
            _write_min_categories(builtin_dir / "categories.txt")

            prev_index = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            try:
                parser = self._load_parser_with_indexjson()
                content = "\n".join(
                    [
                        "# Preset: Test",
                        "# ActivePreset: Test",
                        "",
                        "--filter-tcp=80,443",
                        "--hostlist=lists/twitch.txt",
                        "--lua-desync=pass",
                    ]
                )

                data = parser.parse_preset_content(content)
                self.assertEqual(len(data.categories), 1)
                self.assertEqual(data.categories[0].category, "twitch_tcp")
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index


if __name__ == "__main__":
    unittest.main()
