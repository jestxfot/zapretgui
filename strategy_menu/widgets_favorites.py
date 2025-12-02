from PyQt6.QtWidgets import QToolButton
from PyQt6.QtCore import Qt, pyqtSignal

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
    """Компактный элемент стратегии со звёздочкой избранного слева"""
    
    favoriteToggled = pyqtSignal(str, bool)
    
    def __init__(self, strategy_id, strategy_data, category_key=None, parent=None):
        self.category_key = category_key
        
        from strategy_menu import is_favorite_strategy
        self.is_favorite = is_favorite_strategy(strategy_id, category_key)
        
        super().__init__(strategy_id, strategy_data, parent)
        self._add_favorite_button()
    
    def _apply_style(self, selected):
        """Стиль с учётом избранного"""
        if selected:
            self.setStyleSheet(_STYLE_SELECTED)
        elif self.is_favorite:
            self.setStyleSheet(_STYLE_FAVORITE)
        else:
            self.setStyleSheet(_STYLE_NORMAL)
    
    def _add_favorite_button(self):
        """Добавляет звёздочку избранного слева (вместо кружка)"""
        self.favorite_btn = QToolButton()
        self.favorite_btn.setFixedSize(16, 16)
        self.favorite_btn.setCheckable(True)
        self.favorite_btn.setChecked(self.is_favorite)
        self.favorite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_favorite_style()
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        
        # Вставляем слева (перед текстом)
        if hasattr(self, 'main_layout') and self.main_layout:
            self.main_layout.insertWidget(0, self.favorite_btn)
    
    def _update_favorite_style(self):
        """Стиль звёздочки"""
        if self.is_favorite:
            self.favorite_btn.setText("★")
            self.favorite_btn.setToolTip("Убрать из избранных")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: #ffd700;
                    font-size: 12px;
                }
                QToolButton:hover {
                    background: rgba(255, 215, 0, 0.2);
                    border-radius: 3px;
                }
            """)
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setToolTip("В избранные")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.15);
                    font-size: 12px;
                }
                QToolButton:hover {
                    color: #ffd700;
                    background: rgba(255, 215, 0, 0.1);
                    border-radius: 3px;
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
    
    def mousePressEvent(self, event):
        """Клик с учётом кнопки избранного"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем не кликнули ли по звёздочке
            if hasattr(self, 'favorite_btn'):
                btn_rect = self.favorite_btn.geometry()
                if not btn_rect.contains(event.pos()):
                    self.radio.setChecked(True)
            else:
                self.radio.setChecked(True)
        elif event.button() == Qt.MouseButton.RightButton:
            from .args_preview_dialog import preview_manager
            preview_manager.show_preview(self, self.strategy_id, self.strategy_data)


def get_strategy_widget(strategy_id, strategy_data, category_key, parent=None):
    """Фабричная функция для создания виджета стратегии"""
    return FavoriteCompactStrategyItem(strategy_id, strategy_data, category_key, parent)
