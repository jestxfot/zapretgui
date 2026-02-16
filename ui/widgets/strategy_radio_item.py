# ui/widgets/strategy_radio_item.py
"""
Кнопка категории для выбора стратегии в стиле Windows 11 Fluent Design.
При клике эмитит сигнал для открытия диалога выбора стратегии.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QCursor
import qtawesome as qta
from typing import Optional

from ui.theme import get_theme_tokens


class StrategyRadioItem(QFrame):
    """
    Кнопка категории для выбора стратегии.

    Структура:
    ┌─────────────────────────────────────────────────────────────────┐
    │ 🎬 YouTube TCP  |  TCP 443  |  ● Default Strategy              │
    └─────────────────────────────────────────────────────────────────┘

    При клике эмитит сигнал clicked(category_key) для открытия диалога.

    Signals:
        clicked(str): category_key при клике
    """

    clicked = pyqtSignal(str)

    def __init__(
        self,
        category_key: str,
        name: str,
        description: str = "",
        icon_name: Optional[str] = None,
        icon_color: str = "#2196F3",
        tooltip: str = "",
        list_type: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self._category_key = category_key
        self._name = name
        self._description = description
        self._icon_name = icon_name
        self._icon_color = icon_color
        self._tooltip = tooltip
        self._list_type = list_type
        self._icon_label = None

        # Текущая стратегия
        self._strategy_id = "none"
        self._strategy_name = "Отключено"
        self._pressed = False

        self._build_ui()
        self._apply_style()

        # Mark as interactive: prevents draggable titlebar/content wrappers
        # from interpreting clicks as window-drag.
        self.setProperty("clickable", True)
        self.setProperty("noDrag", True)

        # Устанавливаем тултип после построения UI
        # PyQt6 requires HTML for line breaks in tooltips
        if self._tooltip:
            self.setToolTip(self._tooltip.replace('\n', '<br>'))

    @property
    def category_key(self) -> str:
        return self._category_key

    def _build_ui(self):
        """Создает UI элемента"""
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Ensure background/border from global QSS is painted.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(10)

        # Иконка категории (опционально)
        if self._icon_name:
            try:
                self._icon_label = QLabel()
                self._icon_label.setFixedSize(18, 18)
                self._layout.addWidget(self._icon_label)
                self._apply_icon_color()
            except Exception:
                pass  # Игнорируем ошибки иконок

        # Название категории
        self._name_label = QLabel(self._name)
        name_font = QFont("Segoe UI", 10)
        name_font.setWeight(QFont.Weight.Medium)
        self._name_label.setFont(name_font)
        self._name_label.setProperty("tone", "primary")
        self._name_label.setStyleSheet("background: transparent;")
        self._layout.addWidget(self._name_label)

        # Описание (protocol | ports)
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setFont(QFont("Segoe UI", 9))
            desc_label.setProperty("tone", "muted")
            desc_label.setStyleSheet("background: transparent;")
            self._layout.addWidget(desc_label)

        # Badge для hostlist/ipset
        self._list_badge = None
        if self._list_type:
            self._ensure_list_badge()

        # Растяжение
        self._layout.addStretch(1)

        # Статус точка
        self._status_dot = QLabel()
        self._status_dot.setFont(QFont("Segoe UI", 9))
        self._status_dot.setStyleSheet("color: #888888; background: transparent;")
        self._status_dot.setText("●")
        self._layout.addWidget(self._status_dot)

        # Название стратегии
        self._strategy_label = QLabel("Отключено")
        self._strategy_label.setFont(QFont("Segoe UI", 9))
        self._strategy_label.setProperty("tone", "primary")
        self._strategy_label.setStyleSheet("background: transparent;")
        self._layout.addWidget(self._strategy_label)

    def _ensure_list_badge(self):
        if self._list_badge is None:
            self._list_badge = QLabel()
            # Insert badge before stretch (which is currently at the end of left section).
            insert_index = max(0, self._layout.count() - 1)
            self._layout.insertWidget(insert_index, self._list_badge)
        self._apply_list_badge()

    def _apply_list_badge(self):
        if not self._list_badge:
            return
        if not self._list_type:
            self._list_badge.hide()
            return

        self._list_badge.setText(self._list_type)
        if self._list_type == "hostlist":
            badge_bg = "#00B900"
        else:
            badge_bg = "#8B5CF6"
        self._list_badge.setStyleSheet(f"""
            QLabel {{
                background: {badge_bg};
                color: rgba(245, 245, 245, 0.95);
                border-radius: 8px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 600;
            }}
        """)
        self._list_badge.show()

    def _apply_style(self):
        """Применяет стили к кнопке"""
        # Colors/background are handled by global theme QSS.
        self.setStyleSheet("")

    def _apply_icon_color(self):
        """Обновляет цвет иконки категории по активности."""
        if not self._icon_name or self._icon_label is None:
            return
        try:
            tokens = get_theme_tokens()
            if self.is_active():
                color = self._icon_color
            else:
                # Inactive icons must stay visible in light theme.
                color = "#808080" if tokens.is_light else "#BFC5CF"
            icon = qta.icon(self._icon_name, color=color)
            self._icon_label.setPixmap(icon.pixmap(18, 18))
        except Exception:
            pass

    def set_strategy(self, strategy_id: str, strategy_name: str):
        """Устанавливает текущую стратегию.

        Args:
            strategy_id: ID стратегии ('none' для отключенной)
            strategy_name: Название стратегии для отображения
        """
        self._strategy_id = strategy_id
        self._strategy_name = strategy_name

        # Обновляем UI
        self._strategy_label.setText(strategy_name)

        # Обновляем цвет точки
        if self.is_active():
            self._status_dot.setStyleSheet("color: #6ccb5f; background: transparent;")
        else:
            self._status_dot.setStyleSheet("color: #888888; background: transparent;")

        # Неактивные категории показываем светло-серой иконкой.
        self._apply_icon_color()

    def set_list_type(self, list_type: str | None):
        """Updates the hostlist/ipset badge."""
        self._list_type = list_type
        if self._list_type:
            self._ensure_list_badge()
        elif self._list_badge:
            self._apply_list_badge()

    def get_strategy_id(self) -> str:
        """Возвращает текущий strategy_id."""
        return self._strategy_id

    def is_active(self) -> bool:
        """Возвращает True если стратегия активна (не 'none')."""
        return self._strategy_id != "none"

    def mousePressEvent(self, event):
        """Track press; emit click on release (Qt-like behavior)."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            try:
                event.accept()
            except Exception:
                pass
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            was_pressed = bool(self._pressed)
            self._pressed = False
            if was_pressed and self.rect().contains(event.position().toPoint()):
                self.clicked.emit(self._category_key)
                try:
                    event.accept()
                except Exception:
                    pass
        return super().mouseReleaseEvent(event)

    def leaveEvent(self, event):  # noqa: N802 (Qt override)
        self._pressed = False
        return super().leaveEvent(event)

    def set_visible_by_filter(self, visible: bool):
        """Устанавливает видимость (для фильтрации)"""
        self.setVisible(visible)
