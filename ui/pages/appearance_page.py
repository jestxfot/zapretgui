# ui/pages/appearance_page.py
"""Страница настроек оформления - темы"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QFrame, QGridLayout
)
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard


class ThemeCard(QFrame):
    """Карточка выбора темы"""
    
    def __init__(self, name: str, color: str, is_premium: bool = False, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.is_premium = is_premium
        self._selected = False
        self._hovered = False
        
        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("themeCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Цветовой прямоугольник
        color_widget = QWidget()
        color_widget.setFixedHeight(36)
        color_widget.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
        """)
        layout.addWidget(color_widget)
        
        # Название
        name_layout = QHBoxLayout()
        name_layout.setSpacing(4)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 10px;
        """)
        name_layout.addWidget(name_label)
        
        if is_premium:
            premium_icon = QLabel()
            premium_icon.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(10, 10))
            name_layout.addWidget(premium_icon)
            
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        self._update_style()
        
    def _update_style(self):
        if self._selected:
            border = "2px solid #60cdff"
            bg = "rgba(96, 205, 255, 0.15)"
        elif self._hovered:
            border = "1px solid rgba(255, 255, 255, 0.2)"
            bg = "rgba(255, 255, 255, 0.08)"
        else:
            border = "1px solid rgba(255, 255, 255, 0.1)"
            bg = "rgba(255, 255, 255, 0.04)"
            
        self.setStyleSheet(f"""
            QFrame#themeCard {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
            }}
        """)
        
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class AppearancePage(BasePage):
    """Страница настроек оформления"""
    
    def __init__(self, parent=None):
        super().__init__("Оформление", "Настройка внешнего вида приложения", parent)
        
        self._build_ui()
        
    def _build_ui(self):
        # Выбор темы
        self.add_section_title("Тема оформления")
        
        theme_card = SettingsCard()
        
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(12)
        
        # Описание
        desc = QLabel("Выберите тему оформления. Премиум-темы доступны подписчикам.")
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
        desc.setWordWrap(True)
        theme_layout.addWidget(desc)
        
        # Комбо-бокс выбора темы
        combo_layout = QHBoxLayout()
        combo_layout.setSpacing(12)
        
        combo_label = QLabel("Тема:")
        combo_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        combo_layout.addWidget(combo_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(200)
        self.theme_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 12px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: rgba(96, 205, 255, 0.3);
                color: #ffffff;
            }
        """)
        combo_layout.addWidget(self.theme_combo, 1)
        
        theme_layout.addLayout(combo_layout)
        theme_card.add_layout(theme_layout)
        
        self.add_widget(theme_card)
        
        self.add_spacing(16)
        
        # Премиум темы
        self.add_section_title("Премиум темы")
        
        premium_card = SettingsCard()
        
        premium_layout = QVBoxLayout()
        premium_layout.setSpacing(12)
        
        premium_desc = QLabel(
            "Дополнительные темы доступны подписчикам Zapret Premium. "
            "Включая AMOLED темы и уникальные стили."
        )
        premium_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        premium_desc.setWordWrap(True)
        premium_layout.addWidget(premium_desc)
        
        # Превью премиум тем
        preview_layout = QGridLayout()
        preview_layout.setSpacing(8)
        
        premium_themes = [
            ("AMOLED", "#000000"),
            ("РКН Тян", "#6375c6"),
            ("Pure Black", "#0a0a0a"),
        ]
        
        for i, (name, color) in enumerate(premium_themes):
            card = ThemeCard(name, color, is_premium=True)
            preview_layout.addWidget(card, 0, i)
            
        premium_layout.addLayout(preview_layout)
        
        # Кнопка подписки
        from ui.sidebar import ActionButton
        sub_btn_layout = QHBoxLayout()
        
        self.subscription_btn = ActionButton("Управление подпиской", "fa5s.star")
        self.subscription_btn.setFixedHeight(36)
        sub_btn_layout.addWidget(self.subscription_btn)
        
        sub_btn_layout.addStretch()
        premium_layout.addLayout(sub_btn_layout)
        
        premium_card.add_layout(premium_layout)
        self.add_widget(premium_card)
        
    def update_themes(self, themes: list, current_theme: str = None):
        """Обновляет список тем в комбо-боксе"""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItems(themes)
        
        if current_theme:
            index = self.theme_combo.findText(current_theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
                
        self.theme_combo.blockSignals(False)

