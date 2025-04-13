from PyQt5.QtWidgets import QDialog, QProgressBar, QLabel, QVBoxLayout, QPushButton, QApplication, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer

class StrategyChangeDialog(QDialog):
    """Диалог с прогрессом при смене стратегии обхода DPI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Смена стратегии запрета")
        self.setFixedSize(400, 200)
        
        # Используем WindowModal вместо ApplicationModal для более мягкой блокировки
        # И убираем WindowStaysOnTopHint чтобы избежать проблем с перекрытием
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setWindowModality(Qt.WindowModal)  # Блокирует только родительское окно
        
        # Простой и компактный интерфейс для быстрой отрисовки
        layout = QVBoxLayout(self)
        
        # Заголовок с подсказкой, что происходит
        self.title_label = QLabel("Пожалуйста, подождите...")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Текущее действие
        self.status_label = QLabel("Переключение стратегии обхода блокировок...")
        self.status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Добавляем отступ
        layout.addSpacing(10)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Детальная информация
        self.details_label = QLabel("Это может занять некоторое время")
        self.details_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.details_label)
        
        # Добавляем отступ перед кнопками
        layout.addSpacing(10)
        
        # Кнопка отмены (изначально скрыта, будет показана в конце)
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.safe_close)
        self.close_button.setVisible(False)  # Изначально скрыта
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        # Таймер для анимации прогресса
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.auto_progress = 0
        
        # Храним флаг, чтобы знать когда операция завершена
        self.operation_completed = False
    
    def safe_close(self):
        """Безопасно закрывает диалог без закрытия родительского окна"""
        self.accept()
    
    def start_progress(self, start_value=0):
        """Запускает таймер имитации прогресса"""
        self.auto_progress = start_value
        self.progress_bar.setValue(start_value)
        self.timer.start(300)
        self.close_button.setVisible(False)
        self.operation_completed = False
    
    def stop_progress(self):
        """Останавливает таймер имитации прогресса"""
        self.timer.stop()
    
    def set_progress(self, value):
        """Устанавливает текущий прогресс"""
        self.auto_progress = value
        self.progress_bar.setValue(value)
        QApplication.processEvents()  # Обновляем UI
    
    def set_status(self, text):
        """Устанавливает текущий статус операции"""
        self.status_label.setText(text)
        QApplication.processEvents()  # Обновляем UI
    
    def set_details(self, text):
        """Устанавливает детальную информацию"""
        self.details_label.setText(text)
        QApplication.processEvents()  # Обновляем UI
    
    def update_progress(self):
        """Обновляет прогресс на небольшое значение"""
        if self.auto_progress < 95:
            self.auto_progress += 1
            self.progress_bar.setValue(self.auto_progress)
    
    def complete(self):
        """Отмечает операцию как завершенную и показывает кнопку закрытия"""
        self.stop_progress()
        self.set_progress(100)
        self.set_status("Операция завершена")
        self.operation_completed = True
        self.close_button.setVisible(True)  # Показываем кнопку закрытия
        QApplication.processEvents()  # Обновляем UI
    
    # Переопределяем метод, который вызывается при нажатии кнопки X или клавиши Esc
    def reject(self):
        """Переопределяем метод reject, чтобы предотвратить случайное закрытие"""
        if self.operation_completed:
            self.accept()  # Безопасно закрываем только после завершения операции
        else:
            # Если операция не завершена, показываем предупреждение
            from PyQt5.QtWidgets import QMessageBox
            response = QMessageBox.question(
                self, 
                "Прервать операцию?", 
                "Вы уверены, что хотите прервать смену стратегии? Это может привести к нестабильной работе.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if response == QMessageBox.Yes:
                self.accept()  # Закрываем диалог только если пользователь подтвердил