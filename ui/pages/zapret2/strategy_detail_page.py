# ui/pages/zapret2/strategy_detail_page.py
"""
Страница детального просмотра стратегий для выбранной категории.
Открывается при клике на категорию в Zapret2StrategiesPageNew.
"""

import re
import json

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent, QRectF
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QFrame, QPushButton, QScrollArea, QLineEdit, QMenu, QComboBox, QSpinBox,
    QCheckBox, QPlainTextEdit, QSizePolicy, QTabBar
)
from PyQt6.QtGui import QFont, QFontMetrics, QColor, QPainter, QFontMetricsF
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.dpi_settings_page import Win11ToggleRow
from ui.pages.strategies_page_base import ResetActionButton
from ui.widgets.win11_spinner import Win11Spinner
from ui.widgets.direct_zapret2_strategies_tree import DirectZapret2StrategiesTree, StrategyTreeRow
from strategy_menu.args_preview_dialog import ArgsPreviewDialog
from launcher_common.blobs import get_blobs_info
from preset_zapret2 import PresetManager, SyndataSettings
from ui.zapret2_strategy_marks import DirectZapret2MarksStore, DirectZapret2FavoritesStore
from log import log


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


class FilterModeSelector(QWidget):
    """Селектор режима фильтрации (Hostlist/IPset)"""
    mode_changed = pyqtSignal(str)  # emits "hostlist" or "ipset"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = "hostlist"
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._hostlist_btn = QPushButton("Hostlist")
        self._ipset_btn = QPushButton("IPset")

        for btn in [self._hostlist_btn, self._ipset_btn]:
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)

        self._hostlist_btn.clicked.connect(lambda: self._select("hostlist"))
        self._ipset_btn.clicked.connect(lambda: self._select("ipset"))

        # Стили
        self._update_styles()

        layout.addWidget(self._hostlist_btn)
        layout.addWidget(self._ipset_btn)

    def _select(self, mode: str):
        if mode != self._current_mode:
            self._current_mode = mode
            self._update_styles()
            self.mode_changed.emit(mode)

    def _update_styles(self):
        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                color: #000000;
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """

        # Left button - rounded left corners only
        left_radius = "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
        # Right button - rounded right corners only
        right_radius = "border-top-right-radius: 6px; border-bottom-right-radius: 6px;"

        if self._current_mode == "hostlist":
            self._hostlist_btn.setStyleSheet(active_style.replace("}", left_radius + "}"))
            self._hostlist_btn.setChecked(True)
            self._ipset_btn.setStyleSheet(inactive_style.replace("QPushButton {", "QPushButton { " + right_radius))
            self._ipset_btn.setChecked(False)
        else:
            self._hostlist_btn.setStyleSheet(inactive_style.replace("QPushButton {", "QPushButton { " + left_radius))
            self._hostlist_btn.setChecked(False)
            self._ipset_btn.setStyleSheet(active_style.replace("}", right_radius + "}"))
            self._ipset_btn.setChecked(True)

    def setCurrentMode(self, mode: str, block_signals: bool = False):
        """Set mode without emitting signal if block_signals=True"""
        if mode in ("hostlist", "ipset"):
            self._current_mode = mode
            self._update_styles()
            if not block_signals:
                self.mode_changed.emit(mode)

    def currentMode(self) -> str:
        return self._current_mode


class TTLButtonSelector(QWidget):
    """
    Универсальный селектор значения через ряд кнопок.
    Используется для send_ip_ttl, autottl_delta, autottl_min, autottl_max
    """
    value_changed = pyqtSignal(int)  # Эмитит выбранное значение

    def __init__(self, values: list, labels: list = None, parent=None):
        """
        Args:
            values: список int значений для кнопок, например [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            labels: опциональные метки для кнопок, например ["off", "1", "2", ...]
                   Если None - используются str(value)
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
        layout.setSpacing(2)  # Маленький отступ между кнопками

        for i, (value, label) in enumerate(zip(self._values, self._labels)):
            btn = QPushButton(label)
            btn.setFixedSize(36, 24)  # Увеличено с 28 для видимости текста
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, v=value: self._select(v))
            self._buttons.append((btn, value))
            layout.addWidget(btn)

        layout.addStretch()
        self._update_styles()

    def _select(self, value: int):
        if value != self._current_value:
            self._current_value = value
            self._update_styles()
            self.value_changed.emit(value)

    def _update_styles(self):
        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                color: #000000;
                font-size: 12px;
                font-weight: 600;
                border-radius: 4px;
                padding: 0 2px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                border-radius: 4px;
                padding: 0 2px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """
        for btn, value in self._buttons:
            if value == self._current_value:
                btn.setStyleSheet(active_style)
                btn.setChecked(True)
            else:
                btn.setStyleSheet(inactive_style)
                btn.setChecked(False)

    def setValue(self, value: int, block_signals: bool = False):
        """Устанавливает значение программно"""
        if value in self._values:
            if block_signals:
                self.blockSignals(True)
            self._current_value = value
            self._update_styles()
            if block_signals:
                self.blockSignals(False)

    def value(self) -> int:
        """Возвращает текущее значение"""
        return self._current_value


class ClickableLabel(QLabel):
    """Кликабельный label для breadcrumb навигации в стиле Windows 11"""

    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)
        # Устанавливаем свойство для предотвращения перетаскивания окна
        self.setProperty("clickable", True)
        self.setProperty("noDrag", True)

    def _update_style(self, hovered):
        if hovered:
            self.setStyleSheet("""
                QLabel {
                    color: #7dd7ff;
                    text-decoration: underline;
                    font-size: 22px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                    background: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    color: #60cdff;
                    font-size: 22px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                    background: transparent;
                }
            """)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Принимаем событие нажатия чтобы предотвратить перетаскивание окна"""
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()  # Важно: принимаем событие
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        super().mouseReleaseEvent(event)


class ElidedLabel(QLabel):
    """QLabel, который автоматически обрезает текст с троеточием по ширине."""

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


class ArgsPreview(QLabel):
    """Превью args на 2-3 строки (лёгкий QLabel вместо QTextEdit на каждой строке)."""

    def __init__(self, max_lines: int = 3, parent=None):
        super().__init__(parent)
        self._max_lines = max(1, int(max_lines or 1))
        self._full_text = ""

        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setStyleSheet("""
            QLabel {
                background: transparent;
                color: rgba(255, 255, 255, 0.45);
                padding: 0 4px;
                font-size: 9px;
                font-family: 'Consolas', monospace;
            }
        """)
        self._sync_height()

    def set_full_text(self, text: str):
        self._full_text = text or ""
        self.setToolTip((self._full_text or "").replace("\n", "<br>"))
        self.setText(self._wrap_friendly(self._full_text))

    def full_text(self) -> str:
        return self._full_text

    def _sync_height(self):
        metrics = QFontMetrics(self.font())
        line_h = metrics.lineSpacing()
        # +2 чтобы не резало нижние пиксели глифов на некоторых шрифтах/рендерах.
        self.setMaximumHeight((line_h * self._max_lines) + 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # QLabel сам переформатирует переносы по ширине; высоту держим постоянной.

    @staticmethod
    def _wrap_friendly(text: str) -> str:
        if not text:
            return ""
        # Добавляем точки переноса внутри "длинных слов" аргументов.
        zws = "\u200b"
        return (
            text.replace(":", f":{zws}")
            .replace(",", f",{zws}")
            .replace("=", f"={zws}")
        )


class StrategyRow(QFrame):
    """Строка выбора стратегии с избранным"""

    clicked = pyqtSignal()  # Клик по строке (выбор активной)
    favorite_toggled = pyqtSignal(str, bool)  # (strategy_id, is_favorite)
    marked_working = pyqtSignal(str, object)  # (strategy_id, is_working) where is_working is bool|None

    def __init__(self, strategy_id: str, name: str, args: list = None, parent=None):
        super().__init__(parent)
        self._strategy_id = strategy_id
        self._name = name
        self._args = args or []
        self._selected = False  # Активная (применённая) стратегия
        self._favorite = False  # Избранная (звезда)
        self._is_working = None

        self.setObjectName("strategyRow")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()
        self._update_style()

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(0)

        # Таймер для анимации загрузки
        self._loading_timer = None

        # Верхняя строка: звезда + название + индикатор
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Звезда избранного (отдельная от выбора)
        self._star_btn = QPushButton()
        self._star_btn.setFixedSize(18, 18)
        self._star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._star_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self._star_btn.clicked.connect(self._on_star_clicked)
        self._update_star_icon()
        top_row.addWidget(self._star_btn)

        # Название стратегии
        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #ffffff;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        top_row.addWidget(self._name_label, 1)

        # Индикатор рабочей/нерабочей
        self._working_label = QLabel()
        self._working_label.setStyleSheet("background: transparent;")
        self._working_label.setFixedWidth(16)
        self._working_label.hide()
        top_row.addWidget(self._working_label)

        # Индикатор загрузки (синий спиннер)
        self._loading_label = QLabel()
        self._loading_label.setFixedWidth(20)
        self._loading_label.setStyleSheet("background: transparent;")
        self._loading_label.hide()
        top_row.addWidget(self._loading_label)

        main_layout.addLayout(top_row)

        # Нижняя строка: args (видимые, но не редактируемые)
        self._args_view = None
        if self._strategy_id != "none":
            args_row = QHBoxLayout()
            args_row.setContentsMargins(22, 0, 0, 0)
            args_row.setSpacing(0)

            self._args_view = ArgsPreview(max_lines=3)
            self._args_view.set_full_text(self._format_args_multiline(self._args))
            args_row.addWidget(self._args_view, 1)
            main_layout.addLayout(args_row)

    @staticmethod
    def _format_args_multiline(args: list) -> str:
        parts: list[str] = []
        for part in (args or []):
            if part is None:
                continue
            text = str(part).strip()
            if not text:
                continue
            parts.append(text)
        return "\n".join(parts)

    def _on_star_clicked(self):
        """Переключает избранное"""
        self._favorite = not self._favorite
        self._update_star_icon()
        self.favorite_toggled.emit(self._strategy_id, self._favorite)

    def mousePressEvent(self, event):
        """Клик по строке - выбор активной стратегии"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Не обрабатываем если клик по звезде или полю ввода
            child = self.childAt(event.pos())
            if child not in (self._star_btn, self._args_view):
                self.clicked.emit()
        super().mousePressEvent(event)

    def set_args(self, args: list):
        self._args = args or []
        # UI редактора аргументов вынесен на уровень страницы (см. StrategyDetailPage)
        if self._args_view:
            if isinstance(self._args_view, ArgsPreview):
                self._args_view.set_full_text(self._format_args_multiline(self._args))
            else:
                self._args_view.setPlainText("\n".join(self._args))

    def set_selected(self, selected: bool):
        """Устанавливает активную (применённую) стратегию"""
        self._selected = selected
        self._update_style()

    def set_favorite(self, favorite: bool):
        """Устанавливает избранное"""
        self._favorite = favorite
        self._update_star_icon()

    def is_selected(self) -> bool:
        return self._selected

    def is_favorite(self) -> bool:
        return self._favorite

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QFrame#strategyRow {
                    background: rgba(96, 205, 255, 0.12);
                    border: none;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#strategyRow {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                }
                QFrame#strategyRow:hover {
                    background: rgba(255, 255, 255, 0.04);
                }
            """)

    def _update_star_icon(self):
        """Звезда зависит от избранного, не от выбора"""
        icon = self._get_star_icon(active=self._favorite)
        if icon is not None:
            self._star_btn.setIcon(icon)
        self._star_btn.setIconSize(QSize(14, 14))

    @staticmethod
    def _get_star_icon(active: bool):
        """Lazy-cache qtawesome icons to avoid per-row icon construction cost."""
        try:
            cache = getattr(StrategyRow, "_STAR_ICON_CACHE", None)
            if cache is None:
                cache = {
                    True: qta.icon("fa5s.star", color="#ffd700"),
                    False: qta.icon("mdi.star-outline", color="#ffffff"),
                }
                setattr(StrategyRow, "_STAR_ICON_CACHE", cache)
            return cache[bool(active)]
        except Exception:
            return None

    def set_loading(self, loading: bool):
        """Показывает/скрывает индикатор загрузки"""
        if loading:
            if not self._loading_timer:
                self._loading_timer = QTimer(self)
                self._loading_timer.timeout.connect(self._animate_row_loading)
            self._loading_timer.start(50)
            self._working_label.hide()  # Скрываем working label пока loading
            self._loading_label.show()
            self._animate_row_loading()
        else:
            if self._loading_timer:
                self._loading_timer.stop()
            self._loading_label.hide()

    def _animate_row_loading(self):
        """Анимация спиннера в строке"""
        # Используем qtawesome Spin animation
        icon = qta.icon('fa5s.circle-notch', color='#60cdff', animation=qta.Spin(self._loading_label))
        pixmap = icon.pixmap(14, 14)
        self._loading_label.setPixmap(pixmap)

    def _update_working_indicator(self):
        if self._is_working is True:
            self._working_label.setText("✓")
            self._working_label.setStyleSheet("background: transparent; color: #4ade80; font-size: 12px;")
            self._working_label.show()
        elif self._is_working is False:
            self._working_label.setText("✗")
            self._working_label.setStyleSheet("background: transparent; color: #f87171; font-size: 12px;")
            self._working_label.show()
        else:
            self._working_label.hide()

    def set_working_state(self, is_working):
        self._is_working = is_working
        self._update_working_indicator()

    def contextMenuEvent(self, event):
        """Контекстное меню для пометки стратегии как рабочей/нерабочей"""
        if self._strategy_id == "none":
            return  # Для "Отключено" меню не нужно

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d2d;
                border: none;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
            }
            QMenu::item:selected {
                background: rgba(96, 205, 255, 0.2);
            }
        """)

        mark_working = menu.addAction("✓ Пометить как рабочую")
        mark_not_working = menu.addAction("✗ Пометить как нерабочую")

        action = menu.exec(event.globalPos())

        if action == mark_working:
            new_state = None if self._is_working is True else True
            self._is_working = new_state
            self.marked_working.emit(self._strategy_id, new_state)
            self._update_working_indicator()
        elif action == mark_not_working:
            new_state = None if self._is_working is False else False
            self._is_working = new_state
            self.marked_working.emit(self._strategy_id, new_state)
            self._update_working_indicator()


class FilterChip(QPushButton):
    """Чип фильтра по технике"""

    toggled_filter = pyqtSignal(str, bool)  # (technique, is_active)

    def __init__(
        self,
        text: str,
        technique: str,
        parent=None,
        *,
        selected_radius: int | None = None,
        selected_style: str = "active",
    ):
        super().__init__(text, parent)
        self._technique = technique
        self._active_marker = False
        self._base_radius = 14
        self._selected_radius = int(selected_radius) if selected_radius is not None else self._base_radius
        self._selected_style = str(selected_style or "active").strip().lower() or "active"
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        # Use `toggled` instead of `clicked` so programmatic state changes
        # (e.g. exclusive tab groups) keep visuals in sync.
        self.toggled.connect(self._on_toggled)

    def set_active_marker(self, active: bool) -> None:
        """Marks chip as 'active' (blue) even when it's not checked."""
        want = bool(active)
        if want == bool(self._active_marker):
            return
        self._active_marker = want
        self._update_style()

    def _on_toggled(self, checked: bool):
        self._update_style()
        self.toggled_filter.emit(self._technique, bool(checked))

    def _update_style(self):
        is_selected = bool(self.isChecked())
        radius = self._selected_radius if is_selected else self._base_radius

        # "neutral" style is used for phase tabs:
        # - the *selected* (currently viewed) tab should NOT change color; only shape changes
        # - phases that "contribute args" are marked via `_active_marker` (blue), selected or not
        if self._selected_style == "neutral":
            if bool(self._active_marker):
                self.setStyleSheet('''
                    QPushButton {
                        background: rgba(96, 205, 255, 0.2);
                        border: 1px solid rgba(96, 205, 255, 0.5);
                        border-radius: %dpx;
                        color: #60cdff;
                        padding: 0 12px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: rgba(96, 205, 255, 0.3);
                    }
                ''' % radius)
                return

            # Same visuals as "inactive", but with a different radius when selected.
            self.setStyleSheet('''
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: none;
                    border-radius: %dpx;
                    color: rgba(255, 255, 255, 0.7);
                    padding: 0 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            ''' % radius)
            return

        if is_selected or bool(self._active_marker):
            self.setStyleSheet('''
                QPushButton {
                    background: rgba(96, 205, 255, 0.2);
                    border: 1px solid rgba(96, 205, 255, 0.5);
                    border-radius: %dpx;
                    color: #60cdff;
                    padding: 0 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(96, 205, 255, 0.3);
                }
            ''' % radius)
        else:
            self.setStyleSheet('''
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: none;
                    border-radius: %dpx;
                    color: rgba(255, 255, 255, 0.7);
                    padding: 0 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            ''' % radius)

    def reset(self):
        self._active_marker = False
        self.setChecked(False)
        self._update_style()


class PhaseTabBar(QTabBar):
    """
    Phase tabs for direct_zapret2 TCP multi-phase UI.

    Design (per `.claude/agents/ui-designer.md`):
    - Selected tab: thin cyan underline
    - Active phases (contributing args): cyan text
    - Inactive phases: white text
    - Horizontal scrolling when not fitting: QTabBar scroll buttons
    """

    _ACCENT_CYAN = QColor("#60cdff")
    _TEXT_PRIMARY = QColor(255, 255, 255)
    _TEXT_SECONDARY = QColor(255, 255, 255)
    _BG_HOVER = QColor(255, 255, 255, 15)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_keys: set[str] = set()
        self._hover_index: int = -1

        f = QFont("Segoe UI Variable", 10)
        try:
            f.setWeight(QFont.Weight.DemiBold)
        except Exception:
            pass
        try:
            self.setFont(f)
        except Exception:
            pass

        try:
            self.setMouseTracking(True)
        except Exception:
            pass

    def set_active_keys(self, keys: set[str]) -> None:
        try:
            self._active_keys = {str(k or "").strip().lower() for k in (keys or set()) if str(k or "").strip()}
        except Exception:
            self._active_keys = set()
        self.update()

    def _tab_key(self, index: int) -> str:
        try:
            return str(self.tabData(index) or "").strip().lower()
        except Exception:
            return ""

    def leaveEvent(self, event):  # noqa: N802 (Qt override)
        self._hover_index = -1
        try:
            self.update()
        except Exception:
            pass
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 (Qt override)
        try:
            idx = int(self.tabAt(event.pos()))
        except Exception:
            idx = -1
        if idx != int(self._hover_index):
            self._hover_index = idx
            try:
                self.update()
            except Exception:
                pass
        super().mouseMoveEvent(event)

    def paintEvent(self, event):  # noqa: N802 (Qt override)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        fm = QFontMetricsF(self.font())

        pad_x = 10.0
        pad_y = 6.0
        underline_h = 2.0
        underline_radius = 1.0
        hover_radius = 6.0

        for i in range(self.count()):
            try:
                if not bool(self.isTabVisible(i)):
                    continue
            except Exception:
                pass

            r = self.tabRect(i)
            if r.isNull():
                continue

            is_selected = int(i) == int(self.currentIndex())
            is_hover = int(i) == int(self._hover_index)
            key = self._tab_key(i)
            is_active = bool(key) and (key in (self._active_keys or set()))

            # Hover background (subtle)
            if is_hover:
                try:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(self._BG_HOVER)
                    p.drawRoundedRect(r.adjusted(0, 1, 0, -2), hover_radius, hover_radius)
                except Exception:
                    pass

            # Selected underline
            if is_selected:
                try:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(self._ACCENT_CYAN)
                    underline_y = float(r.bottom()) - underline_h + 1.0
                    p.drawRoundedRect(
                        QRectF(float(r.left()), float(underline_y), float(r.width()), float(underline_h)),
                        underline_radius,
                        underline_radius,
                    )
                except Exception:
                    pass

            # Text
            try:
                text = str(self.tabText(i) or "").strip()
            except Exception:
                text = ""

            try:
                color = self._ACCENT_CYAN if is_active else self._TEXT_SECONDARY
                if is_selected and not is_active:
                    color = self._TEXT_PRIMARY
                p.setPen(color)
            except Exception:
                pass

            tr = r.adjusted(int(pad_x), int(pad_y), -int(pad_x), -int(pad_y))
            try:
                elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, float(max(1, tr.width())))
            except Exception:
                elided = text
            try:
                p.drawText(tr, int(Qt.AlignmentFlag.AlignCenter), elided)
            except Exception:
                pass

        p.end()


class StrategyDetailPage(BasePage):
    """
    Страница детального выбора стратегии для категории.

    Signals:
        strategy_selected(str, str): Эмитится при выборе стратегии (category_key, strategy_id)
        args_changed(str, str, list): Эмитится при изменении аргументов (category_key, strategy_id, new_args)
        strategy_marked(str, str, object): Эмитится при пометке стратегии (category_key, strategy_id, is_working)
        back_clicked(): Эмитится при нажатии кнопки "Назад"
    """

    strategy_selected = pyqtSignal(str, str)  # category_key, strategy_id
    filter_mode_changed = pyqtSignal(str, str)  # category_key, "hostlist"|"ipset"
    args_changed = pyqtSignal(str, str, list)  # category_key, strategy_id, new_args
    strategy_marked = pyqtSignal(str, str, object)  # category_key, strategy_id, is_working (bool|None)
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            title="",  # Заголовок будет установлен динамически
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
        self._active_filters = set()  # Активные фильтры по технике
        # TCP multi-phase UI state (direct_zapret2, tcp.txt + tcp_fake.txt)
        self._tcp_phase_mode = False
        self._phase_tabbar: PhaseTabBar | None = None
        self._phase_tab_index_by_key: dict[str, int] = {}
        self._phase_tab_key_by_index: dict[int, str] = {}
        self._active_phase_key = None
        self._last_active_phase_key_by_category: dict[str, str] = {}
        self._tcp_phase_selected_ids: dict[str, str] = {}  # phase_key -> strategy_id
        self._tcp_phase_custom_args: dict[str, str] = {}  # phase_key -> raw args chunk (if no matching strategy)
        self._tcp_hide_fake_phase = False
        self._tcp_last_enabled_args_by_category: dict[str, str] = {}
        self._waiting_for_process_start = False  # Флаг ожидания запуска DPI
        self._process_monitor_connected = False  # Флаг подключения к process_monitor
        self._fallback_timer = None  # Таймер защиты от бесконечного спиннера
        self._apply_feedback_timer = None  # Быстрый таймер: убрать спиннер после apply
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

        self._build_content()

        # Close hover/pinned preview when the main window hides/deactivates (e.g. tray).
        QTimer.singleShot(0, self._install_main_window_event_filter)

        # Подключаемся к process_monitor для отслеживания статуса DPI
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
                    # Always close: prevents "stuck on top of all windows" previews.
                    self._close_preview_dialog(force=True)
        except Exception:
            pass
        return super().eventFilter(obj, event)

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
        from dpi.zapret2_core_restart import trigger_dpi_reload
        if self.parent_app:
            trigger_dpi_reload(
                self.parent_app,
                reason="preset_settings_changed",
                category_key=self._category_key
            )

    def _build_content(self):
        """Строит содержимое страницы"""
        # Скрываем стандартный заголовок BasePage
        self.title_label.hide()
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.hide()

        # Хедер с breadcrumb-навигацией в стиле Windows 11 Settings
        header = QFrame()
        header.setFrameShape(QFrame.Shape.NoFrame)
        header.setStyleSheet("background: transparent; border: none;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 16)
        header_layout.setSpacing(4)

        # Breadcrumb: "Стратегии DPI > Название категории"
        breadcrumb_layout = QHBoxLayout()
        breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        breadcrumb_layout.setSpacing(0)

        # Кликабельная часть: "Стратегии DPI"
        self._parent_link = ClickableLabel("Стратегии DPI")
        self._parent_link.clicked.connect(self.back_clicked.emit)
        breadcrumb_layout.addWidget(self._parent_link)

        # Разделитель ">"
        self._separator = QLabel("  >  ")
        self._separator.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 22px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                background: transparent;
            }
        """)
        breadcrumb_layout.addWidget(self._separator)

        # Название категории (не кликабельное)
        self._title = QLabel("Выберите категорию")
        self._title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 22px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                background: transparent;
            }
        """)
        breadcrumb_layout.addWidget(self._title)

        breadcrumb_layout.addStretch()
        header_layout.addLayout(breadcrumb_layout)

        # Строка с галочкой и подзаголовком
        subtitle_row = QHBoxLayout()
        subtitle_row.setContentsMargins(0, 0, 0, 0)
        subtitle_row.setSpacing(6)

        # Спиннер загрузки
        self._spinner = Win11Spinner(size=16, color="#60cdff")
        self._spinner.hide()
        subtitle_row.addWidget(self._spinner)

        # Галочка успеха (показывается после загрузки)
        self._success_icon = QLabel()
        self._success_icon.setFixedSize(16, 16)
        self._success_icon.setStyleSheet("background: transparent;")
        self._success_icon.hide()
        subtitle_row.addWidget(self._success_icon)

        # Подзаголовок (протокол | порты)
        self._subtitle = QLabel("")
        self._subtitle.setFont(QFont("Segoe UI", 11))
        self._subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.5); background: transparent;")
        subtitle_row.addWidget(self._subtitle)

        # Выбранная стратегия (мелким шрифтом, справа от портов)
        self._subtitle_strategy = ElidedLabel("")
        self._subtitle_strategy.setFont(QFont("Segoe UI", 11))
        self._subtitle_strategy.setStyleSheet(
            "color: rgba(255, 255, 255, 0.5); background: transparent; padding-left: 10px;"
        )
        self._subtitle_strategy.hide()
        subtitle_row.addWidget(self._subtitle_strategy, 1)

        header_layout.addLayout(subtitle_row)

        self.layout.addWidget(header)

        # ═══════════════════════════════════════════════════════════════
        # ВКЛЮЧЕНИЕ КАТЕГОРИИ + НАСТРОЙКИ
        # ═══════════════════════════════════════════════════════════════
        self._settings_host = QWidget()
        self._settings_host.setStyleSheet("background: transparent;")
        settings_host_layout = QVBoxLayout(self._settings_host)
        settings_host_layout.setContentsMargins(0, 0, 0, 0)
        settings_host_layout.setSpacing(6)

        # Toggle включения/выключения категории (без фоновой карточки)
        self._enable_toggle = Win11ToggleRow(
            "fa5s.power-off", "Включить обход",
            "Активировать DPI-обход для этой категории", "#4CAF50"
        )
        self._enable_toggle.toggled.connect(self._on_enable_toggled)
        settings_host_layout.addWidget(self._enable_toggle)

        # ═══════════════════════════════════════════════════════════════
        # ТУЛБАР НАСТРОЕК КАТЕГОРИИ (фоновой блок)
        # ═══════════════════════════════════════════════════════════════
        self._toolbar_frame = QFrame()
        self._toolbar_frame.setFrameShape(QFrame.Shape.NoFrame)
        self._toolbar_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._toolbar_frame.setVisible(False)
        self._toolbar_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 8px;
            }
        """)
        toolbar_layout = QVBoxLayout(self._toolbar_frame)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)

        # NEW: Режим фильтрации row
        self._filter_mode_frame = QFrame()
        self._filter_mode_frame.setStyleSheet("QFrame { background: transparent; }")
        filter_mode_layout = QHBoxLayout(self._filter_mode_frame)
        filter_mode_layout.setContentsMargins(0, 6, 0, 6)  # Match Win11ToggleRow margins
        filter_mode_layout.setSpacing(12)

        # Icon FIRST
        filter_icon = QLabel()
        filter_icon.setFixedSize(22, 22)  # Match Win11ToggleRow icon size
        filter_icon.setPixmap(qta.icon("fa5s.filter", color="#60cdff").pixmap(18, 18))
        filter_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_mode_layout.addWidget(filter_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Text
        filter_text_layout = QVBoxLayout()
        filter_text_layout.setSpacing(2)
        filter_title = QLabel("Режим фильтрации")
        filter_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        filter_desc = QLabel("Hostlist - по доменам, IPset - по IP")
        filter_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        filter_text_layout.addWidget(filter_title)
        filter_text_layout.addWidget(filter_desc)
        filter_mode_layout.addLayout(filter_text_layout)

        filter_mode_layout.addStretch()

        # Selector
        self._filter_mode_selector = FilterModeSelector()
        self._filter_mode_selector.mode_changed.connect(self._on_filter_mode_changed)
        filter_mode_layout.addWidget(self._filter_mode_selector)

        toolbar_layout.addWidget(self._filter_mode_frame)

        # ═══════════════════════════════════════════════════════════════
        # OUT RANGE SETTINGS
        # ═══════════════════════════════════════════════════════════════
        self._out_range_frame = QFrame()
        self._out_range_frame.setStyleSheet("QFrame { background: transparent; }")
        out_range_main_layout = QHBoxLayout(self._out_range_frame)
        out_range_main_layout.setContentsMargins(0, 6, 0, 6)
        out_range_main_layout.setSpacing(12)

        # Icon
        out_range_icon = QLabel()
        out_range_icon.setFixedSize(22, 22)
        out_range_icon.setPixmap(qta.icon("fa5s.filter", color="#60cdff").pixmap(18, 18))
        out_range_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        out_range_main_layout.addWidget(out_range_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Text
        out_range_text_layout = QVBoxLayout()
        out_range_text_layout.setSpacing(2)
        out_range_title = QLabel("Out Range")
        out_range_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        out_range_desc = QLabel("Ограничение исходящих пакетов для обработки")
        out_range_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        out_range_text_layout.addWidget(out_range_title)
        out_range_text_layout.addWidget(out_range_desc)
        out_range_main_layout.addLayout(out_range_text_layout)

        out_range_main_layout.addStretch()

        # Mode selector (n/d buttons)
        mode_label = QLabel("Режим:")
        mode_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        out_range_main_layout.addWidget(mode_label)

        self._out_range_mode_n = QPushButton("n")
        self._out_range_mode_d = QPushButton("d")
        for btn in [self._out_range_mode_n, self._out_range_mode_d]:
            btn.setFixedSize(36, 28)  # Увеличил ширину для видимости букв
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setToolTip("n = packets count, d = delay")

        self._out_range_mode_n.clicked.connect(lambda: self._select_out_range_mode("n"))
        self._out_range_mode_d.clicked.connect(lambda: self._select_out_range_mode("d"))

        # Set initial state
        self._out_range_mode = "n"
        self._update_out_range_mode_styles()

        out_range_main_layout.addWidget(self._out_range_mode_n)
        out_range_main_layout.addWidget(self._out_range_mode_d)

        # Value spinbox
        value_label = QLabel("Значение:")
        value_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent; margin-left: 12px;")
        out_range_main_layout.addWidget(value_label)

        self._out_range_spin = QSpinBox()
        self._out_range_spin.setRange(1, 999)
        self._out_range_spin.setValue(8)
        self._out_range_spin.setToolTip("--out-range: ограничение количества исходящих пакетов (n) или задержки (d)")
        self._out_range_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                min-width: 60px;
            }
        """)
        self._out_range_spin.valueChanged.connect(self._save_syndata_settings)
        out_range_main_layout.addWidget(self._out_range_spin)

        toolbar_layout.addWidget(self._out_range_frame)

        # ═══════════════════════════════════════════════════════════════
        # SEND SETTINGS (collapsible)
        # ═══════════════════════════════════════════════════════════════
        self._send_frame = QFrame()
        self._send_frame.setStyleSheet("QFrame { background: transparent; }")
        send_layout = QVBoxLayout(self._send_frame)
        send_layout.setContentsMargins(0, 6, 0, 6)
        send_layout.setSpacing(8)

        # Header row with toggle
        send_header = QHBoxLayout()
        send_header.setSpacing(12)
        send_icon = QLabel()
        send_icon.setFixedSize(22, 22)
        send_icon.setPixmap(qta.icon("fa5s.paper-plane", color="#60cdff").pixmap(18, 18))
        send_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        send_header.addWidget(send_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        send_title_layout = QVBoxLayout()
        send_title_layout.setSpacing(2)
        send_title = QLabel("Send параметры")
        send_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        send_desc = QLabel("Отправка копий пакетов")
        send_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        send_title_layout.addWidget(send_title)
        send_title_layout.addWidget(send_desc)
        send_header.addLayout(send_title_layout)
        send_header.addStretch()

        # Enable toggle switch (Win11 style)
        self._send_toggle = QPushButton()
        self._send_toggle.setCheckable(True)
        self._send_toggle.setFixedSize(44, 22)
        self._send_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_toggle.toggled.connect(self._on_send_toggled)
        self._send_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 11px;
                border: none;
            }
            QPushButton:checked {
                background: #60cdff;
            }
        """)
        send_header.addWidget(self._send_toggle)

        send_layout.addLayout(send_header)

        # Settings panel (shown when enabled)
        self._send_settings = QFrame()
        self._send_settings.setVisible(False)
        self._send_settings.setStyleSheet("QFrame { background: transparent; }")
        send_settings_layout = QVBoxLayout(self._send_settings)
        send_settings_layout.setContentsMargins(34, 8, 0, 0)  # Indent to align with text
        send_settings_layout.setSpacing(8)

        # Combo style for Send section
        send_combo_style = """
            QComboBox {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 4px 8px;
                min-width: 140px;
                font-size: 12px;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.12);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid rgba(255, 255, 255, 0.7);
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: rgba(96, 205, 255, 0.3);
            }
        """

        # SpinBox style for Send section
        send_spinbox_style = """
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
            }
        """

        # send_repeats row
        repeats_row = QHBoxLayout()
        repeats_row.setSpacing(8)
        repeats_label = QLabel("repeats:")
        repeats_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        repeats_label.setFixedWidth(60)
        self._send_repeats_spin = QSpinBox()
        self._send_repeats_spin.setRange(0, 10)
        self._send_repeats_spin.setValue(2)
        self._send_repeats_spin.setToolTip("Количество повторных отправок пакета (дефолт: 2)")
        self._send_repeats_spin.setStyleSheet(send_spinbox_style)
        self._send_repeats_spin.valueChanged.connect(self._save_syndata_settings)
        repeats_row.addWidget(repeats_label)
        repeats_row.addWidget(self._send_repeats_spin)
        repeats_row.addStretch()
        send_settings_layout.addLayout(repeats_row)

        # send_ip_ttl row
        send_ip_ttl_row = QHBoxLayout()
        send_ip_ttl_row.setSpacing(8)
        send_ip_ttl_label = QLabel("ip_ttl:")
        send_ip_ttl_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        send_ip_ttl_label.setFixedWidth(60)
        self._send_ip_ttl_selector = TTLButtonSelector(
            values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            labels=["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        )
        self._send_ip_ttl_selector.setToolTip("TTL для IPv4 отправляемых пакетов (off = auto)")
        self._send_ip_ttl_selector.value_changed.connect(self._save_syndata_settings)
        send_ip_ttl_row.addWidget(send_ip_ttl_label)
        send_ip_ttl_row.addWidget(self._send_ip_ttl_selector)
        send_ip_ttl_row.addStretch()
        send_settings_layout.addLayout(send_ip_ttl_row)

        # send_ip6_ttl row
        send_ip6_ttl_row = QHBoxLayout()
        send_ip6_ttl_row.setSpacing(8)
        send_ip6_ttl_label = QLabel("ip6_ttl:")
        send_ip6_ttl_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        send_ip6_ttl_label.setFixedWidth(60)
        self._send_ip6_ttl_selector = TTLButtonSelector(
            values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            labels=["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        )
        self._send_ip6_ttl_selector.setToolTip("TTL для IPv6 отправляемых пакетов (off = auto)")
        self._send_ip6_ttl_selector.value_changed.connect(self._save_syndata_settings)
        send_ip6_ttl_row.addWidget(send_ip6_ttl_label)
        send_ip6_ttl_row.addWidget(self._send_ip6_ttl_selector)
        send_ip6_ttl_row.addStretch()
        send_settings_layout.addLayout(send_ip6_ttl_row)

        # send_ip_id row
        send_ip_id_row = QHBoxLayout()
        send_ip_id_row.setSpacing(8)
        send_ip_id_label = QLabel("ip_id:")
        send_ip_id_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        send_ip_id_label.setFixedWidth(60)
        self._send_ip_id_combo = QComboBox()
        self._send_ip_id_combo.addItems(["none", "seq", "rnd", "zero"])
        self._send_ip_id_combo.setToolTip("Режим IP ID для отправляемых пакетов")
        self._send_ip_id_combo.setStyleSheet(send_combo_style)
        self._send_ip_id_combo.currentTextChanged.connect(self._save_syndata_settings)
        send_ip_id_row.addWidget(send_ip_id_label)
        send_ip_id_row.addWidget(self._send_ip_id_combo)
        send_ip_id_row.addStretch()
        send_settings_layout.addLayout(send_ip_id_row)

        # send_badsum row
        send_badsum_row = QHBoxLayout()
        send_badsum_row.setSpacing(8)
        send_badsum_label = QLabel("badsum:")
        send_badsum_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        send_badsum_label.setFixedWidth(60)
        self._send_badsum_check = QCheckBox()
        self._send_badsum_check.setToolTip("Отправлять пакеты с неправильной контрольной суммой")
        self._send_badsum_check.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.08);
            }
            QCheckBox::indicator:hover {
                background: rgba(255, 255, 255, 0.12);
            }
            QCheckBox::indicator:checked {
                background: #60cdff;
            }
        """)
        self._send_badsum_check.stateChanged.connect(self._save_syndata_settings)
        send_badsum_row.addWidget(send_badsum_label)
        send_badsum_row.addWidget(self._send_badsum_check)
        send_badsum_row.addStretch()
        send_settings_layout.addLayout(send_badsum_row)

        send_layout.addWidget(self._send_settings)
        toolbar_layout.addWidget(self._send_frame)

        # ═══════════════════════════════════════════════════════════════
        # SYNDATA SETTINGS (collapsible)
        # ═══════════════════════════════════════════════════════════════
        self._syndata_frame = QFrame()
        self._syndata_frame.setStyleSheet("QFrame { background: transparent; }")
        syndata_layout = QVBoxLayout(self._syndata_frame)
        syndata_layout.setContentsMargins(0, 6, 0, 6)
        syndata_layout.setSpacing(8)

        # Header row with toggle
        syndata_header = QHBoxLayout()
        syndata_header.setSpacing(12)
        syndata_icon = QLabel()
        syndata_icon.setFixedSize(22, 22)
        syndata_icon.setPixmap(qta.icon("fa5s.cog", color="#60cdff").pixmap(18, 18))
        syndata_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        syndata_header.addWidget(syndata_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        syndata_title_layout = QVBoxLayout()
        syndata_title_layout.setSpacing(2)
        syndata_title = QLabel("Syndata параметры")
        syndata_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        syndata_desc = QLabel("Дополнительные параметры обхода DPI")
        syndata_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        syndata_title_layout.addWidget(syndata_title)
        syndata_title_layout.addWidget(syndata_desc)
        syndata_header.addLayout(syndata_title_layout)
        syndata_header.addStretch()

        # Enable toggle switch (Win11 style)
        self._syndata_toggle = QPushButton()
        self._syndata_toggle.setCheckable(True)
        self._syndata_toggle.setFixedSize(44, 22)
        self._syndata_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._syndata_toggle.toggled.connect(self._on_syndata_toggled)
        self._syndata_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 11px;
                border: none;
            }
            QPushButton:checked {
                background: #60cdff;
            }
        """)
        syndata_header.addWidget(self._syndata_toggle)

        syndata_layout.addLayout(syndata_header)

        # Settings panel (shown when enabled)
        self._syndata_settings = QFrame()
        self._syndata_settings.setVisible(False)
        self._syndata_settings.setStyleSheet("QFrame { background: transparent; }")
        settings_layout = QVBoxLayout(self._syndata_settings)
        settings_layout.setContentsMargins(34, 8, 0, 0)  # Indent to align with text
        settings_layout.setSpacing(8)

        # Combo style
        combo_style = """
            QComboBox {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 4px 8px;
                min-width: 140px;
                font-size: 12px;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.12);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid rgba(255, 255, 255, 0.7);
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: rgba(96, 205, 255, 0.3);
            }
        """

        # Blob selector row
        blob_row = QHBoxLayout()
        blob_row.setSpacing(8)
        blob_label = QLabel("blob:")
        blob_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        blob_label.setFixedWidth(60)
        self._blob_combo = QComboBox()
        # Get all available blobs (system + user)
        try:
            all_blobs = get_blobs_info()
            blob_names = ["none"] + sorted(all_blobs.keys())
        except Exception:
            # Fallback to basic list if blobs module fails
            blob_names = ["none", "tls_google", "tls7"]
        self._blob_combo.addItems(blob_names)
        self._blob_combo.setStyleSheet(combo_style)
        self._blob_combo.currentTextChanged.connect(self._save_syndata_settings)
        blob_row.addWidget(blob_label)
        blob_row.addWidget(self._blob_combo)
        blob_row.addStretch()
        settings_layout.addLayout(blob_row)

        # tls_mod selector row
        tls_mod_row = QHBoxLayout()
        tls_mod_row.setSpacing(8)
        tls_mod_label = QLabel("tls_mod:")
        tls_mod_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        tls_mod_label.setFixedWidth(60)
        self._tls_mod_combo = QComboBox()
        self._tls_mod_combo.addItems(["none", "rnd", "rndsni", "sni=google.com"])
        self._tls_mod_combo.setStyleSheet(combo_style)
        self._tls_mod_combo.currentTextChanged.connect(self._save_syndata_settings)
        tls_mod_row.addWidget(tls_mod_label)
        tls_mod_row.addWidget(self._tls_mod_combo)
        tls_mod_row.addStretch()
        settings_layout.addLayout(tls_mod_row)

        # ═══════════════════════════════════════════════════════════════
        # AUTOTTL SETTINGS (три строки с кнопками)
        # ═══════════════════════════════════════════════════════════════
        autottl_header = QLabel("AutoTTL")
        autottl_header.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        settings_layout.addWidget(autottl_header)

        # Контейнер для трёх строк autottl
        autottl_container = QVBoxLayout()
        autottl_container.setSpacing(6)
        autottl_container.setContentsMargins(0, 0, 0, 0)

        # --- Delta row ---
        delta_row = QHBoxLayout()
        delta_row.setSpacing(8)
        delta_label = QLabel("d:")
        delta_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        delta_label.setFixedWidth(30)
        self._autottl_delta_selector = TTLButtonSelector(
            values=[0, -1, -2, -3, -4, -5, -6, -7, -8, -9],
            labels=["OFF", "-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"]
        )
        self._autottl_delta_selector.setToolTip("Delta: смещение от измеренного TTL (OFF = убрать ip_autottl)")
        self._autottl_delta_selector.value_changed.connect(self._save_syndata_settings)
        delta_row.addWidget(delta_label)
        delta_row.addWidget(self._autottl_delta_selector)
        delta_row.addStretch()
        autottl_container.addLayout(delta_row)

        # --- Min row ---
        min_row = QHBoxLayout()
        min_row.setSpacing(8)
        min_label = QLabel("min:")
        min_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        min_label.setFixedWidth(30)
        self._autottl_min_selector = TTLButtonSelector(
            values=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            labels=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        )
        self._autottl_min_selector.setToolTip("Минимальный TTL")
        self._autottl_min_selector.value_changed.connect(self._save_syndata_settings)
        min_row.addWidget(min_label)
        min_row.addWidget(self._autottl_min_selector)
        min_row.addStretch()
        autottl_container.addLayout(min_row)

        # --- Max row ---
        max_row = QHBoxLayout()
        max_row.setSpacing(8)
        max_label = QLabel("max:")
        max_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        max_label.setFixedWidth(30)
        self._autottl_max_selector = TTLButtonSelector(
            values=[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            labels=["15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
        )
        self._autottl_max_selector.setToolTip("Максимальный TTL")
        self._autottl_max_selector.value_changed.connect(self._save_syndata_settings)
        max_row.addWidget(max_label)
        max_row.addWidget(self._autottl_max_selector)
        max_row.addStretch()
        autottl_container.addLayout(max_row)

        settings_layout.addLayout(autottl_container)

        # TCP flags row
        flags_row = QHBoxLayout()
        flags_row.setSpacing(8)
        flags_label = QLabel("tcp_flags_unset:")
        flags_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        flags_label.setFixedWidth(100)
        self._tcp_flags_combo = QComboBox()
        self._tcp_flags_combo.addItems(["none", "ack", "psh", "ack,psh"])
        self._tcp_flags_combo.setStyleSheet(combo_style)
        self._tcp_flags_combo.currentTextChanged.connect(self._save_syndata_settings)
        flags_row.addWidget(flags_label)
        flags_row.addWidget(self._tcp_flags_combo)
        flags_row.addStretch()
        settings_layout.addLayout(flags_row)

        syndata_layout.addWidget(self._syndata_settings)
        toolbar_layout.addWidget(self._syndata_frame)

        # ═══════════════════════════════════════════════════════════════
        # RESET SETTINGS BUTTON
        # ═══════════════════════════════════════════════════════════════
        self._reset_row_widget = QWidget()
        self._reset_row_widget.setStyleSheet("background: transparent;")
        reset_row = QHBoxLayout(self._reset_row_widget)
        reset_row.setContentsMargins(0, 8, 0, 0)
        reset_row.setSpacing(0)
        reset_row.addStretch()

        self._reset_settings_btn = ResetActionButton(
            "Сбросить настройки",
            confirm_text="Сбросить все?"
        )
        self._reset_settings_btn.reset_confirmed.connect(self._on_reset_settings_confirmed)
        reset_row.addWidget(self._reset_settings_btn)

        toolbar_layout.addWidget(self._reset_row_widget)

        settings_host_layout.addWidget(self._toolbar_frame)
        self.layout.addWidget(self._settings_host)

        # All strategy controls are hidden when the category is disabled.
        self._strategies_block = QWidget()
        self._strategies_block.setStyleSheet("background: transparent;")
        self._strategies_block.setVisible(False)
        strategies_layout = QVBoxLayout(self._strategies_block)
        strategies_layout.setContentsMargins(0, 0, 0, 0)
        strategies_layout.setSpacing(0)

        # Поиск по стратегиям
        self._search_bar_widget = QWidget()
        self._search_bar_widget.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(self._search_bar_widget)
        search_layout.setContentsMargins(0, 0, 0, 8)
        search_layout.setSpacing(0)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по args...")
        self._search_input.setFixedHeight(36)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 0 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 0.08);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        # Кнопка сортировки
        self._sort_btn = QPushButton()
        self._sort_btn.setIcon(qta.icon('fa5s.sort-alpha-down', color='#999999'))
        self._sort_btn.setFixedSize(36, 36)
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setToolTip("Сортировка")
        self._sort_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        self._sort_btn.clicked.connect(self._show_sort_menu)
        search_layout.addWidget(self._sort_btn)

        # Кнопка редактирования args (лениво, отдельная панель)
        self._edit_args_btn = QPushButton()
        self._edit_args_btn.setIcon(qta.icon('fa5s.edit', color='#999999'))
        self._edit_args_btn.setFixedSize(36, 36)
        self._edit_args_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_args_btn.setToolTip("Аргументы стратегии (по выбранной категории)")
        self._edit_args_btn.setEnabled(False)
        self._edit_args_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.02);
            }
        """)
        self._edit_args_btn.clicked.connect(self._toggle_args_editor)
        search_layout.addWidget(self._edit_args_btn)

        strategies_layout.addWidget(self._search_bar_widget)

        # Панель редактирования args (создаём один редактор на страницу вместо QTextEdit на каждой строке)
        self._args_editor_dirty = False
        self._args_editor_frame = QFrame()
        self._args_editor_frame.setVisible(False)
        self._args_editor_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 8px;
            }
        """)
        args_editor_layout = QVBoxLayout(self._args_editor_frame)
        args_editor_layout.setContentsMargins(12, 10, 12, 10)
        args_editor_layout.setSpacing(8)

        args_header = QHBoxLayout()
        args_header.setContentsMargins(0, 0, 0, 0)
        args_header.setSpacing(8)
        args_title = QLabel("Аргументы стратегии (один аргумент на строку)")
        args_title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px; background: transparent;")
        args_header.addWidget(args_title)
        args_header.addStretch()

        self._args_apply_btn = QPushButton("Сохранить")
        self._args_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._args_apply_btn.setEnabled(False)
        self._args_apply_btn.clicked.connect(self._apply_args_editor)
        self._args_apply_btn.setStyleSheet("""
            QPushButton {
                background: rgba(96, 205, 255, 0.18);
                border: 1px solid rgba(96, 205, 255, 0.35);
                border-radius: 6px;
                color: #60cdff;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(96, 205, 255, 0.25); }
            QPushButton:disabled { background: rgba(255,255,255,0.04); border: none; color: rgba(255,255,255,0.35); }
        """)
        args_header.addWidget(self._args_apply_btn)

        self._args_cancel_btn = QPushButton("Скрыть")
        self._args_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._args_cancel_btn.clicked.connect(self._hide_args_editor)
        self._args_cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 6px;
                color: rgba(255,255,255,0.8);
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.08); }
        """)
        args_header.addWidget(self._args_cancel_btn)

        args_editor_layout.addLayout(args_header)

        self._args_editor = QPlainTextEdit()
        self._args_editor.setPlaceholderText("Например:\n--dpi-desync=multisplit\n--dpi-desync-split-pos=1")
        self._args_editor.setMinimumHeight(80)
        self._args_editor.setMaximumHeight(160)
        self._args_editor.setStyleSheet("""
            QPlainTextEdit {
                background: rgba(0, 0, 0, 0.12);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.9);
                padding: 8px;
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }
            QPlainTextEdit:focus {
                border: 1px solid rgba(96, 205, 255, 0.35);
            }
        """)
        self._args_editor.textChanged.connect(self._on_args_editor_changed)
        args_editor_layout.addWidget(self._args_editor)

        strategies_layout.addWidget(self._args_editor_frame)

        # Фильтры по типу стратегии
        self._filters_bar_widget = QWidget()
        self._filters_bar_widget.setStyleSheet("background: transparent;")
        filters_layout = QHBoxLayout(self._filters_bar_widget)
        filters_layout.setContentsMargins(0, 0, 0, 8)
        filters_layout.setSpacing(6)

        self._filter_chips = {}
        techniques = [
            ("Fake", "fake"),
            ("Split", "split"),
            ("Multisplit", "multisplit"),
            ("Disorder", "disorder"),
            ("OOB", "oob"),
            ("Syndata", "syndata"),
        ]

        for label, technique in techniques:
            chip = FilterChip(label, technique)
            chip.toggled_filter.connect(self._on_filter_toggled)
            self._filter_chips[technique] = chip
            filters_layout.addWidget(chip)

        filters_layout.addStretch()

        strategies_layout.addWidget(self._filters_bar_widget)

        # TCP multi-phase "tabs" (shown only for tcp categories in direct_zapret2)
        self._phases_bar_widget = QWidget()
        self._phases_bar_widget.setStyleSheet("background: transparent;")
        self._phases_bar_widget.setVisible(False)
        try:
            # Prevent frameless window drag from stealing tab clicks.
            self._phases_bar_widget.setProperty("noDrag", True)
        except Exception:
            pass
        phases_layout = QHBoxLayout(self._phases_bar_widget)
        phases_layout.setContentsMargins(0, 0, 0, 8)
        phases_layout.setSpacing(0)

        self._phase_tabbar = PhaseTabBar(self)
        self._phase_tabbar.setDrawBase(False)
        self._phase_tabbar.setExpanding(False)
        self._phase_tabbar.setMovable(False)
        self._phase_tabbar.setUsesScrollButtons(True)
        try:
            self._phase_tabbar.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass
        try:
            # Prevent frameless window drag from stealing tab clicks.
            self._phase_tabbar.setProperty("noDrag", True)
        except Exception:
            pass

        # Keep scroll buttons aligned with the app style (tabs are custom-painted).
        self._phase_tabbar.setStyleSheet("""
            QTabBar { background: transparent; }
            QTabBar QToolButton {
                background: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 6px;
                margin: 0 2px;
            }
            QTabBar QToolButton:hover {
                background: rgba(255, 255, 255, 0.10);
            }
        """)

        self._phase_tab_index_by_key = {}
        self._phase_tab_key_by_index = {}
        for phase_key, label in TCP_PHASE_TAB_ORDER:
            idx = self._phase_tabbar.addTab(label)
            key = str(phase_key or "").strip().lower()
            self._phase_tab_index_by_key[key] = idx
            self._phase_tab_key_by_index[idx] = key
            try:
                self._phase_tabbar.setTabData(idx, key)
            except Exception:
                pass

        try:
            self._phase_tabbar.currentChanged.connect(self._on_phase_tab_changed)
        except Exception:
            pass
        try:
            self._phase_tabbar.tabBarClicked.connect(self._on_phase_tab_clicked)
        except Exception:
            pass

        phases_layout.addWidget(self._phase_tabbar, 1)
        strategies_layout.addWidget(self._phases_bar_widget)

        # Лёгкий список стратегий: item-based, без сотен QWidget в layout
        self._strategies_tree = DirectZapret2StrategiesTree(self)
        # Внутренний скролл у дерева (надёжнее, чем растягивать страницу по высоте)
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
        """Обновляет подзаголовок: показывает выбранную стратегию рядом с портами."""
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
                self._subtitle_strategy.setToolTip(text)
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
            self._subtitle_strategy.setToolTip(f"{name}\nID: {sid}")
            self._subtitle_strategy.show()
        except Exception:
            pass

    def show_category(self, category_key: str, category_info, current_strategy_id: str):
        """
        Показывает стратегии для выбранной категории.

        Args:
            category_key: Ключ категории (например, "youtube_https")
            category_info: Объект CategoryInfo с информацией о категории
            current_strategy_id: ID текущей выбранной стратегии
        """
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

        # Обновляем заголовок (только название категории в breadcrumb)
        self._title.setText(category_info.full_name)
        self._subtitle.setText(f"{category_info.protocol}  |  порты: {category_info.ports}")
        self._update_selected_strategy_header(self._selected_strategy_id)

        # Determine whether to use the TCP multi-phase UI:
        # - only for TCP strategies (tcp.txt)
        # - only for direct_zapret2 standard set (no orchestra/zapret1)
        new_strategy_type = str(getattr(category_info, "strategy_type", "") or "tcp").strip().lower()
        is_udp_like_now = self._is_udp_like_category()
        try:
            from strategy_menu.strategies_registry import get_current_strategy_set
            strategy_set = get_current_strategy_set()
        except Exception:
            strategy_set = None
        want_tcp_phase_mode = (new_strategy_type == "tcp") and (not is_udp_like_now) and (strategy_set is None)

        self._tcp_phase_mode = bool(want_tcp_phase_mode)
        try:
            if hasattr(self, "_filters_bar_widget") and self._filters_bar_widget is not None:
                self._filters_bar_widget.setVisible(not self._tcp_phase_mode)
        except Exception:
            pass
        try:
            if hasattr(self, "_phases_bar_widget") and self._phases_bar_widget is not None:
                self._phases_bar_widget.setVisible(self._tcp_phase_mode)
        except Exception:
            pass

        # Для категорий одного strategy_type (особенно tcp) список стратегий одинаковый,
        # поэтому не пересобираем виджеты каждый раз: это ускоряет повторные переходы.
        reuse_list = (
            bool(self._strategies_tree and self._strategies_tree.has_rows())
            and self._loaded_strategy_type == new_strategy_type
            and self._loaded_strategy_set == strategy_set
            and bool(self._loaded_tcp_phase_mode) == bool(want_tcp_phase_mode)
        )

        if not reuse_list:
            # Очищаем старые стратегии
            self._clear_strategies()
            # Загружаем новые
            self._load_strategies()
        else:
            # Обновляем избранное для новой категории
            for sid in (self._strategies_tree.get_strategy_ids() if self._strategies_tree else []):
                want_fav = sid in self._favorite_strategy_ids
                self._strategies_tree.set_favorite_state(sid, want_fav)

            # Обновляем отметки working/not working для новой категории
            self._refresh_working_marks_for_category()

            # Обновляем выделение текущей стратегии
            if self._strategies_tree:
                if self._strategies_tree.has_strategy(self._current_strategy_id):
                    self._strategies_tree.set_selected_strategy(self._current_strategy_id)
                elif self._strategies_tree.has_strategy("none"):
                    self._strategies_tree.set_selected_strategy("none")
                else:
                    self._strategies_tree.clearSelection()
            # Восстанавливаем последнюю позицию прокрутки для этой категории.
            self._restore_scroll_state(category_key, defer=True)

        # Обновляем состояние toggle включения
        is_enabled = self._current_strategy_id != "none"
        self._enable_toggle.setChecked(is_enabled, block_signals=True)

        # Обновляем галочку статуса
        self._update_status_icon(is_enabled)

        # Показываем режим фильтрации только если категория поддерживает оба варианта
        has_ipset = hasattr(category_info, 'base_filter_ipset') and category_info.base_filter_ipset
        has_hostlist = hasattr(category_info, 'base_filter_hostlist') and category_info.base_filter_hostlist
        if has_ipset and has_hostlist:
            self._filter_mode_frame.setVisible(True)
            saved_filter_mode = self._load_category_filter_mode(category_key)
            self._filter_mode_selector.setCurrentMode(saved_filter_mode, block_signals=True)
        else:
            self._filter_mode_frame.setVisible(False)

        # Очищаем поиск и загружаем сохранённую сортировку
        self._search_input.clear()
        self._sort_mode = self._load_category_sort(category_key)

        # Сбрасываем фильтры по технике
        self._active_filters.clear()
        for chip in self._filter_chips.values():
            chip.reset()

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

        # Применяем сохранённую сортировку (если не default)
        self._apply_sort()
        self._apply_filters()

        # Загружаем syndata настройки для категории
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
        else:
            self._send_frame.setVisible(True)
            self._syndata_frame.setVisible(True)

        # Args editor availability depends on whether category is enabled (strategy != none)
        self._refresh_args_editor_state()
        self._set_category_enabled_ui(is_enabled)

        log(f"StrategyDetailPage: показана категория {category_key}, sort_mode={self._sort_mode}", "DEBUG")

    def refresh_from_preset_switch(self):
        """
        Асинхронно перечитывает активный пресет и обновляет текущую категорию (если открыта).
        Вызывается из MainWindow после активации пресета.
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
        """Прокручивает страницу к текущей стратегии (не меняя порядок списка)."""
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
            # ymargin: немного контекста вокруг строки
            self.ensureVisible(center.x(), center.y(), 0, 64)
        except Exception:
            pass

    def _clear_strategies(self):
        """Очищает список стратегий"""
        # Останавливаем ленивую загрузку если она идёт
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
        """Загружает стратегии для текущей категории"""
        try:
            from strategy_menu.strategies_registry import registry

            # Получаем информацию о категории
            category_info = registry.get_category_info(self._category_key)
            if category_info:
                log(f"StrategyDetailPage: категория {self._category_key}, strategy_type={category_info.strategy_type}", "DEBUG")
            else:
                log(f"StrategyDetailPage: категория {self._category_key} не найдена в реестре!", "ERROR")
                return

            # Получаем стратегии для категории
            strategies = registry.get_category_strategies(self._category_key)
            log(f"StrategyDetailPage: загружено {len(strategies)} стратегий для {self._category_key}", "DEBUG")

            # TCP multi-phase: load additional pure-fake strategies from tcp_fake.txt
            if self._tcp_phase_mode:
                try:
                    from strategy_menu.strategy_loader import load_strategies_as_dict
                    fake_strategies = load_strategies_as_dict("tcp_fake")
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
                # Пробуем перезагрузить реестр
                log(f"Стратегии пусты, пробуем перезагрузить реестр...", "WARNING")
                registry.reload_strategies()
                strategies = registry.get_category_strategies(self._category_key)
                log(f"После перезагрузки: {len(strategies)} стратегий", "DEBUG")

                # Если все еще пусто, показываем диагностику
                if not strategies:
                    from strategy_menu.strategy_loader import _get_builtin_dir
                    builtin_dir = _get_builtin_dir()
                    log(f"Builtin директория: {builtin_dir}", "WARNING")
                    log(f"strategy_type для загрузки: {category_info.strategy_type}", "WARNING")

            # Лениво добавляем строки порциями, чтобы не фризить UI
            items = list(strategies.items())

            # "default" порядок UI должен совпадать с порядком в источнике (tcp.txt и т.п.).
            # Текущую/дефолтную стратегию НЕ поднимаем.
            self._pending_strategies_items = items
            self._pending_strategies_index = 0
            self._strategies_load_generation += 1
            gen = self._strategies_load_generation
            total = len(self._pending_strategies_items)
            # "default" порядок UI должен совпадать с фактическим порядком загрузки
            self._default_strategy_order = [sid for sid, _ in self._pending_strategies_items]

            if self._strategies_load_timer:
                try:
                    self._strategies_load_timer.stop()
                    self._strategies_load_timer.deleteLater()
                except Exception:
                    pass
                self._strategies_load_timer = None

            # Для небольших списков создаём всё за один проход: меньше "пересборок" и быстрее.
            if total <= 80:
                self._strategies_load_chunk_size = max(1, total)
                self._load_strategies_batch(gen)
                return

            # Для больших списков добавляем порциями, чтобы UI не фризило.
            self._strategies_load_chunk_size = 25
            self._strategies_load_timer = QTimer(self)
            self._strategies_load_timer.timeout.connect(lambda: self._load_strategies_batch(gen))
            self._strategies_load_timer.start(0)

        except Exception as e:
            import traceback
            log(f"Ошибка загрузки стратегий: {e}", "ERROR")
            log(f"Traceback: {traceback.format_exc()}", "ERROR")

    def _load_strategies_batch(self, gen: int):
        """Добавляет строки стратегий порциями, чтобы UI оставался отзывчивым."""
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

        # Применяем текущие фильтры/поиск к уже добавленным строкам (если они реально активны)
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
            log(f"StrategyDetailPage: добавлено {added} строк стратегий", "DEBUG")
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
        """Добавляет строку стратегии в список"""
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
            log(f"Ошибка сохранения пометки стратегии (preview): {e}", "WARNING")
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

    def _show_preview_dialog(self, strategy_id: str, global_pos, pinned: bool) -> None:
        if not (self._category_key and strategy_id and strategy_id != "none"):
            return

        data = self._get_preview_strategy_data(strategy_id)

        try:
            dlg = self._ensure_preview_dialog()
            if dlg is None:
                return

            try:
                dlg.set_pinned(bool(pinned))
            except Exception:
                pass
            try:
                # Hover: follow cursor + do not auto-close on click. Pinned: static tool window.
                dlg.set_hover_follow((not pinned), offset=None)
            except Exception:
                pass
            self._preview_pinned = bool(pinned)

            dlg.set_strategy_data(
                data,
                strategy_id=strategy_id,
                source_widget=(self._strategies_tree.viewport() if self._strategies_tree else self),
                category_key=self._category_key,
                rating_getter=self._get_preview_rating,
                rating_toggler=self._toggle_preview_rating,
            )

            dlg.show_animated(self._to_qpoint(global_pos))

        except Exception as e:
            log(f"Preview dialog failed: {e}", "DEBUG")

    def _on_tree_preview_requested(self, strategy_id: str, global_pos):
        # Hover preview: do not override a pinned window.
        if self._preview_pinned:
            return
        self._show_preview_dialog(strategy_id, global_pos, pinned=False)

    def _on_tree_preview_pinned_requested(self, strategy_id: str, global_pos):
        # Right click pins the window (Tool window, does not auto-close on focus out).
        self._show_preview_dialog(strategy_id, global_pos, pinned=True)

    def _on_tree_preview_hide_requested(self) -> None:
        # Hide hover preview when cursor leaves the list; keep pinned window.
        self._close_preview_dialog(force=False)

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
        """Обработчик переключения избранного"""
        if not (self._category_key and self._strategies_tree):
            return
        if not strategy_id or strategy_id == "none":
            # "Отключено" не делаем избранным
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
            # Откатываем UI, дерево уже успело оптимистично обновиться
            self._strategies_tree.set_favorite_state(strategy_id, not bool(is_favorite))
            return

        log(f"Favorite toggled: {strategy_id} = {is_favorite}", "DEBUG")

    def _on_tree_working_mark_requested(self, strategy_id: str, is_working):
        """Запрос из UI (ПКМ) на пометку стратегии."""
        if not (self._category_key and strategy_id and strategy_id != "none"):
            return
        self._on_strategy_marked(strategy_id, is_working)
        if self._strategies_tree:
            self._strategies_tree.set_working_state(strategy_id, is_working)

    def _on_strategy_marked(self, strategy_id: str, is_working):
        """Обработчик пометки стратегии как рабочей/нерабочей"""
        if self._category_key:
            # Persist marks for direct_zapret2 mode (two-state)
            try:
                if strategy_id and strategy_id != "none":
                    self._marks_store.set_mark(self._category_key, strategy_id, is_working)
            except Exception as e:
                log(f"Ошибка сохранения пометки стратегии: {e}", "WARNING")

            self.strategy_marked.emit(self._category_key, strategy_id, is_working)
            if is_working is True:
                status = 'working'
            elif is_working is False:
                status = 'not working'
            else:
                status = 'unmarked'
            log(f"Strategy marked: {strategy_id} = {status}", "DEBUG")

    def _on_enable_toggled(self, enabled: bool):
        """Обработчик включения/выключения категории"""
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
                    log(f"Категория {self._category_key} включена (restore phase chain)", "INFO")
                    return
                except Exception as e:
                    log(f"TCP phase restore failed: {e}", "WARNING")

        if enabled:
            # Включаем - восстанавливаем последнюю стратегию (если была), иначе дефолтную
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
                # Показываем анимацию загрузки
                self.show_loading()
                self.strategy_selected.emit(self._category_key, strategy_to_select)
                log(f"Категория {self._category_key} включена со стратегией {strategy_to_select}", "INFO")
            else:
                log(f"Нет доступных стратегий для {self._category_key}", "WARNING")
                self._enable_toggle.setChecked(False, block_signals=True)
                self._set_category_enabled_ui(False)
            self._refresh_args_editor_state()
        else:
            # Запоминаем стратегию перед выключением, чтобы восстановить при включении
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
            # Выключаем - устанавливаем "none"
            self._selected_strategy_id = "none"
            if self._strategies_tree:
                if self._strategies_tree.has_strategy("none"):
                    self._strategies_tree.set_selected_strategy("none")
                else:
                    self._strategies_tree.clearSelection()
            self._update_selected_strategy_header(self._selected_strategy_id)
            # Скрываем галочку
            self._stop_loading()
            self._success_icon.hide()
            self.strategy_selected.emit(self._category_key, "none")
            log(f"Категория {self._category_key} отключена", "INFO")
            self._refresh_args_editor_state()
            self._set_category_enabled_ui(False)

    def _get_default_strategy(self) -> str:
        """Возвращает стратегию по умолчанию для текущей категории"""
        try:
            from strategy_menu.strategies_registry import registry

            # Пробуем получить дефолтную стратегию из реестра
            defaults = registry.get_default_selections()
            if self._category_key in defaults:
                default_id = defaults[self._category_key]
                if default_id and default_id != "none" and (default_id in (self._default_strategy_order or [])):
                    return default_id

            # Иначе берём первую стратегию из списка (не none)
            for sid in (self._default_strategy_order or []):
                if sid and sid != "none":
                    return sid

            return "none"
        except Exception as e:
            log(f"Ошибка получения стратегии по умолчанию: {e}", "DEBUG")
            # Fallback - первая не-none стратегия
            for sid in (self._default_strategy_order or []):
                if sid and sid != "none":
                    return sid
            return "none"

    def _on_filter_mode_changed(self, new_mode: str):
        """Обработчик изменения режима фильтрации для категории"""
        if not self._category_key:
            return

        # Save via PresetManager (triggers DPI reload automatically)
        self._save_category_filter_mode(self._category_key, new_mode)
        self.filter_mode_changed.emit(self._category_key, new_mode)
        log(f"Режим фильтрации для {self._category_key}: {new_mode}", "INFO")

    def _save_category_filter_mode(self, category_key: str, mode: str):
        """Сохраняет режим фильтрации для категории через PresetManager"""
        self._preset_manager.update_category_filter_mode(
            category_key, mode, save_and_sync=True
        )

    def _load_category_filter_mode(self, category_key: str) -> str:
        """Загружает режим фильтрации для категории из PresetManager"""
        return self._preset_manager.get_category_filter_mode(category_key)

    def _save_category_sort(self, category_key: str, sort_order: str):
        """Сохраняет порядок сортировки для категории через PresetManager"""
        # Sort order is UI-only parameter, doesn't affect DPI
        # But save_and_sync=True is needed to persist changes to disk
        # (hot-reload may trigger but sort_order has no effect on winws2)
        self._preset_manager.update_category_sort_order(
            category_key, sort_order, save_and_sync=True
        )

    def _load_category_sort(self, category_key: str) -> str:
        """Загружает порядок сортировки для категории из PresetManager"""
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

    # ═══════════════════════════════════════════════════════════════
    # OUT RANGE METHODS
    # ═══════════════════════════════════════════════════════════════

    def _select_out_range_mode(self, mode: str):
        """Выбор режима out_range (n или d)"""
        if mode != self._out_range_mode:
            self._out_range_mode = mode
            self._update_out_range_mode_styles()
            self._save_syndata_settings()

    def _update_out_range_mode_styles(self):
        """Обновляет стили кнопок режима out_range"""
        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                color: #000000;
                font-size: 12px;
                font-weight: 600;
                border-radius: 4px;
                padding: 0 4px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                border-radius: 4px;
                padding: 0 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """

        if self._out_range_mode == "n":
            self._out_range_mode_n.setStyleSheet(active_style)
            self._out_range_mode_n.setChecked(True)
            self._out_range_mode_d.setStyleSheet(inactive_style)
            self._out_range_mode_d.setChecked(False)
        else:
            self._out_range_mode_n.setStyleSheet(inactive_style)
            self._out_range_mode_n.setChecked(False)
            self._out_range_mode_d.setStyleSheet(active_style)
            self._out_range_mode_d.setChecked(True)

    # ═══════════════════════════════════════════════════════════════
    # SYNDATA SETTINGS METHODS
    # ═══════════════════════════════════════════════════════════════

    def _on_send_toggled(self, checked: bool):
        """Обработчик включения/выключения send параметров"""
        self._send_settings.setVisible(checked)
        self._save_syndata_settings()

    def _on_syndata_toggled(self, checked: bool):
        """Обработчик включения/выключения syndata параметров"""
        self._syndata_settings.setVisible(checked)
        self._save_syndata_settings()

    def _save_syndata_settings(self):
        """Сохраняет syndata настройки для текущей категории через PresetManager"""
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
        """Загружает syndata настройки для категории из PresetManager"""
        protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
        is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
        protocol_key = "udp" if is_udp_like else "tcp"
        syndata = self._preset_manager.get_category_syndata(category_key, protocol=protocol_key)
        return syndata.to_dict()

    def _apply_syndata_settings(self, settings: dict):
        """Применяет syndata настройки к UI без эмиссии сигналов сохранения"""
        # Блокируем сигналы чтобы не вызывать save при загрузке
        self._syndata_toggle.blockSignals(True)
        self._blob_combo.blockSignals(True)
        self._tls_mod_combo.blockSignals(True)
        # TTLButtonSelector использует block_signals=True при setValue
        self._out_range_spin.blockSignals(True)
        self._tcp_flags_combo.blockSignals(True)
        # Блокируем сигналы Send виджетов
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

        # Применяем режим out_range
        self._out_range_mode = settings.get("out_range_mode", "n")
        self._update_out_range_mode_styles()

        tcp_flags_value = settings.get("tcp_flags_unset", "none")
        tcp_flags_index = self._tcp_flags_combo.findText(tcp_flags_value)
        if tcp_flags_index >= 0:
            self._tcp_flags_combo.setCurrentIndex(tcp_flags_index)

        # Применяем Send настройки
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

        # Разблокируем сигналы
        self._syndata_toggle.blockSignals(False)
        self._blob_combo.blockSignals(False)
        self._tls_mod_combo.blockSignals(False)
        # TTLButtonSelector не требует разблокировки (block_signals=True при setValue)
        self._out_range_spin.blockSignals(False)
        self._tcp_flags_combo.blockSignals(False)
        # Разблокируем сигналы Send виджетов
        self._send_toggle.blockSignals(False)
        self._send_repeats_spin.blockSignals(False)
        self._send_ip_id_combo.blockSignals(False)
        self._send_badsum_check.blockSignals(False)

    def get_syndata_settings(self) -> dict:
        """Возвращает текущие syndata настройки для использования в командной строке"""
        return {
            "enabled": self._syndata_toggle.isChecked(),
            "blob": self._blob_combo.currentText(),
            "tls_mod": self._tls_mod_combo.currentText(),
        }

    def _on_reset_settings_confirmed(self):
        """Сбрасывает настройки категории на значения по умолчанию (встроенный шаблон)"""
        if not self._category_key:
            return

        # 1. Reset via PresetManager (saves to preset file)
        if self._preset_manager.reset_category_settings(self._category_key):
            log(f"Настройки категории {self._category_key} сброшены", "INFO")

            # 2. Reload settings from PresetManager and apply to UI
            protocol_raw = str(getattr(self._category_info, "protocol", "") or "").upper()
            is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
            protocol_key = "udp" if is_udp_like else "tcp"
            syndata = self._preset_manager.get_category_syndata(self._category_key, protocol=protocol_key)
            self._apply_syndata_settings(syndata.to_dict())

            # 3. Reset filter_mode selector to stored default
            if hasattr(self, '_filter_mode_frame') and self._filter_mode_frame.isVisible():
                current_mode = self._preset_manager.get_category_filter_mode(self._category_key)
                self._filter_mode_selector.setCurrentMode(current_mode, block_signals=True)

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
                # Consider this as "applied"
                self._stop_loading()
                self.show_success()
            else:
                self._enable_toggle.setChecked(False, block_signals=True)
                self._stop_loading()
                self._success_icon.hide()
            self._update_selected_strategy_header(self._selected_strategy_id)
            self._refresh_args_editor_state()
            self._set_category_enabled_ui((self._selected_strategy_id or "none") != "none")

    def _on_row_clicked(self, strategy_id: str):
        """Обработчик клика по строке стратегии - выбор активной"""
        if self._tcp_phase_mode:
            self._on_tcp_phase_row_clicked(strategy_id)
            return

        prev_strategy_id = self._selected_strategy_id

        self._selected_strategy_id = strategy_id
        if self._strategies_tree:
            self._strategies_tree.set_selected_strategy(strategy_id)
        self._update_selected_strategy_header(self._selected_strategy_id)

        # При смене стратегии закрываем редактор args (чтобы не редактировать "не то")
        if prev_strategy_id != strategy_id:
            self._hide_args_editor(clear_text=False)

        # Синхронизируем toggle
        if strategy_id != "none":
            self._enable_toggle.setChecked(True, block_signals=True)
            # Показываем анимацию загрузки
            self.show_loading()
        else:
            self._stop_loading()
            self._success_icon.hide()

        self._refresh_args_editor_state()
        self._set_category_enabled_ui((strategy_id or "none") != "none")

        # Применяем стратегию (но остаёмся на странице)
        if self._category_key:
            self.strategy_selected.emit(self._category_key, strategy_id)

    def _update_status_icon(self, active: bool):
        """Обновляет галочку статуса в заголовке"""
        if active:
            self.show_success()
        else:
            self._stop_loading()
            self._success_icon.hide()

    def show_loading(self):
        """Показывает анимированный спиннер загрузки"""
        self._success_icon.hide()
        self._spinner.start()
        self._waiting_for_process_start = True  # Ждём запуска DPI
        # Убедимся, что мы подключены к process_monitor
        if not self._process_monitor_connected:
            self._connect_process_monitor()
        # В direct_zapret2 режимах "apply" часто не меняет состояние процесса (hot-reload),
        # поэтому даём быстрый таймаут, чтобы UI не зависал на спиннере.
        self._start_apply_feedback_timer()
        # Запускаем fallback таймер на случай если сигнал не придет
        self._start_fallback_timer()

    def _stop_loading(self):
        """Останавливает анимацию загрузки"""
        self._spinner.stop()
        self._waiting_for_process_start = False  # Больше не ждём
        self._stop_apply_feedback_timer()
        self._stop_fallback_timer()

    def _start_apply_feedback_timer(self, timeout_ms: int = 1500):
        """Быстрый таймер, который завершает спиннер после apply/hot-reload."""
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
        В direct_zapret2 изменения часто применяются без смены процесса (winws2 остаётся запущен),
        поэтому ориентируемся на включенность категории, а не на processStatusChanged.
        """
        if not self._waiting_for_process_start:
            return
        if (self._selected_strategy_id or "none") != "none":
            self.show_success()
        else:
            self._stop_loading()
            self._success_icon.hide()

    def _start_fallback_timer(self):
        """Запускает fallback таймер для защиты от бесконечного спиннера"""
        self._stop_fallback_timer()  # Остановим предыдущий если был
        self._fallback_timer = QTimer(self)
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self._on_fallback_timeout)
        self._fallback_timer.start(10000)  # 10 секунд максимум

    def _stop_fallback_timer(self):
        """Останавливает fallback таймер"""
        if self._fallback_timer:
            self._fallback_timer.stop()
            self._fallback_timer = None

    def _on_fallback_timeout(self):
        """Вызывается если сигнал processStatusChanged не пришел за 10 секунд"""
        if self._waiting_for_process_start:
            log("StrategyDetailPage: fallback timeout - показываем галочку", "DEBUG")
            self.show_success()

    def show_success(self):
        """Показывает зелёную галочку успеха"""
        self._stop_loading()
        self._success_icon.setPixmap(qta.icon('fa5s.check-circle', color='#4ade80').pixmap(16, 16))
        self._success_icon.show()

    def _connect_process_monitor(self):
        """Подключается к сигналу processStatusChanged от ProcessMonitorThread"""
        if self._process_monitor_connected:
            return  # Уже подключены

        try:
            if self.parent_app and hasattr(self.parent_app, 'process_monitor'):
                process_monitor = self.parent_app.process_monitor
                if process_monitor is not None:
                    process_monitor.processStatusChanged.connect(self._on_process_status_changed)
                    self._process_monitor_connected = True
                    log("StrategyDetailPage: подключен к processStatusChanged", "DEBUG")
        except Exception as e:
            log(f"StrategyDetailPage: ошибка подключения к process_monitor: {e}", "DEBUG")

    def _on_process_status_changed(self, is_running: bool):
        """
        Обработчик изменения статуса процесса DPI.
        Вызывается когда winws.exe/winws2.exe запускается или останавливается.
        """
        try:
            if is_running and self._waiting_for_process_start:
                # DPI запустился и мы ждали этого - показываем галочку
                log("StrategyDetailPage: DPI запущен, показываем галочку", "DEBUG")
                self.show_success()
        except Exception as e:
            log(f"StrategyDetailPage._on_process_status_changed error: {e}", "DEBUG")

    def _on_args_changed(self, strategy_id: str, args: list):
        """Обработчик изменения аргументов стратегии"""
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

        active_keys: set[str] = set()
        for key in (self._phase_tab_index_by_key or {}).keys():
            try:
                is_active = bool(self._is_tcp_phase_active_for_ui(key))
            except Exception:
                is_active = False
            if is_active:
                active_keys.add(str(key or "").strip().lower())

        try:
            tabbar.set_active_keys(active_keys)
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
            tabbar = self._phase_tabbar
            idx = (self._phase_tab_index_by_key or {}).get("fake")
            if tabbar is not None and idx is not None:
                tabbar.setTabVisible(int(idx), not hide_fake)
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

        tabbar = self._phase_tabbar
        if not tabbar:
            return

        # If the tab is hidden, fall back to multisplit.
        try:
            idx = (self._phase_tab_index_by_key or {}).get(key)
            if idx is None or not bool(tabbar.isTabVisible(int(idx))):
                key = "multisplit"
        except Exception:
            key = "multisplit"

        idx = (self._phase_tab_index_by_key or {}).get(key)
        if idx is None:
            return

        try:
            tabbar.blockSignals(True)
            tabbar.setCurrentIndex(int(idx))
        finally:
            try:
                tabbar.blockSignals(False)
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

    def _set_category_enabled_ui(self, enabled: bool) -> None:
        """Hides all settings/strategy UI when the category is disabled."""
        want = bool(enabled)
        try:
            if hasattr(self, "_toolbar_frame") and self._toolbar_frame is not None:
                self._toolbar_frame.setVisible(want)
        except Exception:
            pass
        try:
            if hasattr(self, "_strategies_block") and self._strategies_block is not None:
                self._strategies_block.setVisible(want)
                # Prevent hidden stretch items from consuming vertical space and pushing UI around.
                if hasattr(self, "layout") and self.layout is not None:
                    self.layout.setStretchFactor(self._strategies_block, 1 if want else 0)
                if want:
                    self._strategies_block.setMaximumHeight(16777215)
                else:
                    self._strategies_block.setMaximumHeight(0)
        except Exception:
            pass

        if not want:
            # Ensure the args editor doesn't remain open (even though it becomes hidden).
            self._hide_args_editor(clear_text=True)
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
        if not hasattr(self, "_args_editor_frame"):
            return

        if not self._args_editor_frame.isVisible():
            # При открытии всегда подтягиваем актуальные args из preset (категория/протокол)
            self._load_args_into_editor()
            self._args_editor_frame.setVisible(True)
        else:
            self._hide_args_editor(clear_text=False)

    def _hide_args_editor(self, clear_text: bool = False):
        if hasattr(self, "_args_editor_frame"):
            self._args_editor_frame.setVisible(False)
        if hasattr(self, "_args_apply_btn"):
            self._args_apply_btn.setEnabled(False)
        self._args_editor_dirty = False

        if clear_text and hasattr(self, "_args_editor") and self._args_editor:
            try:
                self._args_editor.blockSignals(True)
                self._args_editor.setPlainText("")
            finally:
                self._args_editor.blockSignals(False)

    def _load_args_into_editor(self):
        if not (self._category_key and hasattr(self, "_args_editor") and self._args_editor):
            return

        if (self._selected_strategy_id or "none") == "none":
            self._hide_args_editor(clear_text=True)
            return

        text = ""
        try:
            preset = self._preset_manager.get_active_preset()
            cat = preset.categories.get(self._category_key) if preset else None
            if cat:
                text = cat.udp_args if self._is_udp_like_category() else cat.tcp_args
        except Exception as e:
            log(f"Args editor: failed to load preset args: {e}", "DEBUG")

        try:
            self._args_editor.blockSignals(True)
            self._args_editor.setPlainText((text or "").strip())
        finally:
            self._args_editor.blockSignals(False)

        self._args_editor_dirty = False
        if hasattr(self, "_args_apply_btn"):
            self._args_apply_btn.setEnabled(False)

    def _on_args_editor_changed(self):
        if not hasattr(self, "_args_editor"):
            return
        self._args_editor_dirty = True
        if hasattr(self, "_args_apply_btn"):
            self._args_apply_btn.setEnabled((self._selected_strategy_id or "none") != "none")

    def _apply_args_editor(self):
        if not self._category_key:
            return
        if (self._selected_strategy_id or "none") == "none":
            return
        if not hasattr(self, "_args_editor") or not self._args_editor:
            return

        raw = self._args_editor.toPlainText()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        normalized = "\n".join(lines)

        try:
            preset = self._preset_manager.get_active_preset()
            if not preset:
                return

            if self._category_key not in preset.categories:
                # Fallback: category should exist after selecting a strategy, but be defensive
                preset.categories[self._category_key] = self._preset_manager._create_category_with_defaults(self._category_key)

            cat = preset.categories[self._category_key]

            if self._is_udp_like_category():
                cat.udp_args = normalized
            else:
                cat.tcp_args = normalized

            preset.touch()
            self._preset_manager._save_and_sync_preset(preset)

            self._args_editor_dirty = False
            if hasattr(self, "_args_apply_btn"):
                self._args_apply_btn.setEnabled(False)

            # UI feedback: mimic "apply" spinner behavior
            self.show_loading()

            self._on_args_changed(self._selected_strategy_id, lines)

        except Exception as e:
            log(f"Args editor: failed to save args: {e}", "ERROR")

    def _on_search_changed(self, text: str):
        """Фильтрует стратегии по поисковому запросу"""
        self._apply_filters()

    def _on_filter_toggled(self, technique: str, active: bool):
        """Обработчик переключения фильтра"""
        if active:
            self._active_filters.add(technique)
        else:
            self._active_filters.discard(technique)
        self._apply_filters()

    def _on_phase_tab_changed(self, index: int) -> None:
        """TCP multi-phase: handler for phase tab selection (QTabBar)."""
        if not self._tcp_phase_mode:
            return

        try:
            idx = int(index)
        except Exception:
            return

        key = str((self._phase_tab_key_by_index or {}).get(idx) or "").strip().lower()
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

    def _on_phase_tab_clicked(self, index: int) -> None:
        """
        Ensures phase selection reacts to mouse clicks even when Qt doesn't emit
        `currentChanged` (or when the user clicks the already-selected tab).
        """
        tabbar = self._phase_tabbar
        if not tabbar:
            return
        try:
            idx = int(index)
        except Exception:
            return

        try:
            if int(tabbar.currentIndex()) != idx:
                tabbar.setCurrentIndex(idx)
                return
        except Exception:
            pass

        self._on_phase_tab_changed(idx)

    def _apply_filters(self):
        """Применяет фильтры по технике к списку стратегий"""
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
        """Показывает меню сортировки"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d2d;
                border: none;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: white;
            }
            QMenu::item:selected {
                background: rgba(96, 205, 255, 0.2);
            }
        """)

        default_action = menu.addAction("По умолчанию")
        name_asc_action = menu.addAction("По имени (А-Я)")
        name_desc_action = menu.addAction("По имени (Я-А)")

        action = menu.exec(self._sort_btn.mapToGlobal(self._sort_btn.rect().bottomLeft()))

        if action == default_action:
            self._sort_mode = "default"
        elif action == name_asc_action:
            self._sort_mode = "name_asc"
        elif action == name_desc_action:
            self._sort_mode = "name_desc"

        if action:
            # Сохраняем порядок сортировки для категории в реестр
            if self._category_key:
                self._save_category_sort(self._category_key, self._sort_mode)
            self._apply_sort()

    def _apply_sort(self):
        """Применяет текущую сортировку"""
        if not self._strategies_tree:
            return
        self._strategies_tree.set_sort_mode(self._sort_mode)
        self._strategies_tree.apply_sort()
        # Sorting (takeChildren/addChild) may reset selection in Qt; restore it.
        sid = self._selected_strategy_id or self._current_strategy_id or "none"
        if sid and self._strategies_tree.has_strategy(sid):
            self._strategies_tree.set_selected_strategy(sid)
