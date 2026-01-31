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


class HostlistDomainsInferenceTests(unittest.TestCase):
    def test_user_category_hostlist_domains_is_inferred(self):
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

            # Minimal builtin categories so catalog paths resolve.
            (builtin_dir / "categories.txt").write_text(
                "version = 1.0\n\n[dummy]\nbase_filter = --filter-tcp=443 --hostlist-domains=dummy.example\n",
                encoding="utf-8",
            )

            # User categories in APPDATA
            appdata = tmp_path / "appdata"
            user_file = appdata / "zapret" / "user_categories.txt"
            user_file.parent.mkdir(parents=True, exist_ok=True)
            user_file.write_text(
                "# User categories configuration\n"
                "version = 1.0\n"
                "description = test\n\n"
                "[user_category_1]\n"
                "full_name = 234\n"
                "base_filter = --filter-tcp=443 --hostlist-domains=meduza.io\n",
                encoding="utf-8",
            )

            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            os.environ["APPDATA"] = str(appdata)

            # Load modules under the stub package.
            _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
            parser = _load_module("preset_zapret2.txt_preset_parser", pkg_dir / "txt_preset_parser.py")

            args = "\n".join(
                [
                    "--filter-tcp=443",
                    "--hostlist-domains=meduza.io",
                    "--out-range=-n8",
                    "--lua-desync=pass",
                ]
            )
            key, mode = parser.infer_category_key_from_args(args)
            self.assertEqual(key, "user_category_1")
            self.assertIn(mode, ("base", "hostlist", "ipset"))

            data = parser.parse_preset_content(
                "# Preset: Test\n# ActivePreset: Test\n\n" + args + "\n"
            )
            self.assertEqual(len(data.categories), 1)
            self.assertEqual(data.categories[0].category, "user_category_1")


if __name__ == "__main__":
    unittest.main()

