# ui/widgets/collapsible_group.py
"""
Сворачиваемые группы для группировки стратегий по сервисам.
Стиль Windows 11 Fluent Design.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QCursor
import qtawesome as qta


class CollapsibleServiceHeader(QFrame):
    """
    Заголовок сворачиваемой группы сервиса.

    Содержит:
    - Chevron иконку (вправо/вниз)
    - Название группы
    - Линию-разделитель

    Signals:
        toggled(str, bool): (group_key, is_expanded)
    """

    toggled = pyqtSignal(str, bool)

    def __init__(self, group_key: str, title: str, parent=None):
        super().__init__(parent)
        self._group_key = group_key
        self._title = title
        self._expanded = True
        self._build_ui()
        self._apply_style()

    @property
    def group_key(self) -> str:
        return self._group_key

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def _build_ui(self):
        """Создает UI заголовка"""
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(6)

        # Chevron иконка
        self._chevron = QLabel()
        self._update_chevron()
        self._chevron.setFixedSize(16, 16)
        layout.addWidget(self._chevron)

        # Название группы
        self._title_label = QLabel(self._title)
        self._title_label.setFont(QFont("Segoe UI Semibold", 10))
        layout.addWidget(self._title_label)

        # Линия-разделитель (растягивается)
        self._line = QFrame()
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border: none;
                max-height: 1px;
            }
        """)
        layout.addWidget(self._line, 1)

    def _apply_style(self):
        """Применяет стили"""
        self.setStyleSheet("""
            CollapsibleServiceHeader {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            CollapsibleServiceHeader:hover {
                background: rgba(255, 255, 255, 0.04);
            }
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                background: transparent;
            }
        """)

    def _update_chevron(self):
        """Обновляет иконку chevron"""
        icon_name = "fa5s.chevron-down" if self._expanded else "fa5s.chevron-right"
        icon = qta.icon(icon_name, color="rgba(255, 255, 255, 0.5)")
        self._chevron.setPixmap(icon.pixmap(12, 12))

    def mousePressEvent(self, event):
        """Обработчик клика - переключает состояние"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
        super().mousePressEvent(event)

    def toggle(self):
        """Переключает развернутое/свернутое состояние"""
        self._expanded = not self._expanded
        self._update_chevron()
        self.toggled.emit(self._group_key, self._expanded)

    def set_expanded(self, expanded: bool):
        """Устанавливает состояние (без эмита сигнала)"""
        if self._expanded != expanded:
            self._expanded = expanded
            self._update_chevron()


class CollapsibleGroup(QWidget):
    """
    Сворачиваемая группа с заголовком и контентом.

    Содержит:
    - CollapsibleServiceHeader
    - Контент-виджет (скрывается при сворачивании)

    Signals:
        toggled(str, bool): (group_key, is_expanded)
    """

    toggled = pyqtSignal(str, bool)

    def __init__(self, group_key: str, title: str, parent=None):
        super().__init__(parent)
        self._group_key = group_key
        self._content_widget = None
        self._build_ui(title)

    @property
    def group_key(self) -> str:
        return self._group_key

    @property
    def is_expanded(self) -> bool:
        return self._header.is_expanded

    @property
    def content_widget(self) -> QWidget:
        return self._content_widget

    def _build_ui(self, title: str):
        """Создает UI группы"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Заголовок
        self._header = CollapsibleServiceHeader(self._group_key, title, self)
        self._header.toggled.connect(self._on_header_toggled)
        layout.addWidget(self._header)

        # Контейнер для контента
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(20, 0, 0, 8)  # Отступ слева для иерархии
        self._content_layout.setSpacing(4)
        layout.addWidget(self._content_container)

    def _on_header_toggled(self, group_key: str, is_expanded: bool):
        """Обработчик переключения заголовка"""
        self._content_container.setVisible(is_expanded)
        self.toggled.emit(group_key, is_expanded)

    def set_content(self, widget: QWidget):
        """Устанавливает контент-виджет"""
        # Удаляем старый контент
        if self._content_widget:
            self._content_layout.removeWidget(self._content_widget)
            self._content_widget.deleteLater()

        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def add_widget(self, widget: QWidget):
        """Добавляет виджет в контент"""
        self._content_layout.addWidget(widget)

    def set_expanded(self, expanded: bool):
        """Устанавливает состояние сворачивания"""
        self._header.set_expanded(expanded)
        self._content_container.setVisible(expanded)

    def clear_content(self):
        """Очищает контент"""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._content_widget = None
