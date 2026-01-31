"""
Helpers for consistent LineEdit icons across themes.

Primary use-case: Qt's native clear-button icon can be rendered as dark/black
even on a dark theme. We replace it with an explicit qtawesome icon.
"""

from __future__ import annotations

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLineEdit, QToolButton


def set_line_edit_clear_button_icon(
    line_edit: QLineEdit,
    *,
    icon_name: str = "mdi.close",
    color: str = "rgba(255,255,255,0.75)",
    size: int = 14,
) -> None:
    """
    Replaces the built-in QLineEdit clear button icon with a theme-friendly one.

    Must be called after `line_edit.setClearButtonEnabled(True)`.
    """

    def _apply() -> None:
        btn = line_edit.findChild(QToolButton, "qt_clear_button")
        if not btn:
            return

        pixmap = qta.icon(icon_name, color=color).pixmap(size, size)
        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(size, size))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QToolButton#qt_clear_button {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QToolButton#qt_clear_button:hover {
                background: rgba(255, 255, 255, 0.10);
                border-radius: 6px;
            }
            QToolButton#qt_clear_button:pressed {
                background: rgba(255, 255, 255, 0.16);
                border-radius: 6px;
            }
        """)

    # The clear button can be created lazily by Qt; apply on next event loop tick.
    QTimer.singleShot(0, _apply)

