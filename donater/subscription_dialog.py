import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QLineEdit, QProgressBar, QMessageBox, QGroupBox, QWidget, 
                           QFrame, QInputDialog, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette
from log import log
import pyperclip, webbrowser
from donater import DonateChecker

from typing import Tuple, Optional

class SubscriptionCheckWorker(QThread):
    """Рабочий поток для проверки подписки"""
    finished = pyqtSignal(dict)  # результат проверки
    
    def __init__(self, donate_checker, email):
        super().__init__()
        self.donate_checker = donate_checker
        self.email = email
        
    def run(self):
        try:
            result = self.donate_checker.check_user_subscription(self.email)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({
                'found': False,
                'level': '–',
                'days_remaining': None,
                'status': f'Ошибка проверки: {str(e)}',
                'auto_payment': False
            })

class SubscriptionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.donate_checker = DonateChecker()
        self.current_email = None
        self.setWindowTitle("Управление подпиской")
        self.setMinimumSize(500, 550)
        self.setModal(True)
        
        # Определяем тему
        self.is_dark_theme = self.is_dark_theme_active()
        
        # Создаем стековый виджет для переключения страниц
        self.stack = QStackedWidget()
        self.email_page = QWidget()
        self.main_page = QWidget()
        
        self.stack.addWidget(self.email_page)  # index 0
        self.stack.addWidget(self.main_page)   # index 1
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.stack)
        
        # Строим обе страницы ОДИН раз
        self.init_email_input_ui()
        self.init_main_ui()
        
        # Проверяем есть ли сохраненный email и решаем какую страницу показать
        saved_email = self.donate_checker.get_email_from_registry()
        if saved_email:
            self.current_email = saved_email
            self.stack.setCurrentIndex(1)  # показываем главную страницу
            self.start_subscription_check()
        else:
            self.stack.setCurrentIndex(0)  # показываем страницу ввода email
            
        # Подгоняем размер и фиксируем его для предотвращения дрожания
        self.adjustSize()
        QTimer.singleShot(100, self.fix_window_size)  # фиксируем размер через небольшую задержку        
    def fix_window_size(self):
        """Фиксирует размер окна для предотвращения дрожания"""
        self.adjustSize()
        self.setFixedSize(self.size())
        
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
                'success_text': '#155724',                'error_bg': '#f8d7da',
                'error_border': '#f5c6cb',
                'error_text': '#721c24',
                'group_bg': '#f8f9fa'
            }

    def init_email_input_ui(self):
        """Инициализирует UI для ввода email"""
        layout = QVBoxLayout(self.email_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        styles = self.get_theme_styles()
        
        self.email_page.setStyleSheet(f"""
            QWidget {{
                background-color: {styles['bg_color']};
                color: {styles['text_color']};
            }}
        """)

        # Заголовок
        title_label = QLabel("🔐 Zapret Premium")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Инструкция
        info_label = QLabel(
            "Как получить премиум доступ:\n\n"
            "1. Создайте аккаунт на Boosty и привяжите ОБЯЗАТЕЛЬНО туда почту!\n"
            "2. Оформите подписку на любой период\n"
            "3. Добавьтесь в Telegram чат\n"            "4. Активация происходит в течение 24 часов автоматически по почте\n\n"
            "Введите email, который вы указали на Boosty:"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_label.setWordWrap(True)
        info_label.setFixedHeight(180)
        info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_label.setStyleSheet(f"""
            QLabel {{
                color: {styles['text_color']};
                padding: 15px;
                background-color: {styles['group_bg']};
                border: 1px solid {styles['border_color']};
                border-radius: 8px;
                font-size: 12px;
            }}
        """)
        info_label.setAutoFillBackground(True)
        self.info_label = info_label
        layout.addWidget(info_label)
        
        # Поле ввода email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles['input_bg']};
                color: {styles['input_text']};
                border: 2px solid {styles['border_color']};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: #2196F3;
            }}
        """)
        layout.addWidget(self.email_input)
        
        # Кнопка Boosty
        boosty_btn = QPushButton("🚀 Оформить подписку на Boosty")
        boosty_btn.clicked.connect(self.open_boosty)
        boosty_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF6900;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 12px;
                font-weight: bold;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: #E55A00;
            }}
            QPushButton:pressed {{
                background-color: #CC5100;
            }}
        """)
        layout.addWidget(boosty_btn)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles['border_color']};
                color: {styles['text_color']};
                border: 1px solid {styles['border_color']};
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 12px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {styles['input_bg']};
            }}
        """)
        
        save_btn = QPushButton("Проверить статус")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_email_and_continue)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 12px;
                font-weight: bold;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
            QPushButton:pressed {{
                background-color: #1565C0;
            }}
        """)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        layout.addLayout(buttons_layout)        
        self.email_input.setFocus()

    def init_main_ui(self):
        """Инициализирует основной UI после ввода email"""

        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)
        
        styles = self.get_theme_styles()
        
        self.main_page.setStyleSheet(f"""
            QWidget {{
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
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_label = QLabel("🔐")
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Статус подписки Zapret Premium")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
          # Группа email
        email_group = QGroupBox("Пользователь")
        email_layout = QVBoxLayout(email_group)
        email_layout.setContentsMargins(10, 20, 10, 10)
        
        self.email_display = QLineEdit()
        self.email_display.setText(self.current_email)
        self.email_display.setReadOnly(True)
        self.email_display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles['input_bg']};
                color: {styles['input_text']};
                border: 1px solid {styles['border_color']};
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }}
        """)
        email_layout.addWidget(self.email_display)
        
        change_email_btn = QPushButton("Изменить email")
        change_email_btn.clicked.connect(self.change_email)
        change_email_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles['border_color']};
                color: {styles['text_color']};
                border: 1px solid {styles['border_color']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                margin-top: 5px;
            }}
            QPushButton:hover {{
                background-color: {styles['input_bg']};
            }}
        """)
        email_layout.addWidget(change_email_btn)
        
        main_layout.addWidget(email_group)
        
        # Группа статуса
        status_group = QGroupBox("Статус подписки")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 20, 10, 10)
        
        self.status_text = QLabel("Проверяю...")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setFixedHeight(80)
        self.status_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.status_text.setStyleSheet(f"""
            QLabel {{
                background-color: {styles['input_bg']};
                color: {styles['text_color']};
                border: 2px solid {styles['border_color']};
                padding: 15px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        self.status_text.setAutoFillBackground(True)

        status_layout.addWidget(self.status_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)   # чтобы ширина не плясала
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
        
        info_text = QLabel(            "1. Создайте аккаунт на Boosty и привяжите ОБЯЗАТЕЛЬНО туда почту! Настройте подписку.\n"
            "2. Добавьтесь в Telegram чат\n"
            "3. Активация происходит в течение 24 часов автоматически по почте"
        )
        info_text.setWordWrap(True)
        info_text.setFixedHeight(80)
        info_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_text.setStyleSheet(f"""
            QLabel {{
                color: {styles['text_color']};
                padding: 8px;
                font-size: 11px;
            }}
        """)
        info_text.setAutoFillBackground(True)
        self.info_text = info_text
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

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        control_layout.addWidget(refresh_btn)
        control_layout.addStretch()
        control_layout.addWidget(close_btn)

        main_layout.addWidget(control_panel)
        main_layout.addStretch()

    def save_email_and_continue(self):
        """Сохраняет email и переходит к основному UI"""
        email = self.email_input.text().strip()
        
        if not email:
            QMessageBox.warning(self, "Ошибка", "Введите email")
            return
        
        # Простая валидация email
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Ошибка", "Введите корректный email")
            return
        
        # Сохраняем в реестр
        if self.donate_checker.save_email_to_registry(email):
            self.current_email = email
            self.email_display.setText(email)
            # Переключаемся на главную страницу
            self.stack.setCurrentIndex(1)
            self.start_subscription_check()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить email")

    def change_email(self):
        """Изменяет сохраненный email"""
        email, ok = QInputDialog.getText(self, "Изменить email", 
                                       "Введите новый email:", 
                                       text=self.current_email)
        if ok and email.strip():
            email = email.strip()
            if '@' not in email or '.' not in email:
                QMessageBox.warning(self, "Ошибка", "Введите корректный email")
                return
                
            if self.donate_checker.save_email_to_registry(email):
                self.current_email = email
                self.email_display.setText(email)
                self.start_subscription_check()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить email")

    def open_boosty(self):
        """Открывает страницу подписки на Boosty"""
        try:
            boosty_url = "https://boosty.to/censorliber"
            webbrowser.open(boosty_url)
            log(f"Открыта ссылка на Boosty: {boosty_url}", level="INFO")
            
            QMessageBox.information(self, "Переход на Boosty", 
                                "Страница подписки открыта в браузере.\n\n"
                                "ОБЯЗАТЕЛЬНО ПРИВЯЖИТЕ email К СВОЕМУ АККАУНТУ, "
                                "затем используйте кнопку 'Обновить статус'. Статус выдаётся в течении 24 часов.")
            
        except Exception as e:
            log(f"Ошибка при открытии ссылки на Boosty: {e}", level="ERROR")
            QMessageBox.information(self, "Ссылка на подписку", 
                                "Не удалось автоматически открыть браузер.\n\n"
                                "Скопируйте ссылку для оформления подписки:\n"
                                "https://boosty.to/censorliber")

    def on_subscription_checked(self, result):
        """Обработчик результата проверки подписки"""
        self.progress_bar.setVisible(False)
        styles = self.get_theme_styles()
        
        if result['found']:
            if result['days_remaining'] is not None and result['days_remaining'] > 0:
                # Активная подписка
                status_text = f"✅ {result['status']}\nУровень: {result['level']}"
                self.status_text.setStyleSheet(f"""
                    QLabel {{
                        background-color: {styles['success_bg']};
                        border: 2px solid {styles['success_border']};
                        color: {styles['success_text']};
                        padding: 15px;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                """)
            elif "включен" in result['status'].lower():
                # Активная подписка с автоплатежом
                status_text = f"✅ {result['status']}\nУровень: {result['level']}"
                self.status_text.setStyleSheet(f"""
                    QLabel {{
                        background-color: {styles['success_bg']};
                        border: 2px solid {styles['success_border']};
                        color: {styles['success_text']};
                        padding: 15px;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                """)
            else:
                # Подписка истекла или неактивна
                status_text = f"⚠️ {result['status']}\nУровень: {result['level']}"
                self.status_text.setStyleSheet(f"""
                    QLabel {{
                        background-color: {styles['error_bg']};
                        border: 2px solid {styles['error_border']};
                        color: {styles['error_text']};
                        padding: 15px;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                """)
        else:
            # Пользователь не найден
            status_text = f"❌ {result['status']}"
            self.status_text.setStyleSheet(f"""
                QLabel {{
                    background-color: {styles['error_bg']};
                    border: 2px solid {styles['error_border']};
                    color: {styles['error_text']};
                    padding: 15px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
        
        self.status_text.setText(status_text)
        log(f"Статус подписки обновлен для {self.current_email}: {result['status']}", level="INFO")
        
    def start_subscription_check(self):
        """Запускает проверку статуса подписки в отдельном потоке"""
        if not self.current_email:
            return
            
        try:
            log(f"Запуск проверки статуса подписки для {self.current_email}", level="DEBUG")
            
            # Показываем прогресс-бар
            self.progress_bar.setVisible(True)
            self.status_text.setText("Проверяю статус подписки...")
            
            # Создаем и запускаем worker
            self.worker = SubscriptionCheckWorker(self.donate_checker, self.current_email)
            self.worker.finished.connect(self.on_subscription_checked)
            self.worker.start()
            
        except Exception as e:
            log(f"Ошибка при запуске проверки подписки: {e}", level="ERROR")
            self.progress_bar.setVisible(False)
            self.status_text.setText(f"❌ Ошибка проверки: {str(e)}")

    def refresh_subscription(self):
        """Принудительно обновляет статус подписки"""
        log("Принудительное обновление статуса подписки", level="INFO")
        self.start_subscription_check()