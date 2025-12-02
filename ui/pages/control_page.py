# ui/pages/control_page.py
"""Страница управления - запуск/остановка DPI"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, SettingsRow, ActionButton, StatusIndicator


class BigActionButton(ActionButton):
    """Большая кнопка действия"""
    
    def __init__(self, text: str, icon_name: str = None, accent: bool = False, parent=None):
        super().__init__(text, icon_name, accent, parent)
        self.setFixedHeight(48)
        self.setIconSize(QSize(20, 20))
        
    def _update_style(self):
        if self.accent:
            # Акцентная кнопка - голубая
            if self._hovered:
                bg = "rgba(96, 205, 255, 0.9)"
            else:
                bg = "#60cdff"
            text_color = "#000000"
        else:
            # Обычная кнопка - нейтральная
            if self._hovered:
                bg = "rgba(255, 255, 255, 0.15)"
            else:
                bg = "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: {text_color};
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)


class StopButton(BigActionButton):
    """Кнопка остановки (нейтральная)"""
    
    def _update_style(self):
        # Нейтральная серая кнопка
        if self._hovered:
            bg = "rgba(255, 255, 255, 0.15)"
        else:
            bg = "rgba(255, 255, 255, 0.08)"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)


class ControlPage(BasePage):
    """Страница управления DPI"""
    
    def __init__(self, parent=None):
        super().__init__("Управление", "Запуск и остановка обхода блокировок", parent)
        
        self._build_ui()
        
    def _build_ui(self):
        # Статус работы
        self.add_section_title("Статус работы")
        
        status_card = SettingsCard()
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)
        
        # Иконка статуса (объёмная)
        self.status_icon = QLabel()
        try:
            from ui.fluent_icons import status_pixmap
            self.status_icon.setPixmap(status_pixmap('neutral', 16))
        except:
            self.status_icon.setPixmap(qta.icon('fa5s.circle', color='#888888').pixmap(16, 16))
        self.status_icon.setFixedSize(20, 20)
        status_layout.addWidget(self.status_icon)
        
        # Текст статуса
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(2)
        
        self.status_title = QLabel("Проверка...")
        self.status_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
            }
        """)
        status_text_layout.addWidget(self.status_title)
        
        self.status_desc = QLabel("Определение состояния процесса")
        self.status_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        status_text_layout.addWidget(self.status_desc)
        
        status_layout.addLayout(status_text_layout, 1)
        status_card.add_layout(status_layout)
        self.add_widget(status_card)
        
        self.add_spacing(16)
        
        # Управление
        self.add_section_title("Управление Zapret")
        
        control_card = SettingsCard()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        self.start_btn = BigActionButton("Запустить Zapret", "fa5s.play", accent=True)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = StopButton("Остановить Zapret", "fa5s.stop")
        self.stop_btn.setVisible(False)
        buttons_layout.addWidget(self.stop_btn)
        
        buttons_layout.addStretch()
        control_card.add_layout(buttons_layout)
        
        self.add_widget(control_card)
        
        self.add_spacing(16)
        
        # Текущая стратегия
        self.add_section_title("Текущая стратегия")
        
        strategy_card = SettingsCard()
        
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(12)
        
        self.strategy_icon = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap
            self.strategy_icon.setPixmap(fluent_pixmap('fa5s.cog', 20))
        except:
            self.strategy_icon.setPixmap(qta.icon('fa5s.cog', color='#60cdff').pixmap(20, 20))
        self.strategy_icon.setFixedSize(24, 24)
        strategy_layout.addWidget(self.strategy_icon)
        
        strategy_text_layout = QVBoxLayout()
        strategy_text_layout.setSpacing(2)
        
        self.strategy_label = QLabel("Не выбрана")
        self.strategy_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        strategy_text_layout.addWidget(self.strategy_label)
        
        self.strategy_desc = QLabel("Выберите стратегию в разделе «Стратегии»")
        self.strategy_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
            }
        """)
        strategy_text_layout.addWidget(self.strategy_desc)
        
        strategy_layout.addLayout(strategy_text_layout, 1)
        strategy_card.add_layout(strategy_layout)
        
        self.add_widget(strategy_card)
        
        self.add_spacing(16)
        
        # Дополнительные действия
        self.add_section_title("Дополнительно")
        
        extra_card = SettingsCard()
        
        extra_layout = QHBoxLayout()
        extra_layout.setSpacing(8)
        
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        extra_layout.addWidget(self.test_btn)
        
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        extra_layout.addWidget(self.folder_btn)
        
        extra_layout.addStretch()
        extra_card.add_layout(extra_layout)
        
        self.add_widget(extra_card)
        
    def update_status(self, is_running: bool):
        """Обновляет отображение статуса"""
        try:
            from ui.fluent_icons import status_pixmap
            use_fluent = True
        except:
            use_fluent = False
            
        if is_running:
            self.status_title.setText("Zapret работает")
            self.status_desc.setText("Обход блокировок активен")
            if use_fluent:
                self.status_icon.setPixmap(status_pixmap('running', 16))
            else:
                self.status_icon.setPixmap(qta.icon('fa5s.circle', color='#6ccb5f').pixmap(16, 16))
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(True)
        else:
            self.status_title.setText("Zapret остановлен")
            self.status_desc.setText("Нажмите «Запустить» для активации")
            if use_fluent:
                self.status_icon.setPixmap(status_pixmap('stopped', 16))
            else:
                self.status_icon.setPixmap(qta.icon('fa5s.circle', color='#ff6b6b').pixmap(16, 16))
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(False)
            
    def update_strategy(self, name: str):
        """Обновляет отображение текущей стратегии"""
        if name and name != "Автостарт DPI отключен":
            self.strategy_label.setText(name)
            self.strategy_desc.setText("Активная стратегия обхода")
        else:
            self.strategy_label.setText("Не выбрана")
            self.strategy_desc.setText("Выберите стратегию в разделе «Стратегии»")

