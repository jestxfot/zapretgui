import importlib.util
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


class PresetDropsUnknownPlaceholdersTests(unittest.TestCase):
    def setUp(self):
        # Stub out `log` import to avoid Qt deps in headless test env.
        log_stub = types.ModuleType("log")
        log_stub.log = lambda *_a, **_kw: None
        sys.modules["log"] = log_stub

        self.repo_root = Path(__file__).resolve().parents[1]
        self.pkg_dir = self.repo_root / "preset_zapret2"

        # Create a stub package so relative imports work without importing
        # `preset_zapret2/__init__.py` (which imports GUI deps).
        pkg = types.ModuleType("preset_zapret2")
        pkg.__path__ = [str(self.pkg_dir)]
        sys.modules["preset_zapret2"] = pkg

        self.parser = _load_module("preset_zapret2.txt_preset_parser", self.pkg_dir / "txt_preset_parser.py")

    def test_drops_whole_category_if_hostlist_unknown_txt_present(self):
        data = self.parser.PresetData(name="Test", active_preset="Test", base_args="")

        data.categories.append(
            self.parser.CategoryBlock(
                category="keepme",
                protocol="tcp",
                filter_mode="hostlist",
                filter_file="lists/keepme.txt",
                port="443",
                args="--filter-tcp=443\n--hostlist=lists/keepme.txt\n--lua-desync=KEEP",
            )
        )

        # Bad category: TCP block references placeholder unknown.txt.
        data.categories.append(
            self.parser.CategoryBlock(
                category="badcat",
                protocol="tcp",
                filter_mode="hostlist",
                filter_file="lists/unknown.txt",
                port="80,443",
                args="--filter-tcp=80,443\n--hostlist=lists/unknown.txt\n--lua-desync=BAD_TCP_MARKER",
            )
        )
        # Even if the UDP block doesn't reference unknown.txt, it must be dropped too.
        data.categories.append(
            self.parser.CategoryBlock(
                category="badcat",
                protocol="udp",
                filter_mode="hostlist",
                filter_file="lists/badcat.txt",
                port="443",
                args="--filter-udp=443\n--hostlist=lists/badcat.txt\n--lua-desync=BAD_UDP_MARKER",
            )
        )

        out = self.parser.generate_preset_content(data, include_header=False)
        out_l = out.lower()

        self.assertIn("keepme.txt", out_l)
        self.assertNotIn("unknown.txt", out_l)
        self.assertNotIn("bad_tcp_marker".lower(), out_l)
        self.assertNotIn("bad_udp_marker".lower(), out_l)

    def test_drops_whole_category_if_ipset_unknown_present(self):
        data = self.parser.PresetData(name="Test", active_preset="Test", base_args="")

        data.categories.append(
            self.parser.CategoryBlock(
                category="badipset",
                protocol="tcp",
                filter_mode="ipset",
                filter_file="lists/ipset-unknown.txt",
                port="443",
                args="--filter-tcp=443\n--ipset=lists/ipset-unknown.txt\n--lua-desync=BAD_IPSET_MARKER",
            )
        )

        out = self.parser.generate_preset_content(data, include_header=False)
        out_l = out.lower()

        self.assertNotIn("ipset-unknown.txt", out_l)
        self.assertNotIn("bad_ipset_marker".lower(), out_l)


if __name__ == "__main__":
    unittest.main()

