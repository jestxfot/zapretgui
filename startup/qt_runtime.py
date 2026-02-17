from __future__ import annotations

import os
import sys
from typing import Sequence

from startup.preflight import show_native_message


def install_crash_handlers() -> bool:
    try:
        from log.crash_handler import install_crash_handler

        if os.environ.get("ZAPRET_DISABLE_CRASH_HANDLER") != "1":
            install_crash_handler()
            return True
    except Exception:
        return False

    return False


def install_global_exception_fallback() -> None:
    previous_hook = sys.excepthook

    def global_exception_handler(exctype, value, tb_obj):
        if isinstance(exctype, type) and issubclass(exctype, KeyboardInterrupt):
            if callable(previous_hook) and previous_hook is not global_exception_handler:
                try:
                    previous_hook(exctype, value, tb_obj)
                except Exception:
                    pass
            return

        try:
            import traceback

            error_msg = "".join(traceback.format_exception(exctype, value, tb_obj))
        except Exception as format_error:
            error_msg = f"{exctype}: {value!r} (traceback format failed: {format_error!r})"

        try:
            print(error_msg, file=sys.stderr)
        except Exception:
            pass

        show_native_message("Zapret", f"Unhandled error occurred.\n\n{value}", 0x10)

        if callable(previous_hook) and previous_hook is not global_exception_handler:
            try:
                previous_hook(exctype, value, tb_obj)
            except Exception:
                pass

    sys.excepthook = global_exception_handler


def _set_attr_if_exists(name: str, on: bool = True) -> None:
    from PyQt6.QtCore import QCoreApplication, Qt

    attr = getattr(Qt.ApplicationAttribute, name, None)
    if attr is None:
        attr = getattr(Qt, name, None)
    if attr is not None:
        QCoreApplication.setAttribute(attr, on)


def create_qt_application(argv: Sequence[str]):
    from PyQt6.QtWidgets import QApplication

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    _set_attr_if_exists("AA_EnableHighDpiScaling")
    _set_attr_if_exists("AA_UseHighDpiPixmaps")

    app = QApplication(list(argv))
    app.setQuitOnLastWindowClosed(False)

    try:
        import platform
        from PyQt6.QtWidgets import QProxyStyle, QStyle

        if platform.system() == "Windows":

            class _NoTransientScrollbarsStyle(QProxyStyle):
                def styleHint(self, hint, option=None, widget=None, returnData=None):
                    if hint == QStyle.StyleHint.SH_ScrollBar_Transient:
                        return 0
                    return super().styleHint(hint, option, widget, returnData)

            app.setStyle(_NoTransientScrollbarsStyle(app.style()))
    except Exception:
        pass

    try:
        from log.crash_handler import install_qt_crash_handler

        install_qt_crash_handler(app)
    except Exception:
        pass

    return app
