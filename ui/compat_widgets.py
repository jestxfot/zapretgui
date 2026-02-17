# ui/compat_widgets.py
"""
Compatibility shim: re-exports old custom widgets or their qfluentwidgets replacements.
Pages that import SettingsCard, ActionButton, StatusIndicator from ui.sidebar
can gradually switch to importing from here instead.
"""
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QPushButton,
)
from PyQt6.QtGui import QIcon, QFont

try:
    from qfluentwidgets import (
        CardWidget, SimpleCardWidget, PrimaryPushButton, PushButton,
        TransparentPushButton, BodyLabel, StrongBodyLabel, CaptionLabel,
        SubtitleLabel, TitleLabel, IndeterminateProgressBar, FluentIcon,
        ProgressBar, InfoBar, SwitchButton,
    )
    HAS_FLUENT = True
except ImportError:
    HAS_FLUENT = False


# ---------------------------------------------------------------------------
# SettingsCard — wraps qfluentwidgets CardWidget (or falls back to QFrame)
# ---------------------------------------------------------------------------

class SettingsCard(CardWidget if HAS_FLUENT else QFrame):
    """Card container for settings rows, matching the old SettingsCard API."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        if title:
            title_lbl = StrongBodyLabel(title, self) if HAS_FLUENT else QLabel(title)
            if not HAS_FLUENT:
                title_lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
            self.main_layout.addWidget(title_lbl)

    def add_widget(self, widget: QWidget):
        self.main_layout.addWidget(widget)

    def add_layout(self, layout):
        self.main_layout.addLayout(layout)


# ---------------------------------------------------------------------------
# ActionButton — wraps PrimaryPushButton / PushButton
# ---------------------------------------------------------------------------

class ActionButton(PrimaryPushButton if HAS_FLUENT else QPushButton):
    """Action button matching the old ActionButton(text, icon_name, accent) API."""

    def __init__(self, text: str, icon_name: str | None = None, accent: bool = False, parent=None):
        if HAS_FLUENT:
            if accent:
                PrimaryPushButton.__init__(self, text, parent)
            else:
                # Fall back to regular PushButton for non-accent
                PushButton.__init__(self, text, parent)
        else:
            super().__init__(text, parent)

        self.accent = accent
        self._icon_name = icon_name
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Try to set qtawesome icon if available
        if icon_name:
            self.setIconSize(QSize(16, 16))
            try:
                import qtawesome as qta
                self.setIcon(qta.icon(icon_name, color="#ffffff" if accent else "#cccccc"))
            except Exception:
                pass


# Re-create ActionButton properly to handle accent=False case
class ActionButton(QPushButton):
    """Action button compatible with the old API. Uses Fluent styling."""

    def __init__(self, text: str, icon_name: str | None = None, accent: bool = False, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self._icon_name = icon_name
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if icon_name:
            self.setIconSize(QSize(16, 16))
            try:
                import qtawesome as qta
                self.setIcon(qta.icon(icon_name, color="#ffffff" if accent else "#cccccc"))
            except Exception:
                pass

        if HAS_FLUENT:
            # Apply fluent styling via property
            self.setProperty("accent", accent)


# ---------------------------------------------------------------------------
# StatusIndicator — simple dot + label
# ---------------------------------------------------------------------------

class StatusIndicator(QWidget):
    """Status dot + label widget."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._dot = QFrame(self)
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(
            "QFrame { background: #888; border-radius: 4px; }"
        )
        layout.addWidget(self._dot)

        self._label = CaptionLabel(text, self) if HAS_FLUENT else QLabel(text)
        layout.addWidget(self._label)
        layout.addStretch()

    def set_status(self, text: str, color: str = "#888"):
        self._label.setText(text)
        self._dot.setStyleSheet(
            f"QFrame {{ background: {color}; border-radius: 4px; }}"
        )
