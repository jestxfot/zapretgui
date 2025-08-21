# dns_check_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTextEdit, QLabel, QProgressBar, QFrame)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QTextCursor
from dns_checker import DNSChecker
import socket

class DNSCheckWorker(QObject):
    """Worker для выполнения DNS проверки в отдельном потоке"""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    
    def run(self):
        try:
            checker = DNSChecker()
            results = checker.check_dns_poisoning(log_callback=self.update_signal.emit)
            self.finished_signal.emit(results)
        except Exception as e:
            self.update_signal.emit(f"❌ Ошибка: {str(e)}")
            self.finished_signal.emit({})

class DNSCheckDialog(QDialog):
    """Диалог для проверки DNS подмены"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Проверка DNS подмены")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        self.init_ui()
        self.worker = None
        self.thread = None
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Заголовок
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #2196F3;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        title_layout = QVBoxLayout(title_frame)
        
        title = QLabel("🔍 Проверка DNS подмены провайдером")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: white;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("Проверка резолвинга доменов YouTube и Discord через различные DNS серверы")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 10pt; color: white;")
        title_layout.addWidget(subtitle)
        
        layout.addWidget(title_frame)
        
        # Информационная панель
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        info_text = QLabel(
            "Эта проверка поможет определить:\n"
            "• Блокирует ли провайдер сайты через DNS подмену\n"
            "• Какие DNS серверы возвращают корректные адреса\n"
            "• Какой DNS сервер рекомендуется использовать"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #333; font-size: 9pt;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_frame)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("Готово к проверке")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: #666; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Текстовое поле для результатов
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 9))
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.result_text, 1)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.check_button = QPushButton("🔍 Начать проверку")
        self.check_button.setMinimumHeight(35)
        self.check_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.check_button.clicked.connect(self.start_check)
        button_layout.addWidget(self.check_button)
        
        self.save_button = QPushButton("💾 Сохранить результаты")
        self.save_button.setMinimumHeight(35)
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_button.clicked.connect(self.save_results)
        button_layout.addWidget(self.save_button)
        
        self.close_button = QPushButton("❌ Закрыть")
        self.close_button.setMinimumHeight(35)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c41e3a;
            }
        """)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def start_check(self):
        """Начинает проверку DNS"""
        if self.thread and self.thread.isRunning():
            return
            
        self.result_text.clear()
        self.check_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.status_label.setText("🔄 Выполняется проверка DNS...")
        self.status_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        
        # Создаем поток и worker
        self.thread = QThread()
        self.worker = DNSCheckWorker()
        self.worker.moveToThread(self.thread)
        
        # Подключаем сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.update_signal.connect(self.append_result)
        self.worker.finished_signal.connect(self.on_check_finished)
        
        # Запускаем
        self.thread.start()
    
    def append_result(self, text):
        """Добавляет текст в результаты с форматированием"""
        # Применяем цветовое форматирование
        if "✅" in text:
            color = "#4CAF50"
        elif "❌" in text:
            color = "#f44336"
        elif "⚠️" in text:
            color = "#ff9800"
        elif "🚫" in text:
            color = "#e91e63"
        elif "🔍" in text or "📊" in text:
            color = "#2196F3"
        elif "=" in text and len(text) > 20:
            color = "#666666"
        else:
            color = "#d4d4d4"
        
        # Форматируем текст
        formatted_text = f'<span style="color: {color};">{text}</span>'
        
        # Добавляем в текстовое поле
        cursor = self.result_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(formatted_text + "<br>")
        
        # Автопрокрутка
        self.result_text.verticalScrollBar().setValue(
            self.result_text.verticalScrollBar().maximum()
        )
    
    def on_check_finished(self, results):
        """Обработчик завершения проверки"""
        self.check_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Обновляем статус
        if results and results.get('summary', {}).get('dns_poisoning_detected'):
            self.status_label.setText("⚠️ Обнаружена DNS подмена!")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        else:
            self.status_label.setText("✅ DNS подмены не обнаружено")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        
        # Очистка потока
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread.deleteLater()
            self.thread = None
        
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
    
    def save_results(self):
        """Сохраняет результаты в файл"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from datetime import datetime
        import os
        
        # Выбираем путь для сохранения
        default_filename = f"dns_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты DNS проверки",
            default_filename,
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Получаем текст без HTML тегов
                plain_text = self.result_text.toPlainText()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("DNS CHECK RESULTS\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(plain_text)
                
                QMessageBox.information(
                    self,
                    "Сохранено",
                    f"Результаты сохранены в:\n{file_path}"
                )
                
                # Открываем папку с файлом
                os.startfile(os.path.dirname(file_path))
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось сохранить файл:\n{str(e)}"
                )
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        # Останавливаем поток если он работает
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        
        event.accept()

    def add_quick_check_button(self):
        """Добавляет кнопку быстрой проверки системного DNS"""
        quick_check_btn = QPushButton("⚡ Быстрая проверка системного DNS")
        quick_check_btn.clicked.connect(self.quick_dns_check)
        # Добавьте эту кнопку в layout

    def quick_dns_check(self):
        """Выполняет быструю проверку только системного DNS"""
        self.result_text.clear()
        self.append_result("⚡ БЫСТРАЯ ПРОВЕРКА СИСТЕМНОГО DNS")
        self.append_result("=" * 40)
        
        test_domains = {
            'YouTube': 'www.youtube.com',
            'Discord': 'discord.com',
            'Google': 'google.com'
        }
        
        for name, domain in test_domains.items():
            try:
                ip = socket.gethostbyname(domain)
                self.append_result(f"{name} ({domain}): {ip} ✅")
            except Exception as e:
                self.append_result(f"{name} ({domain}): ❌ Ошибка: {e}")