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


class StrategyInferenceTcpFakeTests(unittest.TestCase):
    def test_tcp_fake_strategies_are_inferred(self):
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

            (builtin_dir / "categories.txt").write_text(
                "version = 1.0\n\n[testcat]\nstrategy_type = tcp\n",
                encoding="utf-8",
            )

            (builtin_dir / "tcp_fake.txt").write_text(
                "[hostfakesplit_multi]\n"
                "name = hostfakesplit_multi\n"
                "--lua-desync=hostfakesplit_multi:hosts=google.com,vimeo.com:tcp_ts=-1000:tcp_md5:repeats=2\n",
                encoding="utf-8",
            )

            prev_index = os.environ.get("ZAPRET_INDEXJSON_FOLDER")
            os.environ["ZAPRET_INDEXJSON_FOLDER"] = str(indexjson)
            try:
                _load_module("preset_zapret2.catalog", pkg_dir / "catalog.py")
                inference = _load_module("preset_zapret2.strategy_inference", pkg_dir / "strategy_inference.py")

                args = "--lua-desync=hostfakesplit_multi:hosts=google.com,vimeo.com:tcp_ts=-1000:tcp_md5:repeats=2"
                self.assertEqual(inference.infer_strategy_id_from_args("testcat", args, "tcp"), "hostfakesplit_multi")

                self.assertEqual(inference.infer_strategy_id_from_args("testcat", "--lua-desync=unknown", "tcp"), "custom")
            finally:
                if prev_index is None:
                    os.environ.pop("ZAPRET_INDEXJSON_FOLDER", None)
                else:
                    os.environ["ZAPRET_INDEXJSON_FOLDER"] = prev_index


if __name__ == "__main__":
    unittest.main()

