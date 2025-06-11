import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QMessageBox, QApplication,
                            QProgressBar, QFrame, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette
from log import log
import pyperclip

class SubscriptionCheckWorker(QThread):
    """Рабочий поток для проверки подписки"""
    finished = pyqtSignal(bool, str)  # (is_premium, status_message)
    
    def __init__(self, donate_checker):
        super().__init__()
        self.donate_checker = donate_checker
        
    def run(self):
        try:
            is_premium, status_msg = self.donate_checker.check_subscription_status(use_cache=False)
            self.finished.emit(is_premium, status_msg)
        except Exception as e:
            self.finished.emit(False, f"Ошибка проверки: {str(e)}")

class SubscriptionDialog(QDialog):
    def __init__(self, parent, donate_checker):
        super().__init__(parent)
        self.donate_checker = donate_checker
        self.setWindowTitle("Управление подпиской")
        self.setFixedSize(550, 450)  # Увеличиваем размер
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
                'error_text': '#f44336'
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
                'error_text': '#721c24'
            }
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        styles = self.get_theme_styles()
        
        # Устанавливаем общий стиль диалога
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles['bg_color']};
                color: {styles['text_color']};
            }}
        """)
        
        # Заголовок
        title_label = QLabel("Управление подпиской Zapret Premium")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {styles['text_color']}; margin: 10px;")
        layout.addWidget(title_label)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"color: {styles['border_color']};")
        layout.addWidget(line)
        
        # UUID машины
        uuid_layout = QVBoxLayout()
        uuid_label = QLabel("UUID вашей машины:")
        uuid_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        uuid_label.setStyleSheet(f"color: {styles['text_color']}; margin-bottom: 5px;")
        uuid_layout.addWidget(uuid_label)
        
        uuid_container = QHBoxLayout()
        uuid_container.setSpacing(10)
        
        # Используем QLineEdit вместо QTextEdit для лучшего отображения
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
        copy_uuid_btn.setMinimumWidth(100)  # Фиксированная ширина
        copy_uuid_btn.clicked.connect(self.copy_uuid)
        copy_uuid_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        uuid_container.addWidget(self.uuid_text)
        uuid_container.addWidget(copy_uuid_btn)
        uuid_layout.addLayout(uuid_container)
        layout.addLayout(uuid_layout)
        
        # Статус подписки
        status_layout = QVBoxLayout()
        status_label = QLabel("Статус подписки:")
        status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        status_label.setStyleSheet(f"color: {styles['text_color']}; margin-bottom: 5px;")
        status_layout.addWidget(status_label)
        
        self.status_text = QLabel("Проверяю...")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setMinimumHeight(60)
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
        status_layout.addWidget(self.status_text)
        layout.addLayout(status_layout)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {styles['border_color']};
                border-radius: 4px;
                background-color: {styles['input_bg']};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #2196F3;
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Информация
        info_text = QLabel(
            "Для получения премиум доступа:\n"
            "1. Скопируйте UUID вашей машины\n"
            "2. Отправьте его разработчику\n"
            "3. После активации перезапустите программу"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"""
            QLabel {{
                background-color: {styles['info_bg']};
                color: {styles['text_color']};
                border: 1px solid {styles['info_border']};
                padding: 12px;
                border-radius: 6px;
                font-size: 11px;
                line-height: 1.4;
            }}
        """)
        layout.addWidget(info_text)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        refresh_btn = QPushButton("Обновить статус")
        refresh_btn.clicked.connect(self.refresh_subscription)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        
        clear_cache_btn = QPushButton("Очистить кэш")
        clear_cache_btn.clicked.connect(self.clear_cache)
        clear_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #ef6c00;
            }
        """)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:pressed {
                background-color: #263238;
            }
        """)
        
        buttons_layout.addWidget(refresh_btn)
        buttons_layout.addWidget(clear_cache_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)
        
    def copy_uuid(self):
        """Копирует UUID в буфер обмена"""
        try:
            uuid = self.donate_checker.get_machine_uuid()
            pyperclip.copy(uuid)
            
            # Показываем временное подтверждение
            original_text = self.sender().text()
            self.sender().setText("✓ Скопировано")
            self.sender().setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }
            """)
            
            QTimer.singleShot(2000, lambda: self.restore_copy_button(original_text))
            
            log("UUID скопирован в буфер обмена", level="INFO")
            
        except Exception as e:
            log(f"Ошибка при копировании UUID: {e}", level="ERROR")
            QMessageBox.warning(self, "Ошибка", "Не удалось скопировать UUID")
    
    def restore_copy_button(self, original_text):
        """Восстанавливает оригинальный текст кнопки копирования"""
        try:
            copy_btn = self.findChild(QPushButton, "")
            for btn in self.findChildren(QPushButton):
                if btn.text() == "✓ Скопировано":
                    btn.setText(original_text)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 8px 15px;
                            border-radius: 4px;
                            font-weight: bold;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                        QPushButton:pressed {
                            background-color: #3d8b40;
                        }
                    """)
                    break
        except Exception:
            pass
    
    def check_subscription_status(self):
        """Проверяет статус подписки в отдельном потоке"""
        self.progress_bar.setVisible(True)
        self.status_text.setText("Проверяю статус подписки...")
        
        self.worker = SubscriptionCheckWorker(self.donate_checker)
        self.worker.finished.connect(self.on_subscription_checked)
        self.worker.start()
    
    def on_subscription_checked(self, is_premium, status_msg):
        """Обработчик результата проверки подписки"""
        self.progress_bar.setVisible(False)
        styles = self.get_theme_styles()
        
        if is_premium:
            self.status_text.setText("✅ Подписка активна")
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
            self.status_text.setText(f"❌ Подписка неактивна\n{status_msg}")
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
        
        log(f"Статус подписки обновлен: {is_premium}", level="INFO")
    
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