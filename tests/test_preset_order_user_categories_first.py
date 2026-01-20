import importlib.util
import os
import sys
import tempfile
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


class PresetOrderUserCategoriesFirstTests(unittest.TestCase):
    def test_user_categories_come_first_in_generated_preset(self):
        # Stub out `log` import to avoid Qt deps in headless test env.
        log_stub = types.ModuleType("log")
        log_stub.log = lambda *_a, **_kw: None
        sys.modules["log"] = log_stub

        repo_root = Path(__file__).resolve().parents[1]
        pkg_dir = repo_root / "preset_zapret2"

        # Create a stub package so relative imports work without importing
        # `preset_zapret2/__init__.py` (which imports GUI deps).
        pkg = types.ModuleType("preset_zapret2")
        pkg.__path__ = [str(pkg_dir)]
        sys.modules["preset_zapret2"] = pkg

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            indexjson = tmp_path / "json"
            builtin_dir = indexjson / "strategies" / "builtin"
            builtin_dir.mkdir(parents=True, exist_ok=True)

            # Minimal builtin categories so sorting can treat youtube as "known".
            (builtin_dir / "categories.txt").write_text(
                "version = 1.0\n\n"
                "[youtube]\n"
                "order = 10\n"
                "command_order = 10\n"
                "base_filter_hostlist = --filter-tcp=443 --hostlist=lists/youtube.txt\n",
                encoding="utf-8",
            )

            # User categories in APPDATA
            appdata = tmp_path / "appdata"
            user_file = appdata / "zapret" / "user_categories.txt"
            user_file.parent.mkdir(parents=True, exist_ok=True)
            user_file.write_text(
                "# User categories configuration\n"
                "version = 1.0\n\n"
                "[user_category_1]\n"
                "full_name = 234\n"
                "base_filter = --filter-tcp=443 --hostlist-domains=meduza.io\n",
                encoding="utf-8",
            )

            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            os.environ["APPDATA"] = str(appdata)

            _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
            parser = _load_module("preset_zapret2.txt_preset_parser", pkg_dir / "txt_preset_parser.py")

            data = parser.PresetData(name="Test", active_preset="Test", base_args="")

            # Intentionally add system category first; generator must reorder.
            data.categories.append(
                parser.CategoryBlock(
                    category="youtube",
                    protocol="tcp",
                    filter_mode="hostlist",
                    filter_file="lists/youtube.txt",
                    port="443",
                    args="--filter-tcp=443\n--hostlist=lists/youtube.txt\n--lua-desync=multisplit",
                )
            )
            data.categories.append(
                parser.CategoryBlock(
                    category="user_category_1",
                    protocol="tcp",
                    filter_mode="hostlist",
                    filter_file="meduza.io",
                    port="443",
                    args="--filter-tcp=443\n--hostlist-domains=meduza.io\n--lua-desync=pass",
                )
            )

            out = parser.generate_preset_content(data, include_header=False)
            blocks = [b.strip() for b in out.split("\n--new\n") if b.strip()]
            self.assertGreaterEqual(len(blocks), 2)
            self.assertIn("meduza.io", blocks[0])
            self.assertIn("youtube", blocks[1])


if __name__ == "__main__":
    unittest.main()

