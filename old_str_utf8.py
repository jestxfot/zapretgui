# ui/pages/zapret2/strategy_detail_page.py
"""
╨б╤В╤А╨░╨╜╨╕╤Ж╨░ ╨┤╨╡╤В╨░╨╗╤М╨╜╨╛╨│╨╛ ╨┐╤А╨╛╤Б╨╝╨╛╤В╤А╨░ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣ ╨┤╨╗╤П ╨▓╤Л╨▒╤А╨░╨╜╨╜╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕.
╨Ю╤В╨║╤А╤Л╨▓╨░╨╡╤В╤Б╤П ╨┐╤А╨╕ ╨║╨╗╨╕╨║╨╡ ╨╜╨░ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤О ╨▓ Zapret2StrategiesPageNew.
"""

import re
import json

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QFrame, QMenu,
    QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont, QFontMetrics, QColor
import qtawesome as qta

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, StrongBodyLabel, SubtitleLabel,
        ComboBox, CheckBox, SpinBox, LineEdit, TextEdit, HorizontalSeparator,
        ToolButton, TransparentToolButton, SwitchButton, SegmentedWidget, TogglePushButton,
        PixmapLabel,
        TitleLabel, TransparentPushButton, IndeterminateProgressRing, RoundMenu, Action,
        MessageBoxBase, InfoBar, FluentIcon,
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import (
        QComboBox as ComboBox, QCheckBox as CheckBox, QSpinBox as SpinBox,
        QLineEdit as LineEdit, QTextEdit as TextEdit, QFrame as HorizontalSeparator, QPushButton,
        QDialog as MessageBoxBase,
    )
    BodyLabel = QLabel
    CaptionLabel = QLabel
    StrongBodyLabel = QLabel
    SubtitleLabel = QLabel
    TitleLabel = QLabel
    ToolButton = QPushButton
    TransparentToolButton = QPushButton
    SwitchButton = QPushButton
    TransparentPushButton = QPushButton
    SegmentedWidget = QWidget
    TogglePushButton = QPushButton
    TextEdit = QWidget
    PixmapLabel = QLabel
    IndeterminateProgressRing = QWidget
    RoundMenu = QMenu
    Action = lambda *a, **kw: None
    InfoBar = None
    FluentIcon = None
    _HAS_FLUENT = False

from ui.pages.base_page import BasePage
from ui.compat_widgets import ActionButton, PrimaryActionButton, SettingsRow, set_tooltip
from ui.pages.dpi_settings_page import Win11ToggleRow
from ui.pages.strategies_page_base import ResetActionButton
from ui.widgets.direct_zapret2_strategies_tree import DirectZapret2StrategiesTree, StrategyTreeRow
from strategy_menu.args_preview_dialog import ArgsPreviewDialog
from launcher_common.blobs import get_blobs_info
from preset_zapret2 import PresetManager, SyndataSettings
from ui.zapret2_strategy_marks import DirectZapret2MarksStore, DirectZapret2FavoritesStore
from ui.theme import get_theme_tokens
from log import log


# тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
# ╨Ф╨Ш╨Р╨Ы╨Ю╨У ╨а╨Х╨Ф╨Р╨Ъ╨в╨Ш╨а╨Ю╨Т╨Р╨Э╨Ш╨п ╨Р╨а╨У╨г╨Ь╨Х╨Э╨в╨Ю╨Т (MessageBoxBase)
# тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

class _ArgsEditorDialog(MessageBoxBase):
    """╨Ф╨╕╨░╨╗╨╛╨│ ╤А╨╡╨┤╨░╨║╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П ╨░╤А╨│╤Г╨╝╨╡╨╜╤В╨╛╨▓ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨╜╨░ ╨▒╨░╨╖╨╡ MessageBoxBase."""

    def __init__(self, initial_text: str = "", parent=None):
        super().__init__(parent)
        if _HAS_FLUENT:
            from qfluentwidgets import SubtitleLabel as _SubLabel
            self._title_lbl = _SubLabel("╨Р╤А╨│╤Г╨╝╨╡╨╜╤В╤Л ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕")
        else:
            self._title_lbl = QLabel("╨Р╤А╨│╤Г╨╝╨╡╨╜╤В╤Л ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕")
        self.viewLayout.addWidget(self._title_lbl)

        if _HAS_FLUENT:
            from qfluentwidgets import CaptionLabel as _Cap
            hint = _Cap("╨Ю╨┤╨╕╨╜ ╨░╤А╨│╤Г╨╝╨╡╨╜╤В ╨╜╨░ ╤Б╤В╤А╨╛╨║╤Г. ╨Ш╨╖╨╝╨╡╨╜╤П╨╡╤В ╤В╨╛╨╗╤М╨║╨╛ ╨▓╤Л╨▒╤А╨░╨╜╨╜╤Г╤О ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤О.")
        else:
            hint = QLabel("╨Ю╨┤╨╕╨╜ ╨░╤А╨│╤Г╨╝╨╡╨╜╤В ╨╜╨░ ╤Б╤В╤А╨╛╨║╤Г.")
        self.viewLayout.addWidget(hint)

        self._text_edit = TextEdit()
        self._text_edit.setPlaceholderText(
            "╨Э╨░╨┐╤А╨╕╨╝╨╡╤А:\n--dpi-desync=multisplit\n--dpi-desync-split-pos=1"
        )
        self._text_edit.setMinimumWidth(420)
        self._text_edit.setMinimumHeight(120)
        self._text_edit.setMaximumHeight(220)
        if _HAS_FLUENT:
            from PyQt6.QtGui import QFont
            self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setText(initial_text)
        self.viewLayout.addWidget(self._text_edit)

        self.yesButton.setText("╨б╨╛╤Е╤А╨░╨╜╨╕╤В╤М")
        self.cancelButton.setText("╨Ю╤В╨╝╨╡╨╜╨░")

    def validate(self) -> bool:
        return True

    def get_text(self) -> str:
        return self._text_edit.toPlainText()


TCP_PHASE_TAB_ORDER: list[tuple[str, str]] = [
    ("fake", "FAKE"),
    ("multisplit", "MULTISPLIT"),
    ("multidisorder", "MULTIDISORDER"),
    ("multidisorder_legacy", "LEGACY"),
    ("tcpseg", "TCPSEG"),
    ("oob", "OOB"),
    ("other", "OTHER"),
]

TCP_PHASE_COMMAND_ORDER: list[str] = [
    "fake",
    "multisplit",
    "multidisorder",
    "multidisorder_legacy",
    "tcpseg",
    "oob",
    "other",
]

TCP_EMBEDDED_FAKE_TECHNIQUES: set[str] = {
    "fakedsplit",
    "fakeddisorder",
    "hostfakesplit",
}


STRATEGY_TECHNIQUE_FILTERS: list[tuple[str, str]] = [
    ("FAKE", "fake"),
    ("SPLIT", "split"),
    ("MULTISPLIT", "multisplit"),
    ("DISORDER", "disorder"),
    ("OOB", "oob"),
    ("SYNDATA", "syndata"),
]

TCP_FAKE_DISABLED_STRATEGY_ID = "__phase_fake_disabled__"
CUSTOM_STRATEGY_ID = "custom"


def _extract_desync_technique_from_arg(line: str) -> str | None:
    """
    Extracts desync function name from a single arg line.

    Examples:
      --lua-desync=fake:blob=tls_google -> "fake"
      --lua-desync=pass -> "pass"
      --dpi-desync=multisplit -> "multisplit"
    """
    s = (line or "").strip()
    m = re.match(r"^--(?:lua-desync|dpi-desync)=([a-zA-Z0-9_-]+)", s)
    if not m:
        return None
    return m.group(1).strip().lower() or None


def _map_desync_technique_to_tcp_phase(technique: str) -> str | None:
    t = (technique or "").strip().lower()
    if not t:
        return None
    # "pass" is a no-op, but keeping it in the main phase ensures
    # categories can still be enabled for send/syndata/out-range-only setups.
    if t == "pass":
        return "multisplit"
    if t == "fake":
        return "fake"
    if t in ("multisplit", "fakedsplit", "hostfakesplit"):
        return "multisplit"
    if t in ("multidisorder", "fakeddisorder"):
        return "multidisorder"
    if t == "multidisorder_legacy":
        return "multidisorder_legacy"
    if t == "tcpseg":
        return "tcpseg"
    if t == "oob":
        return "oob"
    return "other"


def _normalize_args_text(text: str) -> str:
    """Normalizes args text for exact matching (keeps line order)."""
    if not text:
        return ""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    return "\n".join(lines).strip()


class TTLButtonSelector(QWidget):
    """
    ╨г╨╜╨╕╨▓╨╡╤А╤Б╨░╨╗╤М╨╜╤Л╨╣ ╤Б╨╡╨╗╨╡╨║╤В╨╛╤А ╨╖╨╜╨░╤З╨╡╨╜╨╕╤П ╤З╨╡╤А╨╡╨╖ ╤А╤П╨┤ ╨║╨╜╨╛╨┐╨╛╨║.
    ╨Ш╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╡╤В╤Б╤П ╨┤╨╗╤П send_ip_ttl, autottl_delta, autottl_min, autottl_max
    """
    value_changed = pyqtSignal(int)  # ╨н╨╝╨╕╤В╨╕╤В ╨▓╤Л╨▒╤А╨░╨╜╨╜╨╛╨╡ ╨╖╨╜╨░╤З╨╡╨╜╨╕╨╡

    def __init__(self, values: list, labels: list = None, parent=None):
        """
        Args:
            values: ╤Б╨┐╨╕╤Б╨╛╨║ int ╨╖╨╜╨░╤З╨╡╨╜╨╕╨╣ ╨┤╨╗╤П ╨║╨╜╨╛╨┐╨╛╨║, ╨╜╨░╨┐╤А╨╕╨╝╨╡╤А [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            labels: ╨╛╨┐╤Ж╨╕╨╛╨╜╨░╨╗╤М╨╜╤Л╨╡ ╨╝╨╡╤В╨║╨╕ ╨┤╨╗╤П ╨║╨╜╨╛╨┐╨╛╨║, ╨╜╨░╨┐╤А╨╕╨╝╨╡╤А ["off", "1", "2", ...]
                   ╨Х╤Б╨╗╨╕ None - ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╤О╤В╤Б╤П str(value)
        """
        super().__init__(parent)
        self._values = values
        self._labels = labels or [str(v) for v in values]
        self._current_value = values[0]
        self._buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        for i, (value, label) in enumerate(zip(self._values, self._labels)):
            btn = TogglePushButton(self)
            btn.setText(label)
            btn.setFixedSize(36, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, v=value: self._select(v))
            self._buttons.append((btn, value))
            layout.addWidget(btn)

        layout.addStretch()
        self._sync_checked_states()

    def _select(self, value: int):
        if value != self._current_value:
            self._current_value = value
            self._sync_checked_states()
            self.value_changed.emit(value)

    def _sync_checked_states(self):
        for btn, value in self._buttons:
            btn.setChecked(value == self._current_value)

    def setValue(self, value: int, block_signals: bool = False):
        """╨г╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╤В ╨╖╨╜╨░╤З╨╡╨╜╨╕╨╡ ╨┐╤А╨╛╨│╤А╨░╨╝╨╝╨╜╨╛"""
        if value in self._values:
            if block_signals:
                self.blockSignals(True)
            self._current_value = value
            self._sync_checked_states()
            if block_signals:
                self.blockSignals(False)

    def value(self) -> int:
        """╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В ╤В╨╡╨║╤Г╤Й╨╡╨╡ ╨╖╨╜╨░╤З╨╡╨╜╨╕╨╡"""
        return self._current_value


class ElidedLabel(QLabel):
    """QLabel, ╨║╨╛╤В╨╛╤А╤Л╨╣ ╨░╨▓╤В╨╛╨╝╨░╤В╨╕╤З╨╡╤Б╨║╨╕ ╨╛╨▒╤А╨╡╨╖╨░╨╡╤В ╤В╨╡╨║╤Б╤В ╤Б ╤В╤А╨╛╨╡╤В╨╛╤З╨╕╨╡╨╝ ╨┐╨╛ ╤И╨╕╤А╨╕╨╜╨╡."""

    def __init__(self, text: str = "", parent=None):
        # Do not rely on QLabel text layout: setting text can trigger relayout/resize loops.
        # We paint the elided text ourselves in paintEvent for stability.
        super().__init__("", parent)
        self._full_text = text or ""
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().setText("")  # keep QLabel's own text empty; we paint manually
        self.set_full_text(self._full_text)

    def set_full_text(self, text: str) -> None:
        self._full_text = text or ""
        self.update()

    def full_text(self) -> str:
        return self._full_text

    def paintEvent(self, event):  # noqa: N802 (Qt override)
        # Let QLabel paint its background/style (with empty text), then draw elided text.
        super().paintEvent(event)
        text = self._full_text or ""
        if not text:
            return

        try:
            r = self.contentsRect()
            w = max(0, int(r.width()))
            if w <= 0:
                return

            metrics = QFontMetrics(self.font())
            elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, w)

            from PyQt6.QtGui import QPainter

            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            p.setFont(self.font())
            p.setPen(self.palette().color(self.foregroundRole()))
            align = self.alignment() or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            p.drawText(r, int(align), elided)
        except Exception:
            return


class ArgsPreview(CaptionLabel):
    """╨Я╤А╨╡╨▓╤М╤О args ╨╜╨░ 2-3 ╤Б╤В╤А╨╛╨║╨╕ (╨╗╤С╨│╨║╨╕╨╣ label ╨▓╨╝╨╡╤Б╤В╨╛ QTextEdit ╨╜╨░ ╨║╨░╨╢╨┤╨╛╨╣ ╤Б╤В╤А╨╛╨║╨╡)."""

    def __init__(self, max_lines: int = 3, parent=None):
        super().__init__(parent)
        self._max_lines = max(1, int(max_lines or 1))
        self._full_text = ""

        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setFont(QFont("Consolas", 9))
        self.setContentsMargins(4, 0, 4, 0)
        self._sync_height()

    def set_full_text(self, text: str):
        self._full_text = text or ""
        set_tooltip(self, (self._full_text or "").replace("\n", "<br>"))
        self.setText(self._wrap_friendly(self._full_text))

    def full_text(self) -> str:
        return self._full_text

    def _sync_height(self):
        metrics = QFontMetrics(self.font())
        line_h = metrics.lineSpacing()
        # +2 ╤З╤В╨╛╨▒╤Л ╨╜╨╡ ╤А╨╡╨╖╨░╨╗╨╛ ╨╜╨╕╨╢╨╜╨╕╨╡ ╨┐╨╕╨║╤Б╨╡╨╗╨╕ ╨│╨╗╨╕╤Д╨╛╨▓ ╨╜╨░ ╨╜╨╡╨║╨╛╤В╨╛╤А╤Л╤Е ╤И╤А╨╕╤Д╤В╨░╤Е/╤А╨╡╨╜╨┤╨╡╤А╨░╤Е.
        self.setMaximumHeight((line_h * self._max_lines) + 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # QLabel ╤Б╨░╨╝ ╨┐╨╡╤А╨╡╤Д╨╛╤А╨╝╨░╤В╨╕╤А╤Г╨╡╤В ╨┐╨╡╤А╨╡╨╜╨╛╤Б╤Л ╨┐╨╛ ╤И╨╕╤А╨╕╨╜╨╡; ╨▓╤Л╤Б╨╛╤В╤Г ╨┤╨╡╤А╨╢╨╕╨╝ ╨┐╨╛╤Б╤В╨╛╤П╨╜╨╜╨╛╨╣.

    @staticmethod
    def _wrap_friendly(text: str) -> str:
        if not text:
            return ""
        # ╨Ф╨╛╨▒╨░╨▓╨╗╤П╨╡╨╝ ╤В╨╛╤З╨║╨╕ ╨┐╨╡╤А╨╡╨╜╨╛╤Б╨░ ╨▓╨╜╤Г╤В╤А╨╕ "╨┤╨╗╨╕╨╜╨╜╤Л╤Е ╤Б╨╗╨╛╨▓" ╨░╤А╨│╤Г╨╝╨╡╨╜╤В╨╛╨▓.
        zws = "\u200b"
        return (
            text.replace(":", f":{zws}")
            .replace(",", f",{zws}")
            .replace("=", f"={zws}")
        )


class _PresetNameDialog(MessageBoxBase):
    """WinUI-style modal dialog for preset create / rename (uses qfluentwidgets MessageBoxBase)."""

    def __init__(self, mode: str, old_name: str = "", parent=None):
        super().__init__(parent)
        self._mode = mode  # "create" | "rename"

        title_text = "╨б╨╛╨╖╨┤╨░╤В╤М ╨┐╤А╨╡╤Б╨╡╤В" if mode == "create" else "╨Я╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╤В╤М ╨┐╤А╨╡╤Б╨╡╤В"
        self.titleLabel = SubtitleLabel(title_text, self.widget)

        if mode == "rename" and old_name:
            from_label = CaptionLabel(f"╨в╨╡╨║╤Г╤Й╨╡╨╡ ╨╕╨╝╤П: {old_name}", self.widget)
            self.viewLayout.addWidget(self.titleLabel)
            self.viewLayout.addWidget(from_label)
        else:
            self.viewLayout.addWidget(self.titleLabel)

        name_label = BodyLabel("╨Э╨░╨╖╨▓╨░╨╜╨╕╨╡", self.widget)
        self.name_edit = LineEdit(self.widget)
        self.name_edit.setPlaceholderText("╨Т╨▓╨╡╨┤╨╕╤В╨╡ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡ ╨┐╤А╨╡╤Б╨╡╤В╨░тАж")
        if mode == "rename" and old_name:
            self.name_edit.setText(old_name)
        self.name_edit.returnPressed.connect(self._validate_and_accept)

        self._error_label = CaptionLabel("", self.widget)
        try:
            from qfluentwidgets import isDarkTheme as _idt
            _err_clr = "#ff6b6b" if _idt() else "#dc2626"
        except Exception:
            _err_clr = "#dc2626"
        self._error_label.setStyleSheet(f"color: {_err_clr};")
        self._error_label.hide()

        self.viewLayout.addWidget(name_label)
        self.viewLayout.addWidget(self.name_edit)
        self.viewLayout.addWidget(self._error_label)

        self.yesButton.setText("╨б╨╛╨╖╨┤╨░╤В╤М" if mode == "create" else "╨Я╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╤В╤М")
        self.cancelButton.setText("╨Ю╤В╨╝╨╡╨╜╨░")
        self.widget.setMinimumWidth(360)

    def _validate_and_accept(self):
        if self.validate():
            self.accept()

    def validate(self) -> bool:
        name = self.name_edit.text().strip()
        if not name:
            self._error_label.setText("╨Т╨▓╨╡╨┤╨╕╤В╨╡ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡ ╨┐╤А╨╡╤Б╨╡╤В╨░")
            self._error_label.show()
            return False
        self._error_label.hide()
        return True

    def get_name(self) -> str:
        return self.name_edit.text().strip()


class StrategyDetailPage(BasePage):
    """
    ╨б╤В╤А╨░╨╜╨╕╤Ж╨░ ╨┤╨╡╤В╨░╨╗╤М╨╜╨╛╨│╨╛ ╨▓╤Л╨▒╨╛╤А╨░ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕.

    Signals:
        strategy_selected(str, str): ╨н╨╝╨╕╤В╨╕╤В╤Б╤П ╨┐╤А╨╕ ╨▓╤Л╨▒╨╛╤А╨╡ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ (category_key, strategy_id)
        args_changed(str, str, list): ╨н╨╝╨╕╤В╨╕╤В╤Б╤П ╨┐╤А╨╕ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╕ ╨░╤А╨│╤Г╨╝╨╡╨╜╤В╨╛╨▓ (category_key, strategy_id, new_args)
        strategy_marked(str, str, object): ╨н╨╝╨╕╤В╨╕╤В╤Б╤П ╨┐╤А╨╕ ╨┐╨╛╨╝╨╡╤В╨║╨╡ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ (category_key, strategy_id, is_working)
        back_clicked(): ╨н╨╝╨╕╤В╨╕╤В╤Б╤П ╨┐╤А╨╕ ╨╜╨░╨╢╨░╤В╨╕╨╕ ╨║╨╜╨╛╨┐╨║╨╕ "╨Э╨░╨╖╨░╨┤"
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    filter_mode_changed = pyqtSignal(str, str)  # category_key, "hostlist"|"ipset"
    args_changed = pyqtSignal(str, str, list)  # category_key, strategy_id, new_args
    strategy_marked = pyqtSignal(str, str, object)  # category_key, strategy_id, is_working (bool|None)
    back_clicked = pyqtSignal()
    navigate_to_root = pyqtSignal()  # тЖТ PageName.ZAPRET2_DIRECT_CONTROL (skip strategies list)

    def __init__(self, parent=None):
        super().__init__(
            title="",  # ╨Ч╨░╨│╨╛╨╗╨╛╨▓╨╛╨║ ╨▒╤Г╨┤╨╡╤В ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╗╨╡╨╜ ╨┤╨╕╨╜╨░╨╝╨╕╤З╨╡╤Б╨║╨╕
            subtitle="",
            parent=parent
        )
        # BasePage uses `SetMaximumSize` to clamp the content widget to its layout's
        # sizeHint. With dynamic/lazy-loaded content (like strategies list), this can
        # leave the scroll range "stuck" and cut off the bottom. For this page, keep
        # the default constraint so height can grow freely.
        try:
            self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetDefaultConstraint)
        except Exception:
            pass
        # Reset the content widget maximum size too: `SetMaximumSize` may have already
        # applied a maxHeight during BasePage init, and switching the layout constraint
        # afterwards does not always clear that clamp.
        try:
            if hasattr(self, "content") and self.content is not None:
                self.content.setMaximumSize(16777215, 16777215)
        except Exception:
            pass
        self.parent_app = parent
        self._category_key = None
        self._category_info = None
        self._current_strategy_id = "none"
        self._selected_strategy_id = "none"
        self._strategies_tree = None
        self._sort_mode = "default"  # default, name_asc, name_desc
        self._active_filters = set()  # ╨Р╨║╤В╨╕╨▓╨╜╤Л╨╡ ╤Д╨╕╨╗╤М╤В╤А╤Л ╨┐╨╛ ╤В╨╡╤Е╨╜╨╕╨║╨╡
        # TCP multi-phase UI state (direct_zapret2, tcp.txt + tcp_fake.txt)
        self._tcp_phase_mode = False
        self._phase_tabbar: SegmentedWidget | None = None
        self._phase_tab_index_by_key: dict[str, int] = {}
        self._phase_tab_key_by_index: dict[int, str] = {}
        self._active_phase_key = None
        self._last_active_phase_key_by_category: dict[str, str] = {}
        self._tcp_phase_selected_ids: dict[str, str] = {}  # phase_key -> strategy_id
        self._tcp_phase_custom_args: dict[str, str] = {}  # phase_key -> raw args chunk (if no matching strategy)
        self._tcp_hide_fake_phase = False
        self._tcp_last_enabled_args_by_category: dict[str, str] = {}
        self._waiting_for_process_start = False  # ╨д╨╗╨░╨│ ╨╛╨╢╨╕╨┤╨░╨╜╨╕╤П ╨╖╨░╨┐╤Г╤Б╨║╨░ DPI
        self._process_monitor_connected = False  # ╨д╨╗╨░╨│ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║ process_monitor
        self._fallback_timer = None  # ╨в╨░╨╣╨╝╨╡╤А ╨╖╨░╤Й╨╕╤В╤Л ╨╛╤В ╨▒╨╡╤Б╨║╨╛╨╜╨╡╤З╨╜╨╛╨│╨╛ ╤Б╨┐╨╕╨╜╨╜╨╡╤А╨░
        self._apply_feedback_timer = None  # ╨С╤Л╤Б╤В╤А╤Л╨╣ ╤В╨░╨╣╨╝╨╡╤А: ╤Г╨▒╤А╨░╤В╤М ╤Б╨┐╨╕╨╜╨╜╨╡╤А ╨┐╨╛╤Б╨╗╨╡ apply
        self._strategies_load_timer = None
        self._strategies_load_generation = 0
        self._pending_strategies_items = []
        self._pending_strategies_index = 0
        self._loaded_strategy_type = None
        self._loaded_strategy_set = None
        self._loaded_tcp_phase_mode = False
        self._default_strategy_order = []
        self._strategies_loaded_fully = False
        self._page_scroll_by_category: dict[str, int] = {}
        self._tree_scroll_by_category: dict[str, int] = {}

        # PresetManager for category settings storage
        self._preset_manager = PresetManager(
            on_dpi_reload_needed=self._on_dpi_reload_needed
        )
        self._marks_store = DirectZapret2MarksStore.default()
        self._favorites_store = DirectZapret2FavoritesStore.default()
        self._favorite_strategy_ids = set()
        self._preview_dialog = None
        self._preview_pinned = False
        self._main_window = None
        self._strategies_data_by_id = {}
        self._content_built = False

    def _ensure_content_built(self) -> None:
        if self._content_built:
            return
        self._build_content()
        self._content_built = True

        # Close hover/pinned preview when the main window hides/deactivates (e.g. tray).
        QTimer.singleShot(0, self._install_main_window_event_filter)

        # ╨Я╨╛╨┤╨║╨╗╤О╤З╨░╨╡╨╝╤Б╤П ╨║ process_monitor ╨┤╨╗╤П ╨╛╤В╤Б╨╗╨╡╨╢╨╕╨▓╨░╨╜╨╕╤П ╤Б╤В╨░╤В╤Г╤Б╨░ DPI
        self._connect_process_monitor()

    def _install_main_window_event_filter(self) -> None:
        try:
            w = self.window()
        except Exception:
            w = None
        if not w or w is self._main_window:
            return
        self._main_window = w
        try:
            w.installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
        try:
            if obj is self._main_window and event is not None:
                et = event.type()
                if et in (
                    QEvent.Type.Hide,
                    QEvent.Type.Close,
                    QEvent.Type.WindowDeactivate,
                    QEvent.Type.WindowStateChange,
                ):
                    # Don't close if focus went to the preview dialog itself.
                    if et == QEvent.Type.WindowDeactivate and self._preview_dialog is not None:
                        try:
                            from PyQt6.QtWidgets import QApplication as _QApp
                            active = _QApp.activeWindow()
                            if active is not None and active is self._preview_dialog:
                                return super().eventFilter(obj, event)
                        except Exception:
                            pass
                    self._close_preview_dialog(force=True)
                    self._close_filter_combo_popup()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _close_filter_combo_popup(self) -> None:
        """Close the technique filter ComboBox dropdown if it is open."""
        try:
            combo = getattr(self, "_filter_combo", None)
            if combo is not None and hasattr(combo, "_closeComboMenu"):
                combo._closeComboMenu()
        except Exception:
            pass

    def hideEvent(self, event):  # noqa: N802 (Qt override)
        # Ensure floating preview/tool windows do not keep intercepting mouse events
        # after navigation away from this page.
        try:
            self._save_scroll_state()
        except Exception:
            pass
        try:
            self._close_preview_dialog(force=True)
        except Exception:
            pass
        try:
            self._close_filter_combo_popup()
        except Exception:
            pass
        try:
            self._stop_loading()
        except Exception:
            pass
        try:
            self._strategies_load_generation += 1
            if self._strategies_load_timer:
                self._strategies_load_timer.stop()
                self._strategies_load_timer = None
        except Exception:
            pass
        return super().hideEvent(event)

    def _refresh_scroll_range(self) -> None:
        # Ensure QScrollArea recomputes range after dynamic content growth.
        try:
            if self.layout is not None:
                self.layout.invalidate()
                self.layout.activate()
        except Exception:
            pass
        try:
            if hasattr(self, "content") and self.content is not None:
                self.content.updateGeometry()
                self.content.adjustSize()
        except Exception:
            pass
        try:
            self.updateGeometry()
            self.viewport().update()
        except Exception:
            pass

    def _save_scroll_state(self, category_key: str | None = None) -> None:
        key = str(category_key or self._category_key or "").strip()
        if not key:
            return

        try:
            bar = self.verticalScrollBar()
            self._page_scroll_by_category[key] = int(bar.value())
        except Exception:
            pass

        try:
            if self._strategies_tree:
                tree_bar = self._strategies_tree.verticalScrollBar()
                self._tree_scroll_by_category[key] = int(tree_bar.value())
        except Exception:
            pass

    def _restore_scroll_state(self, category_key: str | None = None, defer: bool = False) -> None:
        key = str(category_key or self._category_key or "").strip()
        if not key:
            return

        def _apply() -> None:
            try:
                page_bar = self.verticalScrollBar()
                saved_page = self._page_scroll_by_category.get(key)
                if saved_page is None:
                    page_bar.setValue(page_bar.minimum())
                else:
                    page_bar.setValue(max(page_bar.minimum(), min(int(saved_page), page_bar.maximum())))
            except Exception:
                pass

            try:
                if not self._strategies_tree:
                    return
                tree_bar = self._strategies_tree.verticalScrollBar()
                saved_tree = self._tree_scroll_by_category.get(key)
                if saved_tree is None:
                    return
                tree_bar.setValue(max(tree_bar.minimum(), min(int(saved_tree), tree_bar.maximum())))
            except Exception:
                pass

        if defer:
            QTimer.singleShot(0, _apply)
            QTimer.singleShot(40, _apply)
        else:
            _apply()

    def _on_dpi_reload_needed(self):
        """Callback for PresetManager when DPI reload is needed."""
        # Any preset sync may restart / hot-reload winws2 via the config watcher.
        # Flip the header indicator to spinner so UI matches the real behavior.
        try:
            self.show_loading()
        except Exception:
            pass
        from dpi.zapret2_core_restart import trigger_dpi_reload
        if self.parent_app:
            trigger_dpi_reload(
                self.parent_app,
                reason="preset_settings_changed",
                category_key=self._category_key
            )

    def _on_breadcrumb_item_changed(self, route_key: str) -> None:
        """Breadcrumb click handler: navigate up the hierarchy."""
        # BreadcrumbBar physically deletes trailing items on click тАФ
        # restore the full path immediately so the widget is correct when we return.
        if self._breadcrumb is not None and self._category_key:
            cat_name = ""
            try:
                cat_name = self._category_info.full_name if self._category_info else ""
            except Exception:
                pass
            self._breadcrumb.blockSignals(True)
            try:
                self._breadcrumb.clear()
                self._breadcrumb.addItem("control", "╨г╨┐╤А╨░╨▓╨╗╨╡╨╜╨╕╨╡")
                self._breadcrumb.addItem("strategies", "╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ DPI")
                self._breadcrumb.addItem("detail", cat_name or "╨Ъ╨░╤В╨╡╨│╨╛╤А╨╕╤П")
            finally:
                self._breadcrumb.blockSignals(False)

        if route_key == "control":
            self.navigate_to_root.emit()
        elif route_key == "strategies":
            self.back_clicked.emit()
        # "detail" = current page, nothing to do

    def _build_content(self):
        """╨б╤В╤А╨╛╨╕╤В ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╤Б╤В╤А╨░╨╜╨╕╤Ж╤Л"""
        tokens = get_theme_tokens()
        detail_text_color = tokens.fg_muted if tokens.is_light else tokens.fg

        # ╨б╨║╤А╤Л╨▓╨░╨╡╨╝ ╤Б╤В╨░╨╜╨┤╨░╤А╤В╨╜╤Л╨╣ ╨╖╨░╨│╨╛╨╗╨╛╨▓╨╛╨║ BasePage
        if self.title_label is not None:
            self.title_label.hide()
        if self.subtitle_label is not None:
            self.subtitle_label.hide()

        # ╨е╨╡╨┤╨╡╤А ╤Б breadcrumb-╨╜╨░╨▓╨╕╨│╨░╤Ж╨╕╨╡╨╣ ╨▓ ╤Б╤В╨╕╨╗╨╡ Windows 11 Settings
        header = QFrame()
        header.setFrameShape(QFrame.Shape.NoFrame)
        header.setStyleSheet("background: transparent; border: none;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 16)
        header_layout.setSpacing(4)

        # Breadcrumb navigation: ╨г╨┐╤А╨░╨▓╨╗╨╡╨╜╨╕╨╡ тА║ ╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ DPI тА║ [Category]
        self._breadcrumb = None
        try:
            from qfluentwidgets import BreadcrumbBar as _BreadcrumbBar
            self._breadcrumb = _BreadcrumbBar(self)
            self._breadcrumb.blockSignals(True)
            self._breadcrumb.addItem("control", "╨г╨┐╤А╨░╨▓╨╗╨╡╨╜╨╕╨╡")
            self._breadcrumb.addItem("strategies", "╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ DPI")
            self._breadcrumb.addItem("detail", "╨Ъ╨░╤В╨╡╨│╨╛╤А╨╕╤П")
            self._breadcrumb.blockSignals(False)
            self._breadcrumb.currentItemChanged.connect(self._on_breadcrumb_item_changed)
            header_layout.addWidget(self._breadcrumb)
        except Exception:
            # Fallback: original back button
            back_row = QHBoxLayout()
            back_row.setContentsMargins(0, 0, 0, 0)
            back_row.setSpacing(4)
            self._parent_link = TransparentPushButton(parent=self)
            self._parent_link.setText("╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ DPI")
            self._parent_link.setIcon(qta.icon('fa5s.chevron-left', color=tokens.fg_muted))
            self._parent_link.setIconSize(QSize(12, 12))
            self._parent_link.clicked.connect(self.back_clicked.emit)
            back_row.addWidget(self._parent_link)
            back_row.addStretch()
            header_layout.addLayout(back_row)

        # Current page title
        self._title = TitleLabel("╨Т╤Л╨▒╨╡╤А╨╕╤В╨╡ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤О")
        header_layout.addWidget(self._title)

        # ╨б╤В╤А╨╛╨║╨░ ╤Б ╨│╨░╨╗╨╛╤З╨║╨╛╨╣ ╨╕ ╨┐╨╛╨┤╨╖╨░╨│╨╛╨╗╨╛╨▓╨║╨╛╨╝
        subtitle_row = QHBoxLayout()
        subtitle_row.setContentsMargins(0, 0, 0, 0)
        subtitle_row.setSpacing(6)

        # ╨б╨┐╨╕╨╜╨╜╨╡╤А ╨╖╨░╨│╤А╤Г╨╖╨║╨╕
        self._spinner = IndeterminateProgressRing(start=False)
        self._spinner.setFixedSize(16, 16)
        self._spinner.setStrokeWidth(2)
        self._spinner.hide()
        subtitle_row.addWidget(self._spinner)

        # ╨У╨░╨╗╨╛╤З╨║╨░ ╤Г╤Б╨┐╨╡╤Е╨░ (╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В╤Б╤П ╨┐╨╛╤Б╨╗╨╡ ╨╖╨░╨│╤А╤Г╨╖╨║╨╕)
        self._success_icon = PixmapLabel()
        self._success_icon.setFixedSize(16, 16)
        self._success_icon.hide()
        subtitle_row.addWidget(self._success_icon)

        # ╨Я╨╛╨┤╨╖╨░╨│╨╛╨╗╨╛╨▓╨╛╨║ (╨┐╤А╨╛╤В╨╛╨║╨╛╨╗ | ╨┐╨╛╤А╤В╤Л)
        self._subtitle = BodyLabel("")
        subtitle_row.addWidget(self._subtitle)

        # ╨Т╤Л╨▒╤А╨░╨╜╨╜╨░╤П ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤П (╨╝╨╡╨╗╨║╨╕╨╝ ╤И╤А╨╕╤Д╤В╨╛╨╝, ╤Б╨┐╤А╨░╨▓╨░ ╨╛╤В ╨┐╨╛╤А╤В╨╛╨▓)
        self._subtitle_strategy = ElidedLabel("")
        self._subtitle_strategy.setFont(QFont("Segoe UI", 11))
        try:
            self._subtitle_strategy.setProperty("tone", "muted")
        except Exception:
            pass
        self._subtitle_strategy.setStyleSheet(
            f"background: transparent; padding-left: 10px; color: {detail_text_color};"
        )
        self._subtitle_strategy.hide()
        subtitle_row.addWidget(self._subtitle_strategy, 1)

        header_layout.addLayout(subtitle_row)

        self.layout.addWidget(header)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # ╨Т╨Ъ╨Ы╨о╨з╨Х╨Э╨Ш╨Х ╨Ъ╨Р╨в╨Х╨У╨Ю╨а╨Ш╨Ш + ╨Э╨Р╨б╨в╨а╨Ю╨Щ╨Ъ╨Ш
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._settings_host = QWidget()
        settings_host_layout = QVBoxLayout(self._settings_host)
        settings_host_layout.setContentsMargins(0, 0, 0, 0)
        settings_host_layout.setSpacing(6)

        # Toggle ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╤П/╨▓╤Л╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ (╨▒╨╡╨╖ ╤Д╨╛╨╜╨╛╨▓╨╛╨╣ ╨║╨░╤А╤В╨╛╤З╨║╨╕)
        self._enable_toggle = Win11ToggleRow(
            "fa5s.power-off", "╨Т╨║╨╗╤О╤З╨╕╤В╤М ╨╛╨▒╤Е╨╛╨┤",
            "╨Р╨║╤В╨╕╨▓╨╕╤А╨╛╨▓╨░╤В╤М DPI-╨╛╨▒╤Е╨╛╨┤ ╨┤╨╗╤П ╤Н╤В╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕", "#4CAF50"
        )
        self._enable_toggle.toggled.connect(self._on_enable_toggled)
        settings_host_layout.addWidget(self._enable_toggle)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # ╨в╨г╨Ы╨С╨Р╨а ╨Э╨Р╨б╨в╨а╨Ю╨Х╨Ъ ╨Ъ╨Р╨в╨Х╨У╨Ю╨а╨Ш╨Ш (╤Д╨╛╨╜╨╛╨▓╨╛╨╣ ╨▒╨╗╨╛╨║)
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._toolbar_frame = QFrame()
        self._toolbar_frame.setObjectName("categoryToolbarFrame")
        self._toolbar_frame.setProperty("categoryDisabled", False)
        self._toolbar_frame.setFrameShape(QFrame.Shape.NoFrame)
        self._toolbar_frame.setStyleSheet(
            """
            QFrame#categoryToolbarFrame {
                border: none;
            }
            QFrame#categoryToolbarFrame:hover {
                border: none;
            }
            """
        )
        self._toolbar_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._toolbar_frame.setVisible(False)
        toolbar_layout = QVBoxLayout(self._toolbar_frame)
        toolbar_layout.setContentsMargins(0, 4, 0, 4)
        toolbar_layout.setSpacing(6)

        # ╨а╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ row
        self._filter_mode_frame = SettingsRow(
            "fa5s.filter",
            "╨а╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕",
            "Hostlist - ╨┐╨╛ ╨┤╨╛╨╝╨╡╨╜╨░╨╝, IPset - ╨┐╨╛ IP",
        )
        self._filter_mode_selector = SwitchButton(parent=self)
        self._filter_mode_selector.setOnText("IPset")
        self._filter_mode_selector.setOffText("Hostlist")
        self._filter_mode_selector.checkedChanged.connect(
            lambda checked: self._on_filter_mode_changed("ipset" if checked else "hostlist")
        )
        self._filter_mode_frame.set_control(self._filter_mode_selector)

        toolbar_layout.addWidget(self._filter_mode_frame)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # OUT RANGE SETTINGS
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._out_range_frame = SettingsRow(
            "fa5s.sliders-h",
            "Out Range",
            "╨Ю╨│╤А╨░╨╜╨╕╤З╨╡╨╜╨╕╨╡ ╨╕╤Б╤Е╨╛╨┤╤П╤Й╨╕╤Е ╨┐╨░╨║╨╡╤В╨╛╨▓ ╨┤╨╗╤П ╨╛╨▒╤А╨░╨▒╨╛╤В╨║╨╕",
        )

        mode_label = BodyLabel("╨а╨╡╨╢╨╕╨╝:")
        self._out_range_frame.control_container.addWidget(mode_label)

        self._out_range_seg = SegmentedWidget()
        self._out_range_seg.addItem("n", "n", lambda: self._select_out_range_mode("n"))
        self._out_range_seg.addItem("d", "d", lambda: self._select_out_range_mode("d"))
        set_tooltip(self._out_range_seg, "n = ╨║╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨┐╨░╨║╨╡╤В╨╛╨▓ ╤Б ╤Б╨░╨╝╨╛╨│╨╛ ╨┐╨╡╤А╨▓╨╛╨│╨╛, d = ╨╛╤В╤Б╤З╨╕╤В╤Л╨▓╨░╤В╤М ╨в╨Ю╨Ы╨м╨Ъ╨Ю ╨║╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨┐╨░╨║╨╡╤В╨╛╨▓ ╤Б ╨┤╨░╨╜╨╜╤Л╨╝╨╕ (╨╕╤Б╨║╨╗╤О╤З╨░╤П SYN-ACK-SYN ╤А╤Г╨║╨╛╨┐╨╛╨╢╨░╤В╨╕╨╡)")
        self._out_range_mode = "n"
        self._out_range_seg.setCurrentItem("n")
        self._out_range_frame.control_container.addWidget(self._out_range_seg)

        value_label = BodyLabel("╨Ч╨╜╨░╤З╨╡╨╜╨╕╨╡:")
        self._out_range_frame.control_container.addWidget(value_label)

        self._out_range_spin = SpinBox()
        self._out_range_spin.setRange(1, 999)
        self._out_range_spin.setValue(8)
        set_tooltip(self._out_range_spin, "--out-range: ╨╛╨│╤А╨░╨╜╨╕╤З╨╡╨╜╨╕╨╡ ╨║╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨░ ╨╕╤Б╤Е╨╛╨┤╤П╤Й╨╕╤Е ╨┐╨░╨║╨╡╤В╨╛╨▓ (n) ╨╕╨╗╨╕ ╨╖╨░╨┤╨╡╤А╨╢╨║╨╕ (d)")
        self._out_range_spin.valueChanged.connect(self._save_syndata_settings)
        self._out_range_frame.control_container.addWidget(self._out_range_spin)

        toolbar_layout.addWidget(self._out_range_frame)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # SEND SETTINGS (collapsible)
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._send_frame = QFrame()
        self._send_frame.setFrameShape(QFrame.Shape.NoFrame)
        send_layout = QVBoxLayout(self._send_frame)
        send_layout.setContentsMargins(0, 6, 0, 6)
        send_layout.setSpacing(8)

        self._send_toggle_row = Win11ToggleRow(
            "fa5s.paper-plane", "Send ╨┐╨░╤А╨░╨╝╨╡╤В╤А╤Л", "╨Ю╤В╨┐╤А╨░╨▓╨║╨░ ╨║╨╛╨┐╨╕╨╣ ╨┐╨░╨║╨╡╤В╨╛╨▓"
        )
        self._send_toggle = self._send_toggle_row.toggle
        self._send_toggle_row.toggled.connect(self._on_send_toggled)
        send_layout.addWidget(self._send_toggle_row)

        # Settings panel (shown when enabled)
        self._send_settings = QFrame()
        self._send_settings.setFrameShape(QFrame.Shape.NoFrame)
        self._send_settings.setVisible(False)
        send_settings_layout = QVBoxLayout(self._send_settings)
        send_settings_layout.setContentsMargins(34, 8, 0, 0)  # Indent to align with text
        send_settings_layout.setSpacing(8)

        # send_repeats row
        repeats_row = QHBoxLayout()
        repeats_row.setSpacing(8)
        repeats_label = BodyLabel("repeats:")
        repeats_label.setFixedWidth(60)
        self._send_repeats_spin = SpinBox()
        self._send_repeats_spin.setRange(0, 10)
        self._send_repeats_spin.setValue(2)
        set_tooltip(self._send_repeats_spin, "╨Ъ╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨┐╨╛╨▓╤В╨╛╤А╨╜╤Л╤Е ╨╛╤В╨┐╤А╨░╨▓╨╛╨║ ╨┐╨░╨║╨╡╤В╨░ (╨┤╨╡╤Д╨╛╨╗╤В: 2)")
        self._send_repeats_spin.valueChanged.connect(self._save_syndata_settings)
        repeats_row.addWidget(repeats_label)
        repeats_row.addWidget(self._send_repeats_spin)
        repeats_row.addStretch()
        send_settings_layout.addLayout(repeats_row)

        # send_ip_ttl row
        send_ip_ttl_row = QHBoxLayout()
        send_ip_ttl_row.setSpacing(8)
        send_ip_ttl_label = BodyLabel("ip_ttl:")
        send_ip_ttl_label.setFixedWidth(60)
        self._send_ip_ttl_selector = TTLButtonSelector(
            values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            labels=["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        )
        set_tooltip(self._send_ip_ttl_selector, "TTL ╨┤╨╗╤П IPv4 ╨╛╤В╨┐╤А╨░╨▓╨╗╤П╨╡╨╝╤Л╤Е ╨┐╨░╨║╨╡╤В╨╛╨▓ (off = auto)")
        self._send_ip_ttl_selector.value_changed.connect(self._save_syndata_settings)
        send_ip_ttl_row.addWidget(send_ip_ttl_label)
        send_ip_ttl_row.addWidget(self._send_ip_ttl_selector)
        send_ip_ttl_row.addStretch()
        send_settings_layout.addLayout(send_ip_ttl_row)

        # send_ip6_ttl row
        send_ip6_ttl_row = QHBoxLayout()
        send_ip6_ttl_row.setSpacing(8)
        send_ip6_ttl_label = BodyLabel("ip6_ttl:")
        send_ip6_ttl_label.setFixedWidth(60)
        self._send_ip6_ttl_selector = TTLButtonSelector(
            values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            labels=["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        )
        set_tooltip(self._send_ip6_ttl_selector, "TTL ╨┤╨╗╤П IPv6 ╨╛╤В╨┐╤А╨░╨▓╨╗╤П╨╡╨╝╤Л╤Е ╨┐╨░╨║╨╡╤В╨╛╨▓ (off = auto)")
        self._send_ip6_ttl_selector.value_changed.connect(self._save_syndata_settings)
        send_ip6_ttl_row.addWidget(send_ip6_ttl_label)
        send_ip6_ttl_row.addWidget(self._send_ip6_ttl_selector)
        send_ip6_ttl_row.addStretch()
        send_settings_layout.addLayout(send_ip6_ttl_row)

        # send_ip_id row
        send_ip_id_row = QHBoxLayout()
        send_ip_id_row.setSpacing(8)
        send_ip_id_label = BodyLabel("ip_id:")
        send_ip_id_label.setFixedWidth(60)
        self._send_ip_id_combo = ComboBox()
        self._send_ip_id_combo.addItems(["none", "seq", "rnd", "zero"])
        set_tooltip(self._send_ip_id_combo, "╨а╨╡╨╢╨╕╨╝ IP ID ╨┤╨╗╤П ╨╛╤В╨┐╤А╨░╨▓╨╗╤П╨╡╨╝╤Л╤Е ╨┐╨░╨║╨╡╤В╨╛╨▓")
        self._send_ip_id_combo.currentTextChanged.connect(self._save_syndata_settings)
        send_ip_id_row.addWidget(send_ip_id_label)
        send_ip_id_row.addWidget(self._send_ip_id_combo)
        send_ip_id_row.addStretch()
        send_settings_layout.addLayout(send_ip_id_row)

        # send_badsum row
        send_badsum_row = QHBoxLayout()
        send_badsum_row.setSpacing(8)
        send_badsum_label = BodyLabel("badsum:")
        send_badsum_label.setFixedWidth(60)
        self._send_badsum_check = CheckBox()
        set_tooltip(self._send_badsum_check, "╨Ю╤В╨┐╤А╨░╨▓╨╗╤П╤В╤М ╨┐╨░╨║╨╡╤В╤Л ╤Б ╨╜╨╡╨┐╤А╨░╨▓╨╕╨╗╤М╨╜╨╛╨╣ ╨║╨╛╨╜╤В╤А╨╛╨╗╤М╨╜╨╛╨╣ ╤Б╤Г╨╝╨╝╨╛╨╣")
        self._send_badsum_check.stateChanged.connect(self._save_syndata_settings)
        send_badsum_row.addWidget(send_badsum_label)
        send_badsum_row.addWidget(self._send_badsum_check)
        send_badsum_row.addStretch()
        send_settings_layout.addLayout(send_badsum_row)

        send_layout.addWidget(self._send_settings)
        toolbar_layout.addWidget(self._send_frame)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # SYNDATA SETTINGS (collapsible)
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._syndata_frame = QFrame()
        self._syndata_frame.setFrameShape(QFrame.Shape.NoFrame)
        syndata_layout = QVBoxLayout(self._syndata_frame)
        syndata_layout.setContentsMargins(0, 6, 0, 6)
        syndata_layout.setSpacing(8)

        self._syndata_toggle_row = Win11ToggleRow(
            "fa5s.cog", "Syndata ╨┐╨░╤А╨░╨╝╨╡╤В╤А╤Л", "╨Ф╨╛╨┐╨╛╨╗╨╜╨╕╤В╨╡╨╗╤М╨╜╤Л╨╡ ╨┐╨░╤А╨░╨╝╨╡╤В╤А╤Л ╨╛╨▒╤Е╨╛╨┤╨░ DPI"
        )
        self._syndata_toggle = self._syndata_toggle_row.toggle
        self._syndata_toggle_row.toggled.connect(self._on_syndata_toggled)
        syndata_layout.addWidget(self._syndata_toggle_row)

        # Settings panel (shown when enabled)
        self._syndata_settings = QFrame()
        self._syndata_settings.setFrameShape(QFrame.Shape.NoFrame)
        self._syndata_settings.setVisible(False)
        settings_layout = QVBoxLayout(self._syndata_settings)
        settings_layout.setContentsMargins(34, 8, 0, 0)  # Indent to align with text
        settings_layout.setSpacing(8)

        # Blob selector row
        blob_row = QHBoxLayout()
        blob_row.setSpacing(8)
        blob_label = BodyLabel("blob:")
        blob_label.setFixedWidth(60)
        self._blob_combo = ComboBox()
        # Get all available blobs (system + user)
        try:
            all_blobs = get_blobs_info()
            blob_names = ["none"] + sorted(all_blobs.keys())
        except Exception:
            # Fallback to basic list if blobs module fails
            blob_names = ["none", "tls_google", "tls7"]
        self._blob_combo.addItems(blob_names)
        self._blob_combo.currentTextChanged.connect(self._save_syndata_settings)
        blob_row.addWidget(blob_label)
        blob_row.addWidget(self._blob_combo)
        blob_row.addStretch()
        settings_layout.addLayout(blob_row)

        # tls_mod selector row
        tls_mod_row = QHBoxLayout()
        tls_mod_row.setSpacing(8)
        tls_mod_label = BodyLabel("tls_mod:")
        tls_mod_label.setFixedWidth(60)
        self._tls_mod_combo = ComboBox()
        self._tls_mod_combo.addItems(["none", "rnd", "rndsni", "sni=google.com"])
        self._tls_mod_combo.currentTextChanged.connect(self._save_syndata_settings)
        tls_mod_row.addWidget(tls_mod_label)
        tls_mod_row.addWidget(self._tls_mod_combo)
        tls_mod_row.addStretch()
        settings_layout.addLayout(tls_mod_row)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # AUTOTTL SETTINGS (╤В╤А╨╕ ╤Б╤В╤А╨╛╨║╨╕ ╤Б ╨║╨╜╨╛╨┐╨║╨░╨╝╨╕)
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        autottl_header = CaptionLabel("AutoTTL")
        settings_layout.addWidget(autottl_header)

        # ╨Ъ╨╛╨╜╤В╨╡╨╣╨╜╨╡╤А ╨┤╨╗╤П ╤В╤А╤С╤Е ╤Б╤В╤А╨╛╨║ autottl
        autottl_container = QVBoxLayout()
        autottl_container.setSpacing(6)
        autottl_container.setContentsMargins(0, 0, 0, 0)

        # --- Delta row ---
        delta_row = QHBoxLayout()
        delta_row.setSpacing(8)
        delta_label = BodyLabel("d:")
        delta_label.setFixedWidth(30)
        self._autottl_delta_selector = TTLButtonSelector(
            values=[0, -1, -2, -3, -4, -5, -6, -7, -8, -9],
            labels=["OFF", "-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"]
        )
        set_tooltip(self._autottl_delta_selector, "Delta: ╤Б╨╝╨╡╤Й╨╡╨╜╨╕╨╡ ╨╛╤В ╨╕╨╖╨╝╨╡╤А╨╡╨╜╨╜╨╛╨│╨╛ TTL (OFF = ╤Г╨▒╤А╨░╤В╤М ip_autottl)")
        self._autottl_delta_selector.value_changed.connect(self._save_syndata_settings)
        delta_row.addWidget(delta_label)
        delta_row.addWidget(self._autottl_delta_selector)
        delta_row.addStretch()
        autottl_container.addLayout(delta_row)

        # --- Min row ---
        min_row = QHBoxLayout()
        min_row.setSpacing(8)
        min_label = BodyLabel("min:")
        min_label.setFixedWidth(30)
        self._autottl_min_selector = TTLButtonSelector(
            values=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            labels=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        )
        set_tooltip(self._autottl_min_selector, "╨Ь╨╕╨╜╨╕╨╝╨░╨╗╤М╨╜╤Л╨╣ TTL")
        self._autottl_min_selector.value_changed.connect(self._save_syndata_settings)
        min_row.addWidget(min_label)
        min_row.addWidget(self._autottl_min_selector)
        min_row.addStretch()
        autottl_container.addLayout(min_row)

        # --- Max row ---
        max_row = QHBoxLayout()
        max_row.setSpacing(8)
        max_label = BodyLabel("max:")
        max_label.setFixedWidth(30)
        self._autottl_max_selector = TTLButtonSelector(
            values=[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            labels=["15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
        )
        set_tooltip(self._autottl_max_selector, "╨Ь╨░╨║╤Б╨╕╨╝╨░╨╗╤М╨╜╤Л╨╣ TTL")
        self._autottl_max_selector.value_changed.connect(self._save_syndata_settings)
        max_row.addWidget(max_label)
        max_row.addWidget(self._autottl_max_selector)
        max_row.addStretch()
        autottl_container.addLayout(max_row)

        settings_layout.addLayout(autottl_container)

        # TCP flags row
        flags_row = QHBoxLayout()
        flags_row.setSpacing(8)
        flags_label = BodyLabel("tcp_flags_unset:")
        flags_label.setFixedWidth(100)
        self._tcp_flags_combo = ComboBox()
        self._tcp_flags_combo.addItems(["none", "ack", "psh", "ack,psh"])
        self._tcp_flags_combo.currentTextChanged.connect(self._save_syndata_settings)
        flags_row.addWidget(flags_label)
        flags_row.addWidget(self._tcp_flags_combo)
        flags_row.addStretch()
        settings_layout.addLayout(flags_row)

        syndata_layout.addWidget(self._syndata_settings)
        toolbar_layout.addWidget(self._syndata_frame)

        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        # PRESET ACTIONS + RESET SETTINGS BUTTON
        # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
        self._reset_row_widget = QWidget()
        reset_row = QHBoxLayout(self._reset_row_widget)
        reset_row.setContentsMargins(0, 8, 0, 0)
        reset_row.setSpacing(8)

        self._create_preset_btn = ActionButton("╨б╨╛╨╖╨┤╨░╤В╤М ╨┐╤А╨╡╤Б╨╡╤В", "fa5s.plus")
        set_tooltip(self._create_preset_btn, "╨б╨╛╨╖╨┤╨░╤В╤М ╨╜╨╛╨▓╤Л╨╣ ╨┐╤А╨╡╤Б╨╡╤В ╨╜╨░ ╨╛╤Б╨╜╨╛╨▓╨╡ ╤В╨╡╨║╤Г╤Й╨╕╤Е ╨╜╨░╤Б╤В╤А╨╛╨╡╨║")
        self._create_preset_btn.clicked.connect(self._on_create_preset_clicked)
        reset_row.addWidget(self._create_preset_btn)

        self._rename_preset_btn = ActionButton("╨Я╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╤В╤М", "fa5s.pen")
        set_tooltip(self._rename_preset_btn, "╨Я╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╤В╤М ╤В╨╡╨║╤Г╤Й╨╕╨╣ ╨░╨║╤В╨╕╨▓╨╜╤Л╨╣ ╨┐╤А╨╡╤Б╨╡╤В")
        self._rename_preset_btn.clicked.connect(self._on_rename_preset_clicked)
        reset_row.addWidget(self._rename_preset_btn)

        reset_row.addStretch()

        self._reset_settings_btn = ResetActionButton(
            "╨б╨▒╤А╨╛╤Б╨╕╤В╤М ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕",
            confirm_text="╨б╨▒╤А╨╛╤Б╨╕╤В╤М ╨▓╤Б╨╡?"
        )
        self._reset_settings_btn.reset_confirmed.connect(self._on_reset_settings_confirmed)
        reset_row.addWidget(self._reset_settings_btn)

        toolbar_layout.addWidget(self._reset_row_widget)

        settings_host_layout.addWidget(self._toolbar_frame)
        self.layout.addWidget(self._settings_host)

        # Strategy controls stay visible even for disabled categories.
        self._strategies_block = QWidget()
        self._strategies_block.setObjectName("categoryStrategiesBlock")
        self._strategies_block.setProperty("categoryDisabled", False)
        self._strategies_block.setVisible(False)
        strategies_layout = QVBoxLayout(self._strategies_block)
        strategies_layout.setContentsMargins(0, 0, 0, 0)
        strategies_layout.setSpacing(0)

        # ╨Я╨╛╨╕╤Б╨║ ╨┐╨╛ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤П╨╝
        self._search_bar_widget = QWidget()
        search_layout = QHBoxLayout(self._search_bar_widget)
        search_layout.setContentsMargins(0, 0, 0, 8)
        # Add explicit spacing between the search input and icon buttons.
        # Previously it was 0, which made icons stick together visually.
        search_layout.setSpacing(6)

        self._search_input = LineEdit()
        self._search_input.setPlaceholderText("╨Я╨╛╨╕╤Б╨║ ╨┐╨╛ ╨╕╨╝╨╡╨╜╨╕ ╨╕╨╗╨╕ args...")
        self._search_input.setFixedHeight(36)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        # ╨Ъ╨╜╨╛╨┐╨║╨░ ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨╕
        self._sort_btn = TransparentToolButton(parent=self)
        self._sort_btn.setIconSize(QSize(16, 16))
        self._sort_btn.setFixedSize(36, 36)
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_tooltip(self._sort_btn, "╨б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨░")
        self._sort_btn.clicked.connect(self._show_sort_menu)
        search_layout.addWidget(self._sort_btn)

        # ComboBox ╤Д╨╕╨╗╤М╤В╤А╨░ ╨┐╨╛ ╤В╨╡╤Е╨╜╨╕╨║╨╡ (╨╛╨┤╨╕╨╜╨╛╤З╨╜╤Л╨╣ ╨▓╤Л╨▒╨╛╤А)
        self._filter_combo = ComboBox(parent=self)
        self._filter_combo.setFixedHeight(36)
        self._filter_combo.setFixedWidth(130)
        self._filter_combo.addItem("╨Т╤Б╨╡ ╤В╨╡╤Е╨╜╨╕╨║╨╕")
        for label, _key in STRATEGY_TECHNIQUE_FILTERS:
            self._filter_combo.addItem(label)
        self._filter_combo.setCurrentIndex(0)
        self._filter_combo.currentIndexChanged.connect(self._on_technique_filter_changed)
        search_layout.addWidget(self._filter_combo)

        # ╨Ъ╨╜╨╛╨┐╨║╨░ ╤А╨╡╨┤╨░╨║╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П args (╨╗╨╡╨╜╨╕╨▓╨╛, ╨╛╤В╨┤╨╡╨╗╤М╨╜╨░╤П ╨┐╨░╨╜╨╡╨╗╤М)
        try:
            from qfluentwidgets import FluentIcon as _FIF
            self._edit_args_btn = TransparentToolButton(_FIF.EDIT, parent=self)
        except Exception:
            self._edit_args_btn = TransparentToolButton(parent=self)
            self._edit_args_btn.setIcon(qta.icon('fa5s.edit', color=tokens.fg_faint))
        self._edit_args_btn.setIconSize(QSize(16, 16))
        self._edit_args_btn.setFixedSize(36, 36)
        self._edit_args_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_tooltip(self._edit_args_btn, "╨Р╤А╨│╤Г╨╝╨╡╨╜╤В╤Л ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ (╨┐╨╛ ╨▓╤Л╨▒╤А╨░╨╜╨╜╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕)")
        self._edit_args_btn.setEnabled(False)
        self._edit_args_btn.clicked.connect(self._toggle_args_editor)
        search_layout.addWidget(self._edit_args_btn)

        # Initialize dynamic visuals/tooltips (sort/filter buttons).
        self._update_sort_button_ui()
        self._update_technique_filter_ui()

        strategies_layout.addWidget(self._search_bar_widget)

        self._args_editor_dirty = False

        # TCP multi-phase "tabs" (shown only for tcp categories in direct_zapret2)
        self._phases_bar_widget = QWidget()
        self._phases_bar_widget.setVisible(False)
        try:
            # Prevent frameless window drag from stealing tab clicks.
            self._phases_bar_widget.setProperty("noDrag", True)
        except Exception:
            pass
        phases_layout = QHBoxLayout(self._phases_bar_widget)
        phases_layout.setContentsMargins(0, 0, 0, 8)
        phases_layout.setSpacing(0)

        # SegmentedWidget (qfluentwidgets) for TCP multi-phase tab selection.
        self._phase_tabbar = SegmentedWidget(self)
        try:
            self._phase_tabbar.setProperty("noDrag", True)
        except Exception:
            pass

        self._phase_tab_index_by_key = {}
        self._phase_tab_key_by_index = {}
        for i, (phase_key, label) in enumerate(TCP_PHASE_TAB_ORDER):
            key = str(phase_key or "").strip().lower()
            self._phase_tab_index_by_key[key] = i
            self._phase_tab_key_by_index[i] = key
            try:
                self._phase_tabbar.addItem(
                    key, label,
                    onClick=lambda k=key: self._on_phase_pivot_item_clicked(k)
                )
            except Exception:
                pass

        try:
            self._phase_tabbar.currentItemChanged.connect(self._on_phase_tab_changed)
        except Exception:
            pass

        phases_layout.addWidget(self._phase_tabbar, 1)
        strategies_layout.addWidget(self._phases_bar_widget)

        # ╨Ы╤С╨│╨║╨╕╨╣ ╤Б╨┐╨╕╤Б╨╛╨║ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣: item-based, ╨▒╨╡╨╖ ╤Б╨╛╤В╨╡╨╜ QWidget ╨▓ layout
        self._strategies_tree = DirectZapret2StrategiesTree(self)
        # ╨Т╨╜╤Г╤В╤А╨╡╨╜╨╜╨╕╨╣ ╤Б╨║╤А╨╛╨╗╨╗ ╤Г ╨┤╨╡╤А╨╡╨▓╨░ (╨╜╨░╨┤╤С╨╢╨╜╨╡╨╡, ╤З╨╡╨╝ ╤А╨░╤Б╤В╤П╨│╨╕╨▓╨░╤В╤М ╤Б╤В╤А╨░╨╜╨╕╤Ж╤Г ╨┐╨╛ ╨▓╤Л╤Б╨╛╤В╨╡)
        self._strategies_tree.setProperty("noDrag", True)
        self._strategies_tree.strategy_clicked.connect(self._on_row_clicked)
        self._strategies_tree.favorite_toggled.connect(self._on_favorite_toggled)
        self._strategies_tree.working_mark_requested.connect(self._on_tree_working_mark_requested)
        self._strategies_tree.preview_requested.connect(self._on_tree_preview_requested)
        self._strategies_tree.preview_pinned_requested.connect(self._on_tree_preview_pinned_requested)
        self._strategies_tree.preview_hide_requested.connect(self._on_tree_preview_hide_requested)
        strategies_layout.addWidget(self._strategies_tree, 1)

        self.layout.addWidget(self._strategies_block, 1)

    def _update_selected_strategy_header(self, strategy_id: str) -> None:
        """╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╤В ╨┐╨╛╨┤╨╖╨░╨│╨╛╨╗╨╛╨▓╨╛╨║: ╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В ╨▓╤Л╨▒╤А╨░╨╜╨╜╤Г╤О ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╤А╤П╨┤╨╛╨╝ ╤Б ╨┐╨╛╤А╤В╨░╨╝╨╕."""
        sid = (strategy_id or "none").strip()

        # TCP multi-phase summary (fake + multi*)
        if self._tcp_phase_mode:
            if sid == "none":
                try:
                    self._subtitle_strategy.hide()
                except Exception:
                    pass
                return

            parts: list[str] = []
            for phase in TCP_PHASE_COMMAND_ORDER:
                if phase == "fake" and self._tcp_hide_fake_phase:
                    continue
                psid = (self._tcp_phase_selected_ids.get(phase) or "").strip()
                if not psid:
                    continue
                if phase == "fake" and psid == TCP_FAKE_DISABLED_STRATEGY_ID:
                    continue

                if psid == CUSTOM_STRATEGY_ID:
                    name = CUSTOM_STRATEGY_ID
                else:
                    try:
                        data = dict(self._strategies_data_by_id.get(psid, {}) or {})
                    except Exception:
                        data = {}
                    name = str(data.get("name") or psid).strip() or psid

                parts.append(f"{phase}={name}")

            text = "; ".join(parts).strip()
            if not text:
                try:
                    self._subtitle_strategy.hide()
                except Exception:
                    pass
                return

            try:
                self._subtitle_strategy.set_full_text(text)
                set_tooltip(self._subtitle_strategy, text)
                self._subtitle_strategy.show()
            except Exception:
                pass
            return

        if sid == "none":
            try:
                self._subtitle_strategy.hide()
            except Exception:
                pass
            return

        try:
            data = dict(self._strategies_data_by_id.get(sid, {}) or {})
        except Exception:
            data = {}
        name = str(data.get("name") or sid).strip() or sid

        try:
            self._subtitle_strategy.set_full_text(name)
            set_tooltip(self._subtitle_strategy, f"{name}\nID: {sid}")
            self._subtitle_strategy.show()
        except Exception:
            pass

    def show_category(self, category_key: str, category_info, current_strategy_id: str):
        """
        ╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┤╨╗╤П ╨▓╤Л╨▒╤А╨░╨╜╨╜╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕.

        Args:
            category_key: ╨Ъ╨╗╤О╤З ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, "youtube_https")
            category_info: ╨Ю╨▒╤К╨╡╨║╤В CategoryInfo ╤Б ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╨╡╨╣ ╨╛ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
            current_strategy_id: ID ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╨▓╤Л╨▒╤А╨░╨╜╨╜╨╛╨╣ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕
        """
        self._ensure_content_built()

        prev_key = str(self._category_key or "").strip()
        if prev_key:
            self._save_scroll_state(prev_key)

        log(f"StrategyDetailPage.show_category: {category_key}, current={current_strategy_id}", "DEBUG")
        self._category_key = category_key
        self._category_info = category_info
        self._current_strategy_id = current_strategy_id or "none"
        self._selected_strategy_id = self._current_strategy_id
        self._close_preview_dialog(force=True)
        try:
            self._favorite_strategy_ids = self._favorites_store.get_favorites(category_key)
        except Exception:
            self._favorite_strategy_ids = set()

        # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╨╖╨░╨│╨╛╨╗╨╛╨▓╨╛╨║ (╤В╨╛╨╗╤М╨║╨╛ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╨▓ breadcrumb)
        self._title.setText(category_info.full_name)
        self._subtitle.setText(f"{category_info.protocol}  |  ╨┐╨╛╤А╤В╤Л: {category_info.ports}")
        self._update_selected_strategy_header(self._selected_strategy_id)

        # Sync BreadcrumbBar with the new category
        if self._breadcrumb is not None:
            self._breadcrumb.blockSignals(True)
            try:
                self._breadcrumb.clear()
                self._breadcrumb.addItem("control", "╨г╨┐╤А╨░╨▓╨╗╨╡╨╜╨╕╨╡")
                self._breadcrumb.addItem("strategies", "╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ DPI")
                self._breadcrumb.addItem("detail", category_info.full_name)
            finally:
                self._breadcrumb.blockSignals(False)

        # Determine whether to use the TCP multi-phase UI:
        # - only for TCP strategies (tcp.txt)
        # - only for direct_zapret2 advanced set (no orchestra/zapret1/basic)
        new_strategy_type = str(getattr(category_info, "strategy_type", "") or "tcp").strip().lower()
        is_udp_like_now = self._is_udp_like_category()
        try:
            from strategy_menu.strategies_registry import get_current_strategy_set
            strategy_set = get_current_strategy_set()
        except Exception:
            strategy_set = None
        want_tcp_phase_mode = (
            (new_strategy_type == "tcp")
            and (not is_udp_like_now)
            and (strategy_set in (None, "advanced"))
        )

        self._tcp_phase_mode = bool(want_tcp_phase_mode)
        try:
            if hasattr(self, "_filter_btn") and self._filter_btn is not None:
                self._filter_btn.setVisible(not self._tcp_phase_mode)
        except Exception:
            pass
        try:
            if hasattr(self, "_phases_bar_widget") and self._phases_bar_widget is not None:
                self._phases_bar_widget.setVisible(self._tcp_phase_mode)
        except Exception:
            pass

        # ╨Ф╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╣ ╨╛╨┤╨╜╨╛╨│╨╛ strategy_type (╨╛╤Б╨╛╨▒╨╡╨╜╨╜╨╛ tcp) ╤Б╨┐╨╕╤Б╨╛╨║ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣ ╨╛╨┤╨╕╨╜╨░╨║╨╛╨▓╤Л╨╣,
        # ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╨╜╨╡ ╨┐╨╡╤А╨╡╤Б╨╛╨▒╨╕╤А╨░╨╡╨╝ ╨▓╨╕╨┤╨╢╨╡╤В╤Л ╨║╨░╨╢╨┤╤Л╨╣ ╤А╨░╨╖: ╤Н╤В╨╛ ╤Г╤Б╨║╨╛╤А╤П╨╡╤В ╨┐╨╛╨▓╤В╨╛╤А╨╜╤Л╨╡ ╨┐╨╡╤А╨╡╤Е╨╛╨┤╤Л.
        reuse_list = (
            bool(self._strategies_tree and self._strategies_tree.has_rows())
            and self._loaded_strategy_type == new_strategy_type
            and self._loaded_strategy_set == strategy_set
            and bool(self._loaded_tcp_phase_mode) == bool(want_tcp_phase_mode)
        )

        if not reuse_list:
            # ╨Ю╤З╨╕╤Й╨░╨╡╨╝ ╤Б╤В╨░╤А╤Л╨╡ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕
            self._clear_strategies()
            # ╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╨╝ ╨╜╨╛╨▓╤Л╨╡
            self._load_strategies()
        else:
            # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╨╕╨╖╨▒╤А╨░╨╜╨╜╨╛╨╡ ╨┤╨╗╤П ╨╜╨╛╨▓╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
            for sid in (self._strategies_tree.get_strategy_ids() if self._strategies_tree else []):
                want_fav = sid in self._favorite_strategy_ids
                self._strategies_tree.set_favorite_state(sid, want_fav)

            # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╨╛╤В╨╝╨╡╤В╨║╨╕ working/not working ╨┤╨╗╤П ╨╜╨╛╨▓╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
            self._refresh_working_marks_for_category()

            # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╨▓╤Л╨┤╨╡╨╗╨╡╨╜╨╕╨╡ ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕
            if self._strategies_tree:
                if self._strategies_tree.has_strategy(self._current_strategy_id):
                    self._strategies_tree.set_selected_strategy(self._current_strategy_id)
                elif self._strategies_tree.has_strategy("none"):
                    self._strategies_tree.set_selected_strategy("none")
                else:
                    self._strategies_tree.clearSelection()
            # ╨Т╨╛╤Б╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╨╝ ╨┐╨╛╤Б╨╗╨╡╨┤╨╜╤О╤О ╨┐╨╛╨╖╨╕╤Ж╨╕╤О ╨┐╤А╨╛╨║╤А╤Г╤В╨║╨╕ ╨┤╨╗╤П ╤Н╤В╨╛╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕.
            self._restore_scroll_state(category_key, defer=True)

        # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╡ toggle ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╤П
        is_enabled = self._current_strategy_id != "none"
        self._enable_toggle.setChecked(is_enabled, block_signals=True)

        # ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ ╨│╨░╨╗╨╛╤З╨║╤Г ╤Б╤В╨░╤В╤Г╤Б╨░
        self._update_status_icon(is_enabled)

        # ╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╤А╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ ╤В╨╛╨╗╤М╨║╨╛ ╨╡╤Б╨╗╨╕ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤П ╨┐╨╛╨┤╨┤╨╡╤А╨╢╨╕╨▓╨░╨╡╤В ╨╛╨▒╨░ ╨▓╨░╤А╨╕╨░╨╜╤В╨░
        has_ipset = hasattr(category_info, 'base_filter_ipset') and category_info.base_filter_ipset
        has_hostlist = hasattr(category_info, 'base_filter_hostlist') and category_info.base_filter_hostlist
        if has_ipset and has_hostlist:
            self._filter_mode_frame.setVisible(True)
            saved_filter_mode = self._load_category_filter_mode(category_key)
            self._filter_mode_selector.blockSignals(True)
            self._filter_mode_selector.setChecked(saved_filter_mode == "ipset")
            self._filter_mode_selector.blockSignals(False)
        else:
            self._filter_mode_frame.setVisible(False)

        # ╨Ю╤З╨╕╤Й╨░╨╡╨╝ ╨┐╨╛╨╕╤Б╨║ ╨╕ ╨╖╨░╨│╤А╤Г╨╢╨░╨╡╨╝ ╤Б╨╛╤Е╤А╨░╨╜╤С╨╜╨╜╤Г╤О ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╤Г
        self._search_input.clear()
        self._sort_mode = self._load_category_sort(category_key)

        # ╨б╨▒╤А╨░╤Б╤Л╨▓╨░╨╡╨╝ ╤Д╨╕╨╗╤М╤В╤А╤Л ╨┐╨╛ ╤В╨╡╤Е╨╜╨╕╨║╨╡
        self._active_filters.clear()
        self._update_technique_filter_ui()

        # TCP multi-phase state
        if self._tcp_phase_mode:
            self._load_tcp_phase_state_from_preset()
            self._apply_tcp_phase_tabs_visibility()
            preferred = None
            try:
                preferred = (self._last_active_phase_key_by_category or {}).get(category_key)
            except Exception:
                preferred = None
            if not preferred:
                preferred = self._load_category_last_tcp_phase_tab(category_key)
                if preferred:
                    try:
                        self._last_active_phase_key_by_category[category_key] = preferred
                    except Exception:
                        pass
            if preferred:
                self._set_active_phase_chip(preferred)
            else:
                self._select_default_tcp_phase_tab()

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ ╤Б╨╛╤Е╤А╨░╨╜╤С╨╜╨╜╤Г╤О ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╤Г (╨╡╤Б╨╗╨╕ ╨╜╨╡ default)
        self._apply_sort()
        self._apply_filters()

        # ╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╨╝ syndata ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
        syndata_settings = self._load_syndata_settings(category_key)
        self._apply_syndata_settings(syndata_settings)

        # direct_zapret2 Basic: hide advanced Send/Syndata UI without mutating stored settings.
        is_basic_direct = (strategy_set == "basic")

        # syndata/send are supported only for TCP SYN; for UDP/QUIC always hide.
        protocol_raw = str(getattr(category_info, "protocol", "") or "").upper()
        is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)

        if is_basic_direct:
            self._send_frame.setVisible(False)
            self._syndata_frame.setVisible(False)
            try:
                if hasattr(self, "_reset_row_widget") and self._reset_row_widget is not None:
                    self._reset_row_widget.setVisible(False)
            except Exception:
                pass
        elif is_udp_like:
            # Force-off without saving (only affects visual state and subsequent saves)
            # UDP/QUIC: remove send (same limitation as syndata)
            self._send_toggle.blockSignals(True)
            self._send_toggle.setChecked(False)
            self._send_toggle.blockSignals(False)
            self._send_settings.setVisible(False)
            self._send_frame.setVisible(False)

            self._syndata_toggle.blockSignals(True)
            self._syndata_toggle.setChecked(False)
            self._syndata_toggle.blockSignals(False)
            self._syndata_settings.setVisible(False)
            self._syndata_frame.setVisible(False)

            try:
                if hasattr(self, "_reset_row_widget") and self._reset_row_widget is not None:
                    self._reset_row_widget.setVisible(True)
            except Exception:
                pass
        else:
            self._send_frame.setVisible(True)
            self._syndata_frame.setVisible(True)
            try:
                if hasattr(self, "_reset_row_widget") and self._reset_row_widget is not None:
                    self._reset_row_widget.setVisible(True)
            except Exception:
                pass

        # Args editor availability depends on whether category is enabled (strategy != none)
        self._refresh_args_editor_state()
        self._set_category_enabled_ui(is_enabled)

        log(f"StrategyDetailPage: ╨┐╨╛╨║╨░╨╖╨░╨╜╨░ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤П {category_key}, sort_mode={self._sort_mode}", "DEBUG")

    def refresh_from_preset_switch(self):
        """
        ╨Р╤Б╨╕╨╜╤Е╤А╨╛╨╜╨╜╨╛ ╨┐╨╡╤А╨╡╤З╨╕╤В╤Л╨▓╨░╨╡╤В ╨░╨║╤В╨╕╨▓╨╜╤Л╨╣ ╨┐╤А╨╡╤Б╨╡╤В ╨╕ ╨╛╨▒╨╜╨╛╨▓╨╗╤П╨╡╤В ╤В╨╡╨║╤Г╤Й╤Г╤О ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤О (╨╡╤Б╨╗╨╕ ╨╛╤В╨║╤А╤Л╤В╨░).
        ╨Т╤Л╨╖╤Л╨▓╨░╨╡╤В╤Б╤П ╨╕╨╖ MainWindow ╨┐╨╛╤Б╨╗╨╡ ╨░╨║╤В╨╕╨▓╨░╤Ж╨╕╨╕ ╨┐╤А╨╡╤Б╨╡╤В╨░.
        """
        try:
            QTimer.singleShot(0, self._apply_preset_refresh)
        except Exception:
            try:
                self._apply_preset_refresh()
            except Exception:
                pass

    def _apply_preset_refresh(self):
        if not self._category_key:
            return

        try:
            from strategy_menu.strategies_registry import registry
            category_info = registry.get_category_info(self._category_key) or self._category_info
        except Exception:
            category_info = self._category_info

        if not category_info:
            return

        try:
            selections = self._preset_manager.get_strategy_selections() or {}
            current_strategy_id = selections.get(self._category_key, "none") or "none"
        except Exception:
            current_strategy_id = "none"

        try:
            self.show_category(self._category_key, category_info, current_strategy_id)
        except Exception:
            return

    def _scroll_to_current_strategy(self) -> None:
        """╨Я╤А╨╛╨║╤А╤Г╤З╨╕╨▓╨░╨╡╤В ╤Б╤В╤А╨░╨╜╨╕╤Ж╤Г ╨║ ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ (╨╜╨╡ ╨╝╨╡╨╜╤П╤П ╨┐╨╛╤А╤П╨┤╨╛╨║ ╤Б╨┐╨╕╤Б╨║╨░)."""
        if not self._strategies_tree:
            return

        sid = self._current_strategy_id or "none"
        if sid == "none":
            try:
                bar = self.verticalScrollBar()
                bar.setValue(bar.minimum())
            except Exception:
                pass
            return

        rect = self._strategies_tree.get_strategy_item_rect(sid)
        if rect is None:
            return

        try:
            vp = self._strategies_tree.viewport()
            center = vp.mapTo(self.content, rect.center())
            # ymargin: ╨╜╨╡╨╝╨╜╨╛╨│╨╛ ╨║╨╛╨╜╤В╨╡╨║╤Б╤В╨░ ╨▓╨╛╨║╤А╤Г╨│ ╤Б╤В╤А╨╛╨║╨╕
            self.ensureVisible(center.x(), center.y(), 0, 64)
        except Exception:
            pass

    def _clear_strategies(self):
        """╨Ю╤З╨╕╤Й╨░╨╡╤В ╤Б╨┐╨╕╤Б╨╛╨║ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣"""
        # ╨Ю╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╨╝ ╨╗╨╡╨╜╨╕╨▓╤Г╤О ╨╖╨░╨│╤А╤Г╨╖╨║╤Г ╨╡╤Б╨╗╨╕ ╨╛╨╜╨░ ╨╕╨┤╤С╤В
        self._strategies_load_generation += 1
        if self._strategies_load_timer:
            try:
                self._strategies_load_timer.stop()
                self._strategies_load_timer.deleteLater()
            except Exception:
                pass
            self._strategies_load_timer = None
        self._pending_strategies_items = []
        self._pending_strategies_index = 0

        if self._strategies_tree:
            self._strategies_tree.clear_strategies()
        self._strategies_data_by_id = {}
        self._loaded_strategy_type = None
        self._loaded_strategy_set = None
        self._loaded_tcp_phase_mode = False
        self._default_strategy_order = []
        self._strategies_loaded_fully = False

    def _load_strategies(self):
        """╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╤В ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┤╨╗╤П ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕"""
        try:
            from strategy_menu.strategies_registry import registry

            # ╨Я╨╛╨╗╤Г╤З╨░╨╡╨╝ ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤О ╨╛ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
            category_info = registry.get_category_info(self._category_key)
            if category_info:
                log(f"StrategyDetailPage: ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤П {self._category_key}, strategy_type={category_info.strategy_type}", "DEBUG")
            else:
                log(f"StrategyDetailPage: ╨║╨░╤В╨╡╨│╨╛╤А╨╕╤П {self._category_key} ╨╜╨╡ ╨╜╨░╨╣╨┤╨╡╨╜╨░ ╨▓ ╤А╨╡╨╡╤Б╤В╤А╨╡!", "ERROR")
                return

            # ╨Я╨╛╨╗╤Г╤З╨░╨╡╨╝ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕
            strategies = registry.get_category_strategies(self._category_key)
            log(f"StrategyDetailPage: ╨╖╨░╨│╤А╤Г╨╢╨╡╨╜╨╛ {len(strategies)} ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣ ╨┤╨╗╤П {self._category_key}", "DEBUG")

            # TCP multi-phase: load additional pure-fake strategies from tcp_fake.txt
            if self._tcp_phase_mode:
                try:
                    from strategy_menu.strategies_registry import get_current_strategy_set
                    from strategy_menu.strategy_loader import load_strategies_as_dict
                    current_set = get_current_strategy_set()
                    fake_set = "advanced" if current_set == "advanced" else None
                    fake_strategies = load_strategies_as_dict("tcp_fake", fake_set)
                except Exception:
                    fake_strategies = {}

                combined = {}
                # Preserve source ordering: tcp_fake.txt first, then tcp.txt
                combined.update(fake_strategies or {})
                combined.update(strategies or {})
                strategies = combined

            self._strategies_data_by_id = dict(strategies or {})
            self._update_selected_strategy_header(self._selected_strategy_id)

            self._loaded_strategy_type = str(getattr(category_info, "strategy_type", "") or "tcp").strip().lower()
            try:
                from strategy_menu.strategies_registry import get_current_strategy_set
                self._loaded_strategy_set = get_current_strategy_set()
            except Exception:
                self._loaded_strategy_set = None
            self._loaded_tcp_phase_mode = bool(self._tcp_phase_mode)
            self._default_strategy_order = list(strategies.keys())
            self._strategies_loaded_fully = False

            if not strategies:
                # ╨Я╤А╨╛╨▒╤Г╨╡╨╝ ╨┐╨╡╤А╨╡╨╖╨░╨│╤А╤Г╨╖╨╕╤В╤М ╤А╨╡╨╡╤Б╤В╤А
                log(f"╨б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┐╤Г╤Б╤В╤Л, ╨┐╤А╨╛╨▒╤Г╨╡╨╝ ╨┐╨╡╤А╨╡╨╖╨░╨│╤А╤Г╨╖╨╕╤В╤М ╤А╨╡╨╡╤Б╤В╤А...", "WARNING")
                registry.reload_strategies()
                strategies = registry.get_category_strategies(self._category_key)
                log(f"╨Я╨╛╤Б╨╗╨╡ ╨┐╨╡╤А╨╡╨╖╨░╨│╤А╤Г╨╖╨║╨╕: {len(strategies)} ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣", "DEBUG")

                # ╨Х╤Б╨╗╨╕ ╨▓╤Б╨╡ ╨╡╤Й╨╡ ╨┐╤Г╤Б╤В╨╛, ╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨┤╨╕╨░╨│╨╜╨╛╤Б╤В╨╕╨║╤Г
                if not strategies:
                    from strategy_menu.strategy_loader import _get_builtin_dir
                    builtin_dir = _get_builtin_dir()
                    log(f"Builtin ╨┤╨╕╤А╨╡╨║╤В╨╛╤А╨╕╤П: {builtin_dir}", "WARNING")
                    log(f"strategy_type ╨┤╨╗╤П ╨╖╨░╨│╤А╤Г╨╖╨║╨╕: {category_info.strategy_type}", "WARNING")

            # ╨Ы╨╡╨╜╨╕╨▓╨╛ ╨┤╨╛╨▒╨░╨▓╨╗╤П╨╡╨╝ ╤Б╤В╤А╨╛╨║╨╕ ╨┐╨╛╤А╤Ж╨╕╤П╨╝╨╕, ╤З╤В╨╛╨▒╤Л ╨╜╨╡ ╤Д╤А╨╕╨╖╨╕╤В╤М UI
            items = list(strategies.items())

            # "default" ╨┐╨╛╤А╤П╨┤╨╛╨║ UI ╨┤╨╛╨╗╨╢╨╡╨╜ ╤Б╨╛╨▓╨┐╨░╨┤╨░╤В╤М ╤Б ╨┐╨╛╤А╤П╨┤╨║╨╛╨╝ ╨▓ ╨╕╤Б╤В╨╛╤З╨╜╨╕╨║╨╡ (tcp.txt ╨╕ ╤В.╨┐.).
            # ╨в╨╡╨║╤Г╤Й╤Г╤О/╨┤╨╡╤Д╨╛╨╗╤В╨╜╤Г╤О ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╨Э╨Х ╨┐╨╛╨┤╨╜╨╕╨╝╨░╨╡╨╝.
            self._pending_strategies_items = items
            self._pending_strategies_index = 0
            self._strategies_load_generation += 1
            gen = self._strategies_load_generation
            total = len(self._pending_strategies_items)
            # "default" ╨┐╨╛╤А╤П╨┤╨╛╨║ UI ╨┤╨╛╨╗╨╢╨╡╨╜ ╤Б╨╛╨▓╨┐╨░╨┤╨░╤В╤М ╤Б ╤Д╨░╨║╤В╨╕╤З╨╡╤Б╨║╨╕╨╝ ╨┐╨╛╤А╤П╨┤╨║╨╛╨╝ ╨╖╨░╨│╤А╤Г╨╖╨║╨╕
            self._default_strategy_order = [sid for sid, _ in self._pending_strategies_items]

            if self._strategies_load_timer:
                try:
                    self._strategies_load_timer.stop()
                    self._strategies_load_timer.deleteLater()
                except Exception:
                    pass
                self._strategies_load_timer = None

            # ╨Ф╨╗╤П ╨╜╨╡╨▒╨╛╨╗╤М╤И╨╕╤Е ╤Б╨┐╨╕╤Б╨║╨╛╨▓ ╤Б╨╛╨╖╨┤╨░╤С╨╝ ╨▓╤Б╤С ╨╖╨░ ╨╛╨┤╨╕╨╜ ╨┐╤А╨╛╤Е╨╛╨┤: ╨╝╨╡╨╜╤М╤И╨╡ "╨┐╨╡╤А╨╡╤Б╨▒╨╛╤А╨╛╨║" ╨╕ ╨▒╤Л╤Б╤В╤А╨╡╨╡.
            if total <= 80:
                self._strategies_load_chunk_size = max(1, total)
                self._load_strategies_batch(gen)
                return

            # ╨Ф╨╗╤П ╨▒╨╛╨╗╤М╤И╨╕╤Е ╤Б╨┐╨╕╤Б╨║╨╛╨▓ ╨┤╨╛╨▒╨░╨▓╨╗╤П╨╡╨╝ ╨┐╨╛╤А╤Ж╨╕╤П╨╝╨╕, ╤З╤В╨╛╨▒╤Л UI ╨╜╨╡ ╤Д╤А╨╕╨╖╨╕╨╗╨╛.
            self._strategies_load_chunk_size = 25
            self._strategies_load_timer = QTimer(self)
            self._strategies_load_timer.timeout.connect(lambda: self._load_strategies_batch(gen))
            self._strategies_load_timer.start(0)

        except Exception as e:
            import traceback
            log(f"╨Ю╤И╨╕╨▒╨║╨░ ╨╖╨░╨│╤А╤Г╨╖╨║╨╕ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣: {e}", "ERROR")
            log(f"Traceback: {traceback.format_exc()}", "ERROR")

    def _load_strategies_batch(self, gen: int):
        """╨Ф╨╛╨▒╨░╨▓╨╗╤П╨╡╤В ╤Б╤В╤А╨╛╨║╨╕ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣ ╨┐╨╛╤А╤Ж╨╕╤П╨╝╨╕, ╤З╤В╨╛╨▒╤Л UI ╨╛╤Б╤В╨░╨▓╨░╨╗╤Б╤П ╨╛╤В╨╖╤Л╨▓╤З╨╕╨▓╤Л╨╝."""
        if gen != self._strategies_load_generation:
            return

        if not self._pending_strategies_items:
            if self._strategies_load_timer:
                self._strategies_load_timer.stop()
            return

        chunk_size = int(getattr(self, "_strategies_load_chunk_size", 10) or 10)
        if chunk_size <= 0:
            chunk_size = 10
        start = self._pending_strategies_index
        end = min(start + chunk_size, len(self._pending_strategies_items))

        try:
            if self._strategies_tree:
                self._strategies_tree.setUpdatesEnabled(False)
            else:
                self.setUpdatesEnabled(False)

            for i in range(start, end):
                sid, data = self._pending_strategies_items[i]
                name = (data or {}).get("name", sid)
                args = (data or {}).get("args", [])
                if isinstance(args, str):
                    args = args.split()
                self._add_strategy_row(sid, name, args)

                if not self._tcp_phase_mode:
                    if sid == self._current_strategy_id and self._strategies_tree:
                        self._strategies_tree.set_selected_strategy(sid)

        finally:
            try:
                if self._strategies_tree:
                    self._strategies_tree.setUpdatesEnabled(True)
                else:
                    self.setUpdatesEnabled(True)
            except Exception:
                pass

        self._pending_strategies_index = end

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ ╤В╨╡╨║╤Г╤Й╨╕╨╡ ╤Д╨╕╨╗╤М╤В╤А╤Л/╨┐╨╛╨╕╤Б╨║ ╨║ ╤Г╨╢╨╡ ╨┤╨╛╨▒╨░╨▓╨╗╨╡╨╜╨╜╤Л╨╝ ╤Б╤В╤А╨╛╨║╨░╨╝ (╨╡╤Б╨╗╨╕ ╨╛╨╜╨╕ ╤А╨╡╨░╨╗╤М╨╜╨╛ ╨░╨║╤В╨╕╨▓╨╜╤Л)
        try:
            search_active = bool(self._search_input and self._search_input.text().strip())
        except Exception:
            search_active = False
        if search_active or self._active_filters or self._tcp_phase_mode:
            self._apply_filters()

        if end >= len(self._pending_strategies_items):
            # Done
            if self._strategies_load_timer:
                self._strategies_load_timer.stop()
                self._strategies_load_timer.deleteLater()
                self._strategies_load_timer = None

            added = len(self._strategies_tree.get_strategy_ids()) if self._strategies_tree else 0
            log(f"StrategyDetailPage: ╨┤╨╛╨▒╨░╨▓╨╗╨╡╨╜╨╛ {added} ╤Б╤В╤А╨╛╨║ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣", "DEBUG")
            self._strategies_loaded_fully = True
            self._refresh_working_marks_for_category()

            # Sort after all rows are present (important for lazy load)
            self._apply_sort()
            # Restore active selection highlight after any sorting/filtering
            if self._strategies_tree:
                if self._tcp_phase_mode:
                    self._sync_tree_selection_to_active_phase()
                else:
                    if self._strategies_tree.has_strategy(self._current_strategy_id):
                        self._strategies_tree.set_selected_strategy(self._current_strategy_id)
                    elif self._strategies_tree.has_strategy("none"):
                        self._strategies_tree.set_selected_strategy("none")
            self._refresh_scroll_range()
            if self._tcp_phase_mode:
                QTimer.singleShot(0, self._sync_tree_selection_to_active_phase)
            self._restore_scroll_state(self._category_key, defer=True)

    def _add_strategy_row(self, strategy_id: str, name: str, args: list = None):
        """╨Ф╨╛╨▒╨░╨▓╨╗╤П╨╡╤В ╤Б╤В╤А╨╛╨║╤Г ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨▓ ╤Б╨┐╨╕╤Б╨╛╨║"""
        if not self._strategies_tree:
            return

        args_list = []
        for a in (args or []):
            if a is None:
                continue
            text = str(a).strip()
            if not text:
                continue
            args_list.append(text)

        is_favorite = (strategy_id != "none") and (strategy_id in self._favorite_strategy_ids)
        is_working = None
        if self._category_key and strategy_id != "none":
            try:
                is_working = self._marks_store.get_mark(self._category_key, strategy_id)
            except Exception:
                is_working = None

        self._strategies_tree.add_strategy(
            StrategyTreeRow(
                strategy_id=strategy_id,
                name=name,
                args=args_list,
                is_favorite=is_favorite,
                is_working=is_working,
            )
        )

    def _get_preview_strategy_data(self, strategy_id: str) -> dict:
        data = dict(self._strategies_data_by_id.get(strategy_id, {}) or {})
        if "name" not in data:
            data["name"] = strategy_id

        args = data.get("args", [])
        if isinstance(args, str):
            args_text = args
        elif isinstance(args, (list, tuple)):
            args_text = "\n".join([str(a) for a in args if a is not None]).strip()
        else:
            args_text = ""
        data["args"] = args_text
        return data

    def _get_preview_rating(self, strategy_id: str, category_key: str):
        if not (category_key and strategy_id and strategy_id != "none"):
            return None
        try:
            mark = self._marks_store.get_mark(category_key, strategy_id)
        except Exception:
            return None
        if mark is True:
            return "working"
        if mark is False:
            return "broken"
        return None

    def _toggle_preview_rating(self, strategy_id: str, rating: str, category_key: str):
        if not (category_key and strategy_id and strategy_id != "none"):
            return None
        current = None
        try:
            current = self._marks_store.get_mark(category_key, strategy_id)
        except Exception:
            current = None

        if rating == "working":
            new_state = None if current is True else True
        elif rating == "broken":
            new_state = None if current is False else False
        else:
            new_state = None

        try:
            self._marks_store.set_mark(category_key, strategy_id, new_state)
        except Exception as e:
            log(f"╨Ю╤И╨╕╨▒╨║╨░ ╤Б╨╛╤Е╤А╨░╨╜╨╡╨╜╨╕╤П ╨┐╨╛╨╝╨╡╤В╨║╨╕ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ (preview): {e}", "WARNING")
            return self._get_preview_rating(strategy_id, category_key)

        if self._strategies_tree:
            self._strategies_tree.set_working_state(strategy_id, new_state)

        if new_state is True:
            return "working"
        if new_state is False:
            return "broken"
        return None

    def _close_preview_dialog(self, force: bool = False):
        if self._preview_dialog is None:
            return
        if (not force) and self._preview_pinned:
            return
        try:
            self._preview_dialog.close_dialog()
        except Exception:
            try:
                self._preview_dialog.close()
            except Exception:
                pass
        self._preview_dialog = None
        self._preview_pinned = False

    def _on_preview_closed(self) -> None:
        self._preview_dialog = None
        self._preview_pinned = False

    def _ensure_preview_dialog(self):
        dlg = self._preview_dialog
        if dlg is not None:
            try:
                # Runtime check: C++ object can be deleted under us.
                dlg.isVisible()
                return dlg
            except RuntimeError:
                self._preview_dialog = None
            except Exception:
                return dlg

        parent_win = self._main_window or self.window() or self
        try:
            dlg = ArgsPreviewDialog(parent_win)
            dlg.closed.connect(self._on_preview_closed)
            self._preview_dialog = dlg
            return dlg
        except Exception:
            self._preview_dialog = None
            return None

    @staticmethod
    def _to_qpoint(global_pos):
        try:
            return global_pos.toPoint()
        except Exception:
            return global_pos

    def _show_preview_dialog(self, strategy_id: str, global_pos) -> None:
        if not (self._category_key and strategy_id and strategy_id != "none"):
            return

        data = self._get_preview_strategy_data(strategy_id)

        try:
            dlg = self._ensure_preview_dialog()
            if dlg is None:
                return

            dlg.set_strategy_data(
                data,
                strategy_id=strategy_id,
                category_key=self._category_key,
                rating_getter=self._get_preview_rating,
                rating_toggler=self._toggle_preview_rating,
            )

            dlg.show_animated(self._to_qpoint(global_pos))

        except Exception as e:
            log(f"Preview dialog failed: {e}", "DEBUG")

    def _on_tree_preview_requested(self, strategy_id: str, global_pos):
        pass  # Hover preview disabled; use right-click (╨Я╨Ъ╨Ь) to open dialog.

    def _on_tree_preview_pinned_requested(self, strategy_id: str, global_pos):
        self._show_preview_dialog(strategy_id, global_pos)

    def _on_tree_preview_hide_requested(self) -> None:
        pass  # No hover preview to hide.

    def _refresh_working_marks_for_category(self):
        if not (self._category_key and self._strategies_tree):
            return
        for strategy_id in self._strategies_tree.get_strategy_ids():
            if strategy_id == "none":
                continue
            try:
                self._strategies_tree.set_working_state(
                    strategy_id, self._marks_store.get_mark(self._category_key, strategy_id)
                )
            except Exception:
                pass

    def _on_favorite_toggled(self, strategy_id: str, is_favorite: bool):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨┐╨╡╤А╨╡╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨╕╨╖╨▒╤А╨░╨╜╨╜╨╛╨│╨╛"""
        if not (self._category_key and self._strategies_tree):
            return
        if not strategy_id or strategy_id == "none":
            # "╨Ю╤В╨║╨╗╤О╤З╨╡╨╜╨╛" ╨╜╨╡ ╨┤╨╡╨╗╨░╨╡╨╝ ╨╕╨╖╨▒╤А╨░╨╜╨╜╤Л╨╝
            self._strategies_tree.set_favorite_state("none", False)
            return

        try:
            self._favorites_store.set_favorite(self._category_key, strategy_id, bool(is_favorite))
            if is_favorite:
                self._favorite_strategy_ids.add(strategy_id)
            else:
                self._favorite_strategy_ids.discard(strategy_id)
        except Exception as e:
            log(f"Favorite persist failed: {e}", "WARNING")
            # ╨Ю╤В╨║╨░╤В╤Л╨▓╨░╨╡╨╝ UI, ╨┤╨╡╤А╨╡╨▓╨╛ ╤Г╨╢╨╡ ╤Г╤Б╨┐╨╡╨╗╨╛ ╨╛╨┐╤В╨╕╨╝╨╕╤Б╤В╨╕╤З╨╜╨╛ ╨╛╨▒╨╜╨╛╨▓╨╕╤В╤М╤Б╤П
            self._strategies_tree.set_favorite_state(strategy_id, not bool(is_favorite))
            return

        log(f"Favorite toggled: {strategy_id} = {is_favorite}", "DEBUG")

    def _on_tree_working_mark_requested(self, strategy_id: str, is_working):
        """╨Ч╨░╨┐╤А╨╛╤Б ╨╕╨╖ UI (╨Я╨Ъ╨Ь) ╨╜╨░ ╨┐╨╛╨╝╨╡╤В╨║╤Г ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕."""
        if not (self._category_key and strategy_id and strategy_id != "none"):
            return
        self._on_strategy_marked(strategy_id, is_working)
        if self._strategies_tree:
            self._strategies_tree.set_working_state(strategy_id, is_working)

    def _on_strategy_marked(self, strategy_id: str, is_working):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨┐╨╛╨╝╨╡╤В╨║╨╕ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨║╨░╨║ ╤А╨░╨▒╨╛╤З╨╡╨╣/╨╜╨╡╤А╨░╨▒╨╛╤З╨╡╨╣"""
        if self._category_key:
            # Persist marks for direct_zapret2 mode (two-state)
            try:
                if strategy_id and strategy_id != "none":
                    self._marks_store.set_mark(self._category_key, strategy_id, is_working)
            except Exception as e:
                log(f"╨Ю╤И╨╕╨▒╨║╨░ ╤Б╨╛╤Е╤А╨░╨╜╨╡╨╜╨╕╤П ╨┐╨╛╨╝╨╡╤В╨║╨╕ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕: {e}", "WARNING")

            self.strategy_marked.emit(self._category_key, strategy_id, is_working)
            if is_working is True:
                status = 'working'
            elif is_working is False:
                status = 'not working'
            else:
                status = 'unmarked'
            log(f"Strategy marked: {strategy_id} = {status}", "DEBUG")

    def _on_enable_toggled(self, enabled: bool):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╤П/╨▓╤Л╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕"""
        if not self._category_key:
            return

        # TCP multi-phase: restore last enabled args when toggling back on.
        if self._tcp_phase_mode and enabled:
            try:
                last_args = (self._tcp_last_enabled_args_by_category.get(self._category_key) or "").strip()
            except Exception:
                last_args = ""

            if last_args:
                try:
                    preset = self._preset_manager.get_active_preset()
                    if not preset:
                        return
                    if self._category_key not in preset.categories:
                        preset.categories[self._category_key] = self._preset_manager._create_category_with_defaults(self._category_key)

                    cat = preset.categories[self._category_key]
                    cat.tcp_args = last_args
                    cat.strategy_id = self._infer_strategy_id_from_args_exact(last_args)
                    preset.touch()
                    self._preset_manager._save_and_sync_preset(preset)

                    self._selected_strategy_id = cat.strategy_id or "none"
                    self._current_strategy_id = cat.strategy_id or "none"

                    self._set_category_enabled_ui(True)
                    self._update_selected_strategy_header(self._selected_strategy_id)
                    self._refresh_args_editor_state()

                    # Rebuild phase state + tabs selection
                    self._load_tcp_phase_state_from_preset()
                    self._apply_tcp_phase_tabs_visibility()
                    self._select_default_tcp_phase_tab()
                    self._apply_filters()

                    self.show_loading()
                    self.strategy_selected.emit(self._category_key, self._selected_strategy_id)
                    log(f"╨Ъ╨░╤В╨╡╨│╨╛╤А╨╕╤П {self._category_key} ╨▓╨║╨╗╤О╤З╨╡╨╜╨░ (restore phase chain)", "INFO")
                    return
                except Exception as e:
                    log(f"TCP phase restore failed: {e}", "WARNING")

        if enabled:
            # ╨Т╨║╨╗╤О╤З╨░╨╡╨╝ - ╨▓╨╛╤Б╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╨╝ ╨┐╨╛╤Б╨╗╨╡╨┤╨╜╤О╤О ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О (╨╡╤Б╨╗╨╕ ╨▒╤Л╨╗╨░), ╨╕╨╜╨░╤З╨╡ ╨┤╨╡╤Д╨╛╨╗╤В╨╜╤Г╤О
            strategy_to_select = getattr(self, "_last_enabled_strategy_id", None) or self._get_default_strategy()

            # Rare: strategies catalog may not be available yet (first-run install/extract/update).
            # Try a one-shot reload before giving up and reverting the toggle.
            if (not strategy_to_select or strategy_to_select == "none") and not (self._strategies_data_by_id or {}):
                try:
                    from strategy_menu.strategies_registry import registry
                    registry.reload_strategies()
                    self._clear_strategies()
                    self._load_strategies()
                    strategy_to_select = self._get_default_strategy()
                except Exception:
                    strategy_to_select = strategy_to_select or "none"

            if strategy_to_select and strategy_to_select != "none":
                self._selected_strategy_id = strategy_to_select
                if self._strategies_tree:
                    self._strategies_tree.set_selected_strategy(strategy_to_select)
                self._update_selected_strategy_header(self._selected_strategy_id)
                self._set_category_enabled_ui(True)
                # ╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨░╨╜╨╕╨╝╨░╤Ж╨╕╤О ╨╖╨░╨│╤А╤Г╨╖╨║╨╕
                self.show_loading()
                self.strategy_selected.emit(self._category_key, strategy_to_select)
                log(f"╨Ъ╨░╤В╨╡╨│╨╛╤А╨╕╤П {self._category_key} ╨▓╨║╨╗╤О╤З╨╡╨╜╨░ ╤Б╨╛ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╡╨╣ {strategy_to_select}", "INFO")
            else:
                log(f"╨Э╨╡╤В ╨┤╨╛╤Б╤В╤Г╨┐╨╜╤Л╤Е ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣ ╨┤╨╗╤П {self._category_key}", "WARNING")
                self._enable_toggle.setChecked(False, block_signals=True)
                self._set_category_enabled_ui(False)
            self._refresh_args_editor_state()
        else:
            # ╨Ч╨░╨┐╨╛╨╝╨╕╨╜╨░╨╡╨╝ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╨┐╨╡╤А╨╡╨┤ ╨▓╤Л╨║╨╗╤О╤З╨╡╨╜╨╕╨╡╨╝, ╤З╤В╨╛╨▒╤Л ╨▓╨╛╤Б╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╨┐╤А╨╕ ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╨╕
            if self._selected_strategy_id and self._selected_strategy_id != "none":
                self._last_enabled_strategy_id = self._selected_strategy_id
            # TCP multi-phase: also store full args chain (required for restore)
            if self._tcp_phase_mode:
                try:
                    cur_args = self._get_category_strategy_args_text().strip()
                    if cur_args:
                        self._tcp_last_enabled_args_by_category[self._category_key] = cur_args
                except Exception:
                    pass
            # ╨Т╤Л╨║╨╗╤О╤З╨░╨╡╨╝ - ╤Г╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╨╝ "none"
            self._selected_strategy_id = "none"
            if self._strategies_tree:
                if self._strategies_tree.has_strategy("none"):
                    self._strategies_tree.set_selected_strategy("none")
                else:
                    self._strategies_tree.clearSelection()
            self._update_selected_strategy_header(self._selected_strategy_id)
            # ╨б╨║╤А╤Л╨▓╨░╨╡╨╝ ╨│╨░╨╗╨╛╤З╨║╤Г
            self._stop_loading()
            self._success_icon.hide()
            self.strategy_selected.emit(self._category_key, "none")
            log(f"╨Ъ╨░╤В╨╡╨│╨╛╤А╨╕╤П {self._category_key} ╨╛╤В╨║╨╗╤О╤З╨╡╨╜╨░", "INFO")
            self._refresh_args_editor_state()
            self._set_category_enabled_ui(False)

    def _get_default_strategy(self) -> str:
        """╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╨┐╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О ╨┤╨╗╤П ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕"""
        try:
            from strategy_menu.strategies_registry import registry

            # ╨Я╤А╨╛╨▒╤Г╨╡╨╝ ╨┐╨╛╨╗╤Г╤З╨╕╤В╤М ╨┤╨╡╤Д╨╛╨╗╤В╨╜╤Г╤О ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╨╕╨╖ ╤А╨╡╨╡╤Б╤В╤А╨░
            defaults = registry.get_default_selections()
            if self._category_key in defaults:
                default_id = defaults[self._category_key]
                if default_id and default_id != "none" and (default_id in (self._default_strategy_order or [])):
                    return default_id

            # ╨Ш╨╜╨░╤З╨╡ ╨▒╨╡╤А╤С╨╝ ╨┐╨╡╤А╨▓╤Г╤О ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О ╨╕╨╖ ╤Б╨┐╨╕╤Б╨║╨░ (╨╜╨╡ none)
            for sid in (self._default_strategy_order or []):
                if sid and sid != "none":
                    return sid

            return "none"
        except Exception as e:
            log(f"╨Ю╤И╨╕╨▒╨║╨░ ╨┐╨╛╨╗╤Г╤З╨╡╨╜╨╕╤П ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┐╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О: {e}", "DEBUG")
            # Fallback - ╨┐╨╡╤А╨▓╨░╤П ╨╜╨╡-none ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤П
            for sid in (self._default_strategy_order or []):
                if sid and sid != "none":
                    return sid
            return "none"

    def _on_filter_mode_changed(self, new_mode: str):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤П ╤А╨╡╨╢╨╕╨╝╨░ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕"""
        if not self._category_key:
            return

        # Save via PresetManager (triggers DPI reload automatically)
        self._save_category_filter_mode(self._category_key, new_mode)
        self.filter_mode_changed.emit(self._category_key, new_mode)
        log(f"╨а╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ ╨┤╨╗╤П {self._category_key}: {new_mode}", "INFO")

    def _save_category_filter_mode(self, category_key: str, mode: str):
        """╨б╨╛╤Е╤А╨░╨╜╤П╨╡╤В ╤А╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╤З╨╡╤А╨╡╨╖ PresetManager"""
        self._preset_manager.update_category_filter_mode(
            category_key, mode, save_and_sync=True
        )

    def _load_category_filter_mode(self, category_key: str) -> str:
        """╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╤В ╤А╨╡╨╢╨╕╨╝ ╤Д╨╕╨╗╤М╤В╤А╨░╤Ж╨╕╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╨╕╨╖ PresetManager"""
        return self._preset_manager.get_category_filter_mode(category_key)

    def _save_category_sort(self, category_key: str, sort_order: str):
        """╨б╨╛╤Е╤А╨░╨╜╤П╨╡╤В ╨┐╨╛╤А╤П╨┤╨╛╨║ ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╤З╨╡╤А╨╡╨╖ PresetManager"""
        # Sort order is UI-only parameter, doesn't affect DPI
        # But save_and_sync=True is needed to persist changes to disk
        # (hot-reload may trigger but sort_order has no effect on winws2)
        self._preset_manager.update_category_sort_order(
            category_key, sort_order, save_and_sync=True
        )

    def _load_category_sort(self, category_key: str) -> str:
        """╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╤В ╨┐╨╛╤А╤П╨┤╨╛╨║ ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╨╕╨╖ PresetManager"""
        return self._preset_manager.get_category_sort_order(category_key)

    # ======================================================================
    # TCP PHASE TAB PERSISTENCE (UI-only)
    # ======================================================================

    _REG_TCP_PHASE_TABS_BY_CATEGORY = "TcpPhaseTabByCategory"

    def _load_category_last_tcp_phase_tab(self, category_key: str) -> str | None:
        """Loads the last selected TCP phase tab for a category (persisted in registry)."""
        try:
            from config.reg import reg
            from config import REGISTRY_PATH_GUI
        except Exception:
            return None

        key = str(category_key or "").strip().lower()
        if not key:
            return None

        try:
            raw = reg(REGISTRY_PATH_GUI, self._REG_TCP_PHASE_TABS_BY_CATEGORY)
            if not raw:
                return None
            data = json.loads(raw) if isinstance(raw, str) else {}
            phase = str((data or {}).get(key) or "").strip().lower()
            if phase and phase in (self._phase_tab_index_by_key or {}):
                return phase
        except Exception:
            return None

        return None

    def _save_category_last_tcp_phase_tab(self, category_key: str, phase_key: str) -> None:
        """Saves the last selected TCP phase tab for a category (best-effort)."""
        try:
            from config.reg import reg
            from config import REGISTRY_PATH_GUI
        except Exception:
            return

        cat_key = str(category_key or "").strip().lower()
        phase = str(phase_key or "").strip().lower()
        if not cat_key or not phase:
            return

        # Validate phase key early to avoid persisting garbage.
        if self._tcp_phase_mode and phase not in (self._phase_tab_index_by_key or {}):
            return

        try:
            raw = reg(REGISTRY_PATH_GUI, self._REG_TCP_PHASE_TABS_BY_CATEGORY)
            data = {}
            if isinstance(raw, str) and raw.strip():
                try:
                    data = json.loads(raw) or {}
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
            data[cat_key] = phase
            reg(REGISTRY_PATH_GUI, self._REG_TCP_PHASE_TABS_BY_CATEGORY, json.dumps(data, ensure_ascii=False))
        except Exception:
            return

    # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
    # OUT RANGE METHODS
    # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР

    def _select_out_range_mode(self, mode: str):
        """╨Т╤Л╨▒╨╛╤А ╤А╨╡╨╢╨╕╨╝╨░ out_range (n ╨╕╨╗╨╕ d)"""
        if mode != self._out_range_mode:
            self._out_range_mode = mode
            try:
                self._out_range_seg.setCurrentItem(mode)
            except Exception:
                pass
            self._save_syndata_settings()

    # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР
    # SYNDATA SETTINGS METHODS
    # тХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХРтХР

    def _on_send_toggled(self, checked: bool):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╤П/╨▓╤Л╨║╨╗╤О╤З╨╡╨╜╨╕╤П send ╨┐╨░╤А╨░╨╝╨╡╤В╤А╨╛╨▓"""
        self._send_settings.setVisible(checked)
        self._save_syndata_settings()

    def _on_syndata_toggled(self, checked: bool):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨▓╨║╨╗╤О╤З╨╡╨╜╨╕╤П/╨▓╤Л╨║╨╗╤О╤З╨╡╨╜╨╕╤П syndata ╨┐╨░╤А╨░╨╝╨╡╤В╤А╨╛╨▓"""
        self._syndata_settings.setVisible(checked)
        self._save_syndata_settings()

    def _save_syndata_settings(self):
        """╨б╨╛╤Е╤А╨░╨╜╤П╨╡╤В syndata ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨┤╨╗╤П ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╤З╨╡╤А╨╡╨╖ PresetManager"""
        if not self._category_key:
            return

        # Build SyndataSettings from UI
        syndata = SyndataSettings(
            enabled=self._syndata_toggle.isChecked(),
            blob=self._blob_combo.currentText(),
            tls_mod=self._tls_mod_combo.currentText(),
            autottl_delta=self._autottl_delta_selector.value(),
            autottl_min=self._autottl_min_selector.value(),
            autottl_max=self._autottl_max_selector.value(),
            out_range=self._out_range_spin.value(),
            out_range_mode=self._out_range_mode,
            tcp_flags_unset=self._tcp_flags_combo.currentText(),
            send_enabled=self._send_toggle.isChecked(),
            send_repeats=self._send_repeats_spin.value(),
            send_ip_ttl=self._send_ip_ttl_selector.value(),
            send_ip6_ttl=self._send_ip6_ttl_selector.value(),
            send_ip_id=self._send_ip_id_combo.currentText(),
            send_badsum=self._send_badsum_check.isChecked(),
        )

        log(f"Syndata settings saved for {self._category_key}: {syndata.to_dict()}", "DEBUG")

        # Save with sync=True - ConfigFileWatcher will trigger hot-reload automatically
        # when it detects the preset file change
        protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
        is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
        protocol_key = "udp" if is_udp_like else "tcp"
        self._preset_manager.update_category_syndata(
            self._category_key, syndata, protocol=protocol_key, save_and_sync=True
        )

    def _load_syndata_settings(self, category_key: str) -> dict:
        """╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╤В syndata ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨┤╨╗╤П ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╨╕╨╖ PresetManager"""
        protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
        is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
        protocol_key = "udp" if is_udp_like else "tcp"
        syndata = self._preset_manager.get_category_syndata(category_key, protocol=protocol_key)
        return syndata.to_dict()

    def _apply_syndata_settings(self, settings: dict):
        """╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╤В syndata ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨║ UI ╨▒╨╡╨╖ ╤Н╨╝╨╕╤Б╤Б╨╕╨╕ ╤Б╨╕╨│╨╜╨░╨╗╨╛╨▓ ╤Б╨╛╤Е╤А╨░╨╜╨╡╨╜╨╕╤П"""
        # ╨С╨╗╨╛╨║╨╕╤А╤Г╨╡╨╝ ╤Б╨╕╨│╨╜╨░╨╗╤Л ╤З╤В╨╛╨▒╤Л ╨╜╨╡ ╨▓╤Л╨╖╤Л╨▓╨░╤В╤М save ╨┐╤А╨╕ ╨╖╨░╨│╤А╤Г╨╖╨║╨╡
        self._syndata_toggle.blockSignals(True)
        self._blob_combo.blockSignals(True)
        self._tls_mod_combo.blockSignals(True)
        # TTLButtonSelector ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╡╤В block_signals=True ╨┐╤А╨╕ setValue
        self._out_range_spin.blockSignals(True)
        self._tcp_flags_combo.blockSignals(True)
        # ╨С╨╗╨╛╨║╨╕╤А╤Г╨╡╨╝ ╤Б╨╕╨│╨╜╨░╨╗╤Л Send ╨▓╨╕╨┤╨╢╨╡╤В╨╛╨▓
        self._send_toggle.blockSignals(True)
        self._send_repeats_spin.blockSignals(True)
        self._send_ip_id_combo.blockSignals(True)
        self._send_badsum_check.blockSignals(True)

        self._syndata_toggle.setChecked(settings.get("enabled", False))
        self._syndata_settings.setVisible(settings.get("enabled", False))

        blob_value = settings.get("blob", "none")
        blob_index = self._blob_combo.findText(blob_value)
        if blob_index >= 0:
            self._blob_combo.setCurrentIndex(blob_index)

        tls_mod_value = settings.get("tls_mod", "none")
        tls_mod_index = self._tls_mod_combo.findText(tls_mod_value)
        if tls_mod_index >= 0:
            self._tls_mod_combo.setCurrentIndex(tls_mod_index)

        # AutoTTL settings
        self._autottl_delta_selector.setValue(settings.get("autottl_delta", -2), block_signals=True)
        self._autottl_min_selector.setValue(settings.get("autottl_min", 3), block_signals=True)
        self._autottl_max_selector.setValue(settings.get("autottl_max", 20), block_signals=True)
        self._out_range_spin.setValue(settings.get("out_range", 8))

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ ╤А╨╡╨╢╨╕╨╝ out_range
        self._out_range_mode = settings.get("out_range_mode", "n")
        try:
            self._out_range_seg.setCurrentItem(self._out_range_mode)
        except Exception:
            pass

        tcp_flags_value = settings.get("tcp_flags_unset", "none")
        tcp_flags_index = self._tcp_flags_combo.findText(tcp_flags_value)
        if tcp_flags_index >= 0:
            self._tcp_flags_combo.setCurrentIndex(tcp_flags_index)

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ Send ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕
        self._send_toggle.setChecked(settings.get("send_enabled", False))
        self._send_settings.setVisible(settings.get("send_enabled", False))
        self._send_repeats_spin.setValue(settings.get("send_repeats", 2))
        self._send_ip_ttl_selector.setValue(settings.get("send_ip_ttl", 0), block_signals=True)
        self._send_ip6_ttl_selector.setValue(settings.get("send_ip6_ttl", 0), block_signals=True)

        send_ip_id = settings.get("send_ip_id", "none")
        send_ip_id_index = self._send_ip_id_combo.findText(send_ip_id)
        if send_ip_id_index >= 0:
            self._send_ip_id_combo.setCurrentIndex(send_ip_id_index)

        self._send_badsum_check.setChecked(settings.get("send_badsum", False))

        # ╨а╨░╨╖╨▒╨╗╨╛╨║╨╕╤А╤Г╨╡╨╝ ╤Б╨╕╨│╨╜╨░╨╗╤Л
        self._syndata_toggle.blockSignals(False)
        self._blob_combo.blockSignals(False)
        self._tls_mod_combo.blockSignals(False)
        # TTLButtonSelector ╨╜╨╡ ╤В╤А╨╡╨▒╤Г╨╡╤В ╤А╨░╨╖╨▒╨╗╨╛╨║╨╕╤А╨╛╨▓╨║╨╕ (block_signals=True ╨┐╤А╨╕ setValue)
        self._out_range_spin.blockSignals(False)
        self._tcp_flags_combo.blockSignals(False)
        # ╨а╨░╨╖╨▒╨╗╨╛╨║╨╕╤А╤Г╨╡╨╝ ╤Б╨╕╨│╨╜╨░╨╗╤Л Send ╨▓╨╕╨┤╨╢╨╡╤В╨╛╨▓
        self._send_toggle.blockSignals(False)
        self._send_repeats_spin.blockSignals(False)
        self._send_ip_id_combo.blockSignals(False)
        self._send_badsum_check.blockSignals(False)

    def get_syndata_settings(self) -> dict:
        """╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В ╤В╨╡╨║╤Г╤Й╨╕╨╡ syndata ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨┤╨╗╤П ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╤П ╨▓ ╨║╨╛╨╝╨░╨╜╨┤╨╜╨╛╨╣ ╤Б╤В╤А╨╛╨║╨╡"""
        return {
            "enabled": self._syndata_toggle.isChecked(),
            "blob": self._blob_combo.currentText(),
            "tls_mod": self._tls_mod_combo.currentText(),
        }

    # ======================================================================
    # PRESET CREATE / RENAME
    # ======================================================================

    def _on_create_preset_clicked(self):
        """╨Ю╤В╨║╤А╤Л╨▓╨░╨╡╤В WinUI-╨┤╨╕╨░╨╗╨╛╨│ ╤Б╨╛╨╖╨┤╨░╨╜╨╕╤П ╨╜╨╛╨▓╨╛╨│╨╛ ╨┐╤А╨╡╤Б╨╡╤В╨░."""
        try:
            from preset_zapret2 import PresetManager as _PM
            manager = _PM()
        except Exception as e:
            if InfoBar:
                InfoBar.error(title="╨Ю╤И╨╕╨▒╨║╨░", content=str(e), parent=self.window())
            return

        dialog = _PresetNameDialog("create", parent=self.window())
        if not dialog.exec():
            return
        name = dialog.get_name()
        if not name:
            return
        try:
            if manager.preset_exists(name):
                if InfoBar:
                    InfoBar.warning(
                        title="╨г╨╢╨╡ ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╨╡╤В",
                        content=f"╨Я╤А╨╡╤Б╨╡╤В '{name}' ╤Г╨╢╨╡ ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╨╡╤В.",
                        parent=self.window(),
                    )
                return
            preset = manager.create_preset(name, from_current=True)
            if preset:
                log(f"╨б╨╛╨╖╨┤╨░╨╜ ╨┐╤А╨╡╤Б╨╡╤В '{name}'", "INFO")
                if InfoBar:
                    InfoBar.success(
                        title="╨Я╤А╨╡╤Б╨╡╤В ╤Б╨╛╨╖╨┤╨░╨╜",
                        content=f"╨Я╤А╨╡╤Б╨╡╤В '{name}' ╤Б╨╛╨╖╨┤╨░╨╜ ╨╜╨░ ╨╛╤Б╨╜╨╛╨▓╨╡ ╤В╨╡╨║╤Г╤Й╨╕╤Е ╨╜╨░╤Б╤В╤А╨╛╨╡╨║.",
                        parent=self.window(),
                    )
            else:
                if InfoBar:
                    InfoBar.warning(title="╨Ю╤И╨╕╨▒╨║╨░", content="╨Э╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╤Б╨╛╨╖╨┤╨░╤В╤М ╨┐╤А╨╡╤Б╨╡╤В.", parent=self.window())
        except Exception as e:
            log(f"╨Ю╤И╨╕╨▒╨║╨░ ╤Б╨╛╨╖╨┤╨░╨╜╨╕╤П ╨┐╤А╨╡╤Б╨╡╤В╨░: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="╨Ю╤И╨╕╨▒╨║╨░", content=str(e), parent=self.window())

    def _on_rename_preset_clicked(self):
        """╨Ю╤В╨║╤А╤Л╨▓╨░╨╡╤В WinUI-╨┤╨╕╨░╨╗╨╛╨│ ╨┐╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╨╜╨╕╤П ╤В╨╡╨║╤Г╤Й╨╡╨│╨╛ ╨░╨║╤В╨╕╨▓╨╜╨╛╨│╨╛ ╨┐╤А╨╡╤Б╨╡╤В╨░."""
        try:
            from preset_zapret2 import PresetManager as _PM
            manager = _PM()
            old_name = (manager.get_active_preset_name() or "").strip()
        except Exception as e:
            if InfoBar:
                InfoBar.error(title="╨Ю╤И╨╕╨▒╨║╨░", content=str(e), parent=self.window())
            return

        if not old_name:
            if InfoBar:
                InfoBar.warning(
                    title="╨Э╨╡╤В ╨░╨║╤В╨╕╨▓╨╜╨╛╨│╨╛ ╨┐╤А╨╡╤Б╨╡╤В╨░",
                    content="╨Р╨║╤В╨╕╨▓╨╜╤Л╨╣ ╨┐╤А╨╡╤Б╨╡╤В ╨╜╨╡ ╨╜╨░╨╣╨┤╨╡╨╜.",
                    parent=self.window(),
                )
            return

        dialog = _PresetNameDialog("rename", old_name=old_name, parent=self.window())
        if not dialog.exec():
            return
        new_name = dialog.get_name()
        if not new_name or new_name == old_name:
            return
        try:
            if manager.preset_exists(new_name):
                if InfoBar:
                    InfoBar.warning(
                        title="╨г╨╢╨╡ ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╨╡╤В",
                        content=f"╨Я╤А╨╡╤Б╨╡╤В '{new_name}' ╤Г╨╢╨╡ ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╨╡╤В.",
                        parent=self.window(),
                    )
                return
            if manager.rename_preset(old_name, new_name):
                log(f"╨Я╤А╨╡╤Б╨╡╤В '{old_name}' ╨┐╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╨╜ ╨▓ '{new_name}'", "INFO")
                if InfoBar:
                    InfoBar.success(
                        title="╨Я╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╨╜",
                        content=f"╨Я╤А╨╡╤Б╨╡╤В ╨┐╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╨╜: '{old_name}' тЖТ '{new_name}'.",
                        parent=self.window(),
                    )
            else:
                if InfoBar:
                    InfoBar.warning(title="╨Ю╤И╨╕╨▒╨║╨░", content="╨Э╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╨┐╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╤В╤М ╨┐╤А╨╡╤Б╨╡╤В.", parent=self.window())
        except Exception as e:
            log(f"╨Ю╤И╨╕╨▒╨║╨░ ╨┐╨╡╤А╨╡╨╕╨╝╨╡╨╜╨╛╨▓╨░╨╜╨╕╤П ╨┐╤А╨╡╤Б╨╡╤В╨░: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="╨Ю╤И╨╕╨▒╨║╨░", content=str(e), parent=self.window())

    def _on_reset_settings_confirmed(self):
        """╨б╨▒╤А╨░╤Б╤Л╨▓╨░╨╡╤В ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ ╨╜╨░ ╨╖╨╜╨░╤З╨╡╨╜╨╕╤П ╨┐╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О (╨▓╤Б╤В╤А╨╛╨╡╨╜╨╜╤Л╨╣ ╤И╨░╨▒╨╗╨╛╨╜)"""
        if not self._category_key:
            return

        # 1. Reset via PresetManager (saves to preset file)
        if self._preset_manager.reset_category_settings(self._category_key):
            log(f"╨Э╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕ {self._category_key} ╤Б╨▒╤А╨╛╤И╨╡╨╜╤Л", "INFO")

            # 2. Reload settings from PresetManager and apply to UI
            protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
            is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
            protocol_key = "udp" if is_udp_like else "tcp"
            syndata = self._preset_manager.get_category_syndata(self._category_key, protocol=protocol_key)
            self._apply_syndata_settings(syndata.to_dict())

            # 3. Reset filter_mode selector to stored default
            if hasattr(self, '_filter_mode_frame') and self._filter_mode_frame.isVisible():
                current_mode = self._preset_manager.get_category_filter_mode(self._category_key)
                self._filter_mode_selector.blockSignals(True)
                self._filter_mode_selector.setChecked(current_mode == "ipset")
                self._filter_mode_selector.blockSignals(False)

            # 4. Update selected strategy highlight and enable toggle
            try:
                current_strategy_id = self._preset_manager.get_strategy_selections().get(self._category_key, "none")
            except Exception:
                current_strategy_id = "none"

            self._selected_strategy_id = current_strategy_id or "none"
            self._current_strategy_id = current_strategy_id or "none"

            if self._tcp_phase_mode:
                self._load_tcp_phase_state_from_preset()
                self._apply_tcp_phase_tabs_visibility()
                self._select_default_tcp_phase_tab()
                self._apply_filters()
            else:
                if self._strategies_tree:
                    if self._selected_strategy_id != "none":
                        self._strategies_tree.set_selected_strategy(self._selected_strategy_id)
                    elif self._strategies_tree.has_strategy("none"):
                        self._strategies_tree.set_selected_strategy("none")
                    else:
                        self._strategies_tree.clearSelection()

            if self._selected_strategy_id != "none":
                self._enable_toggle.setChecked(True, block_signals=True)
            else:
                self._enable_toggle.setChecked(False, block_signals=True)

            # Reset writes the preset to disk and triggers the same hot-reload/restart
            # path as any other setting change, so show the spinner.
            self.show_loading()
            self._update_selected_strategy_header(self._selected_strategy_id)
            self._refresh_args_editor_state()
            self._set_category_enabled_ui((self._selected_strategy_id or "none") != "none")

    def _on_row_clicked(self, strategy_id: str):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨║╨╗╨╕╨║╨░ ╨┐╨╛ ╤Б╤В╤А╨╛╨║╨╡ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ - ╨▓╤Л╨▒╨╛╤А ╨░╨║╤В╨╕╨▓╨╜╨╛╨╣"""
        if self._tcp_phase_mode:
            self._on_tcp_phase_row_clicked(strategy_id)
            return

        prev_strategy_id = self._selected_strategy_id

        self._selected_strategy_id = strategy_id
        if self._strategies_tree:
            self._strategies_tree.set_selected_strategy(strategy_id)
        self._update_selected_strategy_header(self._selected_strategy_id)

        # ╨Я╤А╨╕ ╤Б╨╝╨╡╨╜╨╡ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨╖╨░╨║╤А╤Л╨▓╨░╨╡╨╝ ╤А╨╡╨┤╨░╨║╤В╨╛╤А args (╤З╤В╨╛╨▒╤Л ╨╜╨╡ ╤А╨╡╨┤╨░╨║╤В╨╕╤А╨╛╨▓╨░╤В╤М "╨╜╨╡ ╤В╨╛")
        if prev_strategy_id != strategy_id:
            self._hide_args_editor(clear_text=False)

        # ╨б╨╕╨╜╤Е╤А╨╛╨╜╨╕╨╖╨╕╤А╤Г╨╡╨╝ toggle
        if strategy_id != "none":
            self._enable_toggle.setChecked(True, block_signals=True)
            # ╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨░╨╜╨╕╨╝╨░╤Ж╨╕╤О ╨╖╨░╨│╤А╤Г╨╖╨║╨╕
            self.show_loading()
        else:
            self._stop_loading()
            self._success_icon.hide()

        self._refresh_args_editor_state()
        self._set_category_enabled_ui((strategy_id or "none") != "none")

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╤О (╨╜╨╛ ╨╛╤Б╤В╨░╤С╨╝╤Б╤П ╨╜╨░ ╤Б╤В╤А╨░╨╜╨╕╤Ж╨╡)
        if self._category_key:
            self.strategy_selected.emit(self._category_key, strategy_id)

    def _update_status_icon(self, active: bool):
        """╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╤В ╨│╨░╨╗╨╛╤З╨║╤Г ╤Б╤В╨░╤В╤Г╤Б╨░ ╨▓ ╨╖╨░╨│╨╛╨╗╨╛╨▓╨║╨╡"""
        if active:
            self.show_success()
        else:
            self._stop_loading()
            self._success_icon.hide()

    def show_loading(self):
        """╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В ╨░╨╜╨╕╨╝╨╕╤А╨╛╨▓╨░╨╜╨╜╤Л╨╣ ╤Б╨┐╨╕╨╜╨╜╨╡╤А ╨╖╨░╨│╤А╤Г╨╖╨║╨╕"""
        self._success_icon.hide()
        self._spinner.show()
        self._spinner.start()
        self._waiting_for_process_start = True  # ╨Ц╨┤╤С╨╝ ╨╖╨░╨┐╤Г╤Б╨║╨░ DPI
        # ╨г╨▒╨╡╨┤╨╕╨╝╤Б╤П, ╤З╤В╨╛ ╨╝╤Л ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╤Л ╨║ process_monitor
        if not self._process_monitor_connected:
            self._connect_process_monitor()
        # ╨Т direct_zapret2 ╤А╨╡╨╢╨╕╨╝╨░╤Е "apply" ╤З╨░╤Б╤В╨╛ ╨╜╨╡ ╨╝╨╡╨╜╤П╨╡╤В ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╡ ╨┐╤А╨╛╤Ж╨╡╤Б╤Б╨░ (hot-reload),
        # ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╨┤╨░╤С╨╝ ╨▒╤Л╤Б╤В╤А╤Л╨╣ ╤В╨░╨╣╨╝╨░╤Г╤В, ╤З╤В╨╛╨▒╤Л UI ╨╜╨╡ ╨╖╨░╨▓╨╕╤Б╨░╨╗ ╨╜╨░ ╤Б╨┐╨╕╨╜╨╜╨╡╤А╨╡.
        self._start_apply_feedback_timer()
        # ╨Ч╨░╨┐╤Г╤Б╨║╨░╨╡╨╝ fallback ╤В╨░╨╣╨╝╨╡╤А ╨╜╨░ ╤Б╨╗╤Г╤З╨░╨╣ ╨╡╤Б╨╗╨╕ ╤Б╨╕╨│╨╜╨░╨╗ ╨╜╨╡ ╨┐╤А╨╕╨┤╨╡╤В
        self._start_fallback_timer()

    def _stop_loading(self):
        """╨Ю╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╤В ╨░╨╜╨╕╨╝╨░╤Ж╨╕╤О ╨╖╨░╨│╤А╤Г╨╖╨║╨╕"""
        self._spinner.stop()
        self._spinner.hide()
        self._waiting_for_process_start = False  # ╨С╨╛╨╗╤М╤И╨╡ ╨╜╨╡ ╨╢╨┤╤С╨╝
        self._stop_apply_feedback_timer()
        self._stop_fallback_timer()

    def _start_apply_feedback_timer(self, timeout_ms: int = 1500):
        """╨С╤Л╤Б╤В╤А╤Л╨╣ ╤В╨░╨╣╨╝╨╡╤А, ╨║╨╛╤В╨╛╤А╤Л╨╣ ╨╖╨░╨▓╨╡╤А╤И╨░╨╡╤В ╤Б╨┐╨╕╨╜╨╜╨╡╤А ╨┐╨╛╤Б╨╗╨╡ apply/hot-reload."""
        self._stop_apply_feedback_timer()
        self._apply_feedback_timer = QTimer(self)
        self._apply_feedback_timer.setSingleShot(True)
        self._apply_feedback_timer.timeout.connect(self._on_apply_feedback_timeout)
        self._apply_feedback_timer.start(timeout_ms)

    def _stop_apply_feedback_timer(self):
        if self._apply_feedback_timer:
            self._apply_feedback_timer.stop()
            self._apply_feedback_timer = None

    def _on_apply_feedback_timeout(self):
        """
        ╨Т direct_zapret2 ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤П ╤З╨░╤Б╤В╨╛ ╨┐╤А╨╕╨╝╨╡╨╜╤П╤О╤В╤Б╤П ╨▒╨╡╨╖ ╤Б╨╝╨╡╨╜╤Л ╨┐╤А╨╛╤Ж╨╡╤Б╤Б╨░ (winws2 ╨╛╤Б╤В╨░╤С╤В╤Б╤П ╨╖╨░╨┐╤Г╤Й╨╡╨╜),
        ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╨╛╤А╨╕╨╡╨╜╤В╨╕╤А╤Г╨╡╨╝╤Б╤П ╨╜╨░ ╨▓╨║╨╗╤О╤З╨╡╨╜╨╜╨╛╤Б╤В╤М ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕, ╨░ ╨╜╨╡ ╨╜╨░ processStatusChanged.
        """
        if not self._waiting_for_process_start:
            return
        if (self._selected_strategy_id or "none") != "none":
            self.show_success()
        else:
            self._stop_loading()
            self._success_icon.hide()

    def _start_fallback_timer(self):
        """╨Ч╨░╨┐╤Г╤Б╨║╨░╨╡╤В fallback ╤В╨░╨╣╨╝╨╡╤А ╨┤╨╗╤П ╨╖╨░╤Й╨╕╤В╤Л ╨╛╤В ╨▒╨╡╤Б╨║╨╛╨╜╨╡╤З╨╜╨╛╨│╨╛ ╤Б╨┐╨╕╨╜╨╜╨╡╤А╨░"""
        self._stop_fallback_timer()  # ╨Ю╤Б╤В╨░╨╜╨╛╨▓╨╕╨╝ ╨┐╤А╨╡╨┤╤Л╨┤╤Г╤Й╨╕╨╣ ╨╡╤Б╨╗╨╕ ╨▒╤Л╨╗
        self._fallback_timer = QTimer(self)
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self._on_fallback_timeout)
        self._fallback_timer.start(10000)  # 10 ╤Б╨╡╨║╤Г╨╜╨┤ ╨╝╨░╨║╤Б╨╕╨╝╤Г╨╝

    def _stop_fallback_timer(self):
        """╨Ю╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╤В fallback ╤В╨░╨╣╨╝╨╡╤А"""
        if self._fallback_timer:
            self._fallback_timer.stop()
            self._fallback_timer = None

    def _on_fallback_timeout(self):
        """╨Т╤Л╨╖╤Л╨▓╨░╨╡╤В╤Б╤П ╨╡╤Б╨╗╨╕ ╤Б╨╕╨│╨╜╨░╨╗ processStatusChanged ╨╜╨╡ ╨┐╤А╨╕╤И╨╡╨╗ ╨╖╨░ 10 ╤Б╨╡╨║╤Г╨╜╨┤"""
        if self._waiting_for_process_start:
            log("StrategyDetailPage: fallback timeout - ╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨│╨░╨╗╨╛╤З╨║╤Г", "DEBUG")
            self.show_success()

    def show_success(self):
        """╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В ╨╖╨╡╨╗╤С╨╜╤Г╤О ╨│╨░╨╗╨╛╤З╨║╤Г ╤Г╤Б╨┐╨╡╤Е╨░"""
        self._stop_loading()
        self._success_icon.setPixmap(qta.icon('fa5s.check-circle', color='#4ade80').pixmap(16, 16))
        self._success_icon.show()

    def _connect_process_monitor(self):
        """╨Я╨╛╨┤╨║╨╗╤О╤З╨░╨╡╤В╤Б╤П ╨║ ╤Б╨╕╨│╨╜╨░╨╗╤Г processStatusChanged ╨╛╤В ProcessMonitorThread"""
        if self._process_monitor_connected:
            return  # ╨г╨╢╨╡ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╤Л

        try:
            if self.parent_app and hasattr(self.parent_app, 'process_monitor'):
                process_monitor = self.parent_app.process_monitor
                if process_monitor is not None:
                    process_monitor.processStatusChanged.connect(self._on_process_status_changed)
                    self._process_monitor_connected = True
                    log("StrategyDetailPage: ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜ ╨║ processStatusChanged", "DEBUG")
        except Exception as e:
            log(f"StrategyDetailPage: ╨╛╤И╨╕╨▒╨║╨░ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║ process_monitor: {e}", "DEBUG")

    def _on_process_status_changed(self, is_running: bool):
        """
        ╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤П ╤Б╤В╨░╤В╤Г╤Б╨░ ╨┐╤А╨╛╤Ж╨╡╤Б╤Б╨░ DPI.
        ╨Т╤Л╨╖╤Л╨▓╨░╨╡╤В╤Б╤П ╨║╨╛╨│╨┤╨░ winws.exe/winws2.exe ╨╖╨░╨┐╤Г╤Б╨║╨░╨╡╤В╤Б╤П ╨╕╨╗╨╕ ╨╛╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╤В╤Б╤П.
        """
        try:
            if is_running and self._waiting_for_process_start:
                # DPI ╨╖╨░╨┐╤Г╤Б╤В╨╕╨╗╤Б╤П ╨╕ ╨╝╤Л ╨╢╨┤╨░╨╗╨╕ ╤Н╤В╨╛╨│╨╛ - ╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨│╨░╨╗╨╛╤З╨║╤Г
                log("StrategyDetailPage: DPI ╨╖╨░╨┐╤Г╤Й╨╡╨╜, ╨┐╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨│╨░╨╗╨╛╤З╨║╤Г", "DEBUG")
                self.show_success()
        except Exception as e:
            log(f"StrategyDetailPage._on_process_status_changed error: {e}", "DEBUG")

    def _on_args_changed(self, strategy_id: str, args: list):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤П ╨░╤А╨│╤Г╨╝╨╡╨╜╤В╨╛╨▓ ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕"""
        if self._category_key:
            self.args_changed.emit(self._category_key, strategy_id, args)
            log(f"Args changed: {self._category_key}/{strategy_id} = {args}", "DEBUG")

    def _is_udp_like_category(self) -> bool:
        protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
        return ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)

    # ======================================================================
    # TCP MULTI-PHASE (direct_zapret2)
    # ======================================================================

    def _get_category_strategy_args_text(self) -> str:
        """Returns the stored strategy args (tcp_args/udp_args) for the current category."""
        if not self._category_key:
            return ""
        try:
            preset = self._preset_manager.get_active_preset()
            cat = preset.categories.get(self._category_key) if preset else None
            if not cat:
                return ""
            return cat.udp_args if self._is_udp_like_category() else cat.tcp_args
        except Exception:
            return ""

    def _get_strategy_args_text_by_id(self, strategy_id: str) -> str:
        data = dict(self._strategies_data_by_id.get(strategy_id, {}) or {})
        args = data.get("args", "")
        if isinstance(args, (list, tuple)):
            args = "\n".join([str(a) for a in args if a is not None])
        return _normalize_args_text(str(args or ""))

    def _infer_strategy_id_from_args_exact(self, args_text: str) -> str:
        """
        Best-effort exact match against loaded strategies.

        Returns:
            - matching strategy_id if found
            - "custom" if args are non-empty but don't match a single known strategy
            - "none" if args are empty
        """
        normalized = _normalize_args_text(args_text)
        if not normalized:
            return "none"

        for sid, data in (self._strategies_data_by_id or {}).items():
            if not sid or sid in ("none", TCP_FAKE_DISABLED_STRATEGY_ID):
                continue
            args_val = (data or {}).get("args") if isinstance(data, dict) else ""
            if isinstance(args_val, (list, tuple)):
                args_val = "\n".join([str(a) for a in args_val if a is not None])
            candidate = _normalize_args_text(str(args_val or ""))
            if candidate and candidate == normalized:
                return sid

        return CUSTOM_STRATEGY_ID

    def _extract_desync_techniques_from_args(self, args_text: str) -> list[str]:
        out: list[str] = []
        for raw in (args_text or "").splitlines():
            line = raw.strip()
            if not line or not line.startswith("--"):
                continue
            tech = _extract_desync_technique_from_arg(line)
            if tech:
                out.append(tech)
        return out

    def _infer_tcp_phase_key_for_strategy_args(self, args_text: str) -> str | None:
        """
        Returns a single phase key if all desync lines belong to the same phase.
        Otherwise returns None (multi-phase/unknown).
        """
        phase_keys: set[str] = set()
        for tech in self._extract_desync_techniques_from_args(args_text):
            phase = _map_desync_technique_to_tcp_phase(tech)
            if phase:
                phase_keys.add(phase)
        if len(phase_keys) == 1:
            return next(iter(phase_keys))
        return None

    def _is_tcp_phase_active_for_ui(self, phase_key: str) -> bool:
        """
        Phase is considered "active" when it contributes something to the args chain.

        - fake=disabled is NOT active
        - custom is active only if it has non-empty args chunk
        """
        key = str(phase_key or "").strip().lower()
        if not key:
            return False

        sid = (self._tcp_phase_selected_ids.get(key) or "").strip()
        if not sid or sid == "none":
            return False

        if key == "fake" and sid == TCP_FAKE_DISABLED_STRATEGY_ID:
            return False

        if sid == CUSTOM_STRATEGY_ID:
            chunk = _normalize_args_text(self._tcp_phase_custom_args.get(key, ""))
            return bool(chunk)

        return True

    def _update_tcp_phase_chip_markers(self) -> None:
        """
        Highlights all active phases (even when not currently selected).

        In the tab UI, this is implemented by cyan tab text for active phases.
        """
        if not self._tcp_phase_mode:
            return

        tabbar = self._phase_tabbar
        if not tabbar:
            return

        # Update Pivot item text: prefix with "тЧП" for active phases.
        _label_map = {pk: lbl for pk, lbl in TCP_PHASE_TAB_ORDER}
        for key in (self._phase_tab_index_by_key or {}).keys():
            try:
                is_active = bool(self._is_tcp_phase_active_for_ui(key))
            except Exception:
                is_active = False
            try:
                item = (tabbar.items or {}).get(key)
                if item is None:
                    continue
                orig = _label_map.get(key, key.upper())
                new_text = f"тЧП {orig}" if is_active else orig
                if item.text() != new_text:
                    item.setText(new_text)
                    item.adjustSize()
            except Exception:
                pass

    def _load_tcp_phase_state_from_preset(self) -> None:
        """Parses current tcp_args into phase selections (best-effort)."""
        self._tcp_phase_selected_ids = {}
        self._tcp_phase_custom_args = {}
        self._tcp_hide_fake_phase = False

        if not (self._tcp_phase_mode and self._category_key):
            return

        args_text = self._get_category_strategy_args_text()
        args_norm = _normalize_args_text(args_text)
        if not args_norm:
            # Default: fake disabled, no other phases selected.
            self._tcp_phase_selected_ids["fake"] = TCP_FAKE_DISABLED_STRATEGY_ID
            self._update_selected_strategy_header(self._selected_strategy_id)
            self._update_tcp_phase_chip_markers()
            return

        # Split current args into phase chunks (keep line order).
        phase_lines: dict[str, list[str]] = {k: [] for k in TCP_PHASE_COMMAND_ORDER}
        for raw in args_norm.splitlines():
            line = raw.strip()
            if not line or line == "--new":
                continue
            tech = _extract_desync_technique_from_arg(line)
            if not tech:
                continue
            if tech in TCP_EMBEDDED_FAKE_TECHNIQUES:
                self._tcp_hide_fake_phase = True
            phase = _map_desync_technique_to_tcp_phase(tech)
            if not phase:
                continue
            phase_lines.setdefault(phase, []).append(line)

        phase_chunks = {k: _normalize_args_text("\n".join(v)) for k, v in phase_lines.items() if v}

        # Build reverse lookup: (phase_key, normalized_args) -> strategy_id
        lookup: dict[str, dict[str, str]] = {k: {} for k in TCP_PHASE_COMMAND_ORDER}
        for sid, data in (self._strategies_data_by_id or {}).items():
            if not sid or sid == TCP_FAKE_DISABLED_STRATEGY_ID:
                continue
            args_val = (data or {}).get("args") if isinstance(data, dict) else ""
            if isinstance(args_val, (list, tuple)):
                args_val = "\n".join([str(a) for a in args_val if a is not None])
            s_args = _normalize_args_text(str(args_val or ""))
            if not s_args:
                continue
            phase_key = self._infer_tcp_phase_key_for_strategy_args(s_args)
            if not phase_key:
                continue
            # Keep first occurrence if duplicates exist.
            if s_args not in lookup.get(phase_key, {}):
                lookup.setdefault(phase_key, {})[s_args] = sid

        # Fake defaults to disabled if there is no explicit fake chunk.
        if "fake" not in phase_chunks:
            self._tcp_phase_selected_ids["fake"] = TCP_FAKE_DISABLED_STRATEGY_ID

        for phase_key, chunk in phase_chunks.items():
            if phase_key not in TCP_PHASE_COMMAND_ORDER:
                continue
            found = lookup.get(phase_key, {}).get(chunk)
            if found:
                self._tcp_phase_selected_ids[phase_key] = found
            else:
                self._tcp_phase_selected_ids[phase_key] = CUSTOM_STRATEGY_ID
                self._tcp_phase_custom_args[phase_key] = chunk

        self._update_selected_strategy_header(self._selected_strategy_id)
        self._update_tcp_phase_chip_markers()

    def _apply_tcp_phase_tabs_visibility(self) -> None:
        """Shows/hides the FAKE phase tab depending on selected main techniques."""
        if not self._tcp_phase_mode:
            return

        hide_fake = bool(self._tcp_hide_fake_phase)
        try:
            pivot = self._phase_tabbar
            if pivot is not None:
                fake_item = (pivot.items or {}).get("fake")
                if fake_item is not None:
                    fake_item.setVisible(not hide_fake)
        except Exception:
            pass

        if hide_fake and (self._active_phase_key or "") == "fake":
            self._set_active_phase_chip("multisplit")
            try:
                self._apply_filters()
            except Exception:
                pass

    def _set_active_phase_chip(self, phase_key: str) -> None:
        """Selects a phase tab programmatically without firing user side effects twice."""
        key = str(phase_key or "").strip().lower()
        if not (self._tcp_phase_mode and key and key in (self._phase_tab_index_by_key or {})):
            return

        pivot = self._phase_tabbar
        if not pivot:
            return

        # If the item is hidden (fake tab), fall back to multisplit.
        try:
            item = (pivot.items or {}).get(key)
            if item is None or not item.isVisible():
                key = "multisplit"
        except Exception:
            key = "multisplit"

        if key not in (getattr(pivot, "items", {}) or {}):
            return

        try:
            pivot.blockSignals(True)
            pivot.setCurrentItem(key)
        except Exception:
            pass
        finally:
            try:
                pivot.blockSignals(False)
            except Exception:
                pass

        self._active_phase_key = key

    def _select_default_tcp_phase_tab(self) -> None:
        """Chooses the initial active tab for TCP phase UI."""
        if not self._tcp_phase_mode:
            return

        # Prefer a main phase that is currently selected.
        preferred = None
        for k in ("multisplit", "multidisorder", "multidisorder_legacy", "tcpseg", "oob", "other"):
            sid = (self._tcp_phase_selected_ids.get(k) or "").strip()
            if sid:
                preferred = k
                break

        if not preferred:
            preferred = "multisplit"

        if self._tcp_hide_fake_phase and preferred == "fake":
            preferred = "multisplit"

        self._set_active_phase_chip(preferred)

    def _strategy_has_embedded_fake(self, strategy_id: str) -> bool:
        """True if strategy uses a built-in fake technique (fakedsplit/fakeddisorder/hostfakesplit)."""
        if not strategy_id:
            return False
        args_text = self._get_strategy_args_text_by_id(strategy_id)
        for tech in self._extract_desync_techniques_from_args(args_text):
            if tech in TCP_EMBEDDED_FAKE_TECHNIQUES:
                return True
        return False

    def _build_tcp_args_from_phase_state(self) -> str:
        """Builds the ordered chain of --lua-desync lines for tcp_args."""
        if not self._tcp_phase_mode:
            return ""

        out_lines: list[str] = []
        for phase in TCP_PHASE_COMMAND_ORDER:
            if phase == "fake" and self._tcp_hide_fake_phase:
                continue

            sid = (self._tcp_phase_selected_ids.get(phase) or "").strip()
            if not sid:
                continue

            if phase == "fake" and sid == TCP_FAKE_DISABLED_STRATEGY_ID:
                continue

            if sid == CUSTOM_STRATEGY_ID:
                chunk = _normalize_args_text(self._tcp_phase_custom_args.get(phase, ""))
            else:
                chunk = self._get_strategy_args_text_by_id(sid)

            if not chunk:
                continue

            for raw in chunk.splitlines():
                line = raw.strip()
                if line:
                    out_lines.append(line)

        return "\n".join(out_lines).strip()

    def _save_tcp_phase_state_to_preset(self, *, show_loading: bool = True) -> None:
        """Persists current phase state into preset tcp_args and emits selection update."""
        if not (self._tcp_phase_mode and self._category_key):
            return

        new_args = self._build_tcp_args_from_phase_state()

        try:
            preset = self._preset_manager.get_active_preset()
            if not preset:
                return

            if self._category_key not in preset.categories:
                preset.categories[self._category_key] = self._preset_manager._create_category_with_defaults(self._category_key)

            cat = preset.categories[self._category_key]
            cat.tcp_args = new_args
            cat.strategy_id = self._infer_strategy_id_from_args_exact(new_args)
            preset.touch()
            self._preset_manager._save_and_sync_preset(preset)

            # Update local state for enable toggle / UI.
            self._selected_strategy_id = cat.strategy_id or "none"
            self._current_strategy_id = cat.strategy_id or "none"
            self._enable_toggle.setChecked(self._selected_strategy_id != "none", block_signals=True)
            self._set_category_enabled_ui(self._selected_strategy_id != "none")
            self._refresh_args_editor_state()

            # UI feedback
            if show_loading and self._selected_strategy_id != "none":
                self.show_loading()
            elif self._selected_strategy_id == "none":
                self._stop_loading()
                self._success_icon.hide()

            self._update_selected_strategy_header(self._selected_strategy_id)
            self._update_tcp_phase_chip_markers()

            # Notify main page (strategy id is "custom" for multi-phase)
            self.strategy_selected.emit(self._category_key, self._selected_strategy_id)

        except Exception as e:
            log(f"TCP phase save failed: {e}", "ERROR")

    def _on_tcp_phase_row_clicked(self, strategy_id: str) -> None:
        """TCP multi-phase: applies selection for the currently active phase."""
        if not (self._tcp_phase_mode and self._category_key and self._strategies_tree):
            return

        phase = (self._active_phase_key or "").strip().lower()
        if not phase:
            return

        sid = str(strategy_id or "").strip()
        if not sid:
            return

        # Clicking a hidden/filtered row should not happen, but be defensive.
        try:
            if not self._strategies_tree.is_strategy_visible(sid):
                return
        except Exception:
            pass

        # Fake phase: clicking the same strategy again toggles it off.
        if phase == "fake":
            current = (self._tcp_phase_selected_ids.get("fake") or "").strip()
            if current and current == sid:
                # Same click toggles fake off (no separate "disabled" row).
                self._tcp_phase_selected_ids["fake"] = TCP_FAKE_DISABLED_STRATEGY_ID
                self._tcp_phase_custom_args.pop("fake", None)
                try:
                    self._strategies_tree.clear_active_strategy()
                except Exception:
                    pass
            else:
                self._tcp_phase_selected_ids["fake"] = sid
                self._tcp_phase_custom_args.pop("fake", None)
                self._strategies_tree.set_selected_strategy(sid)

            self._save_tcp_phase_state_to_preset(show_loading=True)
            return

        # Other phases: toggle off when clicking the currently selected strategy.
        current = (self._tcp_phase_selected_ids.get(phase) or "").strip()
        if current == sid:
            self._tcp_phase_selected_ids.pop(phase, None)
            self._tcp_phase_custom_args.pop(phase, None)
            try:
                self._strategies_tree.clear_active_strategy()
            except Exception:
                pass
        else:
            self._tcp_phase_selected_ids[phase] = sid
            self._tcp_phase_custom_args.pop(phase, None)
            self._strategies_tree.set_selected_strategy(sid)

        # Embedded-fake techniques remove the FAKE phase tab and suppress separate --lua-desync=fake.
        hide_fake = any(
            self._strategy_has_embedded_fake(sel_id)
            for k, sel_id in self._tcp_phase_selected_ids.items()
            if k != "fake" and sel_id and sel_id not in (CUSTOM_STRATEGY_ID, TCP_FAKE_DISABLED_STRATEGY_ID)
        )
        if not hide_fake:
            # Also detect embedded-fake inside custom chunks.
            for k, chunk in (self._tcp_phase_custom_args or {}).items():
                if k == "fake":
                    continue
                for tech in self._extract_desync_techniques_from_args(chunk):
                    if tech in TCP_EMBEDDED_FAKE_TECHNIQUES:
                        hide_fake = True
                        break
                if hide_fake:
                    break
        self._tcp_hide_fake_phase = hide_fake
        self._apply_tcp_phase_tabs_visibility()

        self._save_tcp_phase_state_to_preset(show_loading=True)

    def _set_category_block_dimmed(self, widget: QWidget | None, dimmed: bool) -> None:
        if widget is None:
            return

        try:
            widget.setProperty("categoryDisabled", bool(dimmed))
            style = widget.style()
            if style is not None:
                style.unpolish(widget)
                style.polish(widget)
            widget.update()
        except Exception:
            pass

        try:
            if dimmed:
                effect = widget.graphicsEffect()
                if not isinstance(effect, QGraphicsOpacityEffect):
                    effect = QGraphicsOpacityEffect(widget)
                    widget.setGraphicsEffect(effect)
                effect.setOpacity(0.56)
            else:
                widget.setGraphicsEffect(None)
        except Exception:
            pass

    def _set_category_enabled_ui(self, enabled: bool) -> None:
        """Keeps controls visible and dims blocks for disabled categories."""
        is_enabled = bool(enabled)
        try:
            if hasattr(self, "_toolbar_frame") and self._toolbar_frame is not None:
                self._toolbar_frame.setVisible(True)
                self._set_category_block_dimmed(self._toolbar_frame, not is_enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "_strategies_block") and self._strategies_block is not None:
                self._strategies_block.setVisible(True)
                self._set_category_block_dimmed(self._strategies_block, not is_enabled)
                if hasattr(self, "layout") and self.layout is not None:
                    self.layout.setStretchFactor(self._strategies_block, 1)
                self._strategies_block.setMaximumHeight(16777215)
        except Exception:
            pass
        try:
            self._refresh_scroll_range()
        except Exception:
            pass

    def _refresh_args_editor_state(self):
        enabled = bool(self._category_key) and (self._selected_strategy_id or "none") != "none"
        try:
            if hasattr(self, "_edit_args_btn"):
                self._edit_args_btn.setEnabled(enabled)
        except Exception:
            pass

        if not enabled:
            self._hide_args_editor(clear_text=True)

    def _toggle_args_editor(self):
        """╨Ю╤В╨║╤А╤Л╨▓╨░╨╡╤В MessageBoxBase ╨┤╨╕╨░╨╗╨╛╨│ ╨┤╨╗╤П ╤А╨╡╨┤╨░╨║╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П args ╤В╨╡╨║╤Г╤Й╨╡╨╣ ╨║╨░╤В╨╡╨│╨╛╤А╨╕╨╕."""
        if not self._category_key:
            return
        if (self._selected_strategy_id or "none") == "none":
            return

        initial = self._load_args_text()
        dlg = _ArgsEditorDialog(initial_text=initial, parent=self.window())
        if dlg.exec():
            self._apply_args_editor(dlg.get_text())

    def _hide_args_editor(self, clear_text: bool = False):
        """╨б╤В╨░╨▒ ╨┤╨╗╤П ╨╛╨▒╤А╨░╤В╨╜╨╛╨╣ ╤Б╨╛╨▓╨╝╨╡╤Б╤В╨╕╨╝╨╛╤Б╤В╨╕ тАФ ╤А╨╡╨┤╨░╨║╤В╨╛╤А ╤В╨╡╨┐╨╡╤А╤М ╨┤╨╕╨░╨╗╨╛╨│."""
        self._args_editor_dirty = False

    def _load_args_text(self) -> str:
        """╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В ╤В╨╡╨║╤Г╤Й╨╕╨╣ args ╤В╨╡╨║╤Б╤В ╨╕╨╖ ╨┐╤А╨╡╤Б╨╡╤В╨░ ╨┤╨╗╤П ╨╛╤В╨║╤А╤Л╤В╨╕╤П ╨▓ ╨┤╨╕╨░╨╗╨╛╨│╨╡."""
        if not self._category_key:
            return ""
        if (self._selected_strategy_id or "none") == "none":
            return ""
        try:
            preset = self._preset_manager.get_active_preset()
            cat = preset.categories.get(self._category_key) if preset else None
            if cat:
                return (cat.udp_args if self._is_udp_like_category() else cat.tcp_args) or ""
        except Exception as e:
            log(f"Args editor: failed to load preset args: {e}", "DEBUG")
        return ""

    def _load_args_into_editor(self):
        """╨б╤В╨░╨▒ ╨┤╨╗╤П ╨╛╨▒╤А╨░╤В╨╜╨╛╨╣ ╤Б╨╛╨▓╨╝╨╡╤Б╤В╨╕╨╝╨╛╤Б╤В╨╕."""
        pass

    def _on_args_editor_changed(self):
        """╨б╤В╨░╨▒ ╨┤╨╗╤П ╨╛╨▒╤А╨░╤В╨╜╨╛╨╣ ╤Б╨╛╨▓╨╝╨╡╤Б╤В╨╕╨╝╨╛╤Б╤В╨╕."""
        pass

    def _apply_args_editor(self, raw: str = ""):
        if not self._category_key:
            return
        if (self._selected_strategy_id or "none") == "none":
            return

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        normalized = "\n".join(lines)

        try:
            preset = self._preset_manager.get_active_preset()
            if not preset:
                return

            if self._category_key not in preset.categories:
                preset.categories[self._category_key] = self._preset_manager._create_category_with_defaults(self._category_key)

            cat = preset.categories[self._category_key]

            if self._is_udp_like_category():
                cat.udp_args = normalized
            else:
                cat.tcp_args = normalized

            preset.touch()
            self._preset_manager._save_and_sync_preset(preset)

            self._args_editor_dirty = False
            self.show_loading()
            self._on_args_changed(self._selected_strategy_id, lines)

        except Exception as e:
            log(f"Args editor: failed to save args: {e}", "ERROR")

    def _on_search_changed(self, text: str):
        """╨д╨╕╨╗╤М╤В╤А╤Г╨╡╤В ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╕ ╨┐╨╛ ╨┐╨╛╨╕╤Б╨║╨╛╨▓╨╛╨╝╤Г ╨╖╨░╨┐╤А╨╛╤Б╤Г"""
        self._apply_filters()

    def _on_filter_toggled(self, technique: str, active: bool):
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨┐╨╡╤А╨╡╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╤Д╨╕╨╗╤М╤В╤А╨░"""
        if active:
            self._active_filters.add(technique)
        else:
            self._active_filters.discard(technique)
        self._update_technique_filter_ui()
        self._apply_filters()

    def _build_sort_tooltip(self) -> str:
        mode = str(self._sort_mode or "default").strip().lower() or "default"
        if mode == "name_asc":
            label = "╨Я╨╛ ╨╕╨╝╨╡╨╜╨╕ (╨Р-╨п)"
        elif mode == "name_desc":
            label = "╨Я╨╛ ╨╕╨╝╨╡╨╜╨╕ (╨п-╨Р)"
        else:
            label = "╨Я╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О"
        return f"╨б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨░: {label}"

    def _update_sort_button_ui(self) -> None:
        btn = getattr(self, "_sort_btn", None)
        if not btn:
            return
        mode = str(self._sort_mode or "default").strip().lower() or "default"
        is_active = mode != "default"
        try:
            tokens = get_theme_tokens()
            color = tokens.accent_hex if is_active else tokens.fg_faint
            btn.setIcon(qta.icon('fa5s.sort-alpha-down', color=color))
        except Exception:
            pass
        try:
            set_tooltip(btn, self._build_sort_tooltip())
        except Exception:
            pass

    def _on_technique_filter_changed(self, index: int) -> None:
        """╨Ю╨▒╤А╨░╨▒╨╛╤В╤З╨╕╨║ ╨▓╤Л╨▒╨╛╤А╨░ ╤В╨╡╤Е╨╜╨╕╨║╨╕ ╨▓ ComboBox ╤Д╨╕╨╗╤М╤В╤А╨░."""
        self._active_filters.clear()
        if index > 0 and index <= len(STRATEGY_TECHNIQUE_FILTERS):
            key = STRATEGY_TECHNIQUE_FILTERS[index - 1][1]
            self._active_filters.add(key)
        self._apply_filters()

    def _update_technique_filter_ui(self) -> None:
        """╨б╨╕╨╜╤Е╤А╨╛╨╜╨╕╨╖╨╕╤А╤Г╨╡╤В ComboBox ╤Б ╤В╨╡╨║╤Г╤Й╨╕╨╝ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╡╨╝ _active_filters."""
        combo = getattr(self, "_filter_combo", None)
        if combo is None:
            return
        active = {str(t or "").strip().lower() for t in (self._active_filters or set()) if str(t or "").strip()}
        if not active:
            target_idx = 0
        else:
            technique = next(iter(active))
            target_idx = 0
            for i, (_label, key) in enumerate(STRATEGY_TECHNIQUE_FILTERS, start=1):
                if key == technique:
                    target_idx = i
                    break
        combo.blockSignals(True)
        combo.setCurrentIndex(target_idx)
        combo.blockSignals(False)

    def _on_phase_tab_changed(self, route_key: str) -> None:
        """TCP multi-phase: handler for Pivot currentItemChanged signal."""
        if not self._tcp_phase_mode:
            return

        key = str(route_key or "").strip().lower()
        if not key:
            return

        self._active_phase_key = key
        try:
            if self._category_key:
                self._last_active_phase_key_by_category[self._category_key] = key
                self._save_category_last_tcp_phase_tab(self._category_key, key)
        except Exception:
            pass

        self._apply_filters()
        self._sync_tree_selection_to_active_phase()

    def _on_phase_pivot_item_clicked(self, key: str) -> None:
        """Called on every click on a phase pivot item (including re-click of current item)."""
        if not self._tcp_phase_mode:
            return
        k = str(key or "").strip().lower()
        if not k:
            return
        # If clicking the already-active tab, just refresh filters (Pivot won't emit currentItemChanged).
        if k == (self._active_phase_key or ""):
            self._apply_filters()
            self._sync_tree_selection_to_active_phase()

    def _apply_filters(self):
        """╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╤В ╤Д╨╕╨╗╤М╤В╤А╤Л ╨┐╨╛ ╤В╨╡╤Е╨╜╨╕╨║╨╡ ╨║ ╤Б╨┐╨╕╤Б╨║╤Г ╤Б╤В╤А╨░╤В╨╡╨│╨╕╨╣"""
        if not self._strategies_tree:
            return
        search_text = self._search_input.text() if self._search_input else ""
        if self._tcp_phase_mode:
            try:
                self._strategies_tree.set_all_strategies_phase(self._active_phase_key)
            except Exception:
                pass
            self._strategies_tree.apply_phase_filter(search_text, self._active_phase_key)
            self._sync_tree_selection_to_active_phase()
            return

        try:
            self._strategies_tree.set_all_strategies_phase(None)
        except Exception:
            pass
        self._strategies_tree.apply_filter(search_text, self._active_filters)
        # Filtering/hiding can drop visual selection; restore for the active strategy if visible.
        sid = self._selected_strategy_id or self._current_strategy_id or "none"
        if sid and self._strategies_tree.has_strategy(sid) and self._strategies_tree.is_strategy_visible(sid):
            self._strategies_tree.set_selected_strategy(sid)

    def _sync_tree_selection_to_active_phase(self) -> None:
        """TCP multi-phase: restores highlighted row for the currently active phase."""
        if not (self._tcp_phase_mode and self._strategies_tree):
            return

        phase = (self._active_phase_key or "").strip().lower()
        if not phase:
            try:
                self._strategies_tree.clear_active_strategy()
            except Exception:
                pass
            return

        sid = (self._tcp_phase_selected_ids.get(phase) or "").strip()
        if sid and sid != CUSTOM_STRATEGY_ID and self._strategies_tree.has_strategy(sid) and self._strategies_tree.is_strategy_visible(sid):
            self._strategies_tree.set_selected_strategy(sid)
            return

        try:
            self._strategies_tree.clear_active_strategy()
        except Exception:
            pass

    def _show_sort_menu(self):
        """╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╤В RoundMenu ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╨╕ ╤Б ╨╕╨║╨╛╨╜╨║╨░╨╝╨╕."""
        menu = RoundMenu(parent=self)

        _sort_icon     = FluentIcon.SCROLL if _HAS_FLUENT else None
        _asc_icon      = FluentIcon.UP     if _HAS_FLUENT else None
        _desc_icon     = FluentIcon.DOWN   if _HAS_FLUENT else None

        def _set_sort(mode: str):
            self._sort_mode = mode
            if self._category_key:
                self._save_category_sort(self._category_key, self._sort_mode)
            self._apply_sort()

        entries = [
            (_sort_icon, "╨Я╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О",  "default"),
            (_asc_icon,  "╨Я╨╛ ╨╕╨╝╨╡╨╜╨╕ (╨Р-╨п)", "name_asc"),
            (_desc_icon, "╨Я╨╛ ╨╕╨╝╨╡╨╜╨╕ (╨п-╨Р)", "name_desc"),
        ]
        for icon, label, mode in entries:
            act = Action(icon, label, checkable=True) if _HAS_FLUENT else Action(label)
            act.setChecked(self._sort_mode == mode)
            act.triggered.connect(lambda _checked, m=mode: _set_sort(m))
            menu.addAction(act)

        try:
            pos = self._sort_btn.mapToGlobal(self._sort_btn.rect().bottomLeft())
        except Exception:
            return
        menu.exec(pos)

    def _apply_sort(self):
        """╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╤В ╤В╨╡╨║╤Г╤Й╤Г╤О ╤Б╨╛╤А╤В╨╕╤А╨╛╨▓╨║╤Г"""
        if not self._strategies_tree:
            return
        self._strategies_tree.set_sort_mode(self._sort_mode)
        self._strategies_tree.apply_sort()
        self._update_sort_button_ui()
        # Sorting (takeChildren/addChild) may reset selection in Qt; restore it.
        sid = self._selected_strategy_id or self._current_strategy_id or "none"
        if sid and self._strategies_tree.has_strategy(sid):
            self._strategies_tree.set_selected_strategy(sid)
