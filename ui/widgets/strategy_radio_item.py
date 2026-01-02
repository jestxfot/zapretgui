# ui/widgets/strategy_radio_item.py
"""
Элемент выбора стратегии для категории в стиле Windows 11 Fluent Design.
Содержит ComboBox для выбора стратегии.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
import qtawesome as qta


class StrategyRadioItem(QFrame):
    """
    Элемент для выбора стратегии через ComboBox.

    Структура:
    ┌─────────────────────────────────────────────────────────┐
    │  🎬 YouTube TCP  |  TCP 443  |  [▼ Default Strategy  ]  │
    └─────────────────────────────────────────────────────────┘

    Содержит:
    - Иконка категории
    - Название категории
    - Описание (protocol|ports)
    - ComboBox со списком стратегий

    Signals:
        selected(str, str): (category_key, strategy_id)
    """

    selected = pyqtSignal(str, str)

    def __init__(
        self,
        category_key: str,
        name: str,
        description: str = "",
        icon_name: str = None,
        icon_color: str = "#2196F3",
        parent=None
    ):
        super().__init__(parent)
        self._category_key = category_key
        self._name = name
        self._description = description
        self._icon_name = icon_name
        self._icon_color = icon_color

        self._build_ui()
        self._apply_style()

    @property
    def category_key(self) -> str:
        return self._category_key

    def _build_ui(self):
        """Создает UI элемента"""
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Иконка категории (опционально)
        if self._icon_name:
            try:
                icon = qta.icon(self._icon_name, color=self._icon_color)
                icon_label = QLabel()
                icon_label.setPixmap(icon.pixmap(18, 18))
                icon_label.setFixedSize(18, 18)
                layout.addWidget(icon_label)
            except Exception:
                pass  # Игнорируем ошибки иконок

        # Название категории
        self._name_label = QLabel(self._name)
        self._name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self._name_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        layout.addWidget(self._name_label)

        # Описание (protocol|ports)
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setFont(QFont("Segoe UI", 9))
            desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
            layout.addWidget(desc_label)

        # Растяжение
        layout.addStretch(1)

        # ComboBox для выбора стратегии
        self._combo = QComboBox()
        self._combo.setFixedWidth(180)
        self._combo.setFixedHeight(28)
        self._combo.setFont(QFont("Segoe UI", 9))
        self._apply_combo_style()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self._combo)

    def _apply_style(self):
        """Применяет стили к строке"""
        self.setStyleSheet("""
            StrategyRadioItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
            }
            StrategyRadioItem:hover {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                background: transparent;
            }
        """)

    def _apply_combo_style(self):
        """Применяет стили Windows 11 Fluent к ComboBox"""
        self._combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 2px 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: #33444E;
                color: #ffffff;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3d5058;
            }
            QScrollBar:vertical {
                width: 0px;
            }
        """)

    def load_strategies(self, strategies: dict):
        """Загружает стратегии в ComboBox.

        Args:
            strategies: {strategy_id: {'name': '...', 'label': '...'}}
        """
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("Отключено", "none")
        for sid, data in strategies.items():
            name = data.get('name', sid)
            self._combo.addItem(name, sid)
        self._combo.blockSignals(False)

    def _on_combo_changed(self, index):
        """Обработчик изменения ComboBox"""
        strategy_id = self._combo.currentData()
        if strategy_id is not None:
            self.selected.emit(self._category_key, strategy_id)

    def set_current_strategy(self, strategy_id: str):
        """Устанавливает текущую стратегию в ComboBox.

        Args:
            strategy_id: ID стратегии для выбора
        """
        index = self._combo.findData(strategy_id)
        if index >= 0:
            self._combo.blockSignals(True)
            self._combo.setCurrentIndex(index)
            self._combo.blockSignals(False)

    def get_current_strategy(self) -> str:
        """Возвращает ID текущей выбранной стратегии."""
        return self._combo.currentData() or "none"

    def set_visible_by_filter(self, visible: bool):
        """Устанавливает видимость (для фильтрации)"""
        self.setVisible(visible)
