from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

from startup.args import StartupArgs, parse_startup_args
from startup.exit_codes import ExitCode
from startup.guards import enforce_admin, enforce_single_instance
from startup.preflight import load_app_metadata, set_workdir_to_app, show_native_message
from startup.profiler import StartupProfiler
from startup.qt_runtime import (
    create_qt_application,
    install_crash_handlers,
    install_global_exception_fallback,
)
from startup.updater import run_update


def _print_help(script_name: str) -> None:
    print(f"Usage: {script_name} [options]")
    print("")
    print("Runtime policy: production-only startup mode")
    print("")
    print("Options:")
    print("  --version                      Print app version")
    print("  --tray                         Start hidden in system tray")
    print("  --update <old_exe> <new_exe>  Apply updater payload")
    print("  --startup-profile              Enable startup stage timing log")
    print("  -h, --help                     Show this help")


def _handle_special_modes(
    args: StartupArgs,
    app_version: str,
    profiler: StartupProfiler,
    script_name: str,
) -> int | None:
    if args.has_invalid_arguments:
        invalid = ", ".join(args.invalid_arguments)
        show_native_message(
            "Zapret",
            f"Unsupported startup arguments: {invalid}\nThis build supports only production startup mode.",
            0x10,
        )
        profiler.mark("special_mode_invalid_args", invalid_arguments=invalid)
        return int(ExitCode.INVALID_ARGUMENTS)

    if args.show_help:
        _print_help(script_name)
        profiler.mark("special_mode_help")
        return int(ExitCode.OK)

    if args.show_version:
        print(app_version)
        profiler.mark("special_mode_version")
        return int(ExitCode.OK)

    if args.update_requested and not args.has_valid_update_payload:
        show_native_message("Zapret", "--update requires <old_exe> <new_exe>", 0x10)
        profiler.mark("special_mode_update_invalid_args")
        return int(ExitCode.INVALID_ARGUMENTS)

    if args.has_valid_update_payload:
        profiler.mark("special_mode_update_start")
        exit_code = run_update(args.update_old_exe or "", args.update_new_exe or "")
        profiler.mark("special_mode_update_done", exit_code=int(exit_code))
        return int(exit_code)

    return None


def run(argv: Sequence[str] | None = None) -> int:
    argv_list = list(argv) if argv is not None else list(sys.argv)
    script_name = Path(argv_list[0]).name if argv_list else "main.py"

    app_dir = set_workdir_to_app(argv_list)

    args = parse_startup_args(argv_list)
    profiler = StartupProfiler(enabled=args.startup_profile)
    profiler.mark("startup_begin")

    try:
        metadata = load_app_metadata(app_dir)
        profiler.mark("metadata_loaded", channel=metadata.channel)

        special_exit_code = _handle_special_modes(args, metadata.app_version, profiler, script_name)
        if special_exit_code is not None:
            profiler.finish(exit_code=special_exit_code)
            return special_exit_code

        continue_running, exit_code = enforce_admin(argv_list)
        profiler.mark("admin_guard", continue_running=continue_running, exit_code=exit_code)
        if not continue_running:
            profiler.finish(exit_code=exit_code)
            return exit_code

        continue_running, exit_code = enforce_single_instance("ZapretSingleInstance")
        profiler.mark("single_instance_guard", continue_running=continue_running, exit_code=exit_code)
        if not continue_running:
            profiler.finish(exit_code=exit_code)
            return exit_code

        crash_handlers_installed = install_crash_handlers()
        profiler.mark("crash_handler", installed=crash_handlers_installed)
        if not crash_handlers_installed:
            install_global_exception_fallback()

        try:
            app = create_qt_application(argv_list)
            profiler.mark("qt_initialized")
        except Exception as error:
            show_native_message("Zapret", f"Failed to initialize Qt: {error}", 0x10)
            profiler.finish(exit_code=int(ExitCode.QT_INIT_FAILED))
            return int(ExitCode.QT_INIT_FAILED)

        from startup.window import LupiDPIApp

        window = LupiDPIApp(start_in_tray=args.start_in_tray, metadata=metadata)
        profiler.mark("window_created", start_in_tray=bool(args.start_in_tray))

        if args.start_in_tray and window.tray_manager is not None:
            window.tray_manager.show_notification(
                "Zapret runs in tray",
                "Application started in background mode.",
            )

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, lambda: profiler.mark("event_loop_entered"))
        exit_code = int(app.exec())
        profiler.mark("event_loop_exited", exit_code=exit_code)
        profiler.finish(exit_code=exit_code)
        return exit_code
    except Exception as error:
        show_native_message("Zapret", f"Startup failed: {error}", 0x10)
        profiler.mark("startup_exception", error=str(error))
        profiler.finish(exit_code=int(ExitCode.STARTUP_FAILURE))
        return int(ExitCode.STARTUP_FAILURE)
