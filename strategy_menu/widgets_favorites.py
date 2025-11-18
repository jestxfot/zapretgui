from PyQt6.QtWidgets import QToolButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .widgets import CompactStrategyItem

# Глобальный кэш стилей (создается один раз)
_STYLE_CACHE = {
    'favorite_active': """
        QToolButton {
            border: none;
            background: transparent;
            color: #ffd700;
            font-size: 16pt;
            font-weight: bold;
            padding: 0px;
            qproperty-iconSize: 20px 20px;
        }
        QToolButton:hover {
            background: rgba(255, 215, 0, 0.2);
            border-radius: 4px;
        }
        QToolButton:pressed {
            background: rgba(255, 215, 0, 0.3);
        }
    """,
    'favorite_inactive': """
        QToolButton {
            border: none;
            background: transparent;
            color: #666;
            font-size: 16pt;
            font-weight: normal;
            padding: 0px;
            qproperty-iconSize: 20px 20px;
        }
        QToolButton:hover {
            color: #ffd700;
            background: rgba(255, 215, 0, 0.1);
            border-radius: 4px;
        }
        QToolButton:pressed {
            background: rgba(255, 215, 0, 0.2);
        }
    """
}


class FavoriteCompactStrategyItem(CompactStrategyItem):
    """Компактный элемент стратегии с кнопкой избранного"""
    
    favoriteToggled = pyqtSignal(str, bool)  # (strategy_id, is_favorite)
    
    def __init__(self, strategy_id, strategy_data, category_key=None, parent=None):
        # Сохраняем категорию до вызова super().__init__()
        self.category_key = category_key
        
        # Проверяем избранное один раз
        from strategy_menu import is_favorite_strategy
        self.is_favorite = is_favorite_strategy(strategy_id, category_key)
        
        # Вызываем родительский конструктор
        super().__init__(strategy_id, strategy_data, parent)
        
        # Добавляем кнопку избранного
        self._add_favorite_button()
        
        # Устанавливаем свойство для CSS (быстрее чем перезапись стилей)
        self.setProperty("favorite", self.is_favorite)
        self.setProperty("selected", False)
        
        # Применяем глобальный стиль один раз
        self._apply_global_style()
    
    def _apply_global_style(self):
        """Применяет глобальный стиль с использованием свойств"""
        self.setStyleSheet("""
            FavoriteCompactStrategyItem {
                border: 1px solid #444;
                border-radius: 4px;
                padding: 0px;
                margin: 2px;
            }
            FavoriteCompactStrategyItem:hover {
                background: #3a3a3a;
                border: 1px solid #555;
            }
            FavoriteCompactStrategyItem[selected="true"] {
                border: 2px solid #2196F3;
                background: #2a2a3a;
            }
            FavoriteCompactStrategyItem[favorite="true"] {
                border: 1px solid #665500;
                background: #2a2a1a;
            }
            FavoriteCompactStrategyItem[favorite="true"]:hover {
                background: #3a3a2a;
                border: 1px solid #ffd700;
            }
            FavoriteCompactStrategyItem[selected="true"][favorite="true"] {
                border: 2px solid #2196F3;
                background: #2a2a3a;
            }
        """)
    
    def _add_favorite_button(self):
        """Добавляет кнопку избранного в существующий layout"""
        self.favorite_btn = QToolButton()
        self.favorite_btn.setFixedSize(25, 25)
        self.favorite_btn.setCheckable(True)
        self.favorite_btn.setChecked(self.is_favorite)
        
        # Используем кэшированный стиль
        self._update_favorite_icon()
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        
        # Вставляем кнопку
        if hasattr(self, 'main_layout') and self.main_layout:
            self.main_layout.insertWidget(1, self.favorite_btn)
        elif self.layout():
            self.layout().insertWidget(1, self.favorite_btn)
    
    def _update_favorite_icon(self):
        """Обновляет иконку кнопки избранного"""
        if self.is_favorite:
            self.favorite_btn.setText("★")
            self.favorite_btn.setToolTip("Удалить из избранных")
            self.favorite_btn.setStyleSheet(_STYLE_CACHE['favorite_active'])
        else:
            self.favorite_btn.setText("★")
            self.favorite_btn.setToolTip("Добавить в избранные")
            self.favorite_btn.setStyleSheet(_STYLE_CACHE['favorite_inactive'])
    
    def _toggle_favorite(self):
        """Переключает статус избранного"""
        from strategy_menu import toggle_favorite_strategy
        
        # Используем категорию при переключении
        is_now_favorite = toggle_favorite_strategy(self.strategy_id, self.category_key)
        
        # Обновляем состояние
        self.is_favorite = is_now_favorite
        self.favorite_btn.setChecked(is_now_favorite)
        
        # Обновляем через свойство
        self.setProperty("favorite", is_now_favorite)
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Обновляем иконку
        self._update_favorite_icon()
        
        # Испускаем сигнал
        self.favoriteToggled.emit(self.strategy_id, is_now_favorite)
    
    def on_radio_toggled(self, checked):
        """Переопределяем для обновления через свойства"""
        super().on_radio_toggled(checked)
        self.setProperty("selected", checked)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def mousePressEvent(self, event):
        """Обрабатываем клики с учетом кнопки избранного"""
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'favorite_btn'):
                btn_rect = self.favorite_btn.geometry()
                if not btn_rect.contains(event.pos()):
                    if hasattr(self, 'radio'):
                        self.radio.setChecked(True)
            else:
                if hasattr(self, 'radio'):
                    self.radio.setChecked(True)
        else:
            super().mousePressEvent(event)


# ✅ УБРАН StrategyWidgetPool - он вызывал краши!
# Qt сам управляет памятью виджетов через parent


def get_strategy_widget(strategy_id, strategy_data, category_key, parent=None):
    """
    Фабричная функция для создания виджета стратегии
    
    ВАЖНО: Каждый раз создается НОВЫЙ виджет!
    Qt автоматически удалит виджет когда удалится parent.
    """
    return FavoriteCompactStrategyItem(strategy_id, strategy_data, category_key, parent)