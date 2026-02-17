from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Sequence


def _is_truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except Exception:
        try:
            print(text, file=sys.stderr)
        except Exception:
            pass


def _is_startup_debug_enabled(argv: Sequence[str]) -> bool:
    env_value = os.environ.get("ZAPRET_STARTUP_DEBUG")
    if env_value is not None and str(env_value).strip() != "":
        return _is_truthy(env_value)

    for arg in argv[1:]:
        if str(arg).strip().lower() in {"--startup-debug", "--verbose-log"}:
            return True

    return False


@dataclass(frozen=True)
class AppMetadata:
    app_version: str
    channel: str
    icon_path: Path
    icon_test_path: Path


def set_workdir_to_app(argv: Sequence[str]) -> Path:
    """Set current working directory to script/exe location."""
    try:
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).resolve().parent
        elif "__compiled__" in globals() and argv:
            app_dir = Path(str(argv[0])).resolve().parent
        else:
            app_dir = Path(__file__).resolve().parent.parent

        os.chdir(app_dir)

        if _is_startup_debug_enabled(argv):
            debug_lines = [
                "=== ZAPRET STARTUP DEBUG ===",
                f"Frozen mode: {getattr(sys, 'frozen', False)}",
                f"sys.executable: {sys.executable}",
                f"sys.argv[0]: {argv[0] if argv else ''}",
                f"Working directory: {app_dir}",
                f"Directory exists: {app_dir.exists()}",
                "========================",
                "",
            ]
            _safe_write_text(app_dir / "zapret_startup.log", "\n".join(debug_lines))

        return app_dir
    except Exception as error:
        import traceback

        fallback_dir = Path.cwd()
        _safe_write_text(
            fallback_dir / "zapret_startup_error.log",
            f"Error setting workdir: {error}\n{traceback.format_exc()}",
        )
        return fallback_dir


def load_app_metadata(app_dir: Path) -> AppMetadata:
    try:
        from config.build_info import APP_VERSION, CHANNEL
    except Exception:
        APP_VERSION = "0.0.0"
        CHANNEL = "stable"

    icon_dir = app_dir / "ico"
    return AppMetadata(
        app_version=str(APP_VERSION),
        channel=str(CHANNEL),
        icon_path=icon_dir / "Zapret2.ico",
        icon_test_path=icon_dir / "ZapretDevLogo4.ico",
    )


def show_native_message(title: str, message: str, flags: int = 0x40) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        print(f"{title}: {message}")
