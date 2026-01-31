# ui/widgets/direct_zapret2_tabs.py

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton


class DirectZapret2Tabs(QWidget):
    """Two-tab segmented switch for direct_zapret2 Strategies section."""

    management_requested = pyqtSignal()
    direct_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("noDrag", True)

        self._active = "management"  # management | direct

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn_management = QPushButton("Управление")
        self._btn_management.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_management.setFixedHeight(32)
        self._btn_management.clicked.connect(self.management_requested.emit)

        self._btn_direct = QPushButton("Прямой запуск")
        self._btn_direct.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_direct.setFixedHeight(32)
        self._btn_direct.clicked.connect(self.direct_requested.emit)

        layout.addWidget(self._btn_management)
        layout.addWidget(self._btn_direct)

        self.set_active("management")

    def set_active(self, key: str) -> None:
        key = (key or "").strip().lower()
        if key not in ("management", "direct"):
            key = "management"
        self._active = key
        self._apply_styles()

    def _apply_styles(self) -> None:
        active_bg = "#60cdff"
        active_fg = "#000000"
        inactive_bg = "rgba(255, 255, 255, 0.08)"
        inactive_fg = "rgba(255, 255, 255, 0.85)"
        inactive_hover_bg = "rgba(255, 255, 255, 0.12)"

        def _btn_style(*, active: bool, left: bool) -> str:
            if active:
                bg = active_bg
                fg = active_fg
                hover = "#60cdff"
            else:
                bg = inactive_bg
                fg = inactive_fg
                hover = inactive_hover_bg

            radius = "border-top-left-radius: 8px; border-bottom-left-radius: 8px;" if left else "border-top-right-radius: 8px; border-bottom-right-radius: 8px;"
            return f"""
                QPushButton {{
                    background-color: {bg};
                    border: none;
                    {radius}
                    color: {fg};
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QPushButton:pressed {{
                    background-color: rgba(96, 205, 255, 0.85);
                }}
            """

        self._btn_management.setStyleSheet(_btn_style(active=self._active == "management", left=True))
        self._btn_direct.setStyleSheet(_btn_style(active=self._active == "direct", left=False))
