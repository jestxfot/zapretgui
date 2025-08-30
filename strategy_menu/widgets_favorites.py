# strategy_menu/widgets_favorites.py

from PyQt6.QtWidgets import QToolButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .widgets import CompactStrategyItem


class FavoriteCompactStrategyItem(CompactStrategyItem):
    """Компактный виджет стратегии с поддержкой избранных для Direct режима"""
    
    favoriteToggled = pyqtSignal(str, bool)  # strategy_id, is_favorite
    
    def __init__(self, strategy_id, strategy_data, parent=None):
        super().__init__(strategy_id, strategy_data, parent)
        
        # Проверяем, является ли стратегия избранной
        from strategy_menu import is_favorite_strategy
        self.is_favorite = is_favorite_strategy(strategy_id)
        
        # Добавляем кнопку избранного
        self._add_favorite_button()
        
        # Обновляем стили
        self._update_styles()
    
    def _add_favorite_button(self):
        """Добавляет кнопку избранного в layout"""
        # Получаем основной layout
        main_layout = self.layout()
        
        # Создаем кнопку
        self.favorite_btn = QToolButton()
        self.favorite_btn.setFixedSize(24, 24)
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.favorite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Вставляем кнопку в начало layout
        main_layout.insertWidget(0, self.favorite_btn)
        
        # Обновляем внешний вид кнопки
        self.update_favorite_button()
    
    def update_favorite_button(self):
        """Обновляет внешний вид кнопки избранного"""
        if self.is_favorite:
            self.favorite_btn.setText("⭐")
            self.favorite_btn.setToolTip("Удалить из избранных")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: #ffd700;
                    font-size: 14pt;
                }
                QToolButton:hover {
                    background: rgba(255, 215, 0, 0.2);
                    border-radius: 4px;
                }
                QToolButton:pressed {
                    background: rgba(255, 215, 0, 0.3);
                }
            """)
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setToolTip("Добавить в избранные")
            self.favorite_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    color: #666;
                    font-size: 14pt;
                }
                QToolButton:hover {
                    color: #ffd700;
                    background: rgba(255, 215, 0, 0.1);
                    border-radius: 4px;
                }
                QToolButton:pressed {
                    background: rgba(255, 215, 0, 0.2);
                }
            """)
    
    def toggle_favorite(self):
        """Переключает статус избранной стратегии"""
        from strategy_menu import toggle_favorite_strategy
        self.is_favorite = toggle_favorite_strategy(self.strategy_id)
        self.update_favorite_button()
        self._update_styles()
        self.favoriteToggled.emit(self.strategy_id, self.is_favorite)
    
    def _update_styles(self):
        """Обновляет стили виджета с учетом избранного"""
        if self.is_selected:
            self.setStyleSheet("""
                CompactStrategyItem {
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                    background: #2a2a3a;
                    padding: 0px;
                    margin: 2px;
                }
            """)
        elif self.is_favorite:
            self.setStyleSheet("""
                CompactStrategyItem {
                    border: 1px solid #665500;
                    border-radius: 4px;
                    background: #2a2a1a;
                    padding: 0px;
                    margin: 2px;
                }
                CompactStrategyItem:hover {
                    background: #3a3a2a;
                    border: 1px solid #ffd700;
                }
            """)
        else:
            self.setStyleSheet("""
                CompactStrategyItem {
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 0px;
                    margin: 2px;
                }
                CompactStrategyItem:hover {
                    background: #3a3a3a;
                    border: 1px solid #555;
                }
            """)
    
    def on_radio_toggled(self, checked):
        """Переопределяем для обновления стилей с учетом избранного"""
        super().on_radio_toggled(checked)
        if not checked:
            self._update_styles()
    
    def mousePressEvent(self, event):
        """Обрабатываем клики с учетом кнопки избранного"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, что клик не на кнопке избранного
            btn_rect = self.favorite_btn.geometry()
            if not btn_rect.contains(event.pos()):
                self.radio.setChecked(True)
        else:
            super().mousePressEvent(event)