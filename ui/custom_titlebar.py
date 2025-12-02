# ui/custom_titlebar.py
"""
Кастомный titlebar для окна со скругленными углами и узкой рамкой.
"""
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, 
    QSizePolicy, QApplication, QMenuBar, QSpacerItem
)
from PyQt6.QtGui import QIcon, QFont, QMouseEvent, QPainter, QColor, QPen

import qtawesome as qta


# Стили для встроенного меню в titlebar
MENUBAR_STYLE = """
QMenuBar {
    background-color: transparent;
    color: #ffffff;
    border: none;
    padding: 0px;
    spacing: 0px;
    font-size: 11px;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QMenuBar::item {
    background-color: transparent;
    color: #ffffff;
    padding: 4px 10px;
    border-radius: 4px;
    margin: 2px 1px;
}

QMenuBar::item:selected {
    background-color: rgba(255, 255, 255, 0.1);
}

QMenuBar::item:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}

QMenu {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    color: #ffffff;
}

QMenu::item:selected {
    background-color: rgba(255, 255, 255, 0.1);
}

QMenu::separator {
    height: 1px;
    background-color: #3d3d3d;
    margin: 4px 8px;
}

QMenu::indicator {
    width: 16px;
    height: 16px;
    margin-left: 4px;
}
"""


class TitleBarButton(QPushButton):
    """Кнопка для titlebar с hover эффектом"""
    
    def __init__(self, icon_name: str, hover_color: str = "#555555", parent=None):
        super().__init__(parent)
        self.hover_color = hover_color
        self.normal_color = "transparent"
        self._hovered = False
        
        # Устанавливаем иконку
        self.setIcon(qta.icon(icon_name, color='white'))
        self.setIconSize(QSize(12, 12))
        
        # Фиксированный размер кнопки
        self.setFixedSize(36, 28)
        
        self._update_style()
        
    def _update_style(self):
        bg_color = self.hover_color if self._hovered else self.normal_color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 0px;
            }}
        """)
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class CloseButton(TitleBarButton):
    """Специальная кнопка закрытия с красным hover"""
    
    def __init__(self, parent=None):
        super().__init__('fa5s.times', '#e81123', parent)


class MinimizeButton(TitleBarButton):
    """Кнопка сворачивания"""
    
    def __init__(self, parent=None):
        super().__init__('fa5s.minus', '#555555', parent)


class MaximizeButton(TitleBarButton):
    """Кнопка максимизации/восстановления"""
    
    def __init__(self, parent=None):
        super().__init__('fa5s.square', '#555555', parent)
        self._is_maximized = False
        
    def set_maximized(self, maximized: bool):
        self._is_maximized = maximized
        icon_name = 'fa5s.clone' if maximized else 'fa5s.square'
        self.setIcon(qta.icon(icon_name, color='white'))


class CustomTitleBar(QWidget):
    """
    Кастомный titlebar для Frameless окна.
    Поддерживает перетаскивание, сворачивание, разворачивание и закрытие.
    Включает встроенный menubar.
    """
    
    # Сигналы
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    drag_started = pyqtSignal()  # Начало перемещения (для отключения Acrylic)
    drag_ended = pyqtSignal()    # Конец перемещения (для включения Acrylic)
    
    def __init__(self, parent=None, title: str = "Zapret 2 GUI", show_icon: bool = True):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self._window_pos = None
        self._is_moving = False
        self._menubar = None
        
        # Высота titlebar (узкая рамка)
        self.setFixedHeight(32)
        self.setObjectName("customTitleBar")
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)
        
        # Иконка приложения (слева)
        if show_icon:
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(20, 20)
            layout.addWidget(self.icon_label)
        
        # Растягиваемый спейсер слева от заголовка
        layout.addStretch(1)
        
        # Заголовок (по центру)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet("""
            QLabel#titleLabel {
                color: #ffffff;
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Растягиваемый спейсер справа от заголовка
        layout.addStretch(1)
        
        # Контейнер для кнопок управления окном (с явным родителем!)
        buttons_widget = QWidget(self)  # ✅ Родитель = self
        buttons_widget.setObjectName("titleBarButtons")
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)
        
        # Кнопки
        self.minimize_btn = MinimizeButton(self)
        self.maximize_btn = MaximizeButton(self)
        self.close_btn = CloseButton(self)
        
        # Подключаем сигналы
        self.minimize_btn.clicked.connect(self._on_minimize)
        self.maximize_btn.clicked.connect(self._on_maximize)
        self.close_btn.clicked.connect(self._on_close)
        
        buttons_layout.addWidget(self.minimize_btn)
        buttons_layout.addWidget(self.maximize_btn)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addWidget(buttons_widget)
        
        # Стиль titlebar
        self._apply_style()
        
    def set_menubar(self, menubar: QMenuBar):
        """Сохраняет ссылку на menubar (теперь он добавляется отдельно под titlebar)"""
        self._menubar = menubar
        
    def _apply_style(self, bg_color: str = "rgba(32, 32, 32, 0.98)", text_color: str = "#ffffff"):
        self.setStyleSheet(f"""
            QWidget#customTitleBar {{
                background-color: {bg_color};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QWidget#titleBarButtons {{
                background-color: transparent;
            }}
        """)
        self.title_label.setStyleSheet(f"""
            QLabel#titleLabel {{
                color: {text_color};
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
        """)
        
    def set_theme_colors(self, bg_color: str = "#1a1a1a", text_color: str = "#ffffff"):
        """Обновляет цвета titlebar в соответствии с темой"""
        self._apply_style(bg_color, text_color)
        
        # Обновляем стили menubar
        if self._menubar:
            is_light = text_color == "#000000"
            
            if is_light:
                # Светлая тема
                menu_style = """
                QMenuBar {
                    background-color: transparent;
                    color: #000000;
                    border: none;
                    padding: 0px;
                    spacing: 0px;
                    font-size: 11px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QMenuBar::item {
                    background-color: transparent;
                    color: #000000;
                    padding: 4px 10px;
                    border-radius: 4px;
                    margin: 2px 1px;
                }
                QMenuBar::item:selected {
                    background-color: rgba(0, 0, 0, 0.1);
                }
                QMenuBar::item:pressed {
                    background-color: rgba(0, 0, 0, 0.15);
                }
                QMenu {
                    background-color: #f5f5f5;
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 24px 6px 12px;
                    border-radius: 4px;
                    color: #000000;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 0, 0, 0.1);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #cccccc;
                    margin: 4px 8px;
                }
                """
            else:
                # Тёмная тема
                menu_bg = "#000000" if bg_color == "#000000" else "#2b2b2b"
                border_color = "#1a1a1a" if bg_color == "#000000" else "#3d3d3d"
                
                menu_style = f"""
                QMenuBar {{
                    background-color: transparent;
                    color: {text_color};
                    border: none;
                    padding: 0px;
                    spacing: 0px;
                    font-size: 11px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
                QMenuBar::item {{
                    background-color: transparent;
                    color: {text_color};
                    padding: 4px 10px;
                    border-radius: 4px;
                    margin: 2px 1px;
                }}
                QMenuBar::item:selected {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
                QMenuBar::item:pressed {{
                    background-color: rgba(255, 255, 255, 0.15);
                }}
                QMenu {{
                    background-color: {menu_bg};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 24px 6px 12px;
                    border-radius: 4px;
                    color: {text_color};
                }}
                QMenu::item:selected {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: {border_color};
                    margin: 4px 8px;
                }}
                """
            
            self._menubar.setStyleSheet(menu_style)
        
    def set_title(self, title: str):
        """Устанавливает заголовок окна"""
        self.title_label.setText(title)
        
    def set_icon(self, icon: QIcon):
        """Устанавливает иконку окна"""
        if hasattr(self, 'icon_label'):
            pixmap = icon.pixmap(QSize(16, 16))
            self.icon_label.setPixmap(pixmap)
            
    def set_maximized_state(self, maximized: bool):
        """Обновляет состояние кнопки максимизации"""
        self.maximize_btn.set_maximized(maximized)
        
    def _on_minimize(self):
        self.minimize_clicked.emit()
        if self.parent_window:
            self.parent_window.showMinimized()
            
    def _on_maximize(self):
        self.maximize_clicked.emit()
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.set_maximized(False)
            else:
                self.parent_window.showMaximized()
                self.maximize_btn.set_maximized(True)
                
    def _on_close(self):
        self.close_clicked.emit()
        if self.parent_window:
            self.parent_window.close()
            
    # Перетаскивание окна
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Не перетаскиваем если клик по кнопкам
            child = self.childAt(event.pos())
            if child and isinstance(child, TitleBarButton):
                event.ignore()
                return
            
            self._drag_pos = event.globalPosition().toPoint()
            self._window_pos = self.parent_window.pos()
            self._is_moving = True
            self.drag_started.emit()  # Отключаем Acrylic для производительности
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_moving and self._drag_pos is not None:
            # Если окно максимизировано, сначала восстанавливаем
            if self.parent_window.isMaximized():
                # Вычисляем относительную позицию клика
                old_width = self.parent_window.width()
                relative_x = self._drag_pos.x() - self.parent_window.x()
                
                self.parent_window.showNormal()
                self.maximize_btn.set_maximized(False)
                
                # Пересчитываем позицию после восстановления
                new_width = self.parent_window.width()
                ratio = new_width / old_width
                self._window_pos = QPoint(
                    int(self._drag_pos.x() - relative_x * ratio),
                    self._drag_pos.y() - 16  # половина высоты titlebar
                )
            
            # Вычисляем новую позицию
            delta = event.globalPosition().toPoint() - self._drag_pos
            new_pos = self._window_pos + delta
            self.parent_window.move(new_pos)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        was_moving = self._is_moving
        self._is_moving = False
        self._drag_pos = None
        self._window_pos = None
        if was_moving:
            self.drag_ended.emit()  # Включаем Acrylic обратно
        event.accept()
        
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Двойной клик для максимизации/восстановления"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            self._on_maximize()


class FramelessWindowMixin:
    """
    Миксин для добавления функционала frameless окна.
    Добавляет поддержку изменения размера окна за края.
    """
    
    RESIZE_MARGIN = 8  # Область для изменения размера (увеличена для удобства)
    
    def init_frameless(self):
        """Инициализация frameless режима"""
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._is_resizing = False
        self._was_maximized = False
        
        # Включаем отслеживание мыши для главного окна
        self.setMouseTracking(True)
        
        # Включаем отслеживание мыши для всех дочерних виджетов
        def enable_mouse_tracking(widget):
            widget.setMouseTracking(True)
            for child in widget.findChildren(QWidget):
                child.setMouseTracking(True)
        
        enable_mouse_tracking(self)
        
    def showMaximized(self):
        """Переопределяем для обновления стилей при максимизации"""
        self._was_maximized = True
        self._update_border_radius(False)
        super().showMaximized()
        
    def showNormal(self):
        """Переопределяем для восстановления скругленных углов"""
        self._was_maximized = False
        self._update_border_radius(True)
        super().showNormal()
        
    def _update_border_radius(self, enable_radius: bool):
        """Обновляет стили скругленных углов"""
        if not hasattr(self, 'container') or not hasattr(self, 'title_bar'):
            return
            
        radius = 10 if enable_radius else 0
        
        # Получаем текущие цвета из стиля контейнера
        current_style = self.container.styleSheet()
        
        # Обновляем радиус в стиле контейнера
        import re
        
        # Извлекаем текущие цвета
        bg_match = re.search(r'background-color:\s*([^;]+);', current_style)
        border_match = re.search(r'border:\s*([^;]+);', current_style)
        
        bg_color = bg_match.group(1).strip() if bg_match else "rgba(30, 30, 30, 240)"
        border_style = border_match.group(1).strip() if border_match else "1px solid rgba(80, 80, 80, 200)"
        
        self.container.setStyleSheet(f"""
            QFrame#mainContainer {{
                background-color: {bg_color};
                border-radius: {radius}px;
                border: {border_style};
            }}
        """)
        
        # Обновляем titlebar
        title_radius = radius if enable_radius else 0
        self.title_bar.setStyleSheet(f"""
            QWidget#customTitleBar {{
                background-color: rgba(26, 26, 26, 240);
                border-top-left-radius: {title_radius}px;
                border-top-right-radius: {title_radius}px;
            }}
            QWidget#titleBarButtons {{
                background-color: transparent;
            }}
        """)
        
    def get_resize_edge(self, pos: QPoint) -> str | None:
        """Определяет край окна для изменения размера"""
        rect = self.rect()
        margin = self.RESIZE_MARGIN
        
        x, y = pos.x(), pos.y()
        width, height = rect.width(), rect.height()
        
        # Определяем край
        left = x < margin
        right = x > width - margin
        top = y < margin
        bottom = y > height - margin
        
        if top and left:
            return 'top-left'
        elif top and right:
            return 'top-right'
        elif bottom and left:
            return 'bottom-left'
        elif bottom and right:
            return 'bottom-right'
        elif left:
            return 'left'
        elif right:
            return 'right'
        elif top:
            return 'top'
        elif bottom:
            return 'bottom'
        
        return None
        
    def update_cursor_for_edge(self, edge: str | None):
        """Обновляет курсор в зависимости от края"""
        cursors = {
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor,
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            'top-left': Qt.CursorShape.SizeFDiagCursor,
            'bottom-right': Qt.CursorShape.SizeFDiagCursor,
            'top-right': Qt.CursorShape.SizeBDiagCursor,
            'bottom-left': Qt.CursorShape.SizeBDiagCursor,
        }
        
        if edge and edge in cursors:
            self.setCursor(cursors[edge])
        else:
            self.unsetCursor()
            
    def handle_resize_mouse_press(self, event: QMouseEvent) -> bool:
        """Обрабатывает нажатие мыши для resize. Возвращает True если начат resize."""
        if event.button() != Qt.MouseButton.LeftButton:
            return False
            
        edge = self.get_resize_edge(event.pos())
        if edge:
            self._resize_edge = edge
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_geometry = self.geometry()
            self._is_resizing = True
            return True
        
        return False
        
    def handle_resize_mouse_move(self, event: QMouseEvent) -> bool:
        """Обрабатывает движение мыши для resize. Возвращает True если в процессе resize."""
        if self._is_resizing and self._resize_edge:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = self._resize_start_geometry
            
            new_x = geo.x()
            new_y = geo.y()
            new_width = geo.width()
            new_height = geo.height()
            
            min_width = self.minimumWidth()
            min_height = self.minimumHeight()
            
            edge = self._resize_edge
            
            if 'left' in edge:
                new_width = max(min_width, geo.width() - delta.x())
                if new_width != min_width:
                    new_x = geo.x() + delta.x()
                    
            if 'right' in edge:
                new_width = max(min_width, geo.width() + delta.x())
                
            if 'top' in edge:
                new_height = max(min_height, geo.height() - delta.y())
                if new_height != min_height:
                    new_y = geo.y() + delta.y()
                    
            if 'bottom' in edge:
                new_height = max(min_height, geo.height() + delta.y())
                
            self.setGeometry(new_x, new_y, new_width, new_height)
            return True
        else:
            # Обновляем курсор
            edge = self.get_resize_edge(event.pos())
            self.update_cursor_for_edge(edge)
            
        return False
        
    def handle_resize_mouse_release(self, event: QMouseEvent):
        """Обрабатывает отпускание мыши для resize."""
        self._is_resizing = False
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geometry = None


def apply_rounded_corners_style(widget: QWidget, radius: int = 10):
    """
    Применяет стиль со скругленными углами к виджету.
    
    Args:
        widget: Виджет для применения стиля
        radius: Радиус скругления углов
    """
    current_style = widget.styleSheet()
    
    rounded_style = f"""
        QWidget#mainContainer {{
            background-color: #2b2b2b;
            border-radius: {radius}px;
            border: 1px solid #3d3d3d;
        }}
    """
    
    widget.setStyleSheet(current_style + rounded_style)

