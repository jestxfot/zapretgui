# ui/pages/zapret2/strategy_detail_page.py
"""
Страница детального просмотра стратегий для выбранной категории.
Открывается при клике на категорию в Zapret2StrategiesPageNew.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QFrame, QPushButton, QScrollArea, QLineEdit, QMenu, QComboBox, QSpinBox,
    QCheckBox, QPlainTextEdit
)
from PyQt6.QtGui import QFont, QFontMetrics
import qtawesome as qta

from ui.pages.base_page import BasePage
from ui.pages.dpi_settings_page import Win11ToggleRow
from ui.pages.strategies_page_base import ResetActionButton
from ui.widgets.win11_spinner import Win11Spinner
from launcher_common.blobs import get_blobs_info
from preset_zapret2 import PresetManager, SyndataSettings
from ui.zapret2_strategy_marks import DirectZapret2MarksStore, DirectZapret2FavoritesStore
from log import log


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

    def __init__(self, text: str, technique: str, parent=None):
        super().__init__(text, parent)
        self._technique = technique
        self._active = False
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self._active = self.isChecked()
        self._update_style()
        self.toggled_filter.emit(self._technique, self._active)

    def _update_style(self):
        if self._active:
            self.setStyleSheet('''
                QPushButton {
                    background: rgba(96, 205, 255, 0.2);
                    border: 1px solid rgba(96, 205, 255, 0.5);
                    border-radius: 14px;
                    color: #60cdff;
                    padding: 0 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(96, 205, 255, 0.3);
                }
            ''')
        else:
            self.setStyleSheet('''
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: none;
                    border-radius: 14px;
                    color: rgba(255, 255, 255, 0.7);
                    padding: 0 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            ''')

    def reset(self):
        self._active = False
        self.setChecked(False)
        self._update_style()


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
        self.parent_app = parent
        self._category_key = None
        self._category_info = None
        self._current_strategy_id = "none"
        self._selected_strategy_id = "none"
        self._strategy_rows = {}
        self._sort_mode = "default"  # default, name_asc, name_desc
        self._active_filters = set()  # Активные фильтры по технике
        self._waiting_for_process_start = False  # Флаг ожидания запуска DPI
        self._process_monitor_connected = False  # Флаг подключения к process_monitor
        self._fallback_timer = None  # Таймер защиты от бесконечного спиннера
        self._strategies_load_timer = None
        self._strategies_load_generation = 0
        self._pending_strategies_items = []
        self._pending_strategies_index = 0
        self._loaded_strategy_type = None
        self._default_strategy_order = []
        self._strategies_loaded_fully = False

        # PresetManager for category settings storage
        self._preset_manager = PresetManager(
            on_dpi_reload_needed=self._on_dpi_reload_needed
        )
        self._marks_store = DirectZapret2MarksStore.default()
        self._favorites_store = DirectZapret2FavoritesStore.default()
        self._favorite_strategy_ids = set()

        self._build_content()

        # Подключаемся к process_monitor для отслеживания статуса DPI
        self._connect_process_monitor()

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
        subtitle_row.addStretch()

        header_layout.addLayout(subtitle_row)

        self.layout.addWidget(header)

        # ═══════════════════════════════════════════════════════════════
        # ТУЛБАР НАСТРОЕК КАТЕГОРИИ
        # ═══════════════════════════════════════════════════════════════
        self._toolbar_frame = QFrame()
        self._toolbar_frame.setFrameShape(QFrame.Shape.NoFrame)
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

        # Toggle включения/выключения категории
        self._enable_toggle = Win11ToggleRow(
            "fa5s.power-off", "Включить обход",
            "Активировать DPI-обход для этой категории", "#4CAF50"
        )
        self._enable_toggle.toggled.connect(self._on_enable_toggled)
        toolbar_layout.addWidget(self._enable_toggle)

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
            values=[-1, -2, -3, -4, -5, -6, -7, -8, -9],
            labels=["-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"]
        )
        self._autottl_delta_selector.setToolTip("Delta: смещение от измеренного TTL")
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
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 8, 0, 0)
        reset_row.addStretch()

        self._reset_settings_btn = ResetActionButton(
            "Сбросить настройки",
            confirm_text="Сбросить все?"
        )
        self._reset_settings_btn.reset_confirmed.connect(self._on_reset_settings_confirmed)
        reset_row.addWidget(self._reset_settings_btn)

        toolbar_layout.addLayout(reset_row)

        self.layout.addWidget(self._toolbar_frame)

        # Поиск по стратегиям
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 8)

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

        self.layout.addLayout(search_layout)

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

        self.layout.addWidget(self._args_editor_frame)

        # Фильтры по типу стратегии
        filters_layout = QHBoxLayout()
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

        self.layout.addLayout(filters_layout)

        # Контейнер для списка стратегий (напрямую в layout, без лишней scroll area)
        # BasePage уже является QScrollArea
        self._strategies_container = QWidget()
        self._strategies_container.setStyleSheet("background: transparent;")
        self._strategies_container_layout = QVBoxLayout(self._strategies_container)
        self._strategies_container_layout.setContentsMargins(0, 0, 0, 0)
        self._strategies_container_layout.setSpacing(6)

        self._favorites_header = QLabel("")
        self._favorites_header.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.65);
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                padding: 6px 0 2px 0;
            }
        """)
        self._favorites_header.hide()
        self._strategies_container_layout.addWidget(self._favorites_header)

        self._favorites_list = QWidget()
        self._favorites_list.setStyleSheet("background: transparent;")
        self._favorites_layout = QVBoxLayout(self._favorites_list)
        self._favorites_layout.setContentsMargins(0, 0, 0, 0)
        self._favorites_layout.setSpacing(2)
        self._favorites_list.hide()
        self._strategies_container_layout.addWidget(self._favorites_list)

        self._favorites_separator = QFrame()
        self._favorites_separator.setFrameShape(QFrame.Shape.HLine)
        self._favorites_separator.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                max-height: 1px;
            }
        """)
        self._favorites_separator.hide()
        self._strategies_container_layout.addWidget(self._favorites_separator)

        self._regular_list = QWidget()
        self._regular_list.setStyleSheet("background: transparent;")
        self._regular_layout = QVBoxLayout(self._regular_list)
        self._regular_layout.setContentsMargins(0, 0, 0, 0)
        self._regular_layout.setSpacing(2)
        self._strategies_container_layout.addWidget(self._regular_list)

        self.layout.addWidget(self._strategies_container, 1)

    def show_category(self, category_key: str, category_info, current_strategy_id: str):
        """
        Показывает стратегии для выбранной категории.

        Args:
            category_key: Ключ категории (например, "youtube_https")
            category_info: Объект CategoryInfo с информацией о категории
            current_strategy_id: ID текущей выбранной стратегии
        """
        log(f"StrategyDetailPage.show_category: {category_key}, current={current_strategy_id}", "DEBUG")
        self._category_key = category_key
        self._category_info = category_info
        self._current_strategy_id = current_strategy_id or "none"
        self._selected_strategy_id = self._current_strategy_id
        try:
            self._favorite_strategy_ids = self._favorites_store.get_favorites(category_key)
        except Exception:
            self._favorite_strategy_ids = set()

        # Обновляем заголовок (только название категории в breadcrumb)
        self._title.setText(category_info.full_name)
        self._subtitle.setText(f"{category_info.protocol}  |  порты: {category_info.ports}")

        # Для категорий одного strategy_type (особенно tcp) список стратегий одинаковый,
        # поэтому не пересобираем виджеты каждый раз: это ускоряет повторные переходы.
        new_strategy_type = str(getattr(category_info, "strategy_type", "") or "tcp")
        reuse_list = bool(self._strategy_rows) and self._loaded_strategy_type == new_strategy_type

        if not reuse_list:
            # Очищаем старые стратегии
            self._clear_strategies()
            # Загружаем новые
            self._load_strategies()
        else:
            # Обновляем избранное для новой категории и перестраиваем секции
            for sid, row in self._strategy_rows.items():
                row.set_favorite(sid in self._favorite_strategy_ids)
            self._reflow_strategy_rows()
            # Обновляем отметки working/not working для новой категории
            self._refresh_working_marks_for_category()

            # Обновляем выделение текущей стратегии (если строка уже загружена)
            for row in self._strategy_rows.values():
                row.set_selected(False)
            if self._current_strategy_id in self._strategy_rows:
                self._strategy_rows[self._current_strategy_id].set_selected(True)

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

        # Применяем сохранённую сортировку (если не default)
        if self._sort_mode != "default":
            self._apply_sort()
        else:
            self._reflow_strategy_rows()

        # Загружаем syndata настройки для категории
        syndata_settings = self._load_syndata_settings(category_key)
        self._apply_syndata_settings(syndata_settings)

        # syndata поддерживается только для TCP SYN, для UDP/QUIC скрываем UI
        protocol_raw = str(getattr(category_info, "protocol", "") or "").upper()
        is_udp_like = ("UDP" in protocol_raw) or ("QUIC" in protocol_raw) or ("L7" in protocol_raw)
        if is_udp_like:
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

        log(f"StrategyDetailPage: показана категория {category_key}, sort_mode={self._sort_mode}", "DEBUG")

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

        for row in self._strategy_rows.values():
            row.deleteLater()
        self._strategy_rows.clear()
        self._loaded_strategy_type = None
        self._default_strategy_order = []
        self._strategies_loaded_fully = False
        self._favorite_strategy_ids = set()
        self._update_favorites_section_visibility()

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

            self._loaded_strategy_type = str(getattr(category_info, "strategy_type", "") or "tcp")
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

            # Приоритет: текущая стратегия и дефолтная, чтобы пользователь видел "своё" раньше
            try:
                from strategy_menu.strategies_registry import registry as _r
                default_id = _r.get_default_selections().get(self._category_key)
            except Exception:
                default_id = None

            priority = []
            seen = set()
            for pid in (self._current_strategy_id, default_id):
                if pid and pid in strategies and pid not in seen:
                    priority.append((pid, strategies[pid]))
                    seen.add(pid)
            rest = [(sid, data) for sid, data in items if sid not in seen]
            self._pending_strategies_items = priority + rest
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
            self.setUpdatesEnabled(False)

            for i in range(start, end):
                sid, data = self._pending_strategies_items[i]
                name = (data or {}).get("name", sid)
                args = (data or {}).get("args", [])
                if isinstance(args, str):
                    args = args.split()
                self._add_strategy_row(sid, name, args)

                if sid == self._current_strategy_id and sid in self._strategy_rows:
                    self._strategy_rows[sid].set_selected(True)

        finally:
            try:
                self.setUpdatesEnabled(True)
            except Exception:
                pass

        self._pending_strategies_index = end

        # Применяем текущие фильтры/поиск к уже добавленным строкам (если они реально активны)
        try:
            search_active = bool(self._search_input and self._search_input.text().strip())
        except Exception:
            search_active = False
        if search_active or self._active_filters:
            self._apply_filters()

        if end >= len(self._pending_strategies_items):
            # Done
            if self._strategies_load_timer:
                self._strategies_load_timer.stop()
                self._strategies_load_timer.deleteLater()
                self._strategies_load_timer = None

            log(f"StrategyDetailPage: добавлено {len(self._strategy_rows)} строк стратегий", "DEBUG")
            self._strategies_loaded_fully = True
            self._refresh_working_marks_for_category()

            # Sort after all rows are present (important for lazy load)
            if self._sort_mode != "default":
                self._apply_sort()

    def _add_strategy_row(self, strategy_id: str, name: str, args: list = None):
        """Добавляет строку стратегии в список"""
        row = StrategyRow(strategy_id, name, args)
        row.clicked.connect(lambda sid=strategy_id: self._on_row_clicked(sid))
        row.favorite_toggled.connect(lambda sid, fav: self._on_favorite_toggled(sid, fav))
        row.marked_working.connect(lambda sid, is_working: self._on_strategy_marked(sid, is_working))
        self._strategy_rows[strategy_id] = row
        row.set_favorite(strategy_id in self._favorite_strategy_ids)
        self._place_row_widget(row)
        if self._sort_mode != "default":
            self._reflow_strategy_rows()

        # Apply persisted working/notworking mark (if any)
        if self._category_key and strategy_id != "none":
            row.set_working_state(self._marks_store.get_mark(self._category_key, strategy_id))

    def _refresh_working_marks_for_category(self):
        if not self._category_key:
            return
        for strategy_id, row in self._strategy_rows.items():
            if strategy_id == "none":
                continue
            try:
                row.set_working_state(self._marks_store.get_mark(self._category_key, strategy_id))
            except Exception:
                pass

    def _on_favorite_toggled(self, strategy_id: str, is_favorite: bool):
        """Обработчик переключения избранного"""
        if not self._category_key:
            return
        if not strategy_id or strategy_id == "none":
            # "Отключено" не делаем избранным
            row = self._strategy_rows.get(strategy_id)
            if row:
                row.set_favorite(False)
            return

        try:
            self._favorites_store.set_favorite(self._category_key, strategy_id, bool(is_favorite))
            if is_favorite:
                self._favorite_strategy_ids.add(strategy_id)
            else:
                self._favorite_strategy_ids.discard(strategy_id)
        except Exception as e:
            log(f"Favorite persist failed: {e}", "WARNING")
            row = self._strategy_rows.get(strategy_id)
            if row:
                row.set_favorite(not bool(is_favorite))
            return

        self._reflow_strategy_rows()
        log(f"Favorite toggled: {strategy_id} = {is_favorite}", "DEBUG")

    def _update_favorites_section_visibility(self):
        count = len(self._favorite_strategy_ids or set())
        show = count > 0
        if show:
            self._favorites_header.setText(f"★ Избранные ({count})")
        self._favorites_header.setVisible(show)
        self._favorites_list.setVisible(show)
        self._favorites_separator.setVisible(show)

    def _take_all_widgets(self, layout: QVBoxLayout) -> list[QWidget]:
        widgets: list[QWidget] = []
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                widgets.append(w)
        return widgets

    def _place_row_widget(self, row: "StrategyRow"):
        if row.is_favorite():
            self._favorites_layout.addWidget(row)
        else:
            self._regular_layout.addWidget(row)
        self._update_favorites_section_visibility()

    def _reflow_strategy_rows(self):
        """Перестраивает порядок строк с секцией избранных сверху."""
        if not self._strategy_rows:
            self._update_favorites_section_visibility()
            return

        fav_ids = set(self._favorite_strategy_ids or set())
        # Вызов может прийти во время lazy-load, когда часть строк ещё не создана.
        existing_ids = list(self._strategy_rows.keys())

        if self._sort_mode == "name_asc":
            existing_ids.sort(key=lambda sid: (self._strategy_rows[sid]._name or "").lower())
        elif self._sort_mode == "name_desc":
            existing_ids.sort(key=lambda sid: (self._strategy_rows[sid]._name or "").lower(), reverse=True)
        else:
            order_index = {sid: i for i, sid in enumerate(self._default_strategy_order or [])}
            existing_ids.sort(key=lambda sid: order_index.get(sid, 10**9))

        fav_order = [sid for sid in existing_ids if sid in fav_ids]
        reg_order = [sid for sid in existing_ids if sid not in fav_ids]

        # Вытаскиваем все виджеты и переукладываем по порядку
        self._take_all_widgets(self._favorites_layout)
        self._take_all_widgets(self._regular_layout)

        for sid in fav_order:
            self._favorites_layout.addWidget(self._strategy_rows[sid])
        for sid in reg_order:
            self._regular_layout.addWidget(self._strategy_rows[sid])

        self._update_favorites_section_visibility()

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

        if enabled:
            # Включаем - восстанавливаем последнюю стратегию (если была), иначе дефолтную
            strategy_to_select = getattr(self, "_last_enabled_strategy_id", None) or self._get_default_strategy()
            if strategy_to_select and strategy_to_select != "none":
                # Снимаем выделение с предыдущей
                if self._selected_strategy_id in self._strategy_rows:
                    self._strategy_rows[self._selected_strategy_id].set_selected(False)
                # Выделяем новую
                if strategy_to_select in self._strategy_rows:
                    self._strategy_rows[strategy_to_select].set_selected(True)
                self._selected_strategy_id = strategy_to_select
                # Показываем анимацию загрузки
                self.show_loading()
                self.strategy_selected.emit(self._category_key, strategy_to_select)
                log(f"Категория {self._category_key} включена со стратегией {strategy_to_select}", "INFO")
            else:
                log(f"Нет доступных стратегий для {self._category_key}", "WARNING")
                self._enable_toggle.setChecked(False, block_signals=True)
            self._refresh_args_editor_state()
        else:
            # Запоминаем стратегию перед выключением, чтобы восстановить при включении
            if self._selected_strategy_id and self._selected_strategy_id != "none":
                self._last_enabled_strategy_id = self._selected_strategy_id
            # Выключаем - устанавливаем "none"
            self._selected_strategy_id = "none"
            # Снимаем выделение со всех стратегий
            for row in self._strategy_rows.values():
                row.set_selected(False)
            # Скрываем галочку
            self._stop_loading()
            self._success_icon.hide()
            self.strategy_selected.emit(self._category_key, "none")
            log(f"Категория {self._category_key} отключена", "INFO")
            self._refresh_args_editor_state()

    def _get_default_strategy(self) -> str:
        """Возвращает стратегию по умолчанию для текущей категории"""
        try:
            from strategy_menu.strategies_registry import registry

            # Пробуем получить дефолтную стратегию из реестра
            defaults = registry.get_default_selections()
            if self._category_key in defaults:
                default_id = defaults[self._category_key]
                if default_id and default_id != "none" and default_id in self._strategy_rows:
                    return default_id

            # Иначе берём первую стратегию из списка (не none)
            for sid in self._strategy_rows.keys():
                if sid != "none":
                    return sid

            return "none"
        except Exception as e:
            log(f"Ошибка получения стратегии по умолчанию: {e}", "DEBUG")
            # Fallback - первая не-none стратегия
            for sid in self._strategy_rows.keys():
                if sid != "none":
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

        self._syndata_toggle.setChecked(settings.get("enabled", True))
        self._syndata_settings.setVisible(settings.get("enabled", True))

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
        self._send_toggle.setChecked(settings.get("send_enabled", True))
        self._send_settings.setVisible(settings.get("send_enabled", True))
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

            # Clear selection visuals
            for row in self._strategy_rows.values():
                row.set_selected(False)

            self._selected_strategy_id = current_strategy_id or "none"
            self._current_strategy_id = current_strategy_id or "none"

            if self._selected_strategy_id != "none" and self._selected_strategy_id in self._strategy_rows:
                self._strategy_rows[self._selected_strategy_id].set_selected(True)
                self._enable_toggle.setChecked(True, block_signals=True)
                # Consider this as "applied"
                self._stop_loading()
                self.show_success()
            else:
                self._enable_toggle.setChecked(False, block_signals=True)
                self._stop_loading()
                self._success_icon.hide()

    def _on_row_clicked(self, strategy_id: str):
        """Обработчик клика по строке стратегии - выбор активной"""
        prev_strategy_id = self._selected_strategy_id

        # Снимаем выделение с предыдущей
        if self._selected_strategy_id in self._strategy_rows:
            self._strategy_rows[self._selected_strategy_id].set_selected(False)
        # Выделяем новую
        if strategy_id in self._strategy_rows:
            self._strategy_rows[strategy_id].set_selected(True)
        self._selected_strategy_id = strategy_id

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
        # Запускаем fallback таймер на случай если сигнал не придет
        self._start_fallback_timer()

    def _stop_loading(self):
        """Останавливает анимацию загрузки"""
        self._spinner.stop()
        self._waiting_for_process_start = False  # Больше не ждём
        self._stop_fallback_timer()

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
            elif not is_running:
                # DPI остановлен - скрываем галочку и спиннер
                self._stop_loading()
                self._success_icon.hide()
                log("StrategyDetailPage: DPI остановлен, скрываем индикаторы", "DEBUG")
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

    def _apply_filters(self):
        """Применяет фильтры по технике к списку стратегий"""
        search_text = self._search_input.text().lower().strip() if self._search_input else ""

        for strategy_id, row in self._strategy_rows.items():
            visible = True

            # Фильтр по поиску (только по args)
            if search_text:
                args_text = " ".join(row._args).lower() if row._args else ""
                visible = search_text in args_text

            # Фильтр по технике (если есть активные фильтры)
            if visible and self._active_filters:
                args_text = " ".join(row._args).lower() if row._args else ""
                has_technique = any(t in args_text for t in self._active_filters)
                visible = has_technique

            row.setVisible(visible)

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
        if not self._strategy_rows:
            return
        self._reflow_strategy_rows()
