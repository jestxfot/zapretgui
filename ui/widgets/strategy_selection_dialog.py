# ui/widgets/strategy_selection_dialog.py
"""
Диалог выбора стратегии для категории.
Открывается при клике на категорию, позволяет выбрать стратегию.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QRadioButton, QGridLayout
)
from PyQt6.QtGui import QFont
import qtawesome as qta


class StrategyRow(QFrame):
    """Компактная строка выбора стратегии с описанием"""

    clicked = pyqtSignal()

    def __init__(self, strategy_id: str, name: str, description: str = "", parent=None):
        super().__init__(parent)
        self._strategy_id = strategy_id
        self._name = name
        self._description = description
        self._selected = False

        self.setObjectName("strategyRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()
        self._update_style()

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Радио-кнопка
        self._radio = QRadioButton()
        self._radio.setStyleSheet("""
            QRadioButton::indicator {
                width: 12px; height: 12px;
                border-radius: 6px;
                border: 2px solid rgba(255, 255, 255, 0.4);
            }
            QRadioButton::indicator:checked {
                border: 2px solid #60cdff;
                background: #60cdff;
            }
        """)
        self._radio.clicked.connect(self.clicked.emit)
        layout.addWidget(self._radio, 0, Qt.AlignmentFlag.AlignTop)

        # Контейнер для названия и описания (вертикально)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        # Название (маленький шрифт)
        name_label = QLabel(self._name)
        name_label.setFont(QFont("Segoe UI", 9))
        name_label.setStyleSheet("color: #ffffff; background: transparent;")
        text_layout.addWidget(name_label)

        # Описание (ещё меньше, серым)
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setFont(QFont("Segoe UI", 8))
            desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.45); background: transparent;")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._radio.blockSignals(True)
        self._radio.setChecked(selected)
        self._radio.blockSignals(False)
        self._update_style()

    def is_selected(self) -> bool:
        return self._selected

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QFrame#strategyRow {
                    background: rgba(96, 205, 255, 0.1);
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#strategyRow {
                    background: transparent;
                    border-radius: 4px;
                }
                QFrame#strategyRow:hover {
                    background: rgba(255, 255, 255, 0.05);
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class StrategySelectionDialog(QDialog):
    """
    Диалог выбора стратегии для категории.

    Signals:
        strategy_selected(str, str, list): (category_key, strategy_id, args)
    """

    strategy_selected = pyqtSignal(str, str, list)

    def __init__(
        self,
        category_key: str,
        category_info,
        current_strategy_id: str,
        parent=None
    ):
        super().__init__(parent)

        self._category_key = category_key
        self._category_info = category_info
        self._current_strategy_id = current_strategy_id
        self._selected_strategy_id = current_strategy_id
        self._strategy_rows = {}  # {strategy_id: StrategyRow}

        self._setup_dialog()
        self._build_ui()
        self._load_strategies()

    def _setup_dialog(self):
        """Настройка диалога"""
        self.setWindowTitle(self._category_info.full_name)
        self.setModal(True)
        self.setMinimumSize(800, 500)
        self.resize(900, 600)

        # Убираем стандартную рамку Windows
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Стиль диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)

    def _build_ui(self):
        """Создает UI диалога"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Заголовок
        self._build_header(main_layout)

        # Контент
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(8)

        # Scroll Area со списком стратегий
        self._build_strategies_list(content_layout)

        # Кнопки
        self._build_buttons(content_layout)

        main_layout.addWidget(content_widget)

    def _build_header(self, parent_layout):
        """Создает заголовок диалога"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.03);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 10)
        header_layout.setSpacing(10)

        # Иконка категории
        try:
            icon_label = QLabel()
            icon = qta.icon(self._category_info.icon_name, color=self._category_info.icon_color)
            icon_label.setPixmap(icon.pixmap(20, 20))
            icon_label.setFixedSize(20, 20)
            icon_label.setStyleSheet("background: transparent;")
            header_layout.addWidget(icon_label)
        except Exception:
            pass

        # Название категории
        title_label = QLabel(self._category_info.full_name)
        title_label.setFont(QFont("Segoe UI Variable Display", 14, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #ffffff; background: transparent;")
        header_layout.addWidget(title_label)

        # Подзаголовок: протокол | порты
        subtitle = f"({self._category_info.protocol} | {self._category_info.ports})"
        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); background: transparent;")
        header_layout.addWidget(subtitle_label)

        header_layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon('fa5s.times', color='rgba(255,255,255,0.6)'))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        parent_layout.addWidget(header)

    def _build_strategies_list(self, parent_layout):
        """Создает ScrollArea со списком стратегий"""
        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        # Контейнер для стратегий (две колонки)
        self._strategies_container = QWidget()
        self._strategies_container.setStyleSheet("background: transparent;")
        self._strategies_layout = QGridLayout(self._strategies_container)
        self._strategies_layout.setContentsMargins(0, 0, 4, 0)
        self._strategies_layout.setSpacing(2)  # Компактно
        self._strategies_layout.setColumnStretch(0, 1)
        self._strategies_layout.setColumnStretch(1, 1)

        scroll_area.setWidget(self._strategies_container)
        parent_layout.addWidget(scroll_area, 1)  # stretch=1

    def _build_buttons(self, parent_layout):
        """Создает кнопки диалога"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addStretch()

        # Кнопка "Отмена"
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedSize(100, 36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.15);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        # Кнопка "Применить"
        apply_btn = QPushButton("Применить")
        apply_btn.setFixedSize(100, 36)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #60cdff;
                color: #000000;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #7dd7ff;
            }
        """)
        apply_btn.clicked.connect(self._on_apply)
        buttons_layout.addWidget(apply_btn)

        parent_layout.addLayout(buttons_layout)

    def _load_strategies(self):
        """Загружает стратегии из реестра"""
        try:
            from strategy_menu.strategies_registry import registry
            strategies = registry.get_category_strategies(self._category_key)
        except Exception:
            strategies = {}

        grid_row = 0
        grid_col = 0

        # Добавляем "Отключено" первым
        row = StrategyRow("none", "Отключено", "")
        row.clicked.connect(lambda: self._on_strategy_selected("none"))
        self._strategies_layout.addWidget(row, grid_row, grid_col)
        self._strategy_rows["none"] = row
        grid_col += 1
        if grid_col >= 2:
            grid_col = 0
            grid_row += 1

        # Добавляем стратегии
        for strategy_id, strategy_data in strategies.items():
            name = strategy_data.get('name', strategy_id)
            desc = strategy_data.get('description', '')  # description, НЕ args

            row = StrategyRow(strategy_id, name, desc)
            row.clicked.connect(lambda sid=strategy_id: self._on_strategy_selected(sid))
            self._strategies_layout.addWidget(row, grid_row, grid_col)
            self._strategy_rows[strategy_id] = row

            grid_col += 1
            if grid_col >= 2:
                grid_col = 0
                grid_row += 1

        # Выбираем текущую стратегию
        if self._current_strategy_id in self._strategy_rows:
            self._strategy_rows[self._current_strategy_id].set_selected(True)
            self._selected_strategy_id = self._current_strategy_id
        else:
            # Если текущая стратегия не найдена, выбираем "Отключено"
            self._strategy_rows["none"].set_selected(True)
            self._selected_strategy_id = "none"

    def _on_strategy_selected(self, strategy_id: str):
        """Обработчик выбора стратегии"""
        # Снимаем выделение с предыдущей
        if self._selected_strategy_id in self._strategy_rows:
            self._strategy_rows[self._selected_strategy_id].set_selected(False)

        # Выделяем новую
        if strategy_id in self._strategy_rows:
            self._strategy_rows[strategy_id].set_selected(True)

        self._selected_strategy_id = strategy_id

    def _on_apply(self):
        """Обработчик кнопки "Применить" """
        # Получаем аргументы выбранной стратегии
        args = []
        if self._selected_strategy_id != "none":
            try:
                from strategy_menu.strategies_registry import registry
                strategies = registry.get_category_strategies(self._category_key)
                if self._selected_strategy_id in strategies:
                    args_data = strategies[self._selected_strategy_id].get('args', [])
                    if isinstance(args_data, list):
                        args = args_data
                    elif isinstance(args_data, str):
                        args = args_data.split()
            except Exception:
                pass

        self.strategy_selected.emit(
            self._category_key,
            self._selected_strategy_id,
            args
        )
        self.accept()

    def mousePressEvent(self, event):
        """Позволяет перетаскивать диалог за заголовок"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, что клик в области заголовка (первые 50 пикселей)
            if event.position().y() < 50:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Перетаскивание диалога"""
        if hasattr(self, '_drag_pos') and self._drag_pos:
            if event.buttons() == Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Завершение перетаскивания"""
        self._drag_pos = None
        super().mouseReleaseEvent(event)
