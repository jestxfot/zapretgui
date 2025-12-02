# ui/pages/home_page.py
"""Главная страница - обзор состояния системы"""

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtGui import QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, StatusIndicator, ActionButton


class StatusCard(QFrame):
    """Большая карточка статуса на главной странице"""
    
    def __init__(self, icon_name: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setMinimumHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        
        # Верхняя строка: иконка + заголовок
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        
        # Иконка (объёмная с градиентом)
        self.icon_label = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap
            self.icon_label.setPixmap(fluent_pixmap(icon_name, 28))
        except:
            self.icon_label.setPixmap(qta.icon(icon_name, color='#60cdff').pixmap(28, 28))
        self.icon_label.setFixedSize(32, 32)
        top_layout.addWidget(self.icon_label)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                font-weight: 500;
            }
        """)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # Значение (большой текст)
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.value_label)
        
        # Дополнительная информация
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # Стиль карточки (Acrylic / Glass эффект)
        self.setStyleSheet("""
            QFrame#statusCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QFrame#statusCard:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
    def set_value(self, value: str, info: str = ""):
        self.value_label.setText(value)
        self.info_label.setText(info)
        
    def set_status_color(self, status: str):
        """Меняет цвет иконки по статусу"""
        colors = {
            'running': '#6ccb5f',
            'stopped': '#ff6b6b',
            'warning': '#ffc107',
            'neutral': '#60cdff',
        }
        color = colors.get(status, colors['neutral'])
        # Для простоты меняем только цвет value_label
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 18px;
                font-weight: 600;
            }}
        """)


class HomePage(BasePage):
    """Главная страница - обзор состояния"""
    
    def __init__(self, parent=None):
        super().__init__("Главная", "Обзор состояния Zapret", parent)
        
        self._build_ui()
        
    def _build_ui(self):
        # Сетка карточек статуса
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Карточка статуса DPI
        self.dpi_status_card = StatusCard("fa5s.shield-alt", "Статус Zapret")
        self.dpi_status_card.set_value("Проверка...", "Определение состояния")
        cards_layout.addWidget(self.dpi_status_card, 0, 0)
        
        # Карточка стратегии
        self.strategy_card = StatusCard("fa5s.cog", "Текущая стратегия")
        self.strategy_card.set_value("Не выбрана", "Выберите стратегию обхода")
        cards_layout.addWidget(self.strategy_card, 0, 1)
        
        # Карточка автозапуска
        self.autostart_card = StatusCard("fa5s.rocket", "Автозапуск")
        self.autostart_card.set_value("Отключён", "Запускайте вручную")
        cards_layout.addWidget(self.autostart_card, 1, 0)
        
        # Карточка подписки
        self.subscription_card = StatusCard("fa5s.star", "Подписка")
        self.subscription_card.set_value("Free", "Базовые функции")
        cards_layout.addWidget(self.subscription_card, 1, 1)
        
        cards_widget = QWidget(self.content)  # ✅ Явный родитель
        cards_widget.setLayout(cards_layout)
        self.add_widget(cards_widget)
        
        self.add_spacing(8)
        
        # Быстрые действия
        self.add_section_title("Быстрые действия")
        
        actions_card = SettingsCard()
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Кнопка запуска
        self.start_btn = ActionButton("Запустить", "fa5s.play", accent=True)
        actions_layout.addWidget(self.start_btn)
        
        # Кнопка остановки
        self.stop_btn = ActionButton("Остановить", "fa5s.stop")
        self.stop_btn.setVisible(False)
        actions_layout.addWidget(self.stop_btn)
        
        # Кнопка теста
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        actions_layout.addWidget(self.test_btn)
        
        # Кнопка папки
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        actions_layout.addWidget(self.folder_btn)
        
        actions_layout.addStretch()
        actions_card.add_layout(actions_layout)
        self.add_widget(actions_card)
        
        self.add_spacing(8)
        
        # Статусная строка
        self.add_section_title("Статус")
        
        status_card = SettingsCard()
        self.status_indicator = StatusIndicator()
        self.status_indicator.set_status("Готов к работе", "neutral")
        status_card.add_widget(self.status_indicator)
        self.add_widget(status_card)
        
        self.add_spacing(12)
        
        # Блок Premium
        self._build_premium_block()
        
    def update_dpi_status(self, is_running: bool, strategy_name: str = None):
        """Обновляет отображение статуса DPI"""
        if is_running:
            self.dpi_status_card.set_value("Запущен", "Обход блокировок активен")
            self.dpi_status_card.set_status_color('running')
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(True)
        else:
            self.dpi_status_card.set_value("Остановлен", "Нажмите Запустить")
            self.dpi_status_card.set_status_color('stopped')
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(False)
            
        if strategy_name:
            # Обрезаем длинные названия для карточки
            display_name = self._truncate_strategy_name(strategy_name)
            self.strategy_card.set_value(display_name, "Активная стратегия")
    
    def _truncate_strategy_name(self, name: str, max_items: int = 2) -> str:
        """Обрезает длинное название стратегии для карточки"""
        if not name or name in ("Не выбрана", "Прямой запуск"):
            return name
            
        # Если это список категорий через запятую
        if ", " in name:
            parts = name.split(", ")
            # Проверяем есть ли "+N" в конце
            extra = ""
            if parts and parts[-1].startswith("+"):
                extra_num = int(parts[-1][1:]) if parts[-1][1:].isdigit() else 0
                parts = parts[:-1]
                extra_num += len(parts) - max_items
                if extra_num > 0:
                    extra = f" +{extra_num}"
            elif len(parts) > max_items:
                extra = f" +{len(parts) - max_items}"
                
            if len(parts) > max_items:
                return ", ".join(parts[:max_items]) + extra
            elif extra:
                return ", ".join(parts) + extra
                
        return name
            
    def update_autostart_status(self, enabled: bool):
        """Обновляет отображение статуса автозапуска"""
        if enabled:
            self.autostart_card.set_value("Включён", "Запускается с Windows")
            self.autostart_card.set_status_color('running')
        else:
            self.autostart_card.set_value("Отключён", "Запускайте вручную")
            self.autostart_card.set_status_color('neutral')
            
    def update_subscription_status(self, is_premium: bool, days: int = None):
        """Обновляет отображение статуса подписки"""
        if is_premium:
            if days:
                self.subscription_card.set_value("Premium", f"Осталось {days} дней")
            else:
                self.subscription_card.set_value("Premium", "Все функции доступны")
            self.subscription_card.set_status_color('running')
        else:
            self.subscription_card.set_value("Free", "Базовые функции")
            self.subscription_card.set_status_color('neutral')
            
    def set_status(self, text: str, status: str = "neutral"):
        """Устанавливает текст статусной строки"""
        self.status_indicator.set_status(text, status)
        
    def _build_premium_block(self):
        """Создает блок Premium на главной странице"""
        premium_card = SettingsCard()
        
        premium_layout = QHBoxLayout()
        premium_layout.setSpacing(16)
        
        # Иконка звезды
        star_label = QLabel()
        star_label.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(32, 32))
        star_label.setFixedSize(40, 40)
        premium_layout.addWidget(star_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title = QLabel("Zapret Premium")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        text_layout.addWidget(title)
        
        desc = QLabel("Дополнительные темы, приоритетная поддержка и VPN-сервис")
        desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        desc.setWordWrap(True)
        text_layout.addWidget(desc)
        
        premium_layout.addLayout(text_layout, 1)
        
        # Кнопка Premium
        self.premium_link_btn = ActionButton("Подробнее", "fa5s.arrow-right")
        self.premium_link_btn.setFixedHeight(36)
        premium_layout.addWidget(self.premium_link_btn)
        
        premium_card.add_layout(premium_layout)
        self.add_widget(premium_card)

