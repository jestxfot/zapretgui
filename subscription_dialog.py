import sys
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QProgressBar, QMessageBox, QGroupBox, QWidget, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette
from log import log
import pyperclip, webbrowser

from typing import Tuple, Optional

class SubscriptionCheckWorker(QThread):
    """Рабочий поток для проверки подписки"""
    finished = pyqtSignal(bool, str, object)  # (is_premium, status_message, days_remaining)
    
    def __init__(self, donate_checker):
        super().__init__()
        self.donate_checker = donate_checker
        
    def run(self):
        try:
            is_premium, status_msg, days_remaining = self.donate_checker.check_subscription_status(use_cache=False)
            self.finished.emit(is_premium, status_msg, days_remaining)
        except Exception as e:
            self.finished.emit(False, f"Ошибка проверки: {str(e)}", None)

class SubscriptionDialog(QDialog):
    def __init__(self, parent, donate_checker):
        super().__init__(parent)
        self.donate_checker = donate_checker
        self.setWindowTitle("Управление подпиской")
        self.setFixedSize(500, 480)  # Более компактный размер
        self.setModal(True)
        
        # Определяем тему
        self.is_dark_theme = self.is_dark_theme_active()
        
        self.init_ui()
        self.check_subscription_status()
        
    def is_dark_theme_active(self):
        """Определяет, активна ли темная тема"""
        palette = self.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        return bg_color.lightness() < 128
        
    def get_theme_styles(self):
        """Возвращает стили для текущей темы"""
        if self.is_dark_theme:
            return {
                'bg_color': '#2b2b2b',
                'text_color': '#ffffff',
                'border_color': '#555555',
                'input_bg': '#404040',
                'input_text': '#ffffff',
                'info_bg': '#1e3a5f',
                'info_border': '#4a90e2',
                'success_bg': '#1e4d3a',
                'success_border': '#4caf50',
                'success_text': '#4caf50',
                'error_bg': '#4d1e1e',
                'error_border': '#f44336',
                'error_text': '#f44336',
                'group_bg': '#383838'
            }
        else:
            return {
                'bg_color': '#ffffff',
                'text_color': '#000000',
                'border_color': '#cccccc',
                'input_bg': '#f0f0f0',
                'input_text': '#000000',
                'info_bg': '#e7f3ff',
                'info_border': '#b3d9ff',
                'success_bg': '#d4edda',
                'success_border': '#c3e6cb',
                'success_text': '#155724',
                'error_bg': '#f8d7da',
                'error_border': '#f5c6cb',
                'error_text': '#721c24',
                'group_bg': '#f8f9fa'
            }
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)
        
        styles = self.get_theme_styles()
        
        # Устанавливаем общий стиль диалога
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles['bg_color']};
                color: {styles['text_color']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {styles['border_color']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: {styles['group_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: {styles['text_color']};
            }}
        """)
        
        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_label = QLabel("🔐")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Управление подпиской Zapret Premium")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {styles['text_color']};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Группа UUID
        uuid_group = QGroupBox("Идентификатор машины")
        uuid_layout = QVBoxLayout(uuid_group)
        uuid_layout.setContentsMargins(10, 20, 10, 10)
        
        uuid_container = QHBoxLayout()
        uuid_container.setSpacing(8)
        
        self.uuid_text = QLineEdit()
        self.uuid_text.setText(self.donate_checker.get_machine_uuid())
        self.uuid_text.setReadOnly(True)
        self.uuid_text.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles['input_bg']};
                color: {styles['input_text']};
                border: 1px solid {styles['border_color']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        
        copy_uuid_btn = QPushButton("Копировать")
        copy_uuid_btn.setFixedWidth(120)
        copy_uuid_btn.clicked.connect(self.copy_uuid)
        
        uuid_container.addWidget(self.uuid_text)
        uuid_container.addWidget(copy_uuid_btn)
        uuid_layout.addLayout(uuid_container)
        main_layout.addWidget(uuid_group)
        
        # Группа статуса
        status_group = QGroupBox("Статус подписки")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 20, 10, 10)
        
        self.status_text = QLabel("Проверяю...")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setMinimumHeight(50)
        self.status_text.setStyleSheet(f"""
            QLabel {{
                background-color: {styles['input_bg']};
                color: {styles['text_color']};
                border: 2px solid {styles['border_color']};
                padding: 12px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        status_layout.addWidget(self.status_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: {styles['input_bg']};
            }}
            QProgressBar::chunk {{
                background-color: #2196F3;
                border-radius: 3px;
            }}
        """)
        status_layout.addWidget(self.progress_bar)
        main_layout.addWidget(status_group)
        
        # Группа инструкций
        info_group = QGroupBox("Как получить премиум доступ")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(10, 20, 10, 10)
        
        info_text = QLabel(
            "1. Скопируйте UUID вашей машины\n"
            "2. Оформите подписку на Boosty\n"
            "3. Добавьтесь в Telegram чат и укажите UUID\n"
            "4. Активация происходит в течение 24 часов"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"""
            QLabel {{
                color: {styles['text_color']};
                padding: 8px;
                font-size: 11px;
                line-height: 1.5;
            }}
        """)
        info_layout.addWidget(info_text)
        
        # Кнопка Boosty
        boosty_btn = QPushButton("🚀 Оформить подписку на Boosty")
        boosty_btn.clicked.connect(self.open_boosty)
        info_layout.addWidget(boosty_btn)

        main_layout.addWidget(info_group)
        
        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 10, 0, 0)
        control_layout.setSpacing(10)

        refresh_btn = QPushButton("Обновить статус")
        refresh_btn.clicked.connect(self.refresh_subscription)

        clear_cache_btn = QPushButton("Очистить кэш")
        clear_cache_btn.clicked.connect(self.clear_cache)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        control_layout.addWidget(refresh_btn)
        control_layout.addWidget(clear_cache_btn)
        control_layout.addStretch()
        control_layout.addWidget(close_btn)

        main_layout.addWidget(control_panel)
        main_layout.addStretch()

    # Остальные методы остаются без изменений
    def open_boosty(self):
        """Открывает страницу подписки на Boosty"""
        try:
            boosty_url = "https://boosty.to/censorliber"
            webbrowser.open(boosty_url)
            log(f"Открыта ссылка на Boosty: {boosty_url}", level="INFO")
            
            QMessageBox.information(self, "Переход на Boosty", 
                                "Страница подписки открыта в браузере.\n\n"
                                "После оформления подписки не забудьте добавиться в Telegram чат и указать свой UUID, "
                                "затем используйте кнопку 'Обновить статус' для проверки активации.")
            
        except Exception as e:
            log(f"Ошибка при открытии ссылки на Boosty: {e}", level="ERROR")
            
            QMessageBox.information(self, "Ссылка на подписку", 
                                "Не удалось автоматически открыть браузер.\n\n"
                                "Скопируйте ссылку для оформления подписки:\n"
                                "https://boosty.to/censorliber\n\n"
                                "После оформления укажите ваш UUID в Telegram чате.")

    def copy_uuid(self):
        """Копирует UUID в буфер обмена"""
        try:
            uuid = self.donate_checker.get_machine_uuid()
            pyperclip.copy(uuid)
            
            original_text = self.sender().text()
            self.sender().setText("✅ Скопировано")
            
            QTimer.singleShot(2000, lambda: self.sender().setText(original_text))
            
            log("UUID скопирован в буфер обмена", level="INFO")
            
        except Exception as e:
            log(f"Ошибка при копировании UUID: {e}", level="ERROR")
            QMessageBox.warning(self, "Ошибка", "Не удалось скопировать UUID")
    
    def on_subscription_checked(self, is_premium, status_msg, days_remaining):
        """Обработчик результата проверки подписки"""
        self.progress_bar.setVisible(False)
        styles = self.get_theme_styles()
        
        if is_premium:
            # Формируем текст статуса с учетом дней
            if days_remaining is not None:
                if days_remaining > 0:
                    status_text = f"✅ Подписка активна (осталось {days_remaining} дней)"
                else:
                    status_text = "⚠️ Подписка истекает сегодня"
            else:
                status_text = "✅ Подписка активна (бессрочная)"
                
            self.status_text.setText(status_text)
            self.status_text.setStyleSheet(f"""
                QLabel {{
                    background-color: {styles['success_bg']};
                    border: 2px solid {styles['success_border']};
                    color: {styles['success_text']};
                    padding: 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
        else:
            self.status_text.setText(f"❌ Подписка неактивна\n{status_msg}")
            self.status_text.setStyleSheet(f"""
                QLabel {{
                    background-color: {styles['error_bg']};
                    border: 2px solid {styles['error_border']};
                    color: {styles['error_text']};
                    padding: 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
        
        log(f"Статус подписки обновлен: {is_premium}, дней осталось: {days_remaining}", level="INFO")
        
    def check_subscription_status(self):
        """Запускает проверку статуса подписки в отдельном потоке"""
        try:
            log("Запуск проверки статуса подписки в диалоге", level="DEBUG")
            
            # Показываем прогресс-бар
            self.progress_bar.setVisible(True)
            self.status_text.setText("Проверяю статус подписки...")
            
            # Создаем и запускаем worker
            self.worker = SubscriptionCheckWorker(self.donate_checker)
            self.worker.finished.connect(self.on_subscription_checked)
            self.worker.start()
            
        except Exception as e:
            log(f"Ошибка при запуске проверки подписки: {e}", level="ERROR")
            self.progress_bar.setVisible(False)
            self.status_text.setText(f"❌ Ошибка проверки: {str(e)}")

    def refresh_subscription(self):
        """Принудительно обновляет статус подписки"""
        log("Принудительное обновление статуса подписки", level="INFO")
        self.check_subscription_status()
    
    def clear_cache(self):
        """Очищает кэш подписки"""
        try:
            self.donate_checker.clear_cache()
            QMessageBox.information(self, "Кэш очищен", 
                                  "Кэш подписки успешно очищен.\n"
                                  "При следующей проверке данные будут загружены заново.")
            log("Кэш подписки очищен пользователем", level="INFO")
        except Exception as e:
            log(f"Ошибка при очистке кэша: {e}", level="ERROR")
            QMessageBox.warning(self, "Ошибка", "Не удалось очистить кэш")