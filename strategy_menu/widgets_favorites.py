from PyQt6.QtWidgets import QToolButton
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QPoint

from .widgets import CompactStrategyItem


# Стили для избранных
_STYLE_SELECTED = """
    FavoriteCompactStrategyItem {
        background: rgba(96, 205, 255, 0.15);
        border: 1px solid rgba(96, 205, 255, 0.5);
        border-radius: 4px;
    }
"""
_STYLE_FAVORITE = """
    FavoriteCompactStrategyItem {
        background: rgba(255, 215, 0, 0.08);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 4px;
    }
    FavoriteCompactStrategyItem:hover {
        background: rgba(255, 215, 0, 0.12);
        border-color: rgba(255, 215, 0, 0.4);
    }
"""
_STYLE_NORMAL = """
    FavoriteCompactStrategyItem {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 4px;
    }
    FavoriteCompactStrategyItem:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.15);
    }
"""


class FavoriteCompactStrategyItem(CompactStrategyItem):
    """Компактный элемент стратегии со звёздочкой избранного и hover tooltip"""
    
    favoriteToggled = pyqtSignal(str, bool)
    
    def __init__(self, strategy_id, strategy_data, category_key=None, parent=None):
        self.category_key = category_key
        
        from strategy_menu import is_favorite_strategy
        self.is_favorite = is_favorite_strategy(strategy_id, category_key)
        
        super().__init__(strategy_id, strategy_data, parent)
        self._add_favorite_button()
        
        # Включаем отслеживание мыши для hover tooltip
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
    
    def _apply_style(self, selected):
        """Стиль с учётом избранного"""
        if selected:
            self.setStyleSheet(_STYLE_SELECTED)
        elif self.is_favorite:
            self.setStyleSheet(_STYLE_FAVORITE)
        else:
            self.setStyleSheet(_STYLE_NORMAL)
    
    def _add_favorite_button(self):
        """Добавляет звёздочку избранного слева (вынесена за пределы основного контента)"""
        self.favorite_btn = QToolButton()
        self.favorite_btn.setFixedSize(28, 28)
        self.favorite_btn.setCheckable(True)
        self.favorite_btn.setChecked(self.is_favorite)
        self.favorite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_favorite_style()
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        
        if hasattr(self, 'main_layout') and self.main_layout:
            # Вставляем звезду первой с отрицательным отступом чтобы была левее
            self.main_layout.insertWidget(0, self.favorite_btn)
            self.main_layout.setContentsMargins(2, 4, 10, 4)  # Меньше слева
    
    def _update_favorite_style(self):
        """Стиль звёздочки - крупная и заметная"""
        if self.is_favorite:
            self.favorite_btn.setText("★")
            self.favorite_btn.setToolTip("Убрать из избранных")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: #ffc107;
                    font-size: 20px;
                    padding: 0;
                    margin: 0;
                }
                QToolButton:hover {
                    color: #ffca28;
                }
            """)
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setToolTip("Добавить в избранные")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.15);
                    font-size: 20px;
                    padding: 0;
                    margin: 0;
                }
                QToolButton:hover {
                    color: #ffc107;
                }
            """)
    
    def _toggle_favorite(self):
        """Переключает избранное"""
        from strategy_menu import toggle_favorite_strategy
        
        self.is_favorite = toggle_favorite_strategy(self.strategy_id, self.category_key)
        self.favorite_btn.setChecked(self.is_favorite)
        self._update_favorite_style()
        self._apply_style(self.is_selected)
        self.favoriteToggled.emit(self.strategy_id, self.is_favorite)
    
    def _on_toggled(self, checked):
        """Переопределяем переключение"""
        self.is_selected = checked
        self._apply_style(checked)
        if checked:
            self.clicked.emit(self.strategy_id)
    
    def enterEvent(self, event):
        """При наведении мыши показываем hover tooltip"""
        try:
            from .hover_tooltip import tooltip_manager
            
            pos = self.mapToGlobal(QPoint(self.width() + 10, 0))
            tooltip_manager.show_tooltip(pos, self.strategy_data, self.strategy_id, delay=600)
        except Exception:
            pass
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """При уходе мыши скрываем tooltip"""
        try:
            from .hover_tooltip import tooltip_manager
            tooltip_manager.hide_tooltip(delay=100)
        except Exception:
            pass
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Клик с учётом кнопки избранного"""
        # Скрываем tooltip при клике
        try:
            from .hover_tooltip import tooltip_manager
            tooltip_manager.hide_immediately()
        except Exception:
            pass
        
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'favorite_btn'):
                btn_rect = self.favorite_btn.geometry()
                if not btn_rect.contains(event.pos()):
                    self.radio.setChecked(True)
            else:
                self.radio.setChecked(True)
        super().mousePressEvent(event)


def get_strategy_widget(strategy_id, strategy_data, category_key, parent=None):
    """Фабричная функция для создания виджета стратегии"""
    return FavoriteCompactStrategyItem(strategy_id, strategy_data, category_key, parent)
