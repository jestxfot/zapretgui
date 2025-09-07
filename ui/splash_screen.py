# ui/splash_screen.py
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PyQt6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QIcon
import qtawesome as qta
import os
from config import APP_VERSION, CHANNEL, ICON_PATH, ICON_TEST_PATH
from log import log

class SplashScreen(QWidget):
    """Загрузочный экран как виджет внутри главного окна"""
    
    load_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self._loading_complete = False
        
    def init_ui(self):
        """Инициализация интерфейса"""
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Устанавливаем фоновый градиент для всего виджета
        self.setStyleSheet("""
            SplashScreen {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1e3c72,
                    stop: 0.5 #2a5298,
                    stop: 1 #7e8ba3
                );
            }
        """)
        
        # Центральный контейнер
        central_container = QWidget()
        central_layout = QVBoxLayout(central_container)
        central_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_layout.setSpacing(20)
        
        # Логотип из ICO файла
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Определяем какую иконку использовать
        icon_path = ICON_TEST_PATH if CHANNEL.lower() == "test" else ICON_PATH
        
        # Проверяем существование файла
        if os.path.exists(icon_path):
            # Загружаем иконку из ICO файла
            icon = QIcon(icon_path)
            # Получаем pixmap нужного размера (150x150 для большего логотипа)
            pixmap = icon.pixmap(150, 150)
            
            # Если нужно, можно добавить эффект тени или свечения
            enhanced_pixmap = self._add_glow_effect(pixmap)
            icon_label.setPixmap(enhanced_pixmap if enhanced_pixmap else pixmap)
            
            log(f"Загружена иконка из {icon_path}", "DEBUG")
        else:
            # Fallback на иконку щита если файл не найден
            log(f"Иконка не найдена: {icon_path}, используем fallback", "WARNING")
            icon = qta.icon('fa5s.shield-alt', color='white')
            pixmap = icon.pixmap(150, 150)
            icon_label.setPixmap(pixmap)
        
        central_layout.addWidget(icon_label)
        
        # Заголовок
        title = QLabel(f"Zapret v{APP_VERSION}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 36px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 10px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
        """)
        central_layout.addWidget(title)
        
        # Подзаголовок
        subtitle = QLabel(f"Канал: {CHANNEL}")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        central_layout.addWidget(subtitle)
        
        # Разделитель
        central_layout.addSpacing(40)
        
        # Контейнер для прогресса
        progress_container = QWidget()
        progress_container.setMaximumWidth(450)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(20, 0, 20, 0)  # Уменьшаем отступы по бокам

        # Статус загрузки
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 10px;
            }
        """)
        progress_layout.addWidget(self.status_label)
        
        # Прогресс-бар (исправленные стили без белых артефактов)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(35)
        self.progress_bar.setMinimumWidth(400) # Уменьшаем до 400
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(0, 0, 0, 0.25);
                border: none;  /* Убираем границу совсем */
                border-radius: 17px;
                padding: 0px;
                margin: 0px;
                /* Добавляем внутреннюю тень для глубины */
                background-clip: padding-box;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0.5, x2: 1, y2: 0.5,
                    stop: 0 #2ECC71,
                    stop: 0.3 #27AE60,
                    stop: 0.6 #4CAF50,
                    stop: 1 #8BC34A
                );
                border-radius: 17px;
                /* Убираем любые отступы между chunk и контейнером */
                subcontrol-position: center;
                subcontrol-origin: content;
            }
        """)
        progress_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Процентный индикатор
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 5px;
            }
        """)
        progress_layout.addWidget(self.percent_label)
        
        # Детальная информация
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 5px;
            }
        """)
        progress_layout.addWidget(self.detail_label)
        
        central_layout.addWidget(progress_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем центральный контейнер в основной layout
        layout.addWidget(central_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Анимация появления
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in()
    
    def _add_glow_effect(self, pixmap):
        """Добавляет эффект свечения к иконке"""
        try:
            # Создаем новый pixmap с дополнительным пространством для свечения
            glow_size = 10
            from PyQt6.QtCore import QSize
            new_size = pixmap.size().expandedTo(pixmap.size() + QSize(glow_size * 2, glow_size * 2))
            result = QPixmap(new_size)
            result.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(result)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Рисуем мягкое свечение
            for i in range(glow_size, 0, -1):
                opacity = 0.03 * (glow_size - i)
                painter.setOpacity(opacity)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, int(255 * opacity)))
                
                # Рисуем размытый круг для свечения
                painter.drawEllipse(
                    result.rect().center(),
                    pixmap.width() // 2 + i,
                    pixmap.height() // 2 + i
                )
            
            # Рисуем основную иконку
            painter.setOpacity(1.0)
            painter.drawPixmap(
                (result.width() - pixmap.width()) // 2,
                (result.height() - pixmap.height()) // 2,
                pixmap
            )
            
            painter.end()
            return result
            
        except Exception as e:
            log(f"Ошибка добавления эффекта свечения: {e}", "DEBUG")
            return None
        
    def fade_in(self):
        """Анимация появления"""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()
        
    def fade_out(self):
        """Анимация исчезновения"""
        if self._loading_complete:
            return
            
        self._loading_complete = True
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self.load_complete.emit)
        self.fade_animation.start()
        
    def set_progress(self, value: int, status: str = "", detail: str = ""):
        """Обновляет прогресс загрузки"""
        # Обновляем значение прогресс-бара
        self.progress_bar.setValue(min(value, 100))
        
        # Обновляем процентный индикатор
        self.percent_label.setText(f"{min(value, 100)}%")
        
        # Обновляем тексты
        if status:
            self.status_label.setText(status)
        if detail:
            self.detail_label.setText(detail)
        
        # Закрываем ТОЛЬКО при значении ровно 100
        if value == 100 and not self._loading_complete:
            log(f"SplashScreen: закрытие при прогрессе 100% (status: {status})", "DEBUG")
            QTimer.singleShot(500, self.fade_out)
        elif value > 100:
            # Если больше 100, устанавливаем 99 чтобы не закрыть преждевременно
            self.progress_bar.setValue(99)
            self.percent_label.setText("99%")
            
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
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 10px;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
            }
        """)
        self.percent_label.setText("Ошибка")
        self.percent_label.setStyleSheet("""
            QLabel {
                color: #ff5252;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        # Автоматически скрываем через 3 секунды при ошибке
        QTimer.singleShot(3000, self.fade_out)