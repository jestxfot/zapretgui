# ui/fluent_app_window.py
"""
Main app window using qfluentwidgets FluentWindow (WinUI 3 style).
Replaces the old QWidget + FramelessWindowMixin + CustomTitleBar stack.
"""
import os
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    setTheme, Theme, setThemeColor, NavigationAvatarWidget,
)
from qfluentwidgets import NavigationWidget
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from config import APP_VERSION, ICON_PATH, ICON_TEST_PATH, CHANNEL
from log import log


class ZapretFluentWindow(FluentWindow):
    """Main app window using qfluentwidgets FluentWindow (WinUI 3 style)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Zapret2 v{APP_VERSION}")
        self.setMinimumSize(900, 500)

        # Set app icon
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        self._app_icon = None
        if os.path.exists(icon_path):
            self._app_icon = QIcon(icon_path)
            self.setWindowIcon(self._app_icon)
            app = QApplication.instance()
            if app:
                app.setWindowIcon(self._app_icon)

        # Apply dark theme by default
        setTheme(Theme.DARK)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def addPageToNav(self, page: QWidget, icon, text: str,
                     position=NavigationItemPosition.SCROLL,
                     parent=None, is_transparent=True):
        """Wrapper for addSubInterface that ensures objectName is set."""
        if not page.objectName():
            page.setObjectName(page.__class__.__name__)
        return self.addSubInterface(
            page, icon, text,
            position=position,
            parent=parent,
            isTransparent=is_transparent,
        )

    def addSeparatorToNav(self):
        """Add a separator line in the navigation."""
        self.navigationInterface.addSeparator()
