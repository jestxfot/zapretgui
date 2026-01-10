"""
ci_build.py - Headless build for GitHub Actions (Nuitka + Inno Setup).

Usage (PowerShell):
  # Use values from config/build_info.py
  python build_zapret/ci_build.py

  # Or override explicitly
  python build_zapret/ci_build.py --channel stable --version 1.2.3
  python build_zapret/ci_build.py --channel test --version 1.2.3
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from .nuitka_builder import run_nuitka
    from .write_build_info import write_build_info
except ImportError:  # pragma: no cover
    # Support running as a script: `python build_zapret/ci_build.py`
    from nuitka_builder import run_nuitka
    from write_build_info import write_build_info


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "main.py").exists() and (p / "config").is_dir():
            return p
    raise FileNotFoundError("main.py not found; fix find_project_root()")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    shown = " ".join(str(c) for c in cmd)
    print(f"> {shown}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["stable", "test"])
    parser.add_argument("--version")
    parser.add_argument(
        "--out",
        default="artifact",
        help="Output directory (will contain zapret.exe)",
    )
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

    # 1) Update build info only if explicitly overridden.
    # On CI push builds we usually want "as committed" values.
    if "--channel" in sys.argv or "--version" in sys.argv:
        write_build_info(args.channel, args.version)

    # 2) Build GUI executable via Nuitka (onedir). Output copied to ./<out>/
    out_dir = (root / args.out).resolve()
    produced = run_nuitka(
        args.channel,
        args.version,
        root,
        python_exe,
        run_func=lambda c, **_: run(list(c)),
        target_dir=out_dir,
    )
    if not produced.exists():
        raise FileNotFoundError(f"zapret.exe not found at {produced}")

    print(f"OK: {produced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
