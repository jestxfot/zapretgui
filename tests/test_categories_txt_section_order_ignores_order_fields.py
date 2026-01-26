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


class CategoriesTxtSectionOrderTests(unittest.TestCase):
    def test_section_order_is_used_even_if_order_fields_exist(self):
        # Stub out `log` import to avoid Qt deps in headless test env.
        log_stub = types.ModuleType("log")
        log_stub.log = lambda *_a, **_kw: None
        sys.modules["log"] = log_stub

        # Stub `config` and `strategy_menu.user_categories_store` required at import time.
        config_stub = types.ModuleType("config")
        config_stub.INDEXJSON_FOLDER = "."
        sys.modules["config"] = config_stub

        strategy_menu_pkg = types.ModuleType("strategy_menu")
        strategy_menu_pkg.__path__ = []
        sys.modules["strategy_menu"] = strategy_menu_pkg

        user_store_stub = types.ModuleType("strategy_menu.user_categories_store")
        user_store_stub.get_user_categories_file_path = lambda: Path("does-not-exist")
        sys.modules["strategy_menu.user_categories_store"] = user_store_stub

        repo_root = Path(__file__).resolve().parents[1]
        loader = _load_module("strategy_menu.strategy_loader", repo_root / "strategy_menu" / "strategy_loader.py")

        parsed = loader.load_categories_txt_text(
            "version = 1.0\n\n"
            "[b]\n"
            "order = 999\n"
            "command_order = 999\n"
            "\n"
            "[a]\n"
            "order = 1\n"
            "command_order = 1\n",
            source_name="test",
        )
        self.assertIsNotNone(parsed)
        cats = parsed["categories"]
        self.assertEqual([c["key"] for c in cats], ["b", "a"])
        self.assertEqual([c["order"] for c in cats], [1, 2])
        self.assertEqual([c["command_order"] for c in cats], [1, 2])


if __name__ == "__main__":
    unittest.main()

