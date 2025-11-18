# subscription_dialog.py - исправленная версия

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox, QWidget, QTabWidget, QGroupBox,
    QTextBrowser
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import webbrowser
from datetime import datetime

from .donate import SimpleDonateChecker, RegistryManager

class WorkerThread(QThread):
    """Поток для выполнения операций"""
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, target, args=None):
        super().__init__()
        self.target = target
        self.args = args or ()
        
    def run(self):
        try:
            result = self.target(*self.args)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class SubscriptionDialog(QDialog):
    """Диалог управления подпиской - простая версия"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checker = SimpleDonateChecker()
        self.current_thread = None
        
        # Настройки окна
        self.setWindowTitle("Zapret Premium")
        self.setModal(True)
        self.setMinimumSize(500, 600)
        self.setMaximumSize(600, 700)
        
        # Инициализация интерфейса
        self._init_ui()
        
        # Проверка сохраненного ключа
        self._check_saved_key()
    
    def _init_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Заголовок
        title = QLabel("🔐 Zapret Premium")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Табы
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Вкладка активации
        self.activation_tab = self._create_activation_tab()
        self.tabs.addTab(self.activation_tab, "Активация")
        
        # Вкладка статуса
        self.status_tab = self._create_status_tab()
        self.tabs.addTab(self.status_tab, "Статус")
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _create_activation_tab(self):
        """Создание вкладки активации"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Инструкции
        instructions_group = QGroupBox("📱 Как получить ключ")
        instructions_layout = QVBoxLayout()
        
        # Используем QTextBrowser вместо QTextEdit
        instructions_text = QTextBrowser()
        instructions_text.setReadOnly(True)
        instructions_text.setMaximumHeight(200)
        instructions_text.setOpenExternalLinks(False)  # Отключаем автоматическое открытие
        instructions_text.setHtml("""
        <ol>
        <li>Откройте <a href="https://t.me/zapretvpns_bot" style="color: #0088cc;">Telegram бота</a></li>
        <li>Выберите подходящий тариф</li>
        <li>Пополните баланс на нужную сумму</li>
        <li>Оплатите подписку с внутриботового баланса</li>
        <li>Получите ключ в боте через команду /newkey</li>
        <li>Введите ключ ниже</li>
        <li>ОБЯЗАТЕЛЬНО перезапустите приложение</li>
        </ol>
        """)
        # Обработчик клика по ссылке
        instructions_text.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))
        
        instructions_layout.addWidget(instructions_text)
        instructions_group.setLayout(instructions_layout)
        layout.addWidget(instructions_group)
        
        # Поле ввода ключа
        key_group = QGroupBox("🔑 Ключ активации")
        key_layout = QVBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setMinimumHeight(35)
        key_font = QFont()
        key_font.setPointSize(12)
        self.key_input.setFont(key_font)
        key_layout.addWidget(self.key_input)
        
        # Статус активации
        self.activation_status = QLabel("")
        self.activation_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activation_status.setWordWrap(True)
        self.activation_status.setMinimumHeight(30)
        key_layout.addWidget(self.activation_status)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # Кнопки
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.activate_btn = QPushButton("✨ Активировать ключ")
        self.activate_btn.setMinimumHeight(40)
        activate_font = QFont()
        activate_font.setPointSize(11)
        activate_font.setBold(True)
        self.activate_btn.setFont(activate_font)
        self.activate_btn.clicked.connect(self._activate_key)
        buttons_layout.addWidget(self.activate_btn)
        
        telegram_btn = QPushButton("🚀 Открыть Telegram бот")
        telegram_btn.setMinimumHeight(35)
        telegram_btn.clicked.connect(lambda: webbrowser.open("https://t.me/zapretvpns_bot"))
        buttons_layout.addWidget(telegram_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        return widget
    
    def _create_status_tab(self):
        """Создание вкладки статуса"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Статус подписки
        status_group = QGroupBox("📊 Статус подписки")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Проверка...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(60)
        status_font = QFont()
        status_font.setPointSize(12)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_label)
        
        self.status_details = QLabel("")
        self.status_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_details.setWordWrap(True)
        status_layout.addWidget(self.status_details)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Информация об устройстве
        device_group = QGroupBox("💻 Информация об устройстве")
        device_layout = QVBoxLayout()
        
        self.device_info = QLabel(f"ID устройства: {self.checker.device_id[:16]}...")
        device_layout.addWidget(self.device_info)
        
        saved_key = RegistryManager.get_key()
        if saved_key:
            self.key_info = QLabel(f"Сохраненный ключ: {saved_key[:4]}****")
            device_layout.addWidget(self.key_info)
        else:
            self.key_info = QLabel("Ключ не сохранен")
            device_layout.addWidget(self.key_info)
        
        last_check = RegistryManager.get_last_check()
        if last_check:
            self.last_check_info = QLabel(f"Последняя проверка: {last_check.strftime('%d.%m.%Y %H:%M')}")
            device_layout.addWidget(self.last_check_info)
        else:
            self.last_check_info = QLabel("Проверка не выполнялась")
            device_layout.addWidget(self.last_check_info)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Кнопки управления
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.refresh_btn = QPushButton("🔄 Обновить статус")
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.clicked.connect(self._check_status)
        buttons_layout.addWidget(self.refresh_btn)
        
        self.change_key_btn = QPushButton("🔑 Изменить ключ")
        self.change_key_btn.setMinimumHeight(35)
        self.change_key_btn.clicked.connect(self._change_key)
        buttons_layout.addWidget(self.change_key_btn)
        
        self.test_btn = QPushButton("🔗 Проверить соединение")
        self.test_btn.setMinimumHeight(35)
        self.test_btn.clicked.connect(self._test_connection)
        buttons_layout.addWidget(self.test_btn)
        
        extend_btn = QPushButton("💬 Продлить подписку")
        extend_btn.setMinimumHeight(35)
        extend_btn.clicked.connect(lambda: webbrowser.open("https://t.me/zapretvpns_bot"))
        buttons_layout.addWidget(extend_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        return widget
    
    def _check_saved_key(self):
        """Проверка сохраненного ключа"""
        saved_key = RegistryManager.get_key()
        if saved_key:
            self.tabs.setCurrentIndex(1)  # Переключаемся на вкладку статуса
            self._check_status()
        else:
            self.tabs.setCurrentIndex(0)  # Остаемся на вкладке активации
    
    def _activate_key(self):
        """Активация ключа"""
        key = self.key_input.text().strip()
        if not key:
            self.activation_status.setText("❌ Введите ключ активации")
            self.activation_status.setStyleSheet("color: red;")
            return
        
        # Блокируем кнопку
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("⏳ Активация...")
        self.activation_status.setText("🔄 Проверка ключа...")
        self.activation_status.setStyleSheet("color: blue;")
        
        # Запускаем в потоке
        self.current_thread = WorkerThread(self.checker.activate, args=(key,))
        self.current_thread.result_ready.connect(self._on_activation_complete)
        self.current_thread.error_occurred.connect(self._on_activation_error)
        self.current_thread.start()
    
    def _on_activation_complete(self, result):
        """Обработка результата активации"""
        success, message = result
        
        # Разблокируем кнопку
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("✨ Активировать ключ")
        
        if success:
            self.activation_status.setText("✅ Ключ успешно активирован!")
            self.activation_status.setStyleSheet("color: green;")
            # Обновляем информацию о ключе
            saved_key = RegistryManager.get_key()
            if saved_key:
                self.key_info.setText(f"Сохраненный ключ: {saved_key[:4]}****")
            # Переключаемся на вкладку статуса
            self.tabs.setCurrentIndex(1)
            self._check_status()
        else:
            self.activation_status.setText(f"❌ {message}")
            self.activation_status.setStyleSheet("color: red;")
    
    def _on_activation_error(self, error):
        """Обработка ошибки активации"""
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("✨ Активировать ключ")
        self.activation_status.setText(f"❌ Ошибка: {error}")
        self.activation_status.setStyleSheet("color: red;")
    
    def _check_status(self):
        """Проверка статуса подписки"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Проверка...")
        self.status_label.setText("🔄 Проверка статуса...")
        self.status_details.setText("")
        
        self.current_thread = WorkerThread(self.checker.check_device_activation)
        self.current_thread.result_ready.connect(self._on_status_complete)
        self.current_thread.error_occurred.connect(self._on_status_error)
        self.current_thread.start()
    
    def _on_status_complete(self, result):
        """Обработка результата проверки статуса"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Обновить статус")
        
        # Обновляем время последней проверки
        last_check = RegistryManager.get_last_check()
        if last_check:
            self.last_check_info.setText(f"Последняя проверка: {last_check.strftime('%d.%m.%Y %H:%M')}")
        
        # ✅ КРИТИЧНО: Проверяем что result не None и это словарь
        if result is None:
            self.status_label.setText("❌ Ошибка получения статуса")
            self.status_label.setStyleSheet("color: red;")
            self.status_details.setText("Сервер вернул пустой ответ")
            self.status_details.setStyleSheet("color: gray;")
            return
        
        if not isinstance(result, dict):
            self.status_label.setText("❌ Неверный формат ответа")
            self.status_label.setStyleSheet("color: red;")
            self.status_details.setText(f"Получен: {type(result).__name__}")
            self.status_details.setStyleSheet("color: gray;")
            return
        
        # ✅ ДОБАВИТЬ: Проверяем наличие ключей
        if 'activated' not in result:
            self.status_label.setText("❌ Неполный ответ сервера")
            self.status_label.setStyleSheet("color: red;")
            self.status_details.setText("Отсутствует поле 'activated'")
            self.status_details.setStyleSheet("color: gray;")
            return
        
        # Теперь безопасно обращаемся к result
        try:
            if result['activated']:
                self.status_label.setText("✅ Подписка активна")
                self.status_label.setStyleSheet("color: green;")
                
                days_remaining = result.get('days_remaining')
                if days_remaining is not None:
                    if days_remaining > 30:
                        self.status_details.setText(f"Осталось дней: {days_remaining}")
                        self.status_details.setStyleSheet("color: green;")
                    elif days_remaining > 7:
                        self.status_details.setText(f"⚠️ Осталось дней: {days_remaining}\nРекомендуем продлить подписку")
                        self.status_details.setStyleSheet("color: orange;")
                    else:
                        self.status_details.setText(f"⚠️ Осталось дней: {days_remaining}\nСрочно продлите подписку!")
                        self.status_details.setStyleSheet("color: red;")
                else:
                    status_msg = result.get('status', 'Статус неизвестен')
                    self.status_details.setText(status_msg)
                    self.status_details.setStyleSheet("")
            else:
                self.status_label.setText("❌ Подписка не активна")
                self.status_label.setStyleSheet("color: red;")
                status_msg = result.get('status', 'Подписка не найдена')
                self.status_details.setText(status_msg)
                self.status_details.setStyleSheet("color: gray;")
                
        except Exception as e:
            # Дополнительная защита
            self.status_label.setText("❌ Ошибка обработки ответа")
            self.status_label.setStyleSheet("color: red;")
            self.status_details.setText(f"Ошибка: {str(e)}")
            self.status_details.setStyleSheet("color: gray;")
    
    def _on_status_error(self, error):
        """Обработка ошибки проверки статуса"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Обновить статус")
        self.status_label.setText(f"❌ Ошибка проверки")
        self.status_label.setStyleSheet("color: red;")
        self.status_details.setText(error)
        self.status_details.setStyleSheet("color: gray;")
    
    def _test_connection(self):
        """Тест соединения"""
        self.test_btn.setEnabled(False)
        self.test_btn.setText("⏳ Проверка...")
        
        self.current_thread = WorkerThread(self.checker.test_connection)
        self.current_thread.result_ready.connect(self._on_connection_test_complete)
        self.current_thread.error_occurred.connect(self._on_connection_test_error)
        self.current_thread.start()
    
    def _on_connection_test_complete(self, result):
        """Обработка результата теста соединения"""
        success, message = result
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🔗 Проверить соединение")
        
        if success:
            QMessageBox.information(self, "Успех", f"✅ {message}")
        else:
            QMessageBox.warning(self, "Ошибка", f"❌ {message}")
    
    def _on_connection_test_error(self, error):
        """Обработка ошибки теста соединения"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🔗 Проверить соединение")
        QMessageBox.critical(self, "Ошибка", f"Ошибка теста: {error}")
    
    def _change_key(self):
        """Изменение ключа"""
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Вы уверены, что хотите изменить ключ?\nТекущий ключ будет удален.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Очищаем сохраненный ключ
            RegistryManager.delete_key()
            # Очищаем поле ввода
            self.key_input.clear()
            self.activation_status.setText("")
            # Обновляем информацию
            self.key_info.setText("Ключ не сохранен")
            # Переключаемся на вкладку активации
            self.tabs.setCurrentIndex(0)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.quit()
            self.current_thread.wait()
        event.accept()