# ui/splash_screen.py
"""
Splash Screen в стиле Windows 11 Fluent Design.
Мягкие цвета, плавные анимации, полупрозрачность.
"""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect, QApplication, QFrame
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QIcon, QTransform, QPen, QPainterPath
import qtawesome as qta
import os
import math
import threading
from config import APP_VERSION, CHANNEL, ICON_PATH, ICON_TEST_PATH
from log import log

# ═══════════════════════════════════════════════════════════════════════════════
# ЦВЕТОВАЯ ПАЛИТРА - Windows 11 Fluent (мягкие, приглушённые тона)
# ═══════════════════════════════════════════════════════════════════════════════
FLUENT_ACCENT = "#60cdff"           # Основной акцент (ui-designer.md)
FLUENT_ACCENT_LIGHT = "#8ad9ff"     # Светлее для glow
FLUENT_ACCENT_DARK = "#3fbde8"      # Темнее для pressed
FLUENT_BG = "28, 28, 28"            # BG_PRIMARY (приближено)
FLUENT_BG_LIGHT = "32, 32, 32"      # Чуть светлее для градиента
FLUENT_BORDER = "255, 255, 255"     # Для rgba бордеров в стилях
FLUENT_TEXT = "#ffffff"             # Белый текст
FLUENT_TEXT_SECONDARY = "rgba(255, 255, 255, 0.7)"  # Вторичный текст


class AnimatedIconWidget(QWidget):
    """Виджет с анимированной иконкой - минималистичная версия для Fluent Design"""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.rotation_angle = 0.0
        self.scale_factor = 0.85
        self.target_scale = 1.0

        # Защита от конкурентного рисования
        self._paint_lock = threading.Lock()
        self._is_destroyed = False

        # Размер виджета с небольшим запасом
        size = int(pixmap.width() * 1.4)
        self.setFixedSize(size, size)

        # Таймер анимации (реже для производительности)
        self.rotation_timer = QTimer(self)
        self.rotation_timer.timeout.connect(self._update_rotation)
        self.rotation_timer.start(25)  # ~40 FPS вместо 60

        # Параметры - более плавные
        self.rotation_speed = 0.3  # Медленнее вращение
        self.pulse_phase = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0
        self.progress = 0

        # Мягкий ореол
        self.glow_phase = 0.0

        # Одно кольцо вместо трёх (минимализм)
        self.energy_rings = [{'phase': 0.0, 'speed': 0.03}]
        
    def _update_rotation(self):
        """Обновление анимации - плавная версия"""
        self.rotation_angle = (self.rotation_angle + self.rotation_speed) % 360
        self.pulse_phase += 0.04  # Медленнее пульсация
        self.glow_phase += 0.06

        # Обновляем кольца энергии
        for ring in self.energy_rings:
            ring['phase'] += ring['speed']

        # Убрана тряска - более спокойная анимация
        self.shake_offset_x = 0
        self.shake_offset_y = 0

        self.update()
        
    def set_progress(self, progress: int):
        """Обновляет состояние в зависимости от прогресса - плавная версия"""
        progress = max(0, min(100, progress))
        self.progress = progress

        # Плавный рост масштаба
        self.scale_factor = 0.85 + (progress / 100.0) * 0.15

        # Вращение почти постоянное (минимальные изменения)
        self.rotation_speed = 0.3 + (progress / 100.0) * 0.2
        
    def paintEvent(self, event):
        """Отрисовка иконки - минималистичная версия Fluent Design"""
        if self._is_destroyed:
            return

        if not self._paint_lock.acquire(blocking=False):
            return

        try:
            painter = QPainter(self)
            if not painter.isActive():
                return

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            center_x = self.width() / 2
            center_y = self.height() / 2

            # Мягкое кольцо (одно, тонкое)
            if self.progress > 5:
                for ring in self.energy_rings:
                    ring_progress = (math.sin(ring['phase']) + 1) / 2
                    base_size = self.original_pixmap.width() * self.scale_factor
                    ring_size = int(base_size * (1.0 + ring_progress * 0.4))
                    ring_alpha = int(30 * (1 - ring_progress) * min(1.0, self.progress / 30))

                    if ring_alpha > 0:
                        # ACCENT_CYAN вместо синего
                        ring_pen = QPen(QColor(96, 205, 255, ring_alpha), 1)
                        painter.setPen(ring_pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawEllipse(
                            int(center_x - ring_size/2),
                            int(center_y - ring_size/2),
                            ring_size, ring_size
                        )

            # Мягкий ореол (subtle glow)
            if self.progress > 10:
                glow_size = int(self.original_pixmap.width() * self.scale_factor * 1.3)
                glow_alpha = int(20 + 15 * math.sin(self.glow_phase))

                glow_gradient = QLinearGradient(
                    center_x - glow_size/2, center_y - glow_size/2,
                    center_x + glow_size/2, center_y + glow_size/2
                )
                # ACCENT_CYAN
                glow_gradient.setColorAt(0.0, QColor(96, 205, 255, 0))
                glow_gradient.setColorAt(0.5, QColor(96, 205, 255, glow_alpha))
                glow_gradient.setColorAt(1.0, QColor(96, 205, 255, 0))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_gradient)
                painter.drawEllipse(
                    int(center_x - glow_size/2),
                    int(center_y - glow_size/2),
                    glow_size, glow_size
                )

            # Минимальная пульсация
            pulse = math.sin(self.pulse_phase) * 0.01
            current_scale = self.scale_factor + pulse

            # Трансформация иконки
            transform = QTransform()
            transform.translate(center_x, center_y)
            transform.rotate(self.rotation_angle)
            transform.scale(current_scale, current_scale)
            transform.translate(-self.original_pixmap.width() / 2, -self.original_pixmap.height() / 2)

            painter.setTransform(transform)
            painter.drawPixmap(0, 0, self.original_pixmap)
            painter.end()

        except Exception:
            pass
        finally:
            self._paint_lock.release()
        
    def stop_animation(self):
        """Останавливает анимацию"""
        self._is_destroyed = True
        self.rotation_timer.stop()


class SplashScreen(QWidget):
    """
    Splash Screen в стиле Windows 11 Fluent Design.
    Мягкие цвета, плавные анимации, минималистичный дизайн.
    """

    load_complete = pyqtSignal()
    _progress_signal = pyqtSignal(int, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Флаги окна: без рамки, НЕ always-on-top, прозрачный фон для скруглённых углов
        # parent задан -> Dialog (транзиент к главному окну, без taskbar)
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        if parent is None:
            # fallback: не показываем в taskbar, но без WindowStaysOnTopHint
            flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Размер и позиция - компактное окно в стиле Windows 11
        self.setFixedSize(480, 520)
        self._center_on_screen()

        self.animated_icon = None
        self._loading_complete = False

        # Параметры для отрисовки - Windows 11 Fluent стиль
        self._border_radius = 12  # Меньше радиус как в Windows 11
        self._glow_animation_phase = 0.0
        self._particle_effects = []  # Минимум частиц

        self.init_ui()
        self._progress_signal.connect(self._do_set_progress)

        # Анимация свечения рамки (медленнее для мягкости)
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(50)  # Реже для производительности

        # Эффект появления
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self._fade_in()
    
    def _fade_in(self):
        """Анимация плавного появления"""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def _update_glow(self):
        """Обновление анимации свечения рамки - минималистичная версия"""
        self._glow_animation_phase += 0.03  # Медленнее для мягкости

        # Частицы отключены для чистого Windows 11 стиля
        # Только мягкое свечение рамки

        self.update()  # Перерисовка
    
    def _center_on_screen(self):
        """Центрирует окно на экране"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
    
    def paintEvent(self, event):
        """Кастомная отрисовка в стиле Windows 11 Fluent Design"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = self._border_radius

        # ═══════════════════════════════════════════════════════════
        # СЛОЙ 1: Мягкое внешнее свечение (subtle glow)
        # ═══════════════════════════════════════════════════════════
        glow_intensity = (math.sin(self._glow_animation_phase) + 1) / 2  # 0-1
        glow_alpha = int(20 + 15 * glow_intensity)  # Меньше интенсивность

        # Только один мягкий слой свечения
        glow_color = QColor(96, 205, 255, glow_alpha)  # ACCENT_CYAN
        glow_rect = rect.adjusted(4, 4, -4, -4)

        path = QPainterPath()
        path.addRoundedRect(QRectF(glow_rect), radius + 4, radius + 4)
        painter.fillPath(path, glow_color)

        # ═══════════════════════════════════════════════════════════
        # СЛОЙ 2: Основной фон с градиентом (Windows 11 style)
        # ═══════════════════════════════════════════════════════════
        bg_rect = rect.adjusted(1, 1, -1, -1)

        # Полупрозрачный "glass" фон (BG_PRIMARY ~ 0.85)
        bg_gradient = QLinearGradient(0, 0, 0, self.height())
        bg_gradient.setColorAt(0.0, QColor(32, 32, 32, 235))      # Верх
        bg_gradient.setColorAt(0.5, QColor(28, 28, 28, 225))      # Середина
        bg_gradient.setColorAt(1.0, QColor(24, 24, 24, 217))      # Низ

        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(bg_rect), radius, radius)
        painter.fillPath(bg_path, bg_gradient)

        # ═══════════════════════════════════════════════════════════
        # СЛОЙ 3: Тонкая рамка (Windows 11 style - 1px)
        # ═══════════════════════════════════════════════════════════
        border_rect = rect.adjusted(1, 1, -1, -1)

        # Статичная мягкая рамка (без анимации для чистоты)
        border_color = QColor(255, 255, 255, 18)  # Мягкий бордер

        border_pen = QPen(border_color, 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(border_rect), radius, radius)

        # ═══════════════════════════════════════════════════════════
        # СЛОЙ 4: Тонкий блик сверху (subtle glass effect)
        # ═══════════════════════════════════════════════════════════
        highlight_rect = QRectF(bg_rect.x() + 15, bg_rect.y() + 2,
                                bg_rect.width() - 30, 25)
        highlight_gradient = QLinearGradient(0, highlight_rect.top(), 0, highlight_rect.bottom())
        highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 8))
        highlight_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))

        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(highlight_rect, radius - 1, radius - 1)
        painter.fillPath(highlight_path, highlight_gradient)

        painter.end()
    
    def init_ui(self):
        """Инициализация интерфейса в стиле Windows 11 Fluent"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Центральный контейнер
        central_container = QWidget(self)
        central_container.setStyleSheet("background: transparent;")
        central_layout = QVBoxLayout(central_container)
        central_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_layout.setSpacing(12)

        # Иконка
        icon_path = ICON_TEST_PATH if CHANNEL.lower() == "test" else ICON_PATH

        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            pixmap = icon.pixmap(96, 96)  # Компактнее
        else:
            icon = qta.icon('fa5s.shield-alt', color=FLUENT_ACCENT)
            pixmap = icon.pixmap(96, 96)

        self.animated_icon = AnimatedIconWidget(pixmap, parent=central_container)
        central_layout.addWidget(self.animated_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        central_layout.addSpacing(8)

        # Заголовок - чистый белый без градиента
        title = QLabel("Zapret2")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            QLabel {{
                color: {FLUENT_TEXT};
                font-size: 32px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                background: transparent;
                letter-spacing: 1px;
            }}
        """)
        central_layout.addWidget(title)

        # Подзаголовок
        subtitle = QLabel("Обход блокировок")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {FLUENT_TEXT_SECONDARY};
                font-size: 13px;
                font-weight: 400;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
                letter-spacing: 1px;
            }}
        """)
        central_layout.addWidget(subtitle)

        central_layout.addSpacing(4)

        # Версия - мягкий синий
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"""
            QLabel {{
                color: {FLUENT_ACCENT};
                font-size: 13px;
                font-weight: 500;
                font-family: 'Segoe UI', 'Consolas', monospace;
                background: transparent;
            }}
        """)
        central_layout.addWidget(version_label)

        # Канал (если не release)
        if CHANNEL.lower() != "release":
            channel_label = QLabel(f"{CHANNEL.upper()}")
            channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            channel_label.setStyleSheet(f"""
                QLabel {{
                    color: {FLUENT_ACCENT};
                    background: rgba(96, 205, 255, 0.14);
                    border: 1px solid rgba(96, 205, 255, 0.35);
                    font-size: 10px;
                    font-weight: 600;
                    padding: 4px 12px;
                    border-radius: 12px;
                }}
            """)
            central_layout.addWidget(channel_label, alignment=Qt.AlignmentFlag.AlignCenter)

        central_layout.addSpacing(16)

        # Контейнер прогресса
        progress_container = QFrame(central_container)
        progress_container.setMaximumWidth(360)
        progress_container.setObjectName("progressCard")
        progress_container.setStyleSheet("""
            QFrame#progressCard {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(8)

        # Статус
        self.status_label = QLabel("Загрузка...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {FLUENT_TEXT_SECONDARY};
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }}
        """)
        progress_layout.addWidget(self.status_label)

        # Прогресс-бар в стиле Windows 11
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)  # Тонкий как в Windows 11
        self.progress_bar.setMinimumWidth(320)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {FLUENT_ACCENT};
                border-radius: 2px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Процент
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_label.setStyleSheet(f"""
            QLabel {{
                color: {FLUENT_ACCENT};
                font-size: 12px;
                font-weight: 500;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }}
        """)
        progress_layout.addWidget(self.percent_label)

        # Детали
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }
        """)
        progress_layout.addWidget(self.detail_label)

        central_layout.addWidget(progress_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(central_container, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
    
    def fade_out(self):
        """Анимация исчезновения"""
        if self._loading_complete:
            return
        
        self._loading_complete = True
        
        # Останавливаем анимации
        if hasattr(self, '_glow_timer'):
            self._glow_timer.stop()
        if self.animated_icon:
            self.animated_icon.stop_animation()
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(450)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self._on_fade_complete)
        self.fade_animation.start()
    
    def _on_fade_complete(self):
        """Вызывается после завершения анимации исчезновения"""
        self.load_complete.emit()
        self.close()
    
    def set_progress(self, value: int, status: str = "", detail: str = ""):
        """Обновляет прогресс (потокобезопасно)"""
        import threading
        if QApplication.instance() and threading.current_thread() != threading.main_thread():
            self._progress_signal.emit(value, status, detail)
            return
        self._do_set_progress(value, status, detail)
    
    def _do_set_progress(self, value: int, status: str = "", detail: str = ""):
        """Внутренний метод обновления прогресса"""
        try:
            self.progress_bar.setValue(min(value, 100))
            self.percent_label.setText(f"{min(value, 100)}%")
            
            if self.animated_icon:
                self.animated_icon.set_progress(min(value, 100))
            
            if status:
                self.status_label.setText(status)
            if detail:
                self.detail_label.setText(detail)
            
            if value >= 100 and not self._loading_complete:
                log("SplashScreen: прогресс 100%, закрываемся", "DEBUG")
                QTimer.singleShot(300, self.fade_out)
        except RuntimeError:
            pass
    
    def finish(self):
        """Принудительное завершение splash"""
        self.set_progress(100, "Готово!", "")
    
    def show_error(self, error: str):
        """Показывает ошибку и закрывает splash через 3 секунды"""
        if self.animated_icon:
            self.animated_icon.stop_animation()

        # Цвет ошибки - мягкий красный
        error_color = "#e06c75"

        self.status_label.setText(f"Ошибка: {error}")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {error_color};
                font-size: 12px;
                font-weight: 500;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }}
        """)
        self.percent_label.setText("—")
        self.percent_label.setStyleSheet(f"""
            QLabel {{
                color: {error_color};
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }}
        """)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {error_color};
                border-radius: 2px;
            }}
        """)
        QTimer.singleShot(3000, self.fade_out)
