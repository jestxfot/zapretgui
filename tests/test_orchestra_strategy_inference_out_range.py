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


class OrchestraStrategyInferenceOutRangeTests(unittest.TestCase):
    def test_infer_matches_when_preset_args_drop_out_range(self):
        repo_root = Path(__file__).resolve().parents[1]
        pkg_dir = repo_root / "preset_orchestra_zapret2"

        pkg = types.ModuleType("preset_orchestra_zapret2")
        pkg.__path__ = [str(pkg_dir)]
        sys.modules["preset_orchestra_zapret2"] = pkg

        catalog = _load_module("preset_orchestra_zapret2.catalog", pkg_dir / "catalog.py")
        inference = _load_module(
            "preset_orchestra_zapret2.strategy_inference",
            pkg_dir / "strategy_inference.py",
        )

        # Deterministic synthetic catalog: strategy has out-range + pass.
        catalog.load_categories = lambda: {
            "googlevideo_tcp": {"strategy_type": "tcp"}
        }
        catalog.load_strategies = lambda strategy_type, strategy_set=None: (
            {"default": {"args": "--out-range=-d1000\n--lua-desync=pass"}}
            if strategy_type == "tcp"
            else {}
        )

        # Simulates parser output where --out-range was removed from strategy_args.
        inferred = inference.infer_strategy_id_from_args(
            "googlevideo_tcp",
            "--lua-desync=pass",
            "tcp",
            strategy_set="orchestra",
        )
        self.assertEqual(inferred, "default")


if __name__ == "__main__":
    unittest.main()
