import importlib.util
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "utils" / "circular_strategy_numbering.py"
    spec = importlib.util.spec_from_file_location("circular_strategy_numbering", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()
renumber_circular_strategies = _module.renumber_circular_strategies
strip_strategy_tags = _module.strip_strategy_tags


def test_renumber_circular_and_payload_groups():
    source = "\n".join(
        [
            "--lua-desync=circular_quality:key=tls",
            "--lua-desync=pass",
            "--lua-desync=send:repeats=2 --lua-desync=syndata:blob=tls7",
            "--payload=tls_client_hello",
            "--lua-desync=fake:blob=tls_google",
            "--new",
            "--lua-desync=circular:fails=1",
            "--lua-desync=pass",
        ]
    )

    numbered = renumber_circular_strategies(source)

    assert "--lua-desync=circular_quality:key=tls" in numbered
    assert "--lua-desync=pass:strategy=1" in numbered
    assert "--lua-desync=send:repeats=2:strategy=2 --lua-desync=syndata:blob=tls7:strategy=2" in numbered
    assert "--payload=tls_client_hello" in numbered
    assert "--lua-desync=fake:blob=tls_google:strategy=1" in numbered
    assert "--lua-desync=circular:fails=1" in numbered


def test_strip_strategy_tags_removes_all_legacy_tags():
    source = "--lua-desync=pass:strategy=3\n--lua-desync=fake:blob=tls7:strategy=12"
    cleaned = strip_strategy_tags(source)
    assert ":strategy=" not in cleaned
    assert cleaned == "--lua-desync=pass\n--lua-desync=fake:blob=tls7"
