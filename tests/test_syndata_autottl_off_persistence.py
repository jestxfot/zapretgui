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


class SyndataAutoTTLOffPersistenceTests(unittest.TestCase):
    def test_missing_ip_autottl_is_treated_as_off(self):
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

        parser = _load_module("preset_zapret2.txt_preset_parser", pkg_dir / "txt_preset_parser.py")

        args = "--lua-desync=syndata:blob=tls_google:tls_mod=none"
        out = parser.extract_syndata_from_args(args)

        self.assertTrue(out.get("enabled"))
        self.assertEqual(out.get("autottl_delta"), 0)


if __name__ == "__main__":
    unittest.main()

