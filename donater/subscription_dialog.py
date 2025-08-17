# subscription_dialog.py - стабильная версия без багов с размером

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QProgressBar, QMessageBox, QWidget, 
    QFrame, QStackedWidget, QApplication, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QLinearGradient
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any

from .donate import SimpleDonateChecker, RegistryManager

class WorkerThread(QThread):
    """Поток для выполнения блокирующих операций"""
    
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, target, args=None, kwargs=None):
        super().__init__()
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        
    def run(self):
        try:
            self.progress_updated.emit(10, "Подключение к серверу...")
            result = self.target(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class StyledWidget(QWidget):
    """Базовый виджет со стилями"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

class Card(QFrame):
    """Простая карточка без сложных эффектов"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")

        self.setStyleSheet("")  # Сброс унаследованных стилей (чтобы не было багов с окнами! добавлять всегда обязательно!)
        
class SubscriptionDialog(QDialog):
    """Главное окно управления подпиской"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checker = SimpleDonateChecker()
        self.current_thread = None
        
        # Стандартное окно без кастомизации
        self.setWindowTitle("Zapret Premium")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # Отключить изменение размера окна
        self.setSizeGripEnabled(False)
        
        # Установить политику размера
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Определяем тему
        self.is_dark_theme = self._is_dark_theme()
        
        # Инициализация UI
        self._init_ui()
        
        # Применяем стили
        self._apply_styles()

        # Определяем начальную страницу
        self._setup_initial_page()

        self.setFixedSize(550, 700)

    def sizeHint(self):
        """Фиксированный размер окна"""
        return QSize(550, 700)

    def minimumSizeHint(self):
        """Минимальный размер окна"""
        return QSize(550, 700)
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Контейнер для содержимого
        self.container = StyledWidget()
        self.container.setObjectName("Container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(0)
        
        # Стековый виджет для страниц
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.stack)
        
        main_layout.addWidget(self.container)
        
        # Создаем страницы
        self._create_pages()
    
    def _is_dark_theme(self) -> bool:
        """Определение темной темы"""
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        return bg_color.lightness() < 128
    
    def _get_colors(self) -> Dict[str, str]:
        """Получить цветовую схему"""
        if self.is_dark_theme:
            return {
                'bg': '#1a1a1a',
                'container': '#242424',
                'card': '#2d2d2d',
                'card_hover': '#353535',
                'text': '#ffffff',
                'text_secondary': '#a0a0a0',
                'border': '#3a3a3a',
                'accent': '#4a9eff',
                'accent_hover': '#357dd8',
                'accent_dark': '#2968c0',
                'error': '#ff4757',
                'warning': '#ffa502',
                'success': '#2ed573',
                'telegram': '#0088cc'
            }
        else:
            return {
                'bg': '#ffffff',
                'container': '#f8f9fa',
                'card': '#ffffff',
                'card_hover': '#f5f5f5',
                'text': '#2c3e50',
                'text_secondary': '#7f8c8d',
                'border': '#dfe4ea',
                'accent': '#3498db',
                'accent_hover': '#2980b9',
                'accent_dark': '#21618c',
                'error': '#e74c3c',
                'warning': '#f39c12',
                'success': '#27ae60',
                'telegram': '#0088cc'
            }
    
    def _apply_styles(self):
        """Применить стили"""
        colors = self._get_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg']};
            }}
            
            #Container {{
                background-color: {colors['container']};
            }}
            
            QLabel {{
                color: {colors['text']};
                background-color: transparent;
            }}
            
            QLabel[class="title"] {{
                font-size: 24px;
                font-weight: bold;
                padding: 5px;
                margin-bottom: 5px;
            }}
            
            QLabel[class="subtitle"] {{
                font-size: 14px;
                color: {colors['text_secondary']};
                padding: 2px;
                margin-bottom: 20px;
            }}
            
            QLabel[class="heading"] {{
                font-size: 16px;
                font-weight: bold;
                padding: 0 0 8px 0;
            }}
            
            #Card {{
                background-color: {colors['card']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
            }}
            
            QLineEdit {{
                background-color: {colors['card']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }}
            
            QLineEdit:focus {{
                border-color: {colors['accent']};
            }}
            
            QPushButton {{
                background-color: {colors['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }}
            
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['accent_dark']};
            }}
            
            QPushButton:disabled {{
                background-color: {colors['border']};
                color: {colors['text_secondary']};
            }}
            
            QPushButton[class="secondary"] {{
                background-color: {colors['card']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
            }}
            
            QPushButton[class="secondary"]:hover {{
                background-color: {colors['card_hover']};
                border-color: {colors['accent']};
            }}
            
            QPushButton[class="telegram"] {{
                background-color: {colors['telegram']};
            }}
            
            QPushButton[class="telegram"]:hover {{
                background-color: #0077b5;
            }}
            
            QPushButton[class="danger"] {{
                background-color: {colors['error']};
            }}
            
            QPushButton[class="danger"]:hover {{
                background-color: #d63031;
            }}
            
            QProgressBar {{
                background-color: {colors['border']};
                border: none;
                border-radius: 4px;
                height: 6px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {colors['accent']};
                border-radius: 3px;
            }}
            
            QStackedWidget {{
                background-color: transparent;
            }}
            
            QMessageBox {{
                background-color: {colors['card']};
                color: {colors['text']};
            }}
            
            QMessageBox QPushButton {{
                min-width: 80px;
            }}
        """)
    
    def _create_pages(self):
        """Создать страницы"""
        # Страница активации
        self.activation_page = self._create_activation_page()
        self.stack.addWidget(self.activation_page)
        
        # Страница статуса
        self.status_page = self._create_status_page()
        self.stack.addWidget(self.status_page)
    
    def _create_activation_page(self) -> QWidget:
        """Создать страницу активации"""
        page = StyledWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Заголовок
        title = QLabel("🔐 Zapret Premium")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Активация премиум подписки")
        subtitle.setProperty("class", "subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Инструкции
        instructions_card = Card()
        instructions_layout = QVBoxLayout(instructions_card)
        instructions_layout.setSpacing(8)
        
        instructions_title = QLabel("📱 Как получить ключ:")
        instructions_title.setProperty("class", "heading")
        instructions_layout.addWidget(instructions_title)
        
        steps = [
            '1. Откройте <a href="https://boosty.to/censorliber">Boosty</a>',
            "2. Выберите подходящий тариф",
            "3. Оплатите подписку",
            '4. Получите ключ в <a href="https://t.me/zapretvpns_bot">Telegram боте</a>',
            "5. Введите ключ ниже"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setWordWrap(True)
            step_label.setOpenExternalLinks(True)
            step_label.setTextFormat(Qt.TextFormat.RichText)
            step_label.setStyleSheet(f"color: {self._get_colors()['text_secondary']}; padding: 2px 0;")
            instructions_layout.addWidget(step_label)
        
        layout.addWidget(instructions_card)
        
        # Поле ввода ключа
        input_card = Card()
        input_layout = QVBoxLayout(input_card)
        input_layout.setSpacing(10)
        
        key_label = QLabel("🔑 Ключ активации:")
        key_label.setProperty("class", "heading")
        input_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.returnPressed.connect(self._activate_key)
        input_layout.addWidget(self.key_input)
        
        self.activation_progress = QProgressBar()
        self.activation_progress.setVisible(False)
        self.activation_progress.setTextVisible(False)
        input_layout.addWidget(self.activation_progress)
        
        self.activation_status = QLabel()
        self.activation_status.setVisible(False)
        self.activation_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activation_status.setStyleSheet("font-size: 13px;")
        input_layout.addWidget(self.activation_status)
        
        layout.addWidget(input_card)
        
        # Кнопки
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 10, 0, 0)
        
        activate_btn = QPushButton("✨ Активировать ключ")
        activate_btn.clicked.connect(self._activate_key)
        buttons_layout.addWidget(activate_btn)
        
        telegram_btn = QPushButton("🚀 Открыть Telegram бот")
        telegram_btn.setProperty("class", "telegram")
        telegram_btn.clicked.connect(self._open_telegram)
        buttons_layout.addWidget(telegram_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        # Сохраняем ссылки
        self.activate_btn = activate_btn
        
        return page
    
    def _create_status_page(self) -> QWidget:
        """Создать страницу статуса"""
        page = StyledWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Заголовок
        title = QLabel("📊 Статус подписки")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Карточка статуса
        status_card = Card()
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(8)
        
        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet("font-size: 48px;")
        status_layout.addWidget(self.status_icon)
        
        self.status_text = QLabel()
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet("font-size: 18px; font-weight: bold;")
        status_layout.addWidget(self.status_text)
        
        self.status_details = QLabel()
        self.status_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_details.setWordWrap(True)
        status_layout.addWidget(self.status_details)
        
        self.status_progress = QProgressBar()
        self.status_progress.setVisible(False)
        self.status_progress.setTextVisible(False)
        status_layout.addWidget(self.status_progress)
        
        layout.addWidget(status_card)
        
        # Информация об устройстве
        device_card = Card()
        device_layout = QVBoxLayout(device_card)
        device_layout.setSpacing(5)
        
        device_title = QLabel("💻 Информация об устройстве")
        device_title.setProperty("class", "heading")
        device_layout.addWidget(device_title)
        
        info_style = f"color: {self._get_colors()['text_secondary']}; font-size: 13px;"
        
        self.device_info = QLabel(f"ID: {self.checker.device_id[:16]}...")
        self.device_info.setStyleSheet(info_style)
        device_layout.addWidget(self.device_info)
        
        saved_key = RegistryManager.get_key()
        if saved_key:
            key_info = QLabel(f"Ключ: {saved_key[:4]}****")
            key_info.setStyleSheet(info_style)
            device_layout.addWidget(key_info)
        
        last_check = RegistryManager.get_last_check()
        if last_check:
            check_info = QLabel(f"Последняя проверка: {last_check.strftime('%d.%m.%Y %H:%M')}")
            check_info.setStyleSheet(info_style)
            device_layout.addWidget(check_info)
        
        layout.addWidget(device_card)
        
        # Кнопки управления
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setContentsMargins(0, 10, 0, 0)
        
        change_key_btn = QPushButton("🔑 Изменить ключ")
        change_key_btn.setProperty("class", "secondary")
        change_key_btn.clicked.connect(self._change_key)
        buttons_layout.addWidget(change_key_btn)
        
        telegram_btn = QPushButton("💬 Продлить подписку")
        telegram_btn.setProperty("class", "telegram")
        telegram_btn.clicked.connect(self._open_boosty)
        buttons_layout.addWidget(telegram_btn)
        
        test_btn = QPushButton("🔗 Проверить соединение")
        test_btn.setProperty("class", "secondary")
        test_btn.clicked.connect(self._test_connection)
        buttons_layout.addWidget(test_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        # Сохраняем ссылки
        self.test_btn = test_btn
        
        return page
    
    def _setup_initial_page(self):
        """Определить начальную страницу"""
        saved_key = RegistryManager.get_key()
        if saved_key:
            self.stack.setCurrentIndex(1)
            self._check_status()
        else:
            self.stack.setCurrentIndex(0)
    
    def _activate_key(self):
        """Активировать ключ"""
        key = self.key_input.text().strip()
        if not key:
            self._show_error("Введите ключ активации")
            return
        
        # Блокируем UI
        self.activate_btn.setEnabled(False)
        self.key_input.setEnabled(False)
        self.activation_progress.setVisible(True)
        self.activation_status.setVisible(True)
        self.activation_status.setText("🔄 Активация...")
        
        # Запускаем в потоке
        self.current_thread = WorkerThread(
            self.checker.activate,
            args=(key,)
        )
        self.current_thread.result_ready.connect(self._on_activation_complete)
        self.current_thread.error_occurred.connect(self._on_activation_error)
        self.current_thread.progress_updated.connect(self._update_progress)
        self.current_thread.start()
    
    def _on_activation_complete(self, result):
        """Обработка результата активации"""
        success, message = result
        
        # Разблокируем UI
        self.activate_btn.setEnabled(True)
        self.key_input.setEnabled(True)
        self.activation_progress.setVisible(False)
        self.activation_status.setVisible(False)
        
        if success:
            self._show_success("Ключ успешно активирован!")
            self.stack.setCurrentIndex(1)
            self._check_status()
        else:
            self._show_error(f"Ошибка активации: {message}")
    
    def _on_activation_error(self, error):
        """Обработка ошибки активации"""
        self.activate_btn.setEnabled(True)
        self.key_input.setEnabled(True)
        self.activation_progress.setVisible(False)
        self.activation_status.setVisible(False)
        self._show_error(f"Ошибка: {error}")
    
    def _check_status(self):
        """Проверить статус подписки"""
        self.status_progress.setVisible(True)
        
        self.current_thread = WorkerThread(
            self.checker.check_device_activation
        )
        self.current_thread.result_ready.connect(self._on_status_complete)
        self.current_thread.error_occurred.connect(self._on_status_error)
        self.current_thread.start()
    
    def _on_status_complete(self, result):
        """Обработка результата проверки статуса"""
        self.status_progress.setVisible(False)
        
        colors = self._get_colors()
        
        if result['activated']:
            self.status_icon.setText("✅")
            self.status_text.setText("Подписка активна")
            self.status_text.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {colors['success']};")
            
            if result['auto_payment']:
                self.status_details.setText("♾️ Бесконечная подписка\nАвтопродление включено")
            elif result['days_remaining'] is not None:
                days = result['days_remaining']
                if days > 30:
                    self.status_details.setText(f"Осталось дней: {days}")
                    self.status_details.setStyleSheet(f"color: {colors['text_secondary']};")
                elif days > 7:
                    self.status_icon.setText("⚠️")
                    self.status_details.setText(f"Осталось дней: {days}\nРекомендуем продлить подписку")
                    self.status_details.setStyleSheet(f"color: {colors['warning']};")
                else:
                    self.status_icon.setText("⚠️")
                    self.status_details.setText(f"Осталось дней: {days}\nСрочно продлите подписку!")
                    self.status_details.setStyleSheet(f"color: {colors['error']};")
            else:
                self.status_details.setText(result['status'])
                self.status_details.setStyleSheet(f"color: {colors['text_secondary']};")
        else:
            self.status_icon.setText("❌")
            self.status_text.setText("Подписка не активна")
            self.status_text.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {colors['error']};")
            self.status_details.setText(result['status'])
            self.status_details.setStyleSheet(f"color: {colors['text_secondary']};")
    
    def _on_status_error(self, error):
        """Обработка ошибки проверки статуса"""
        self.status_progress.setVisible(False)
        self.status_icon.setText("⚠️")
        self.status_text.setText("Ошибка проверки")
        self.status_details.setText(error)
    
    def _test_connection(self):
        """Проверить соединение"""
        self.test_btn.setEnabled(False)
        
        self.current_thread = WorkerThread(
            self.checker.test_connection
        )
        self.current_thread.result_ready.connect(self._on_connection_test_complete)
        self.current_thread.error_occurred.connect(
            lambda e: (self._show_error(f"Ошибка: {e}"), self.test_btn.setEnabled(True))
        )
        self.current_thread.start()
    
    def _on_connection_test_complete(self, result):
        """Обработка результата теста соединения"""
        success, message = result
        self.test_btn.setEnabled(True)
        
        if success:
            self._show_success(f"✅ {message}")
        else:
            self._show_error(f"❌ {message}")
    
    def _change_key(self):
        """Изменить ключ"""
        self.key_input.clear()
        self.stack.setCurrentIndex(0)
    
    def _update_progress(self, value, message):
        """Обновить прогресс"""
        if self.stack.currentIndex() == 0:
            self.activation_status.setText(message)

    def _open_boosty(self):
        """Открыть Boosty"""
        try:
            webbrowser.open("https://boosty.to/censorliber")
        except Exception as e:
            self._show_error(f"Не удалось открыть браузер: {e}")

    def _open_telegram(self):
        """Открыть Telegram бот"""
        try:
            webbrowser.open("https://t.me/zapretvpns_bot")
        except Exception as e:
            self._show_error(f"Не удалось открыть браузер: {e}")
    
    def _show_error(self, message: str):
        """Показать сообщение об ошибке"""
        QMessageBox.critical(self, "Ошибка", message)
    
    def _show_success(self, message: str):
        """Показать сообщение об успехе"""
        QMessageBox.information(self, "Успех", message)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
        
        if hasattr(self.checker, 'clear_cache'):
            self.checker.clear_cache()
        
        event.accept()