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


class PresetOrderFollowsCategoriesFileOrderTests(unittest.TestCase):
    def test_generated_preset_follows_categories_txt_section_order_when_no_order_fields(self):
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

            # No `order`/`command_order`: must preserve section order [b] then [a].
            (builtin_dir / "categories.txt").write_text(
                "version = 1.0\n\n"
                "[b]\n"
                "order = 999\n"
                "command_order = 999\n"
                "base_filter = --filter-tcp=443\n\n"
                "[a]\n"
                "order = 1\n"
                "command_order = 1\n"
                "base_filter = --filter-tcp=443\n",
                encoding="utf-8",
            )

            prev_index = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            try:
                _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
                parser = _load_module("preset_zapret2.txt_preset_parser", pkg_dir / "txt_preset_parser.py")

                data = parser.PresetData(name="Test", active_preset="Test", base_args="")

                # Add categories in reverse of file order; generator must reorder.
                data.categories.append(
                    parser.CategoryBlock(
                        category="a",
                        protocol="tcp",
                        filter_mode="base",
                        filter_file="",
                        port="443",
                        args="--filter-tcp=443\n--lua-desync=first",
                    )
                )
                data.categories.append(
                    parser.CategoryBlock(
                        category="b",
                        protocol="tcp",
                        filter_mode="base",
                        filter_file="",
                        port="443",
                        args="--filter-tcp=443\n--lua-desync=second",
                    )
                )

                out = parser.generate_preset_content(data, include_header=False)
                blocks = [b.strip() for b in out.split("\n--new\n") if b.strip()]
                self.assertGreaterEqual(len(blocks), 2)
                self.assertIn("--lua-desync=second", blocks[0])
                self.assertIn("--lua-desync=first", blocks[1])
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index


if __name__ == "__main__":
    unittest.main()
