# ui/close_dialog.py
"""
Fluent Design диалог выбора варианта закрытия приложения.
Показывается при нажатии на крестик (X) в titlebar.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont

try:
    import qtawesome as qta
    HAS_QTAWESOME = True
except ImportError:
    HAS_QTAWESOME = False


class CloseDialog(QDialog):
    """
    Fluent Design диалог: "Закрыть только GUI" или "Закрыть GUI + остановить DPI".

    Результат:
      - self.result_stop_dpi = None  -> отмена (Esc / клик мимо)
      - self.result_stop_dpi = False -> закрыть только GUI
      - self.result_stop_dpi = True  -> закрыть GUI + остановить DPI
    """

    # Размеры
    DIALOG_WIDTH = 380
    DIALOG_MIN_HEIGHT = 200
    BORDER_RADIUS = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_stop_dpi = None  # None = отмена

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(self.DIALOG_WIDTH)

        # Fade-in анимация
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._init_ui()
        self.setWindowOpacity(0.0)

    # ------------------------------------------------------------------
    #  UI
    # ------------------------------------------------------------------
    def _init_ui(self):
        # Основной контейнер с тенью
        self._container = QWidget(self)
        self._container.setObjectName("closeDialogContainer")

        shadow = QGraphicsDropShadowEffect(self._container)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self._container.setGraphicsEffect(shadow)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)  # место под тень
        root_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("Закрыть приложение")
        title.setObjectName("closeDialogTitle")
        title_font = QFont("Segoe UI", 14)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)

        # Подпись
        subtitle = QLabel("DPI обход (winws) продолжит работать в фоне,\n"
                          "если вы закроете только GUI.")
        subtitle.setObjectName("closeDialogSubtitle")
        subtitle.setWordWrap(True)
        sub_font = QFont("Segoe UI", 10)
        subtitle.setFont(sub_font)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # Кнопки
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)

        # Кнопка 1: Закрыть только GUI (accent)
        self._btn_gui = self._make_button(
            "Закрыть только GUI",
            icon_name="fa5s.window-close" if HAS_QTAWESOME else None,
            accent=False,
        )
        self._btn_gui.clicked.connect(self._on_gui_only)
        buttons_layout.addWidget(self._btn_gui)

        # Кнопка 2: Закрыть + остановить DPI
        self._btn_stop = self._make_button(
            "Закрыть и остановить DPI",
            icon_name="fa5s.power-off" if HAS_QTAWESOME else None,
            accent=True,
            danger=True,
        )
        self._btn_stop.clicked.connect(self._on_stop_dpi)
        buttons_layout.addWidget(self._btn_stop)

        layout.addLayout(buttons_layout)

        # Кнопка "Отмена" (текстовая, без фона)
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        self._btn_cancel = QPushButton("Отмена")
        self._btn_cancel.setObjectName("closeDialogCancelBtn")
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.setFixedHeight(32)
        self._btn_cancel.clicked.connect(self.reject)
        cancel_layout.addWidget(self._btn_cancel)
        cancel_layout.addStretch()
        layout.addLayout(cancel_layout)

        self._apply_styles()

    def _make_button(self, text: str, icon_name: str = None,
                     accent: bool = False, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40)
        btn.setFont(QFont("Segoe UI", 11))

        if icon_name and HAS_QTAWESOME:
            btn.setIcon(qta.icon(icon_name, color="white"))

        btn.setProperty("accent", accent)
        btn.setProperty("danger", danger)
        return btn

    # ------------------------------------------------------------------
    #  Стили (поддержка тёмной/светлой темы)
    # ------------------------------------------------------------------
    def _apply_styles(self):
        is_light = self._detect_light_theme()

        if is_light:
            bg = "#f5f5f5"
            border = "#d0d0d0"
            title_color = "#1a1a1a"
            sub_color = "#555555"
            btn_bg = "#e0e0e0"
            btn_hover = "#d0d0d0"
            btn_text = "#1a1a1a"
            danger_bg = "#dc3545"
            danger_hover = "#c82333"
            cancel_color = "#666666"
            cancel_hover = "rgba(0,0,0,0.06)"
        else:
            bg = "#2b2b2b"
            border = "#3d3d3d"
            title_color = "#ffffff"
            sub_color = "#aaaaaa"
            btn_bg = "#3d3d3d"
            btn_hover = "#4d4d4d"
            btn_text = "#ffffff"
            danger_bg = "#e81123"
            danger_hover = "#c50f1f"
            cancel_color = "#888888"
            cancel_hover = "rgba(255,255,255,0.08)"

        radius = self.BORDER_RADIUS

        self._container.setStyleSheet(f"""
            QWidget#closeDialogContainer {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
        """)

        # Заголовок
        title_widget = self._container.findChild(QLabel, "closeDialogTitle")
        if title_widget:
            title_widget.setStyleSheet(f"color: {title_color}; background: transparent;")

        # Подпись
        sub_widget = self._container.findChild(QLabel, "closeDialogSubtitle")
        if sub_widget:
            sub_widget.setStyleSheet(f"color: {sub_color}; background: transparent;")

        # Кнопка "Закрыть только GUI"
        self._btn_gui.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton:pressed {{
                background-color: {border};
            }}
        """)

        # Кнопка "Закрыть и остановить DPI" (красная)
        self._btn_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {danger_bg};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {danger_hover};
            }}
            QPushButton:pressed {{
                background-color: {danger_bg};
            }}
        """)

        # Кнопка "Отмена"
        self._btn_cancel.setStyleSheet(f"""
            QPushButton#closeDialogCancelBtn {{
                background: transparent;
                color: {cancel_color};
                border: none;
                font-size: 11px;
            }}
            QPushButton#closeDialogCancelBtn:hover {{
                background: {cancel_hover};
                border-radius: 6px;
            }}
        """)

    def _detect_light_theme(self) -> bool:
        """Определяет, используется ли светлая тема."""
        try:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            if tm and hasattr(tm, "_current_theme"):
                name = tm._current_theme or ""
                return "Светлая" in name or "Light" in name.lower()
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    #  Рисование скруглённого контейнера
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        # Полностью прозрачный фон (рисует контейнер через stylesheet)
        pass

    # ------------------------------------------------------------------
    #  Показ / анимация
    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        # Центрируем относительно родителя
        self._center_on_parent()
        # Fade-in
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

    def _center_on_parent(self):
        parent = self.parent()
        if parent:
            try:
                pr = parent.geometry()
                x = pr.x() + (pr.width() - self.width()) // 2
                y = pr.y() + (pr.height() - self.height()) // 2
                self.move(x, y)
                return
            except Exception:
                pass
        # Fallback: центр экрана
        screen = QApplication.primaryScreen()
        if screen:
            sr = screen.availableGeometry()
            self.move(
                sr.x() + (sr.width() - self.width()) // 2,
                sr.y() + (sr.height() - self.height()) // 2,
            )

    # ------------------------------------------------------------------
    #  Обработчики кнопок
    # ------------------------------------------------------------------
    def _on_gui_only(self):
        self.result_stop_dpi = False
        self.accept()

    def _on_stop_dpi(self):
        self.result_stop_dpi = True
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


def ask_close_action(parent=None):
    """
    Показывает диалог и возвращает:
      - None  -> пользователь отменил
      - False -> закрыть только GUI
      - True  -> закрыть GUI + остановить DPI
    """
    dlg = CloseDialog(parent)
    dlg.exec()
    return dlg.result_stop_dpi
