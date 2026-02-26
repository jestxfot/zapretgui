import importlib.util
import sys
import types
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create spec for {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_repo_root = Path(__file__).resolve().parents[1]
_pkg_dir = _repo_root / "preset_orchestra_zapret2"
_pkg = types.ModuleType("preset_orchestra_zapret2")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules["preset_orchestra_zapret2"] = _pkg

_inference = _load_module(
    "preset_orchestra_zapret2.strategy_inference",
    _pkg_dir / "strategy_inference.py",
)
_parser = _load_module(
    "preset_orchestra_zapret2.txt_preset_parser",
    _pkg_dir / "txt_preset_parser.py",
)

normalize_args = _inference.normalize_args
extract_strategy_args = _parser.extract_strategy_args


def test_normalize_args_ignores_strategy_tags():
    with_tags = "\n".join(
        [
            "--lua-desync=pass:strategy=1",
            "--lua-desync=fake:blob=tls7:strategy=2",
        ]
    )
    without_tags = "\n".join(
        [
            "--lua-desync=fake:blob=tls7",
            "--lua-desync=pass",
        ]
    )

    assert normalize_args(with_tags) == normalize_args(without_tags)


def test_extract_strategy_args_removes_strategy_tags():
    block_args = "\n".join(
        [
            "--filter-tcp=443",
            "--lua-desync=pass:strategy=1",
            "--lua-desync=fake:blob=tls7:strategy=2",
        ]
    )

    extracted = extract_strategy_args(block_args)
    assert ":strategy=" not in extracted
    assert "--lua-desync=pass" in extracted
    assert "--lua-desync=fake:blob=tls7" in extracted
