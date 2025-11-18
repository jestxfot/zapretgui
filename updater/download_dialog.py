"""
download_dialog.py
────────────────────────────────────────────────────────────────
Красивый диалог загрузки обновления с прогресс-баром
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                             QPushButton, QHBoxLayout, QWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont, QMovie, QIcon, QDesktopServices, QCursor
import os
import time
from config import ICON_PATH, ICON_TEST_PATH, CHANNEL

class DownloadDialog(QDialog):
    """Модальный диалог загрузки обновления"""
    
    cancelled = pyqtSignal()
    retry_requested = pyqtSignal()  # Новый сигнал для повторной попытки
    # ✅ СТАТИЧЕСКАЯ ПЕРЕМЕННАЯ ДЛЯ ОТСЛЕЖИВАНИЯ АКТИВНОГО ДИАЛОГА
    _active_instance = None
    
    def __init__(self, parent=None, version="", total_size=0):
        # ✅ ЗАКРЫВАЕМ ПРЕДЫДУЩИЙ ЭКЗЕМПЛЯР ЕСЛИ ОН ЕСТЬ
        if DownloadDialog._active_instance is not None:
            try:
                DownloadDialog._active_instance.close()
                DownloadDialog._active_instance = None
            except:
                pass
        
        super().__init__(parent)
        
        # ✅ СОХРАНЯЕМ ТЕКУЩИЙ ЭКЗЕМПЛЯР
        DownloadDialog._active_instance = self

        self.version = version
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = None
        self._cancelled = False
        self._download_failed = False
        self._download_complete = False
        
        self.setupUI()
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
        
        # Устанавливаем иконку
        icon_path = ICON_TEST_PATH if CHANNEL == "test" else ICON_PATH
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
    
    def setupUI(self):
        """Создаёт интерфейс диалога"""
        self.setWindowTitle(f"Загрузка обновления {self.version}")
        self.setFixedSize(500, 300)
        
        # Основной layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        self.title_label = QLabel(f"📥 Загрузка Zapret {self.version}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Информация о загрузке
        self.info_label = QLabel("Подготовка к загрузке...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3daee9;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                           stop: 0 #3daee9, stop: 1 #1d99f3);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Детали загрузки
        details_layout = QHBoxLayout()
        
        self.speed_label = QLabel("Скорость: ---")
        self.speed_label.setStyleSheet("color: #888;")
        details_layout.addWidget(self.speed_label)
        
        details_layout.addStretch()
        
        self.time_label = QLabel("Осталось: ---")
        self.time_label.setStyleSheet("color: #888;")
        details_layout.addWidget(self.time_label)
        
        layout.addLayout(details_layout)
        
        # Статус
        self.status_label = QLabel("Не закрывайте это окно до завершения загрузки")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #f67400; font-style: italic;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { color: #ddd; }")
        layout.addWidget(separator)
        
        # Контейнер для кнопок (изначально скрыт)
        self.button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Кнопка повторной попытки
        self.retry_button = QPushButton("🔄 Попробовать снова")
        self.retry_button.setStyleSheet("""
            QPushButton {
                background-color: #3daee9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1d99f3;
            }
            QPushButton:pressed {
                background-color: #1a86d0;
            }
        """)
        self.retry_button.clicked.connect(self.on_retry_clicked)
        button_layout.addWidget(self.retry_button)
        
        button_layout.addSpacing(10)
        
        # Кнопка отмены/закрытия
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #da4453;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c92434;
            }
            QPushButton:pressed {
                background-color: #a91925;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        self.button_container.setLayout(button_layout)
        self.button_container.hide()  # Изначально скрыто
        layout.addWidget(self.button_container)
        
        layout.addStretch()

        # Информационное сообщение
        self.info_msg_label = QLabel("⚠️ Загрузка может занять несколько минут в зависимости от скорости интернета")
        self.info_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_msg_label.setStyleSheet("color: #666; font-size: 10px;")
        self.info_msg_label.setWordWrap(True)
        layout.addWidget(self.info_msg_label)

        # ✅ КЛИКАБЕЛЬНАЯ ССЫЛКА НА TELEGRAM
        self.telegram_link_label = QLabel(
            '💬 <a href="https://t.me/zapretnetdiscordyoutube" style="color: #3daee9; text-decoration: none;">'
            'Если обновление зависло скачайте файл по ссылке (там всегда свежие версии)</a>'
        )
        self.telegram_link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.telegram_link_label.setOpenExternalLinks(True)  # Автоматически открывает ссылки
        self.telegram_link_label.setStyleSheet("""
            QLabel {
                color: #3daee9;
                font-size: 10px;
                padding: 5px;
            }
            QLabel:hover {
                background-color: rgba(61, 174, 233, 0.1);
                border-radius: 3px;
            }
        """)
        self.telegram_link_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # Курсор-рука
        self.telegram_link_label.setWordWrap(True)

        # Добавляем обработчик для логирования кликов
        self.telegram_link_label.linkActivated.connect(self.on_telegram_link_clicked)

        layout.addWidget(self.telegram_link_label)

        self.setLayout(layout)
        
        # Таймер для обновления скорости
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_speed)
        self.update_timer.start(1000)  # Обновляем каждую секунду

    def on_telegram_link_clicked(self, url: str):
        """Обработчик клика по ссылке Telegram (для логирования)"""
        from log import log
        log(f"🔗 Пользователь перешёл по ссылке: {url}", "📥 DOWNLOAD")
        # QLabel с setOpenExternalLinks(True) автоматически откроет ссылку

    def update_progress(self, percent: int, downloaded_bytes: int = 0, total_bytes: int = 0):
        """Обновляет прогресс загрузки"""
        self.progress_bar.setValue(percent)
        
        if total_bytes > 0:
            self.downloaded = downloaded_bytes
            self.total_size = total_bytes
            
            # Обновляем информацию
            downloaded_mb = downloaded_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            self.info_label.setText(f"Загружено {downloaded_mb:.1f} МБ из {total_mb:.1f} МБ")
            
            # Запоминаем время начала
            if self.start_time is None and downloaded_bytes > 0:
                self.start_time = time.time()
    
    def update_speed(self):
        """Обновляет отображение скорости загрузки"""
        if self.start_time and self.downloaded > 0 and not self._download_failed:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                speed_bytes = self.downloaded / elapsed
                speed_mb = speed_bytes / (1024 * 1024)
                self.speed_label.setText(f"Скорость: {speed_mb:.1f} МБ/с")
                
                # Расчёт оставшегося времени
                if self.total_size > 0 and speed_bytes > 0:
                    remaining_bytes = self.total_size - self.downloaded
                    remaining_seconds = remaining_bytes / speed_bytes
                    
                    if remaining_seconds < 60:
                        self.time_label.setText(f"Осталось: {int(remaining_seconds)} сек")
                    else:
                        remaining_minutes = remaining_seconds / 60
                        self.time_label.setText(f"Осталось: {int(remaining_minutes)} мин")
    
    def set_status(self, status: str):
        """Устанавливает текст статуса"""
        self.status_label.setText(status)
    
    def download_complete(self):
        """Вызывается при завершении загрузки"""
        self._download_complete = True
        self._download_failed = False
        
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #27ae60;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                           stop: 0 #27ae60, stop: 1 #229954);
                border-radius: 3px;
            }
        """)
        
        self.title_label.setText(f"✅ Zapret {self.version} загружен")
        self.info_label.setText("Загрузка завершена успешно!")
        self.status_label.setText("Запуск установщика...")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

    
    def download_failed(self, error: str):
        """Вызывается при ошибке загрузки"""
        self._download_failed = True
        self._download_complete = False
        
        # Останавливаем таймер обновления
        self.update_timer.stop()
        
        # Меняем стиль прогресс-бара на красный
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #da4453;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 30px;
            }
            QProgressBar::chunk {
                background: #da4453;
                border-radius: 3px;
            }
        """)
        
        # Обновляем тексты
        self.title_label.setText(f"❌ Ошибка загрузки")
        self.info_label.setText("Не удалось загрузить обновление")
        
        # Форматируем сообщение об ошибке
        if "ConnectionPool" in error or "Connection" in error:
            error_text = "Ошибка подключения к серверу. Проверьте интернет-соединение."
        elif "Timeout" in error:
            error_text = "Превышено время ожидания ответа от сервера."
        elif "404" in error:
            error_text = "Файл обновления не найден на сервере."
        elif "403" in error:
            error_text = "Доступ к файлу обновления запрещён."
        else:
            error_text = error[:200] if len(error) > 200 else error
        
        self.status_label.setText(error_text)
        self.status_label.setStyleSheet("color: #da4453; font-weight: bold;")
        
        # Скрываем детали скорости
        self.speed_label.setText("---")
        self.time_label.setText("---")
        
        # Показываем кнопки
        self.button_container.show()
        self.retry_button.show()
        self.cancel_button.setText("Закрыть")
        
        # Обновляем информационное сообщение
        self.info_msg_label.setText("💡 Попробуйте ещё раз или проверьте подключение к интернету")
    
    def on_retry_clicked(self):
        """Обработчик кнопки повтора"""
        # Сбрасываем состояние
        self._download_failed = False
        self.start_time = None
        self.downloaded = 0
        
        # Восстанавливаем UI
        self.title_label.setText(f"📥 Загрузка Zapret {self.version}")
        self.info_label.setText("Повторная попытка загрузки...")
        self.status_label.setText("Подключение к серверу...")
        self.status_label.setStyleSheet("color: #f67400; font-style: italic;")
        
        # Сбрасываем прогресс-бар
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3daee9;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                           stop: 0 #3daee9, stop: 1 #1d99f3);
                border-radius: 3px;
            }
        """)
        
        # Скрываем кнопки
        self.button_container.hide()
        
        # Восстанавливаем детали
        self.speed_label.setText("Скорость: ---")
        self.time_label.setText("Осталось: ---")
        self.speed_label.show()
        self.time_label.show()
        
        # Перезапускаем таймер
        self.update_timer.start(1000)
        
        # Эмитим сигнал для повторной попытки
        self.retry_requested.emit()
    
    def on_cancel_clicked(self):
        """Обработчик кнопки отмены"""
        self._cancelled = True
        self.cancelled.emit()
        self.reject()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # ✅ ОЧИЩАЕМ ССЫЛКУ НА АКТИВНЫЙ ЭКЗЕМПЛЯР
        if DownloadDialog._active_instance == self:
            DownloadDialog._active_instance = None

        # Разрешаем закрытие если загрузка завершена, отменена или произошла ошибка
        if self._download_complete or self._cancelled or self._download_failed:
            event.accept()
        else:
            # Предотвращаем закрытие во время активной загрузки
            if self.progress_bar.value() > 0 and self.progress_bar.value() < 100:
                event.ignore()
                self.status_label.setText("⚠️ Пожалуйста, дождитесь завершения загрузки или нажмите 'Отмена'")
                self.status_label.setStyleSheet("color: #da4453; font-weight: bold;")
                # Показываем кнопку отмены
                self.button_container.show()
                self.retry_button.hide()
                self.cancel_button.show()
            else:
                event.accept()
        
        super().closeEvent(event)