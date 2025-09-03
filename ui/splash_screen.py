# ui/splash_screen.py
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PyQt6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QLinearGradient
import qtawesome as qta
from config import APP_VERSION, CHANNEL
from log import log

class SplashScreen(QWidget):
    """Современный загрузочный экран для Zapret"""
    
    load_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_ui()
        
        # Флаг завершения загрузки
        self._loading_complete = False
        
    def init_ui(self):
        """Инициализация интерфейса"""
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Контейнер с фоном
        self.container = QWidget()
        self.container.setObjectName("splashContainer")
        self.container.setStyleSheet("""
            #splashContainer {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1e3c72,
                    stop: 0.5 #2a5298,
                    stop: 1 #7e8ba3
                );
                border-radius: 20px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)
        
        # Логотип/Иконка
        icon_label = QLabel()
        icon = qta.icon('fa5s.shield-alt', color='white')
        pixmap = icon.pixmap(96, 96)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(icon_label)
        
        # Заголовок
        title = QLabel(f"Zapret v{APP_VERSION}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        container_layout.addWidget(title)
        
        # Подзаголовок
        subtitle = QLabel(f"Канал: {CHANNEL}")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        container_layout.addWidget(subtitle)
        
        # Разделитель
        container_layout.addSpacing(20)
        
        # Статус загрузки
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 10px;
            }
        """)
        container_layout.addWidget(self.status_label)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 10px;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0.5, x2: 1, y2: 0.5,
                    stop: 0 #4CAF50,
                    stop: 0.5 #8BC34A,
                    stop: 1 #CDDC39
                );
                border-radius: 10px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Детальная информация
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        container_layout.addWidget(self.detail_label)
        
        # Добавляем растяжку
        container_layout.addStretch()
        
        # Добавляем контейнер в основной layout
        layout.addWidget(self.container)
        
        # Устанавливаем размер окна
        self.setFixedSize(450, 350)
        
        # Центрируем окно
        self.center_on_screen()
        
        # Анимация появления
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in()
        
    def center_on_screen(self):
        """Центрирует окно на экране"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def fade_in(self):
        """Анимация появления"""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()
        
    def fade_out_and_close(self):
        """Анимация исчезновения и закрытие"""
        if self._loading_complete:
            return  # Уже закрываемся
            
        self._loading_complete = True
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self._on_fade_complete)
        self.fade_animation.start()
        
    def _on_fade_complete(self):
        """Обработчик завершения анимации"""
        self.load_complete.emit()
        self.close()
        
    def set_progress(self, value: int, status: str = "", detail: str = ""):
        """Обновляет прогресс загрузки"""
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)
        if detail:
            self.detail_label.setText(detail)
            
        # Если загрузка завершена
        if value >= 100 and not self._loading_complete:
            QTimer.singleShot(500, self.fade_out_and_close)
            
    def set_status(self, text: str):
        """Обновляет статус"""
        self.status_label.setText(text)
        
    def set_detail(self, text: str):
        """Обновляет детальную информацию"""
        self.detail_label.setText(text)
        
    def show_error(self, error: str):
        """Показывает ошибку"""
        self.status_label.setText(f"❌ Ошибка: {error}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ff5252;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 10px;
            }
        """)
        # Автоматически закрываем через 3 секунды при ошибке
        QTimer.singleShot(3000, self.fade_out_and_close)