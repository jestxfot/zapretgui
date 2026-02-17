from __future__ import annotations

import subprocess
import sys
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from startup.preflight import AppMetadata


_CACHED_LOG = None


def _runtime_log(message: str, level: str = "INFO") -> None:
    global _CACHED_LOG

    if _CACHED_LOG is None:
        try:
            from log import log as app_log

            _CACHED_LOG = app_log
        except Exception:
            _CACHED_LOG = False

    if _CACHED_LOG:
        _CACHED_LOG(message, level)
        return

    try:
        print(f"[{level}] {message}", file=sys.stderr)
    except Exception:
        pass


class TrayManager:
    def __init__(self, window: "LupiDPIApp", icon: QIcon) -> None:
        self.window = window
        self.tray = QSystemTrayIcon(icon, window)
        self.tray.setToolTip(f"Zapret v{window.metadata.app_version}")

        menu = QMenu(window)
        show_action = QAction("Open Zapret", menu)
        show_action.triggered.connect(self.show_window)

        quit_action = QAction("Exit", menu)
        quit_action.triggered.connect(window.exit_application)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.activateWindow()
        self.window.raise_()

    def show_notification(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3500)

    def cleanup(self) -> None:
        self.tray.hide()


class LupiDPIApp(QMainWindow):
    """Minimal production shell used by startup entrypoint."""

    def __init__(self, *, start_in_tray: bool, metadata: AppMetadata):
        super().__init__()
        self.start_in_tray = start_in_tray
        self.metadata = metadata
        self._force_quit = False
        self._tray_hint_shown = False
        self.tray_manager: Optional[TrayManager] = None
        self.status_label: Optional[QLabel] = None

        self._configure_window()
        self._build_ui()
        self._init_tray()

        if self.start_in_tray and self.tray_manager is not None:
            QTimer.singleShot(0, self.hide)
        else:
            self.show()

    def _configure_window(self) -> None:
        self.setWindowTitle(f"Zapret v{self.metadata.app_version}")
        self.setMinimumSize(780, 500)
        self.resize(980, 620)

        icon_path = self.metadata.icon_test_path if self.metadata.channel == "test" else self.metadata.icon_path
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            style = self.style()
            if style is not None:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            else:
                icon = QIcon()

        self.setWindowIcon(icon)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setWindowIcon(icon)

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Zapret")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle = QLabel(
            "Production startup runtime is active. "
            "This shell intentionally keeps startup deterministic and lightweight."
        )
        subtitle.setWordWrap(True)

        runtime_label = QLabel("Runtime policy: production-only")
        runtime_label.setStyleSheet("padding: 8px; border: 1px solid #555; border-radius: 6px;")

        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("padding: 8px; border: 1px solid #777; border-radius: 6px;")

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        open_folder_btn = QPushButton("Open Working Folder")
        open_folder_btn.clicked.connect(self.open_folder)

        diagnostics_btn = QPushButton("Show Diagnostics")
        diagnostics_btn.clicked.connect(
            lambda: self.set_status("Legacy diagnostics pages are removed in production runtime.")
        )

        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self.exit_application)

        action_row.addWidget(open_folder_btn)
        action_row.addWidget(diagnostics_btn)
        action_row.addStretch(1)
        action_row.addWidget(exit_btn)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(runtime_label)
        layout.addWidget(self.status_label)
        layout.addLayout(action_row)
        layout.addStretch(1)

        self.setCentralWidget(root)

    def _init_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            _runtime_log("System tray is unavailable on this machine", "WARNING")
            return

        self.tray_manager = TrayManager(self, self.windowIcon())

    def set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.setText(f"Status: {text}")
        _runtime_log(text, "INFO")

    def change_theme(self, *args, **kwargs) -> None:
        _ = args, kwargs
        self.set_status("Theme switching is disabled in production runtime shell.")

    def open_folder(self) -> None:
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer.exe", "."], close_fds=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "."], close_fds=True)
            else:
                subprocess.Popen(["xdg-open", "."], close_fds=True)
        except Exception as error:
            self.set_status(f"Failed to open folder: {error}")

    def open_connection_test(self) -> None:
        self.set_status("Connection test page is removed in production runtime.")

    def show_servers_page(self) -> None:
        self.set_status("Servers page is removed in production runtime.")

    def show_page(self, page_name) -> bool:
        self.set_status(f"Page navigation is removed in production runtime: {page_name}")
        return False

    def exit_application(self) -> None:
        self._force_quit = True
        if self.tray_manager is not None:
            self.tray_manager.cleanup()
        QApplication.quit()

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        if a0 is None:
            return

        if self.tray_manager is not None and not self._force_quit:
            a0.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray_manager.show_notification(
                    "Zapret is still running",
                    "Use tray icon to reopen or exit app.",
                )
            return

        if self.tray_manager is not None:
            self.tray_manager.cleanup()
        super().closeEvent(a0)
