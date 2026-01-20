import unittest
import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create spec for {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


repo_root = Path(__file__).resolve().parents[1]
process_status = _load_module("process_status", repo_root / "utils" / "process_status.py")
format_expected_process_status = process_status.format_expected_process_status


class ProcessStatusFormattingTests(unittest.TestCase):
    def test_expected_running_shows_pid(self):
        s = format_expected_process_status("winws2.exe", {"winws2.exe": [12345]})
        self.assertIn("✅", s)
        self.assertIn("winws2.exe", s)
        self.assertIn("12345", s)

    def test_expected_not_running_but_other_running_mentions_other(self):
        s = format_expected_process_status("winws2.exe", {"winws.exe": [222]})
        self.assertIn("winws2.exe", s)
        self.assertIn("не запущен", s)
        self.assertIn("winws.exe", s)
        self.assertIn("222", s)

    def test_expected_not_running_no_other(self):
        s = format_expected_process_status("winws.exe", {})
        self.assertIn("winws.exe", s)
        self.assertIn("не запущен", s)


if __name__ == "__main__":
    unittest.main()
