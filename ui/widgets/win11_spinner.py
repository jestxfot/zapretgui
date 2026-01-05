"""Windows 11 style spinner - rotating arc indicator"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class Win11Spinner(QWidget):
    """Спиннер в стиле Windows 11 - кольцо с бегущей дугой"""

    def __init__(self, size=20, color="#60cdff", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self._arc_length = 90  # Длина дуги в градусах

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

    def start(self):
        """Запускает анимацию"""
        self._timer.start(16)  # ~60 FPS
        self.show()

    def stop(self):
        """Останавливает анимацию"""
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Фоновое кольцо (полупрозрачное)
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        margin = 3
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.drawEllipse(rect)

        # Активная дуга
        pen.setColor(self._color)
        painter.setPen(pen)

        start_angle = int((90 - self._angle) * 16)
        span_angle = int(-self._arc_length * 16)
        painter.drawArc(rect, start_angle, span_angle)
