# ui/pages/strategy_detail_page.py
"""
Страница детального просмотра стратегий для выбранной категории.
Открывается при клике на категорию в StrategiesPage.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QFrame, QPushButton, QScrollArea, QLineEdit, QMenu, QComboBox, QSpinBox
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from .dpi_settings_page import Win11ToggleRow
from ui.widgets.win11_spinner import Win11Spinner
from log import log
from strategy_menu.blobs import get_blobs_info


class TlsModToggle(QPushButton):
    """Toggle-кнопка для tls_mod параметра"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._update_style)
        self._update_style(False)

    def _update_style(self, checked: bool):
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background: #60cdff;
                    color: #000000;
                    border: none;
                    border-radius: 4px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: rgba(255, 255, 255, 0.7);
                    border: none;
                    border-radius: 4px;
                    padding: 0 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.12);
                }
            """)


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
            from log import log
            log(f"[FilterModeSelector] Выбран режим: {mode}", "DEBUG")
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


class StrategyRow(QFrame):
    """Строка выбора стратегии с избранным и редактируемыми аргументами"""

    clicked = pyqtSignal()  # Клик по строке (выбор активной)
    favorite_toggled = pyqtSignal(str, bool)  # (strategy_id, is_favorite)
    args_changed = pyqtSignal(str, list)  # (strategy_id, new_args)
    marked_working = pyqtSignal(str, object)  # (strategy_id, is_working)

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
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(0)

        # Таймер для анимации загрузки
        self._loading_timer = None

        # Верхняя строка: звезда + название + индикатор
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        # Звезда избранного (отдельная от выбора)
        self._star_btn = QPushButton()
        self._star_btn.setFixedSize(20, 20)
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
                font-size: 13px;
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

        # Нижняя строка: аргументы (только для не-none)
        if self._strategy_id != "none":
            args_row = QHBoxLayout()
            args_row.setContentsMargins(26, 0, 0, 0)
            args_row.setSpacing(0)

            self._args_edit = QLineEdit()
            self._args_edit.setText(" ".join(self._args))
            self._args_edit.setPlaceholderText("args...")
            self._args_edit.setFixedHeight(20)
            self._args_edit.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    color: rgba(255, 255, 255, 0.4);
                    padding: 0 4px;
                    font-size: 10px;
                    font-family: 'Consolas', monospace;
                }
                QLineEdit:focus {
                    background: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.7);
                }
            """)
            self._args_edit.editingFinished.connect(self._on_args_edited)
            args_row.addWidget(self._args_edit, 1)

            main_layout.addLayout(args_row)
        else:
            self._args_edit = None

    def _on_star_clicked(self):
        """Переключает избранное"""
        self._favorite = not self._favorite
        self._update_star_icon()
        self.favorite_toggled.emit(self._strategy_id, self._favorite)

    def _on_args_edited(self):
        """Аргументы изменены"""
        if self._args_edit:
            new_args = self._args_edit.text().split()
            if new_args != self._args:
                self._args = new_args
                self.args_changed.emit(self._strategy_id, new_args)

    def mousePressEvent(self, event):
        """Клик по строке - выбор активной стратегии"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Не обрабатываем если клик по звезде или полю ввода
            child = self.childAt(event.pos())
            if child not in (self._star_btn, self._args_edit):
                self.clicked.emit()
        super().mousePressEvent(event)

    def set_args(self, args: list):
        self._args = args or []
        if self._args_edit:
            self._args_edit.setText(" ".join(self._args))

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
        if self._favorite:
            self._star_btn.setIcon(qta.icon('fa5s.star', color='#ffd700'))
        else:
            self._star_btn.setIcon(qta.icon('mdi.star-outline', color='#ffffff'))
        self._star_btn.setIconSize(QSize(16, 16))

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

        clear_mark = None
        if self._is_working is not None:
            menu.addSeparator()
            clear_mark = menu.addAction("Снять пометку")

        action = menu.exec(event.globalPos())

        if action == mark_working:
            self._is_working = True
            self.marked_working.emit(self._strategy_id, True)
            self._update_working_indicator()
        elif action == mark_not_working:
            self._is_working = False
            self.marked_working.emit(self._strategy_id, False)
            self._update_working_indicator()
        elif clear_mark is not None and action == clear_mark:
            self._is_working = None
            self.marked_working.emit(self._strategy_id, None)
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
    args_changed = pyqtSignal(str, str, list)  # category_key, strategy_id, new_args
    strategy_marked = pyqtSignal(str, str, object)  # category_key, strategy_id, is_working (bool or None)
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

        # Защита от быстрого переключения стратегий
        self._is_switching = False  # Флаг блокировки во время переключения
        self._pending_strategy_id = None  # Ожидающая стратегия (для debounce)
        self._switch_timer = QTimer(self)  # Таймер debounce
        self._switch_timer.setSingleShot(True)
        self._switch_timer.setInterval(150)  # 150ms debounce
        self._switch_timer.timeout.connect(self._apply_pending_strategy)

        self._build_content()

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
        # OUT-RANGE SETTINGS (отдельная опция)
        # ═══════════════════════════════════════════════════════════════
        self._out_range_frame = QFrame()
        self._out_range_frame.setStyleSheet("QFrame { background: transparent; }")
        out_range_layout = QHBoxLayout(self._out_range_frame)
        out_range_layout.setContentsMargins(0, 6, 0, 6)
        out_range_layout.setSpacing(12)

        # Icon
        out_range_icon = QLabel()
        out_range_icon.setFixedSize(22, 22)
        out_range_icon.setPixmap(qta.icon("fa5s.sliders-h", color="#60cdff").pixmap(18, 18))
        out_range_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        out_range_layout.addWidget(out_range_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Text
        out_range_text_layout = QVBoxLayout()
        out_range_text_layout.setSpacing(2)
        out_range_title = QLabel("Out-Range")
        out_range_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        out_range_desc = QLabel("Диапазон обрабатываемых пакетов")
        out_range_desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        out_range_text_layout.addWidget(out_range_title)
        out_range_text_layout.addWidget(out_range_desc)
        out_range_layout.addLayout(out_range_text_layout)

        out_range_layout.addStretch()

        # Mode selector (d/n) - две кнопки как у Hostlist/IPset
        self._out_range_d_btn = QPushButton("d")
        self._out_range_n_btn = QPushButton("n")

        for btn in [self._out_range_d_btn, self._out_range_n_btn]:
            btn.setFixedHeight(28)
            btn.setMinimumWidth(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._out_range_d_btn.setToolTip("data packets only")
        self._out_range_n_btn.setToolTip("all packets")
        # IMPORTANT: lambda must accept optional 'checked' parameter from clicked signal
        self._out_range_d_btn.clicked.connect(lambda checked=False: self._set_out_range_mode("d"))
        self._out_range_n_btn.clicked.connect(lambda checked=False: self._set_out_range_mode("n"))

        # По умолчанию n
        self._out_range_mode = "n"
        self._update_out_range_mode_styles()

        out_range_layout.addWidget(self._out_range_d_btn)
        out_range_layout.addWidget(self._out_range_n_btn)

        # Spinbox
        self._out_range_spin = QSpinBox()
        self._out_range_spin.setRange(0, 100)
        self._out_range_spin.setValue(4)  # По умолчанию 4
        self._out_range_spin.setSpecialValueText("off")
        self._out_range_spin.setToolTip("--out-range=-dN или --out-range=-nN")
        self._out_range_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                min-width: 75px;
            }
        """)
        self._out_range_spin.valueChanged.connect(self._save_out_range_settings)
        out_range_layout.addWidget(self._out_range_spin)

        toolbar_layout.addWidget(self._out_range_frame)

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
        self._blob_combo.setStyleSheet(combo_style)
        self._blob_combo.currentTextChanged.connect(self._save_syndata_settings)
        self._populate_blob_combo()  # Динамическая загрузка из blobs.py
        blob_row.addWidget(blob_label)
        blob_row.addWidget(self._blob_combo)
        blob_row.addStretch()
        settings_layout.addLayout(blob_row)

        # tls_mod selector row - toggle buttons (can be combined)
        tls_mod_row = QHBoxLayout()
        tls_mod_row.setSpacing(8)
        tls_mod_label = QLabel("tls_mod:")
        tls_mod_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        tls_mod_label.setFixedWidth(60)
        tls_mod_row.addWidget(tls_mod_label)

        # Toggle buttons для комбинируемых модов
        self._tls_mod_buttons = {}
        for mod_name in ["rnd", "rndsni", "dupsid", "padencap"]:
            btn = TlsModToggle(mod_name)
            btn.toggled.connect(self._save_syndata_settings)
            self._tls_mod_buttons[mod_name] = btn
            tls_mod_row.addWidget(btn)

        # sni= input
        sni_label = QLabel("sni=")
        sni_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent; margin-left: 8px;")
        tls_mod_row.addWidget(sni_label)
        self._sni_input = QLineEdit()
        self._sni_input.setPlaceholderText("google.com")
        self._sni_input.setFixedWidth(100)
        self._sni_input.setFixedHeight(26)
        self._sni_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 0 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.12);
            }
        """)
        self._sni_input.textChanged.connect(self._save_syndata_settings)
        tls_mod_row.addWidget(self._sni_input)

        tls_mod_row.addStretch()
        settings_layout.addLayout(tls_mod_row)

        # IP AutoTTL row - автоматический TTL
        autottl_row = QHBoxLayout()
        autottl_row.setSpacing(8)
        autottl_label = QLabel("ip_autottl:")
        autottl_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        autottl_label.setFixedWidth(70)
        autottl_row.addWidget(autottl_label)

        # Toggle для включения/выключения autottl
        self._autottl_toggle = QPushButton("off")
        self._autottl_toggle.setCheckable(True)
        self._autottl_toggle.setChecked(False)
        self._autottl_toggle.setFixedHeight(28)
        self._autottl_toggle.setMinimumWidth(40)
        self._autottl_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._autottl_toggle.clicked.connect(self._on_autottl_toggle)
        autottl_row.addWidget(self._autottl_toggle)

        # Delta presets: -1 до -8 (отрицательные для DPI bypass)
        self._autottl_delta_presets = {}
        delta_values = [-1, -2, -3, -4, -5, -6, -7, -8]
        for delta in delta_values:
            btn = QPushButton(str(delta))
            btn.setFixedHeight(28)
            btn.setMinimumWidth(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, d=delta: self._set_autottl_delta(d))
            self._autottl_delta_presets[delta] = btn
            autottl_row.addWidget(btn)

        # Min-Max спинбоксы
        min_label = QLabel("min:")
        min_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        autottl_row.addWidget(min_label)

        self._autottl_min_spin = QSpinBox()
        self._autottl_min_spin.setRange(1, 255)
        self._autottl_min_spin.setValue(3)
        self._autottl_min_spin.setFixedWidth(50)
        self._autottl_min_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
        """)
        self._autottl_min_spin.valueChanged.connect(self._save_syndata_settings)
        autottl_row.addWidget(self._autottl_min_spin)

        max_label = QLabel("max:")
        max_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        autottl_row.addWidget(max_label)

        self._autottl_max_spin = QSpinBox()
        self._autottl_max_spin.setRange(1, 255)
        self._autottl_max_spin.setValue(20)
        self._autottl_max_spin.setFixedWidth(50)
        self._autottl_max_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
        """)
        self._autottl_max_spin.valueChanged.connect(self._save_syndata_settings)
        autottl_row.addWidget(self._autottl_max_spin)

        # Инициализация стилей
        self._autottl_enabled = False
        self._autottl_delta = -1
        self._update_autottl_styles()

        autottl_row.addStretch()
        settings_layout.addLayout(autottl_row)

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

        # Send row - отправка дубликата с repeats
        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        send_label = QLabel("send:")
        send_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")
        send_label.setFixedWidth(60)

        # Toggle для включения send
        self._send_toggle = TlsModToggle("вкл")
        self._send_toggle.setChecked(True)  # По умолчанию включен
        self._send_toggle.setFixedWidth(40)
        self._send_toggle.toggled.connect(self._save_syndata_settings)

        # repeats spinbox
        repeats_label = QLabel("repeats:")
        repeats_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent; margin-left: 8px;")
        self._send_repeats_spin = QSpinBox()
        self._send_repeats_spin.setRange(1, 20)
        self._send_repeats_spin.setValue(2)  # По умолчанию 2
        self._send_repeats_spin.setToolTip("--lua-desync=send:repeats=N")
        self._send_repeats_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
            }
        """)
        self._send_repeats_spin.valueChanged.connect(self._save_syndata_settings)

        send_row.addWidget(send_label)
        send_row.addWidget(self._send_toggle)
        send_row.addWidget(repeats_label)
        send_row.addWidget(self._send_repeats_spin)
        send_row.addStretch()
        settings_layout.addLayout(send_row)

        syndata_layout.addWidget(self._syndata_settings)
        toolbar_layout.addWidget(self._syndata_frame)

        # ═══════════════════════════════════════════════════════════════
        # КНОПКА СБРОСА НАСТРОЕК КАТЕГОРИИ
        # ═══════════════════════════════════════════════════════════════
        self._reset_frame = QFrame()
        self._reset_frame.setStyleSheet("QFrame { background: transparent; }")
        reset_layout = QHBoxLayout(self._reset_frame)
        reset_layout.setContentsMargins(0, 6, 0, 6)
        reset_layout.setSpacing(12)

        reset_layout.addStretch()

        # Кнопка сброса настроек категории
        self._reset_settings_btn = QPushButton("Сбросить настройки")
        self._reset_settings_btn.setIcon(qta.icon("fa5s.undo", color="#ff8a65"))
        self._reset_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_settings_btn.setToolTip("Сбросить syndata, send, out-range и filter mode к значениям по умолчанию")
        self._reset_settings_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 138, 101, 0.1);
                border: 1px solid rgba(255, 138, 101, 0.3);
                border-radius: 6px;
                color: #ff8a65;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 138, 101, 0.2);
                border-color: rgba(255, 138, 101, 0.5);
            }
        """)
        self._reset_settings_btn.clicked.connect(self._reset_category_settings)
        reset_layout.addWidget(self._reset_settings_btn)

        toolbar_layout.addWidget(self._reset_frame)

        self.layout.addWidget(self._toolbar_frame)

        # Поиск по стратегиям
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск стратегий...")
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

        self.layout.addLayout(search_layout)

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
        self._strategies_layout = QVBoxLayout()
        self._strategies_layout.setContentsMargins(0, 0, 0, 0)
        self._strategies_layout.setSpacing(4)
        self._strategies_layout.addStretch()

        self.layout.addLayout(self._strategies_layout, 1)

    def show_category(self, category_key: str, category_info, current_strategy_id: str):
        """
        Показывает стратегии для выбранной категории.

        Args:
            category_key: Ключ категории (например, "youtube_https")
            category_info: Объект CategoryInfo с информацией о категории
            current_strategy_id: ID текущей выбранной стратегии
        """
        log(f"StrategyDetailPage.show_category: {category_key}, current={current_strategy_id}", "DEBUG")

        # Сбрасываем состояние debounce и блокировки при смене категории
        self._switch_timer.stop()
        self._pending_strategy_id = None
        self._is_switching = False

        self._category_key = category_key
        self._category_info = category_info
        self._current_strategy_id = current_strategy_id or "none"
        self._selected_strategy_id = self._current_strategy_id

        # Обновляем заголовок (только название категории в breadcrumb)
        self._title.setText(category_info.full_name)
        self._subtitle.setText(f"{category_info.protocol}  |  порты: {category_info.ports}")

        # Очищаем старые стратегии
        self._clear_strategies()

        # Загружаем новые
        self._load_strategies()

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
            log(f"[load_category] Категория: {category_key}, загруженный режим: {saved_filter_mode}", "DEBUG")
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

        # Загружаем syndata настройки для категории
        syndata_settings = self._load_syndata_settings(category_key)
        self._apply_syndata_settings(syndata_settings)

        # Load out-range settings
        out_range_settings = self._load_out_range_settings(category_key)
        self._apply_out_range_settings(out_range_settings)

        log(f"StrategyDetailPage: показана категория {category_key}, sort_mode={self._sort_mode}", "DEBUG")

    def _clear_strategies(self):
        """Очищает список стратегий"""
        for row in self._strategy_rows.values():
            row.deleteLater()
        self._strategy_rows.clear()

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

            for sid, data in strategies.items():
                name = data.get('name', sid)
                args = data.get('args', [])
                if isinstance(args, str):
                    args = args.split()
                self._add_strategy_row(sid, name, args)

            log(f"StrategyDetailPage: добавлено {len(self._strategy_rows)} строк стратегий", "DEBUG")

            # Выбираем текущую стратегию
            if self._current_strategy_id in self._strategy_rows:
                self._strategy_rows[self._current_strategy_id].set_selected(True)

        except Exception as e:
            import traceback
            log(f"Ошибка загрузки стратегий: {e}", "ERROR")
            log(f"Traceback: {traceback.format_exc()}", "ERROR")

    def _add_strategy_row(self, strategy_id: str, name: str, args: list = None):
        """Добавляет строку стратегии в список"""
        row = StrategyRow(strategy_id, name, args)
        row.clicked.connect(lambda sid=strategy_id: self._on_row_clicked(sid))
        row.favorite_toggled.connect(lambda sid, fav: self._on_favorite_toggled(sid, fav))
        row.args_changed.connect(lambda sid, new_args: self._on_args_changed(sid, new_args))
        row.marked_working.connect(lambda sid, is_working: self._on_strategy_marked(sid, is_working))
        # Вставляем перед stretch
        self._strategies_layout.insertWidget(self._strategies_layout.count() - 1, row)
        self._strategy_rows[strategy_id] = row

    def _on_favorite_toggled(self, strategy_id: str, is_favorite: bool):
        """Обработчик переключения избранного"""
        if is_favorite and strategy_id in self._strategy_rows:
            # Перемещаем избранную стратегию наверх
            row = self._strategy_rows[strategy_id]
            self._strategies_layout.removeWidget(row)
            self._strategies_layout.insertWidget(0, row)
        log(f"Favorite toggled: {strategy_id} = {is_favorite}", "DEBUG")

    def _on_strategy_marked(self, strategy_id: str, is_working):
        """Обработчик пометки стратегии как рабочей/нерабочей"""
        if self._category_key:
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

        # Блокируем быстрые переключения
        if self._is_switching:
            log(f"Toggle ignored - already switching", "DEBUG")
            return

        # Останавливаем pending операцию если есть
        self._switch_timer.stop()
        self._pending_strategy_id = None

        if enabled:
            # Включаем - выбираем стратегию по умолчанию или первую доступную
            strategy_to_select = self._get_default_strategy()
            if strategy_to_select and strategy_to_select != "none":
                # Снимаем выделение с предыдущей
                if self._selected_strategy_id in self._strategy_rows:
                    self._strategy_rows[self._selected_strategy_id].set_selected(False)
                # Выделяем новую
                if strategy_to_select in self._strategy_rows:
                    self._strategy_rows[strategy_to_select].set_selected(True)
                self._selected_strategy_id = strategy_to_select

                self._is_switching = True
                # Показываем анимацию загрузки
                self.show_loading()
                # Блокируем UI на время запуска DPI
                self.set_strategies_enabled(False)
                self.strategy_selected.emit(self._category_key, strategy_to_select)
                log(f"Категория {self._category_key} включена со стратегией {strategy_to_select}", "INFO")
                # Снимаем блокировку через задержку (500ms для гарантированного старта DPI)
                QTimer.singleShot(500, self._unlock_switching)
            else:
                log(f"Нет доступных стратегий для {self._category_key}", "WARNING")
                self._enable_toggle.setChecked(False, block_signals=True)
        else:
            # Выключаем - устанавливаем "none"
            self._selected_strategy_id = "none"
            # Снимаем выделение со всех стратегий
            for row in self._strategy_rows.values():
                row.set_selected(False)
            # Скрываем галочку
            self._stop_loading()
            self._success_icon.hide()

            # Блокируем UI на время остановки DPI
            self.set_strategies_enabled(False)

            self._is_switching = True
            self.strategy_selected.emit(self._category_key, "none")
            log(f"Категория {self._category_key} отключена", "INFO")
            # Снимаем блокировку через задержку (500ms для гарантированной остановки DPI)
            QTimer.singleShot(500, self._unlock_switching)

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

        log(f"[_on_filter_mode_changed] Категория: {self._category_key}, новый режим: {new_mode}", "DEBUG")
        # Используем централизованный модуль: сохранит в реестр + перезапустит DPI
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        rs.save_filter_mode(self._category_key, new_mode)
        log(f"Режим фильтрации для {self._category_key}: {new_mode} СОХРАНЕН", "INFO")

        # Перезапускаем winws2 если категория включена
        if self._selected_strategy_id and self._selected_strategy_id != "none":
            self.strategy_selected.emit(self._category_key, self._selected_strategy_id)

    def _set_out_range_mode(self, mode: str):
        """Устанавливает режим out-range (d или n)"""
        log(f"_set_out_range_mode called: mode={mode}", "DEBUG")
        if mode not in ("d", "n"):
            log(f"Invalid out-range mode: {mode}", "WARNING")
            return
        self._out_range_mode = mode
        self._update_out_range_mode_styles()
        self._save_out_range_settings()
        log(f"Out-range mode successfully set to: {self._out_range_mode}", "DEBUG")

    def _update_out_range_mode_styles(self):
        """Обновляет стили кнопок d/n"""
        active_style = """
            QPushButton {
                background: #60cdff;
                border: none;
                border-radius: 4px;
                color: #000000;
                font-size: 13px;
                font-weight: 700;
                padding: 0 8px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """
        if self._out_range_mode == "d":
            self._out_range_d_btn.setStyleSheet(active_style)
            self._out_range_n_btn.setStyleSheet(inactive_style)
        else:
            self._out_range_d_btn.setStyleSheet(inactive_style)
            self._out_range_n_btn.setStyleSheet(active_style)

    def _save_out_range_settings(self):
        """Сохраняет out-range настройки в реестр"""
        if not self._category_key:
            log("_save_out_range_settings: category_key is empty, skipping", "WARNING")
            return

        # Используем централизованный модуль
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        settings = {
            "mode": self._out_range_mode,
            "value": self._out_range_spin.value(),
        }
        rs.save_out_range(self._category_key, settings)

        # Перезапускаем winws2 если категория включена
        if self._selected_strategy_id and self._selected_strategy_id != "none":
            self.strategy_selected.emit(self._category_key, self._selected_strategy_id)

    def _load_out_range_settings(self, category_key: str) -> dict:
        """Загружает out-range настройки из реестра"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        return rs.load_out_range(category_key)

    def _apply_out_range_settings(self, settings: dict):
        """Применяет out-range настройки к UI"""
        self._out_range_spin.blockSignals(True)

        self._out_range_mode = settings.get("mode", "n")
        self._update_out_range_mode_styles()
        self._out_range_spin.setValue(settings.get("value", 4))

        self._out_range_spin.blockSignals(False)

    def _save_category_filter_mode(self, category_key: str, mode: str):
        """Сохраняет режим фильтрации для категории в реестр"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        rs.save_filter_mode(category_key, mode)

    def _load_category_filter_mode(self, category_key: str) -> str:
        """Загружает режим фильтрации для категории из реестра"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        return rs.load_filter_mode(category_key)

    def _save_category_sort(self, category_key: str, sort_order: str):
        """Сохраняет порядок сортировки для категории в реестр"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        rs.save_sort_order(category_key, sort_order)

    def _load_category_sort(self, category_key: str) -> str:
        """Загружает порядок сортировки для категории из реестра"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        return rs.load_sort_order(category_key)

    # ═══════════════════════════════════════════════════════════════
    # SYNDATA SETTINGS METHODS
    # ═══════════════════════════════════════════════════════════════

    def _on_syndata_toggled(self, checked: bool):
        """Обработчик включения/выключения syndata параметров"""
        self._syndata_settings.setVisible(checked)
        self._save_syndata_settings()

    def _populate_blob_combo(self):
        """Загружает список блобов из blobs.py в комбобокс"""
        self._blob_combo.blockSignals(True)
        self._blob_combo.clear()
        self._blob_combo.addItem("none")
        try:
            blobs_info = get_blobs_info()
            for blob_name, info in sorted(blobs_info.items()):
                self._blob_combo.addItem(blob_name)
                # Tooltip с описанием
                idx = self._blob_combo.count() - 1
                desc = info.get("description", "")
                if desc:
                    self._blob_combo.setItemData(idx, desc, Qt.ItemDataRole.ToolTipRole)
        except Exception as e:
            log(f"Ошибка загрузки блобов: {e}", "WARNING")
            # Fallback - добавляем базовые блобы
            self._blob_combo.addItems(["tls_google", "fake_default_tls"])
        self._blob_combo.blockSignals(False)

    def _get_tls_mod_value(self) -> str:
        """Собирает значение tls_mod из toggle-кнопок и sni input"""
        mods = []
        for mod_name, btn in self._tls_mod_buttons.items():
            if btn.isChecked():
                mods.append(mod_name)
        # Добавляем sni= если заполнено
        sni_value = self._sni_input.text().strip()
        if sni_value:
            mods.append(f"sni={sni_value}")
        return ",".join(mods) if mods else "none"

    def _save_syndata_settings(self):
        """Сохраняет syndata настройки для текущей категории в реестр и перезапускает winws2"""
        if not self._category_key:
            return

        # Собираем настройки из UI
        settings = {
            "enabled": self._syndata_toggle.isChecked(),
            "blob": self._blob_combo.currentText(),
            "tls_mod": self._get_tls_mod_value(),
            "autottl_enabled": self._autottl_enabled,
            "autottl_delta": self._autottl_delta,
            "autottl_min": self._autottl_min_spin.value(),
            "autottl_max": self._autottl_max_spin.value(),
            "tcp_flags_unset": self._tcp_flags_combo.currentText(),
            "send_enabled": self._send_toggle.isChecked(),
            "send_repeats": self._send_repeats_spin.value(),
        }

        # Используем централизованный модуль
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        rs.save_syndata(self._category_key, settings)

        # Перезапускаем winws2 если категория включена
        if self._selected_strategy_id and self._selected_strategy_id != "none":
            self.strategy_selected.emit(self._category_key, self._selected_strategy_id)

    def _on_autottl_toggle(self, checked: bool):
        """Toggle autottl on/off"""
        self._autottl_enabled = checked
        self._autottl_toggle.setText("on" if checked else "off")
        self._update_autottl_styles()
        self._save_syndata_settings()

    def _set_autottl_delta(self, delta: int):
        """Устанавливает delta и включает autottl"""
        self._autottl_enabled = True
        self._autottl_delta = delta
        self._autottl_toggle.setChecked(True)
        self._autottl_toggle.setText("on")
        self._update_autottl_styles()
        self._save_syndata_settings()

    def _update_autottl_styles(self):
        """Обновляет стили кнопок autottl"""
        # Стиль toggle
        if self._autottl_enabled:
            self._autottl_toggle.setStyleSheet("""
                QPushButton {
                    background: rgba(34, 197, 94, 0.3);
                    border: 1px solid rgba(34, 197, 94, 0.6);
                    border-radius: 4px;
                    color: #22c55e;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 4px 8px;
                }
            """)
        else:
            self._autottl_toggle.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)

        # Стили пресетов delta
        active_style = """
            QPushButton {
                background: rgba(96, 165, 250, 0.3);
                border: 1px solid rgba(96, 165, 250, 0.6);
                border-radius: 4px;
                color: #60a5fa;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 6px;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """
        disabled_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.3);
                font-size: 12px;
                padding: 4px 6px;
            }
        """

        for delta, btn in self._autottl_delta_presets.items():
            if not self._autottl_enabled:
                btn.setStyleSheet(disabled_style)
            elif delta == self._autottl_delta:
                btn.setStyleSheet(active_style)
            else:
                btn.setStyleSheet(inactive_style)

        # Включаем/выключаем min/max спинбоксы
        self._autottl_min_spin.setEnabled(self._autottl_enabled)
        self._autottl_max_spin.setEnabled(self._autottl_enabled)

    def _load_syndata_settings(self, category_key: str) -> dict:
        """Загружает syndata настройки для категории из реестра"""
        from strategy_menu.preset_configuration_zapret2 import registry_settings as rs
        return rs.load_syndata(category_key)

    def _apply_syndata_settings(self, settings: dict):
        """Применяет syndata настройки к UI без эмиссии сигналов сохранения"""
        # Блокируем сигналы чтобы не вызывать save при загрузке
        self._syndata_toggle.blockSignals(True)
        self._blob_combo.blockSignals(True)
        self._autottl_min_spin.blockSignals(True)
        self._autottl_max_spin.blockSignals(True)
        self._tcp_flags_combo.blockSignals(True)
        self._sni_input.blockSignals(True)
        self._send_toggle.blockSignals(True)
        self._send_repeats_spin.blockSignals(True)
        for btn in self._tls_mod_buttons.values():
            btn.blockSignals(True)

        self._syndata_toggle.setChecked(settings.get("enabled", True))
        self._syndata_settings.setVisible(settings.get("enabled", True))

        blob_value = settings.get("blob", "none")
        blob_index = self._blob_combo.findText(blob_value)
        if blob_index >= 0:
            self._blob_combo.setCurrentIndex(blob_index)

        # Парсим tls_mod и применяем к кнопкам
        tls_mod_value = settings.get("tls_mod", "none")
        # Сбрасываем все кнопки и sni input
        for btn in self._tls_mod_buttons.values():
            btn.setChecked(False)
        self._sni_input.clear()
        # Применяем сохранённые значения
        if tls_mod_value and tls_mod_value != "none":
            for mod in tls_mod_value.split(","):
                mod = mod.strip()
                if mod.startswith("sni="):
                    self._sni_input.setText(mod[4:])
                elif mod in self._tls_mod_buttons:
                    self._tls_mod_buttons[mod].setChecked(True)

        # AutoTTL
        self._autottl_enabled = settings.get("autottl_enabled", False)
        self._autottl_delta = settings.get("autottl_delta", 1)
        self._autottl_toggle.setChecked(self._autottl_enabled)
        self._autottl_toggle.setText("on" if self._autottl_enabled else "off")
        self._autottl_min_spin.setValue(settings.get("autottl_min", 3))
        self._autottl_max_spin.setValue(settings.get("autottl_max", 20))
        self._update_autottl_styles()

        tcp_flags_value = settings.get("tcp_flags_unset", "none")
        tcp_flags_index = self._tcp_flags_combo.findText(tcp_flags_value)
        if tcp_flags_index >= 0:
            self._tcp_flags_combo.setCurrentIndex(tcp_flags_index)

        self._send_toggle.setChecked(settings.get("send_enabled", True))
        self._send_repeats_spin.setValue(settings.get("send_repeats", 2))

        # Разблокируем сигналы
        self._syndata_toggle.blockSignals(False)
        self._blob_combo.blockSignals(False)
        self._autottl_min_spin.blockSignals(False)
        self._autottl_max_spin.blockSignals(False)
        self._tcp_flags_combo.blockSignals(False)
        self._sni_input.blockSignals(False)
        self._send_toggle.blockSignals(False)
        self._send_repeats_spin.blockSignals(False)
        for btn in self._tls_mod_buttons.values():
            btn.blockSignals(False)

    def get_syndata_settings(self) -> dict:
        """Возвращает текущие syndata настройки для использования в командной строке"""
        return {
            "enabled": self._syndata_toggle.isChecked(),
            "blob": self._blob_combo.currentText(),
            "tls_mod": self._get_tls_mod_value(),
        }

    def _on_row_clicked(self, strategy_id: str):
        """Обработчик клика по строке стратегии - выбор активной с debounce"""
        # КРИТИЧНО: блокируем все клики во время переключения
        if self._is_switching:
            log(f"Row click BLOCKED - already switching", "DEBUG")
            return

        # Если это та же стратегия - игнорируем
        if strategy_id == self._selected_strategy_id and not self._pending_strategy_id:
            return

        # Снимаем выделение с предыдущей
        if self._selected_strategy_id in self._strategy_rows:
            self._strategy_rows[self._selected_strategy_id].set_selected(False)
        # Также снимаем с pending если она была
        if self._pending_strategy_id and self._pending_strategy_id in self._strategy_rows:
            self._strategy_rows[self._pending_strategy_id].set_selected(False)

        # Выделяем новую
        if strategy_id in self._strategy_rows:
            self._strategy_rows[strategy_id].set_selected(True)

        # Синхронизируем toggle визуально сразу
        if strategy_id != "none":
            self._enable_toggle.setChecked(True, block_signals=True)
            # Показываем анимацию загрузки
            self.show_loading()
        else:
            self._stop_loading()
            self._success_icon.hide()

        # Сохраняем pending стратегию и перезапускаем таймер (debounce)
        self._pending_strategy_id = strategy_id
        self._switch_timer.stop()
        self._switch_timer.start()

        log(f"Strategy click (debounced): {strategy_id}, pending...", "DEBUG")

    def _apply_pending_strategy(self):
        """Применяет отложенную стратегию после debounce таймера"""
        if not self._pending_strategy_id:
            return

        strategy_id = self._pending_strategy_id
        self._pending_strategy_id = None

        # Проверяем что не происходит другое переключение
        if self._is_switching:
            log(f"Skipping strategy apply - already switching", "DEBUG")
            return

        self._is_switching = True

        try:
            # Блокируем UI на время перезапуска DPI
            self.set_strategies_enabled(False)

            # Обновляем selected_strategy_id только после debounce
            self._selected_strategy_id = strategy_id

            # Применяем стратегию (но остаёмся на странице)
            if self._category_key:
                log(f"Applying strategy: {self._category_key}/{strategy_id}", "DEBUG")
                self.strategy_selected.emit(self._category_key, strategy_id)
        finally:
            # Снимаем блокировку через небольшую задержку
            # чтобы дать время на обработку сигнала
            QTimer.singleShot(100, self._unlock_switching)

    def _unlock_switching(self):
        """Снимает блокировку переключения"""
        self._is_switching = False

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

    def _stop_loading(self):
        """Останавливает анимацию загрузки"""
        self._spinner.stop()

    def show_success(self):
        """Показывает зелёную галочку успеха"""
        self._stop_loading()
        self._success_icon.setPixmap(qta.icon('fa5s.check-circle', color='#4ade80').pixmap(16, 16))
        self._success_icon.show()
        # Разблокируем UI после успешного запуска
        self.set_strategies_enabled(True)

    def set_strategies_enabled(self, enabled: bool):
        """Блокирует/разблокирует список стратегий"""
        for row in self._strategy_rows.values():
            row.setEnabled(enabled)
            # КРИТИЧНО: блокируем сигналы чтобы клики не накапливались в очереди
            row.blockSignals(not enabled)

        # Также блокируем поиск, фильтры и toggle
        if hasattr(self, '_search_input'):
            self._search_input.setEnabled(enabled)
        if hasattr(self, '_filter_chips'):
            for chip in self._filter_chips.values():
                chip.setEnabled(enabled)
        if hasattr(self, '_enable_toggle'):
            self._enable_toggle.setEnabled(enabled)

        log(f"Strategies UI {'enabled' if enabled else 'disabled'} (signals {'unblocked' if enabled else 'BLOCKED'})", "DEBUG")

    def _on_args_changed(self, strategy_id: str, args: list):
        """Обработчик изменения аргументов стратегии"""
        if self._category_key:
            self.args_changed.emit(self._category_key, strategy_id, args)
            log(f"Args changed: {self._category_key}/{strategy_id} = {args}", "DEBUG")

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

            # Фильтр по поиску
            if search_text:
                name_match = search_text in row._name.lower()
                args_match = False
                if row._args:
                    args_text = " ".join(row._args).lower()
                    args_match = search_text in args_text
                visible = name_match or args_match

            # Фильтр по технике (если есть активные фильтры)
            if visible and self._active_filters:
                # Проверяем и аргументы и название стратегии
                args_text = " ".join(row._args).lower() if row._args else ""
                name_text = row._name.lower()
                combined_text = f"{name_text} {args_text}"
                has_technique = any(t in combined_text for t in self._active_filters)
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

        # Получаем список строк
        rows = list(self._strategy_rows.values())

        if self._sort_mode == "name_asc":
            rows.sort(key=lambda r: r._name.lower())
        elif self._sort_mode == "name_desc":
            rows.sort(key=lambda r: r._name.lower(), reverse=True)
        # default - оставляем как есть (порядок загрузки)
        else:
            return

        # Переупорядочиваем виджеты
        for i, row in enumerate(rows):
            self._strategies_layout.removeWidget(row)
            self._strategies_layout.insertWidget(i, row)

    def _reset_category_settings(self):
        """Сбрасывает все настройки категории к значениям по умолчанию"""
        if not self._category_key:
            return

        log(f"Сброс настроек категории {self._category_key} к значениям по умолчанию", "INFO")

        # Значения по умолчанию для syndata
        default_syndata = {
            "enabled": True,
            "blob": "none",
            "tls_mod": "none",
            "autottl_enabled": False,
            "autottl_delta": -1,
            "autottl_min": 3,
            "autottl_max": 20,
            "tcp_flags_unset": "none",
            "send_enabled": True,
            "send_repeats": 2,
        }

        # Значения по умолчанию для out-range
        default_out_range = {
            "mode": "n",
            "value": 4,
        }

        # Значение по умолчанию для filter_mode
        default_filter_mode = "hostlist"

        # Применяем настройки к UI
        self._apply_syndata_settings(default_syndata)
        self._apply_out_range_settings(default_out_range)
        self._filter_mode_selector.setCurrentMode(default_filter_mode, block_signals=True)

        # Сохраняем дефолты в реестр (а не удаляем!)
        try:
            from config import REGISTRY_PATH
            import winreg
            import json

            # Сохраняем syndata дефолты
            try:
                key_path = f"{REGISTRY_PATH}\\CategorySyndata"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, self._category_key, 0, winreg.REG_SZ, json.dumps(default_syndata))
            except Exception as e:
                log(f"Ошибка сохранения syndata: {e}", "DEBUG")

            # Сохраняем out-range дефолты
            try:
                key_path = f"{REGISTRY_PATH}\\CategoryOutRange"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, self._category_key, 0, winreg.REG_SZ, json.dumps(default_out_range))
            except Exception as e:
                log(f"Ошибка сохранения out_range: {e}", "DEBUG")

            # Сохраняем filter_mode дефолт
            try:
                key_path = f"{REGISTRY_PATH}\\CategoryFilterMode"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, self._category_key, 0, winreg.REG_SZ, default_filter_mode)
            except Exception as e:
                log(f"Ошибка сохранения filter_mode: {e}", "DEBUG")

            log(f"Настройки категории {self._category_key} сброшены к дефолтам", "INFO")

            # Перезапускаем winws2 если категория включена
            if self._selected_strategy_id and self._selected_strategy_id != "none":
                self.strategy_selected.emit(self._category_key, self._selected_strategy_id)

        except Exception as e:
            log(f"Ошибка сброса настроек категории: {e}", "ERROR")
