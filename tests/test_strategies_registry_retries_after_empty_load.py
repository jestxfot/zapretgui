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


class StrategiesRegistryRetriesAfterEmptyLoadTests(unittest.TestCase):
    def test_lazy_import_retries_after_empty_result(self):
        repo_root = Path(__file__).resolve().parents[1]
        pkg_dir = repo_root / "strategy_menu"

        # Create a stub package to avoid importing strategy_menu/__init__.py
        # (it depends on Windows winreg).
        pkg = types.ModuleType("strategy_menu")
        pkg.__path__ = [str(pkg_dir)]
        pkg.get_strategy_launch_method = lambda: "direct_zapret2"
        sys.modules["strategy_menu"] = pkg

        registry_mod = _load_module(
            "strategy_menu.strategies_registry",
            pkg_dir / "strategies_registry.py",
        )

        calls = {"n": 0}

        def fake_load(strategy_type: str, strategy_set=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return {}
            return {"s1": {"name": "s1", "args": "--x"}}

        registry_mod._strategies_cache.clear()
        registry_mod._imported_types.clear()
        registry_mod._failed_import_last_attempt_at.clear()
        registry_mod._failed_import_logged.clear()
        registry_mod._FAILED_IMPORT_RETRY_SECONDS = 0.0
        registry_mod._load_strategies_from_json = fake_load

        self.assertEqual(registry_mod._lazy_import_base_strategies("tcp"), {})
        self.assertIn("s1", registry_mod._lazy_import_base_strategies("tcp"))
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()

