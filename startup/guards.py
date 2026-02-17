from __future__ import annotations

import atexit
import ctypes
import subprocess
import sys
from typing import Sequence

from startup.exit_codes import ExitCode
from startup.preflight import show_native_message


def _runtime_log(message: str, level: str = "INFO") -> None:
    try:
        print(f"[{level}] {message}", file=sys.stderr)
    except Exception:
        pass


def enforce_admin(argv: Sequence[str]) -> tuple[bool, int]:
    """Returns (continue_running, exit_code)."""
    if sys.platform != "win32":
        return True, int(ExitCode.OK)

    try:
        from startup.admin_check import is_admin
    except Exception as error:
        _runtime_log(f"Admin guard setup failed: {error}", "ERROR")
        show_native_message("Zapret", f"Admin guard setup failed: {error}", 0x10)
        return False, int(ExitCode.GUARD_SETUP_FAILED)

    if is_admin():
        return True, int(ExitCode.OK)

    try:
        params = subprocess.list2cmdline(list(argv)[1:])
        shell_exec_result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,
        )
        if int(shell_exec_result) <= 32:
            raise OSError(f"ShellExecuteW returned {int(shell_exec_result)}")

        _runtime_log("Elevation requested successfully; exiting current process", "INFO")
        return False, int(ExitCode.OK)
    except Exception as error:
        _runtime_log(f"Failed to request admin rights: {error}", "ERROR")
        show_native_message("Zapret", f"Admin rights are required: {error}", 0x10)
        return False, int(ExitCode.ELEVATION_FAILED)


def enforce_single_instance(mutex_name: str = "ZapretSingleInstance") -> tuple[bool, int]:
    """Returns (continue_running, exit_code)."""
    from startup.single_instance import create_mutex, release_mutex

    mutex_handle, already_running = create_mutex(mutex_name)

    if not mutex_handle:
        _runtime_log("Single-instance guard setup failed (CreateMutexW)", "ERROR")
        show_native_message("Zapret", "Single-instance guard setup failed.", 0x10)
        return False, int(ExitCode.GUARD_SETUP_FAILED)

    if already_running:
        show_native_message(
            "Zapret",
            "Zapret is already running. Close existing instance first.",
            0x40,
        )
        return False, int(ExitCode.OK)

    atexit.register(lambda: release_mutex(mutex_handle))
    return True, int(ExitCode.OK)
