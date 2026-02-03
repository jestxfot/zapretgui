"""
ci_build.py - Headless CI build (Nuitka onedir -> folder artifact).

Пример:
  python -m build_zapret.ci_build --out artifact
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from utils.proxy_env import apply_zapret_proxy_env
except Exception:
    apply_zapret_proxy_env = None  # type: ignore

from .nuitka_builder import run_nuitka
from .write_build_info import write_build_info


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "main.py").exists() and (p / "config").is_dir():
            return p
    raise FileNotFoundError("main.py not found; fix find_project_root()")


def run(cmd: list[str], *, capture: bool = False) -> str | None:
    shown = " ".join(str(c) for c in cmd)
    print(f"> {shown}", flush=True)
    res = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return res.stdout if capture else None


def main() -> int:
    if apply_zapret_proxy_env is not None:
        try:
            apply_zapret_proxy_env()
        except Exception:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["stable", "test"])
    parser.add_argument("--version")
    parser.add_argument("--out", default="artifact", help="Output directory for onedir build")
    args = parser.parse_args()

    root = find_project_root(Path(__file__).resolve())
    python_exe = sys.executable.replace("pythonw.exe", "python.exe")

    if args.channel is None or args.version is None:
        from config.build_info import CHANNEL as DEFAULT_CHANNEL, APP_VERSION as DEFAULT_VERSION

        args.channel = args.channel or DEFAULT_CHANNEL
        args.version = args.version or DEFAULT_VERSION

    print(f"ROOT={root}")
    print(f"PY={python_exe}")
    print(f"CHANNEL={args.channel}")
    print(f"VERSION={args.version}")

    # Если явно задали channel/version — синхронизируем build_info.py
    if "--channel" in sys.argv or "--version" in sys.argv:
        write_build_info(args.channel, args.version)

    out_dir = (root / args.out).resolve()
    produced = run_nuitka(
        args.channel,
        args.version,
        root,
        python_exe,
        run_func=lambda c, **kw: run(list(c), capture=bool(kw.get("capture"))),
        target_dir=out_dir,
    )
    if not produced.exists():
        raise FileNotFoundError(f"Zapret.exe not found at {produced}")

    print(f"OK: {produced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
