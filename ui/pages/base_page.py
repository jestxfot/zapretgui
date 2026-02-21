# ui/pages/base_page.py
"""Базовый класс для страниц — использует qfluentwidgets ScrollArea."""

import sys
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QPlainTextEdit, QTextEdit,
)
from PyQt6.QtGui import QFont

try:
    from qfluentwidgets import (ScrollArea as _FluentScrollArea, TitleLabel, BodyLabel, StrongBodyLabel,
                                PlainTextEdit as _FluentPlainTextEdit, TextEdit as _FluentTextEdit)
    _USE_FLUENT = True
except ImportError:
    _FluentScrollArea = QScrollArea
    _FluentPlainTextEdit = QPlainTextEdit
    _FluentTextEdit = QTextEdit
    _USE_FLUENT = False


class ScrollBlockingPlainTextEdit(_FluentPlainTextEdit):
    """PlainTextEdit с fluent-скроллбарами, не пропускающий прокрутку к родителю.

    SmoothScrollDelegate (из qfluentwidgets) намеренно пропускает wheel-событие
    к родителю когда достигнута граница скролла (return False в eventFilter).
    Переопределяем wheelEvent чтобы принять событие и не дать BasePage прокрутиться.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("noDrag", True)

    def wheelEvent(self, event):
        # SmoothScrollDelegate поглощает событие когда НЕ у границы (возвращает True),
        # поэтому этот метод вызывается ТОЛЬКО у границы скролла.
        event.accept()


class ScrollBlockingTextEdit(_FluentTextEdit):
    """TextEdit с fluent-скроллбарами, не пропускающий прокрутку к родителю."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("noDrag", True)

    def wheelEvent(self, event):
        event.accept()


class BasePage(_FluentScrollArea):
    """Базовый класс для страниц контента.

    Uses qfluentwidgets ScrollArea for smooth Fluent-style scrolling.
    The public API (self.layout, add_widget, add_spacing, add_section_title,
    self.parent_app, self.title_label, self.subtitle_label) is kept
    backward-compatible so all 40+ pages work without changes.
    """

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.parent_app = parent

        # Ensure objectName is set (required by FluentWindow.addSubInterface)
        if not self.objectName():
            self.setObjectName(self.__class__.__name__)

        # --- ScrollArea config ---
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; }"
        )

        # Apply smooth scroll preference from registry
        try:
            from config.reg import get_smooth_scroll_enabled
            from qfluentwidgets.common.smooth_scroll import SmoothMode
            if not get_smooth_scroll_enabled():
                self.setSmoothMode(SmoothMode.NO_SMOOTH, Qt.Orientation.Vertical)
        except Exception:
            pass

        # --- Content container ---
        self.content = QWidget(self)
        self.content.setStyleSheet("background-color: transparent;")
        # Expanding horizontally so the content fills the viewport width and
        # word-wrapped labels can actually wrap instead of overflowing.
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setWidget(self.content)

        # --- Main layout (backward-compat: self.layout) ---
        self.vBoxLayout = QVBoxLayout(self.content)
        self.vBoxLayout.setContentsMargins(36, 28, 36, 28)
        self.vBoxLayout.setSpacing(16)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Backward compatibility: old pages use self.layout.addWidget(...)
        self.layout = self.vBoxLayout

        # --- Title ---
        if _USE_FLUENT:
            self.title_label = TitleLabel(title, self.content)
        else:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(
                "font-size: 28px; font-weight: 600; "
                "font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; "
                "padding-bottom: 4px;"
            )
        self.vBoxLayout.addWidget(self.title_label)

        # --- Subtitle ---
        if subtitle:
            if _USE_FLUENT:
                self.subtitle_label = BodyLabel(subtitle, self.content)
            else:
                self.subtitle_label = QLabel(subtitle)
                self.subtitle_label.setStyleSheet("font-size: 12px; padding-bottom: 16px;")
            self.subtitle_label.setWordWrap(True)
            self.vBoxLayout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None

    # ------------------------------------------------------------------
    # Public helpers (backward-compat with all 40+ pages)
    # ------------------------------------------------------------------

    def add_widget(self, widget: QWidget, stretch: int = 0):
        """Добавляет виджет на страницу"""
        self.vBoxLayout.addWidget(widget, stretch)

    def add_spacing(self, height: int = 16):
        """Добавляет вертикальный отступ"""
        from PyQt6.QtWidgets import QSpacerItem
        spacer = QSpacerItem(0, height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.vBoxLayout.addItem(spacer)

    def add_section_title(self, text: str, return_widget: bool = False):
        """Добавляет заголовок секции"""
        if _USE_FLUENT:
            label = StrongBodyLabel(text, self.content)
        else:
            label = QLabel(text)
            label.setStyleSheet("font-size: 13px; font-weight: 600; padding-top: 8px; padding-bottom: 4px;")
        label.setProperty("tone", "primary")
        self.vBoxLayout.addWidget(label)
        if return_widget:
            return label
