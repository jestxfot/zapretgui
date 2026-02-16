from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, pyqtProperty, QPointF, QEvent
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient
from ui.theme import get_theme_tokens


class AnimatedConstructionScene(QWidget):
    """Элегантная анимация с пульсирующими кольцами и частицами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self._phase = 0.0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        
        # Частицы
        import random
        self._particles = []
        for _ in range(12):
            self._particles.append({
                "angle": random.uniform(0, 360),
                "radius": random.uniform(0.3, 0.8),
                "speed": random.uniform(0.3, 0.8),
                "size": random.uniform(3, 6)
            })

    def _tick(self):
        self._phase = (self._phase + 0.015) % 1.0
        for p in self._particles:
            p["angle"] = (p["angle"] + p["speed"]) % 360
        self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = get_theme_tokens()

        rect = self.rect().adjusted(32, 16, -32, -16)  # Расширенный фон
        cx, cy = rect.center().x(), rect.center().y()
        max_radius = min(rect.width(), rect.height()) / 2 - 20

        # Фон
        bg = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomRight()))
        c0 = QColor(tokens.surface_bg_hover)
        c1 = QColor(tokens.surface_bg)
        c0.setAlpha(250)
        c1.setAlpha(250)
        bg.setColorAt(0, c0)
        bg.setColorAt(1, c1)
        painter.setBrush(QBrush(bg))
        border = QColor(tokens.divider)
        border.setAlpha(80)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(rect, 16, 16)

        # Пульсирующие кольца
        for i in range(3):
            ring_phase = (self._phase + i * 0.33) % 1.0
            radius = max_radius * ring_phase
            alpha = int(80 * (1 - ring_phase))

            ring_color = QColor(tokens.accent_hex)
            ring_color.setAlpha(alpha)
            painter.setPen(QPen(ring_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        # Центральный круг
        center_pulse = 0.8 + 0.2 * math.sin(self._phase * math.pi * 2)
        center_size = int(24 * center_pulse)
        gradient = QLinearGradient(cx - center_size, cy - center_size, cx + center_size, cy + center_size)
        g0 = QColor(tokens.accent_hex)
        g1 = QColor(tokens.accent_hex)
        g0.setAlpha(180)
        g1.setAlpha(120)
        gradient.setColorAt(0, g0)
        gradient.setColorAt(1, g1)
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - center_size), int(cy - center_size), center_size * 2, center_size * 2)

        # Частицы вокруг
        for p in self._particles:
            angle_rad = math.radians(p["angle"])
            r = max_radius * p["radius"]
            px = cx + r * math.cos(angle_rad)
            py = cy + r * math.sin(angle_rad)
            size = int(p["size"])
            
            alpha = int(120 + 60 * math.sin(self._phase * math.pi * 4 + p["angle"]))
            particle = QColor(tokens.accent_hex)
            particle.setAlpha(alpha)
            painter.setBrush(particle)
            painter.drawEllipse(int(px - size/2), int(py - size/2), size, size)

        # Текст - выше центра
        fg = QColor(tokens.fg)
        fg.setAlpha(200)
        painter.setPen(fg)
        font = QFont("Segoe UI Variable", 12, QFont.Weight.Medium)
        painter.setFont(font)
        text_rect = rect.adjusted(0, 0, 0, -30)  # Поднимаем текст
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "Разрабатывается…")




class BlockcheckPage(QWidget):
    """Вкладка Blockcheck с тизером."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BlockcheckPage")
        self._applying_theme_styles = False
        self._theme_refresh_scheduled = False
        self._card_frames = []
        self._card_title_labels = []
        self._card_body_labels = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        self.title_label = QLabel("Blockcheck")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Автоматический анализ блокировок и диагностика сети в один клик")
        layout.addWidget(self.subtitle_label)

        scene = AnimatedConstructionScene(self)
        layout.addWidget(scene)

        # Блок "СКОРО" - по всей ширине
        self.soon_badge = QLabel("СКОРО")
        self.soon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.soon_badge)

        self.soon_text = QLabel(
            "Мониторинг DPI, тестирование операторов и автоматический поиск рабочих стратегий появятся в ближайших обновлениях. "
            "Мы строим Blockcheck, чтобы вы могли увидеть весь путь обхода блокировок в одном окне."
        )
        self.soon_text.setWordWrap(True)
        self.soon_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.soon_text)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(18)

        cards = [
            ("🛰", "Живой мониторинг сети",
             "Отслеживайте изменения DPI в реальном времени и получайте подсказки, какие режимы стоит включить."),
            ("🤖", "Авто-поиск стратегий",
             "Blockcheck протестирует десятки профилей и найдёт лучший вариант для вашего провайдера."),
        ]

        for emoji, title_text, body in cards:
            card = QFrame()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            card_layout.setSpacing(8)

            icon_label = QLabel(emoji)
            icon_label.setStyleSheet("font-size: 22px;")
            card_layout.addWidget(icon_label)

            title_label = QLabel(title_text)
            card_layout.addWidget(title_label)

            body_label = QLabel(body)
            body_label.setWordWrap(True)
            card_layout.addWidget(body_label)

            self._card_frames.append(card)
            self._card_title_labels.append(title_label)
            self._card_body_labels.append(body_label)

            cards_row.addWidget(card)

        layout.addLayout(cards_row)
        layout.addStretch(1)

        self._apply_theme()

    def _apply_theme(self) -> None:
        if self._applying_theme_styles:
            return
        self._applying_theme_styles = True
        try:
            tokens = get_theme_tokens()
            self.title_label.setStyleSheet(
                f"color: {tokens.fg}; font-size: 32px; font-weight: 800; font-family: {tokens.font_family_qss};"
            )
            self.subtitle_label.setStyleSheet(
                f"color: {tokens.fg_muted}; font-size: 16px;"
            )
            self.soon_badge.setStyleSheet(
                f"color: {tokens.fg}; font-weight: 600; letter-spacing: 3px; font-size: 11px; padding: 8px 0; border-radius: 12px; background: {tokens.accent_soft_bg};"
            )
            self.soon_text.setStyleSheet(
                f"color: {tokens.fg_muted}; font-size: 13px;"
            )

            card_qss = f"""
                QFrame {{
                    background-color: {tokens.surface_bg};
                    border: none;
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    background-color: {tokens.surface_bg_hover};
                }}
                QLabel {{
                    border: none;
                    background: transparent;
                }}
            """
            for card in self._card_frames:
                card.setStyleSheet(card_qss)
            for label in self._card_title_labels:
                label.setStyleSheet(f"color: {tokens.fg}; font-size: 14px; font-weight: 600;")
            for label in self._card_body_labels:
                label.setStyleSheet(f"color: {tokens.fg_muted}; font-size: 13px;")
        finally:
            self._applying_theme_styles = False

    def _schedule_theme_refresh(self) -> None:
        if self._applying_theme_styles:
            return
        if self._theme_refresh_scheduled:
            return
        self._theme_refresh_scheduled = True
        QTimer.singleShot(0, self._on_debounced_theme_change)

    def _on_debounced_theme_change(self) -> None:
        self._theme_refresh_scheduled = False
        self._apply_theme()
        self.update()

    def changeEvent(self, event):  # noqa: N802 (Qt override)
        try:
            if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
                self._schedule_theme_refresh()
        except Exception:
            pass
        return super().changeEvent(event)
