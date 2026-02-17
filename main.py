from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from startup.entry import run

if TYPE_CHECKING:
    from startup.window import LupiDPIApp


def __getattr__(name: str):
    if name == "LupiDPIApp":
        from startup.window import LupiDPIApp as _LupiDPIApp

        return _LupiDPIApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
