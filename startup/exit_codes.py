from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    INVALID_ARGUMENTS = 2
    UPDATE_FAILED = 10
    GUARD_SETUP_FAILED = 20
    ELEVATION_FAILED = 21
    QT_INIT_FAILED = 30
    STARTUP_FAILURE = 99
