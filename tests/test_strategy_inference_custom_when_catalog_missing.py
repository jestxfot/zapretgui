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


class StrategyInferenceCustomWhenCatalogMissingTests(unittest.TestCase):
    def test_non_empty_args_become_custom_if_catalog_missing(self):
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
                # Ensure the test is deterministic even if a real catalog exists on disk.
                catalog._candidate_indexjson_dirs = lambda: [Path(indexjson)]

                inference = _load_module("preset_zapret2.strategy_inference", pkg_dir / "strategy_inference.py")

                self.assertEqual(inference.infer_strategy_id_from_args("youtube", "", "tcp"), "none")
                self.assertEqual(inference.infer_strategy_id_from_args("youtube", "--lua-desync=pass", "tcp"), "custom")
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index


if __name__ == "__main__":
    unittest.main()

