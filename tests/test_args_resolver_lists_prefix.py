import importlib.util
import os
import sys
import tempfile
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


repo_root = Path(__file__).resolve().parents[1]
args_resolver = _load_module("args_resolver", repo_root / "utils" / "args_resolver.py")
resolve_args_paths = args_resolver.resolve_args_paths


class ArgsResolverListsPrefixTests(unittest.TestCase):
    def test_resolves_bare_hostlist_into_lists_dir(self):
        with tempfile.TemporaryDirectory() as td:
            lists_dir = os.path.join(td, "lists")
            bin_dir = os.path.join(td, "bin")
            os.makedirs(lists_dir, exist_ok=True)
            os.makedirs(bin_dir, exist_ok=True)

            result = resolve_args_paths(["--hostlist=youtube.txt"], lists_dir, bin_dir)

            self.assertEqual(len(result), 1)
            _, value = result[0].split("=", 1)
            self.assertEqual(os.path.normpath(value), os.path.normpath(os.path.join(lists_dir, "youtube.txt")))

    def test_does_not_duplicate_lists_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            lists_dir = os.path.join(td, "lists")
            bin_dir = os.path.join(td, "bin")
            os.makedirs(lists_dir, exist_ok=True)
            os.makedirs(bin_dir, exist_ok=True)

            result = resolve_args_paths(["--hostlist=lists/discord.txt"], lists_dir, bin_dir)

            self.assertEqual(len(result), 1)
            _, value = result[0].split("=", 1)
            self.assertEqual(os.path.normpath(value), os.path.normpath(os.path.join(lists_dir, "discord.txt")))


if __name__ == "__main__":
    unittest.main()
