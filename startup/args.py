from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Sequence


def _is_truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class StartupArgs:
    show_help: bool
    show_version: bool
    start_in_tray: bool
    startup_profile: bool
    update_requested: bool
    update_old_exe: str | None
    update_new_exe: str | None
    invalid_arguments: tuple[str, ...]

    @property
    def has_valid_update_payload(self) -> bool:
        return bool(self.update_old_exe and self.update_new_exe)

    @property
    def has_invalid_arguments(self) -> bool:
        return len(self.invalid_arguments) > 0


def parse_startup_args(argv: Sequence[str]) -> StartupArgs:
    argv_list = list(argv)

    startup_profile = _is_truthy(os.environ.get("ZAPRET_STARTUP_PROFILE", ""))
    if "--startup-profile" in argv_list:
        startup_profile = True

    update_requested = "--update" in argv_list
    update_old_exe = None
    update_new_exe = None

    if update_requested:
        update_index = argv_list.index("--update")
        if update_index + 2 < len(argv_list):
            update_old_exe = str(argv_list[update_index + 1])
            update_new_exe = str(argv_list[update_index + 2])

    invalid_arguments: list[str] = []
    for legacy_flag in ("--mode", "--modern", "--hybrid"):
        if legacy_flag in argv_list:
            invalid_arguments.append(legacy_flag)

    return StartupArgs(
        show_help=("--help" in argv_list) or ("-h" in argv_list),
        show_version="--version" in argv_list,
        start_in_tray="--tray" in argv_list,
        startup_profile=startup_profile,
        update_requested=update_requested,
        update_old_exe=update_old_exe,
        update_new_exe=update_new_exe,
        invalid_arguments=tuple(invalid_arguments),
    )
