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


class CatalogDoesNotCacheMissesTests(unittest.TestCase):
    def test_catalog_retries_when_json_dir_appears_later(self):
        repo_root = Path(__file__).resolve().parents[1]
        pkg_dir = repo_root / "preset_zapret2"

        pkg = types.ModuleType("preset_zapret2")
        pkg.__path__ = [str(pkg_dir)]
        sys.modules["preset_zapret2"] = pkg

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            indexjson = tmp_path / "json"

            prev_index = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            try:
                catalog = _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
                # Remove backoff so the test can check immediate retry deterministically.
                catalog._PATHS_MISS_BACKOFF_SECONDS = 0.0
                # Force the catalog to consider only this temp directory. On CI/dev
                # machines there may be a real catalog elsewhere on disk, which would
                # make the initial "miss" non-deterministic.
                catalog._candidate_indexjson_dirs = lambda: [Path(indexjson)]

                self.assertEqual(catalog.load_strategies("tcp"), {})

                builtin_dir = indexjson / "strategies" / "builtin"
                user_dir = indexjson / "strategies" / "user"
                builtin_dir.mkdir(parents=True, exist_ok=True)
                user_dir.mkdir(parents=True, exist_ok=True)

                (builtin_dir / "tcp.txt").write_text(
                    "[test]\n"
                    "name = test\n"
                    "--lua-desync=multisplit\n",
                    encoding="utf-8",
                )

                strategies = catalog.load_strategies("tcp")
                self.assertIn("test", strategies)
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index


if __name__ == "__main__":
    unittest.main()
