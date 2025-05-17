# connection_test.py
import os
import subprocess
import logging
import requests, webbrowser
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

class ConnectionTestWorker(QThread):
    """Рабочий поток для выполнения тестов соединения."""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    # В методе __init__ обновите настройку логирования:
    def __init__(self, test_type="all"):
        super().__init__()
        self.test_type = test_type
        self.log_filename = "connection_test.log"
        
        # Настройка логгирования с явным указанием кодировки
        # Удаляем существующие обработчики, если они есть
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Настраиваем новый обработчик с правильной кодировкой
        logging.basicConfig(
            filename=self.log_filename,
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
        # Добавляем специальный обработчик с указанной кодировкой
        file_handler = logging.FileHandler(self.log_filename, 'w', 'utf-8')
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
        logging.getLogger().handlers = [file_handler]
    
    def log_message(self, message):
        """Записывает сообщение в лог и отправляет сигнал в GUI."""
        logging.info(message)
        self.update_signal.emit(message)
    
    def ping(self, host, count=4):
        """Выполняет ping до указанного хоста."""
        try:
            self.log_message(f"Проверка доступности для URL: {host}")
            
            # Параметры для Windows
            command = ["ping", "-n", str(count), host]
            
            # Запускаем ping без отображения консоли
            if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
                subprocess.CREATE_NO_WINDOW = 0x08000000
            
            result = subprocess.run(command, capture_output=True, text=True, 
                                creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout
            
            # Анализируем результат для Windows
            if "TTL=" in output:
                success_count = output.count("TTL=")
                self.log_message(f"{host}: Отправлено: {count}, Получено: {success_count}")
                for line in output.splitlines():
                    if "TTL=" in line:
                        # Извлекаем время из строки
                        try:
                            ms = line.split("время=")[1].split("мс")[0].strip()
                            self.log_message(f"\tДоступен (Latency: {ms}ms)")
                        except:
                            self.log_message(f"\tДоступен")
                    elif "узел недоступен" in line.lower() or "превышен интервал" in line.lower():
                        self.log_message(f"\tНедоступен")
            else:
                self.log_message(f"{host}: Отправлено: {count}, Получено: 0")
                self.log_message(f"\tНедоступен")
                
            return True
        except Exception as e:
            self.log_message(f"Ошибка при проверке {host}: {str(e)}")
            return False
    
    def check_discord(self):
        """Проверяет доступность Discord."""
        self.log_message("Запуск проверки доступности Discord:")
        self.ping("discord.com")
        self.log_message("")
        self.log_message("Проверка доступности Discord завершена.")
    
    def check_youtube(self):
        """Проверяет доступность YouTube и связанных ресурсов."""
        youtube_ips = [
            "212.188.49.81",
            "74.125.168.135",
            "173.194.140.136",
            "172.217.131.103"
        ]
        
        youtube_addresses = [
            "rr6.sn-jvhnu5g-n8v6.googlevideo.com",
            "rr4---sn-jvhnu5g-c35z.googlevideo.com",
            "rr4---sn-jvhnu5g-n8ve7.googlevideo.com",
            "rr2---sn-aigl6nze.googlevideo.com",
            "rr7---sn-jvhnu5g-c35e.googlevideo.com",
            "rr3---sn-jvhnu5g-c35d.googlevideo.com",
            "rr3---sn-q4fl6n6r.googlevideo.com"
        ]
        
        self.log_message("Запуск проверки доступности YouTube:")
        self.ping("www.youtube.com")
        
        for ip in youtube_ips:
            self.log_message(f"Проверка доступности для IP: {ip}")
            self.ping(ip)
        
        for address in youtube_addresses:
            self.ping(address)
        
        self.log_message("")
        
        # Проверяем jnn-pa.googleapis.com через HTTP запрос
        try:
            response = requests.get("https://jnn-pa.googleapis.com", timeout=5)
            self.log_message(f"Запрос https://jnn-pa.googleapis.com успешен: {response.status_code}")
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                error_msg = "Ошибка 403: ВЫ НЕ СМОЖЕТЕ СМОТРЕТЬ ЮТУБ с помощью сайта youtube.com ЧЕРЕЗ ZAPRET! Вам следует запустить Zapret, а после скачать Freetube по ссылке freetubeapp.io и смотреть видео там. Или скачайте для своего браузера скрипт Tampermonkey по ссылке: https://zapret.now.sh/script.user.js"
                self.log_message(error_msg)
                
                # Вопрос о дополнительной информации выводится в GUI
                self.update_signal.emit("YOUTUBE_ERROR_403")
            else:
                self.log_message(f"Ошибка при запросе: {str(e)}")
        except requests.exceptions.RequestException as e:
            if "404" in str(e):
                self.log_message(f"Ошибка при запросе: {str(e)}")
                success_msg = "Если Вы видите ошибку 404, то Вы успешно сможете разблокировать YouTube через Zapret! Ничего дополнительно скачивать не требуется."
                self.log_message(success_msg)
            else:
                self.log_message(f"Ошибка при запросе: {str(e)}")
        
        self.log_message("Проверка доступности YouTube завершена.")
        self.log_message(f"Лог сохранён в файле {os.path.abspath(self.log_filename)}")
    
    def run(self):
        """Выполнение тестов в отдельном потоке."""
        self.log_message(f"Запуск тестирования соединения ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        self.log_message("="*50)
        
        if self.test_type == "discord":
            self.check_discord()
        elif self.test_type == "youtube":
            self.check_youtube()
        elif self.test_type == "all":
            self.check_discord()
            self.log_message("\n" + "="*30 + "\n")
            self.check_youtube()
        
        self.log_message("="*50)
        self.log_message("Тестирование завершено")
        self.finished_signal.emit()

class ConnectionTestDialog(QDialog):
    """Диалоговое окно для тестирования соединений."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Тестирование соединения")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.init_ui()
        self.worker = None
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = QVBoxLayout()
        
        # Комбобокс для выбора теста
        self.test_combo = QComboBox(self)
        self.test_combo.addItems(["Все тесты", "Discord", "YouTube"])
        layout.addWidget(self.test_combo)
        
        # Кнопки
        self.start_button = QPushButton("Начать тестирование", self)
        self.start_button.clicked.connect(self.start_test)
        layout.addWidget(self.start_button)
        
        self.save_log_button = QPushButton("Сохранить лог", self)
        self.save_log_button.clicked.connect(self.save_log)
        self.save_log_button.setEnabled(False)
        layout.addWidget(self.save_log_button)
        
        # Текстовое поле для вывода результатов
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def start_test(self):
        """Запускает выбранный тест."""
        selection = self.test_combo.currentText()
        test_type = "all"
        
        if selection == "Discord":
            test_type = "discord"
        elif selection == "YouTube":
            test_type = "youtube"
        
        # Очищаем текстовое поле
        self.result_text.clear()
        
        # Отключаем кнопки
        self.start_button.setEnabled(False)
        self.test_combo.setEnabled(False)
        
        # Создаем и запускаем рабочий поток
        self.worker = ConnectionTestWorker(test_type)
        self.worker.update_signal.connect(self.update_result)
        self.worker.finished_signal.connect(self.on_test_finished)
        self.worker.start()
    
    def update_result(self, message):
        """Обновляет текстовое поле с результатами теста."""
        if message == "YOUTUBE_ERROR_403":
            # Специальная обработка для ошибки 403 YouTube
            reply = QMessageBox.question(
                self, 
                "Ошибка YouTube",
                "Ошибка 403: YouTube требует дополнительной настройки. Узнать подробнее?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open("https://github.com/youtubediscord/youtube_59second")
        else:
            # Добавляем текст в окно результатов
            self.result_text.append(message)
            # Прокручиваем до конца
            self.result_text.verticalScrollBar().setValue(
                self.result_text.verticalScrollBar().maximum()
            )
    
    def on_test_finished(self):
        """Обработчик завершения тестов."""
        self.start_button.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.save_log_button.setEnabled(True)
    
    def save_log(self):
        """Сохраняет лог в текстовый файл."""
        if not os.path.exists("connection_test.log"):
            QMessageBox.warning(self, "Ошибка", "Файл журнала не найден.")
            return
        
        try:
            save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connection_test_saved.log")
            
            # Чтение и запись с явным указанием кодировки UTF-8
            with open("connection_test.log", "r", encoding="utf-8") as src, \
                open(save_path, "w", encoding="utf-8") as dest:
                dest.write(src.read())
            
            QMessageBox.information(
                self, 
                "Сохранение успешно", 
                f"Лог сохранен в файл:\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ошибка при сохранении", 
                f"Не удалось сохранить файл журнала:\n{str(e)}"
            )