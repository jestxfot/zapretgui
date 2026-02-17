from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys
import time

from startup.exit_codes import ExitCode
from startup.preflight import show_native_message


def _runtime_log(message: str, level: str = "INFO") -> None:
    try:
        print(f"[{level}] {message}", file=sys.stderr)
    except Exception:
        pass


def _wait_until_writable(path: Path, *, attempts: int = 10, delay_s: float = 0.5) -> None:
    for _ in range(attempts):
        if not path.exists() or os.access(path, os.W_OK):
            return
        time.sleep(delay_s)


def _copy_with_retries(src: Path, dst: Path, *, retries: int = 4) -> None:
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            shutil.copy2(src, dst)
            if src.stat().st_size != dst.stat().st_size:
                raise OSError(
                    f"size mismatch: src={src.stat().st_size} dst={dst.stat().st_size}"
                )
            return
        except Exception as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(0.3 * (attempt + 1))

    raise OSError(f"Failed to copy update payload after {retries} attempts: {last_error}")


def run_update(old_exe: str, new_exe: str) -> int:
    old_path = Path(old_exe)
    new_path = Path(new_exe)

    if not new_path.exists():
        show_native_message("Zapret", f"Update payload not found: {new_path}", 0x10)
        return int(ExitCode.INVALID_ARGUMENTS)

    _wait_until_writable(old_path)

    try:
        _copy_with_retries(new_path, old_path)
        subprocess.Popen([str(old_path)], close_fds=True)
        _runtime_log("Update package applied", "INFO")
        return int(ExitCode.OK)
    except Exception as error:
        _runtime_log(f"Failed to apply update: {error}", "ERROR")
        show_native_message("Zapret", f"Update failed: {error}", 0x10)
        return int(ExitCode.UPDATE_FAILED)
    finally:
        try:
            new_path.unlink(missing_ok=True)
        except Exception:
            pass
