# ui/close_dialog.py
"""
Fluent Design диалог выбора варианта закрытия приложения.
Показывается при нажатии на крестик (X) в titlebar.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QColor, QFont
from typing import Optional

try:
    import qtawesome as qta
    HAS_QTAWESOME = True
except ImportError:
    qta = None
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
    DIALOG_MIN_HEIGHT = 218
    BORDER_RADIUS = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_stop_dpi = None  # None = отмена

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
        )
        self.setWindowModality(
            Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(self.DIALOG_WIDTH)
        self.setMinimumHeight(self.DIALOG_MIN_HEIGHT)

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

        self._shadow = QGraphicsDropShadowEffect(self._container)
        self._shadow.setBlurRadius(38)
        self._shadow.setOffset(0, 6)
        self._shadow.setColor(QColor(0, 0, 0, 96))
        self._container.setGraphicsEffect(self._shadow)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)  # место под тень
        root_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)

        # Заголовок
        title = QLabel("Закрыть приложение")
        title.setObjectName("closeDialogTitle")
        title_font = QFont("Segoe UI Variable", 16)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)

        # Подпись
        subtitle = QLabel("DPI обход (winws) продолжит работать в фоне,\n"
                          "если вы закроете только GUI.")
        subtitle.setObjectName("closeDialogSubtitle")
        subtitle.setWordWrap(True)
        sub_font = QFont("Segoe UI Variable", 10)
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
        self._btn_gui.setObjectName("closeDialogGuiBtn")
        self._btn_gui.setDefault(True)
        self._btn_gui.setAutoDefault(True)
        self._btn_gui.clicked.connect(self._on_gui_only)
        buttons_layout.addWidget(self._btn_gui)

        # Кнопка 2: Закрыть + остановить DPI
        self._btn_stop = self._make_button(
            "Закрыть и остановить DPI",
            icon_name="fa5s.power-off" if HAS_QTAWESOME else None,
            accent=True,
            danger=True,
        )
        self._btn_stop.setObjectName("closeDialogStopBtn")
        self._btn_stop.setAutoDefault(False)
        self._btn_stop.clicked.connect(self._on_stop_dpi)
        buttons_layout.addWidget(self._btn_stop)

        layout.addLayout(buttons_layout)

        # Кнопка "Отмена" (текстовая, без фона)
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        self._btn_cancel = QPushButton("Отмена")
        self._btn_cancel.setObjectName("closeDialogCancelBtn")
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.setFixedHeight(34)
        self._btn_cancel.setAutoDefault(False)
        self._btn_cancel.clicked.connect(self.reject)
        cancel_layout.addWidget(self._btn_cancel)
        cancel_layout.addStretch()
        layout.addLayout(cancel_layout)

        self._apply_styles()

    def _make_button(self, text: str, icon_name: Optional[str] = None,
                     accent: bool = False, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setFont(QFont("Segoe UI Variable", 10))
        btn.setIconSize(QSize(14, 14))

        btn.setProperty("accent", accent)
        btn.setProperty("danger", danger)
        btn.setProperty("iconName", icon_name or "")
        return btn

    def _apply_icon(self, button: QPushButton, color: str):
        if not HAS_QTAWESOME:
            return

        icon_name = button.property("iconName")
        if icon_name:
            button.setIcon(qta.icon(icon_name, color=color))

    # ------------------------------------------------------------------
    #  Стили (поддержка тёмной/светлой темы)
    # ------------------------------------------------------------------
    def _apply_styles(self):
        is_light = self._detect_light_theme()

        if is_light:
            bg_top = "rgba(255, 255, 255, 246)"
            bg_bottom = "rgba(243, 246, 251, 246)"
            border = "rgba(133, 145, 163, 0.48)"
            title_color = "#171b24"
            sub_color = "#495262"
            btn_bg = "rgba(236, 240, 247, 0.96)"
            btn_hover = "rgba(224, 230, 240, 0.98)"
            btn_pressed = "rgba(213, 220, 232, 0.98)"
            btn_border = "rgba(141, 154, 174, 0.56)"
            btn_text = "#1f2735"
            danger_bg = "#cf3d3d"
            danger_hover = "#b53333"
            danger_pressed = "#9f2d2d"
            cancel_color = "#5f6878"
            cancel_hover = "rgba(0, 0, 0, 0.05)"
            focus_border = "#2b6de6"
            shadow_color = QColor(0, 0, 0, 66)
        else:
            bg_top = "rgba(45, 49, 55, 248)"
            bg_bottom = "rgba(35, 39, 45, 248)"
            border = "rgba(255, 255, 255, 0.16)"
            title_color = "#f5f8ff"
            sub_color = "#c5ccda"
            btn_bg = "rgba(255, 255, 255, 0.08)"
            btn_hover = "rgba(255, 255, 255, 0.14)"
            btn_pressed = "rgba(255, 255, 255, 0.18)"
            btn_border = "rgba(255, 255, 255, 0.24)"
            btn_text = "#f3f7ff"
            danger_bg = "#db4646"
            danger_hover = "#c03b3b"
            danger_pressed = "#a93333"
            cancel_color = "#a3acbc"
            cancel_hover = "rgba(255, 255, 255, 0.08)"
            focus_border = "#78a7ff"
            shadow_color = QColor(0, 0, 0, 124)

        self._shadow.setColor(shadow_color)

        radius = self.BORDER_RADIUS

        self._container.setStyleSheet(f"""
            QWidget#closeDialogContainer {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_top},
                    stop:1 {bg_bottom}
                );
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
            QPushButton#closeDialogGuiBtn {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {btn_border};
                border-radius: 10px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton#closeDialogGuiBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#closeDialogGuiBtn:pressed {{
                background-color: {btn_pressed};
            }}
            QPushButton#closeDialogGuiBtn:focus {{
                border: 1px solid {focus_border};
            }}
        """)

        # Кнопка "Закрыть и остановить DPI" (красная)
        self._btn_stop.setStyleSheet(f"""
            QPushButton#closeDialogStopBtn {{
                background-color: {danger_bg};
                color: #ffffff;
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton#closeDialogStopBtn:hover {{
                background-color: {danger_hover};
            }}
            QPushButton#closeDialogStopBtn:pressed {{
                background-color: {danger_pressed};
            }}
            QPushButton#closeDialogStopBtn:focus {{
                border: 1px solid rgba(255, 255, 255, 0.58);
            }}
        """)

        self._apply_icon(self._btn_gui, btn_text)
        self._apply_icon(self._btn_stop, "#ffffff")

        # Кнопка "Отмена"
        self._btn_cancel.setStyleSheet(f"""
            QPushButton#closeDialogCancelBtn {{
                background: transparent;
                color: {cancel_color};
                border: none;
                font-size: 12px;
                font-weight: 600;
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
                return "Светлая" in name or "light" in name.lower()
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


class StartStrategyWarningDialog(QDialog):
    """Фирменный warning-диалог о том, что стратегия не выбрана."""

    DIALOG_WIDTH = 380
    DIALOG_MIN_HEIGHT = 204
    BORDER_RADIUS = 14

    def __init__(self, parent=None, title: str = "Стратегия не выбрана", subtitle: str = ""):
        super().__init__(parent)
        self._title_text = title
        self._subtitle_text = subtitle or (
            "Для запуска Zapret выберите хотя бы одну стратегию "
            "в разделе «Стратегии»."
        )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
        )
        self.setWindowModality(
            Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(self.DIALOG_WIDTH)
        self.setMinimumHeight(self.DIALOG_MIN_HEIGHT)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._init_ui()
        self.setWindowOpacity(0.0)

    def _init_ui(self) -> None:
        self._container = QWidget(self)
        self._container.setObjectName("startWarnDialogContainer")

        self._shadow = QGraphicsDropShadowEffect(self._container)
        self._shadow.setBlurRadius(38)
        self._shadow.setOffset(0, 6)
        self._shadow.setColor(QColor(0, 0, 0, 96))
        self._container.setGraphicsEffect(self._shadow)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel(self._title_text)
        title.setObjectName("startWarnDialogTitle")
        title_font = QFont("Segoe UI Variable", 16)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(self._subtitle_text)
        subtitle.setObjectName("startWarnDialogSubtitle")
        subtitle.setWordWrap(True)
        sub_font = QFont("Segoe UI Variable", 10)
        subtitle.setFont(sub_font)
        layout.addWidget(subtitle)

        layout.addSpacing(6)

        self._btn_ok = QPushButton("Понятно")
        self._btn_ok.setObjectName("startWarnDialogOkBtn")
        self._btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ok.setFixedHeight(42)
        self._btn_ok.setFont(QFont("Segoe UI Variable", 10))
        self._btn_ok.setIconSize(QSize(14, 14))
        self._btn_ok.setDefault(True)
        self._btn_ok.setAutoDefault(True)
        self._btn_ok.clicked.connect(self.accept)
        layout.addWidget(self._btn_ok)

        self._apply_styles()

    def _apply_icon(self, color: str) -> None:
        if not HAS_QTAWESOME:
            return
        try:
            self._btn_ok.setIcon(qta.icon("fa5s.exclamation-triangle", color=color))
        except Exception:
            pass

    def _apply_styles(self) -> None:
        is_light = self._detect_light_theme()

        if is_light:
            bg_top = "rgba(255, 255, 255, 246)"
            bg_bottom = "rgba(243, 246, 251, 246)"
            border = "rgba(133, 145, 163, 0.48)"
            title_color = "#171b24"
            sub_color = "#495262"
            btn_bg = "rgba(236, 240, 247, 0.96)"
            btn_hover = "rgba(224, 230, 240, 0.98)"
            btn_pressed = "rgba(213, 220, 232, 0.98)"
            btn_border = "rgba(141, 154, 174, 0.56)"
            btn_text = "#1f2735"
            focus_border = "#2b6de6"
            shadow_color = QColor(0, 0, 0, 66)
        else:
            bg_top = "rgba(45, 49, 55, 248)"
            bg_bottom = "rgba(35, 39, 45, 248)"
            border = "rgba(255, 255, 255, 0.16)"
            title_color = "#f5f8ff"
            sub_color = "#c5ccda"
            btn_bg = "rgba(255, 255, 255, 0.08)"
            btn_hover = "rgba(255, 255, 255, 0.14)"
            btn_pressed = "rgba(255, 255, 255, 0.18)"
            btn_border = "rgba(255, 255, 255, 0.24)"
            btn_text = "#f3f7ff"
            focus_border = "#78a7ff"
            shadow_color = QColor(0, 0, 0, 124)

        self._shadow.setColor(shadow_color)

        radius = self.BORDER_RADIUS
        self._container.setStyleSheet(f"""
            QWidget#startWarnDialogContainer {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_top},
                    stop:1 {bg_bottom}
                );
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
        """)

        title_widget = self._container.findChild(QLabel, "startWarnDialogTitle")
        if title_widget:
            title_widget.setStyleSheet(f"color: {title_color}; background: transparent;")

        sub_widget = self._container.findChild(QLabel, "startWarnDialogSubtitle")
        if sub_widget:
            sub_widget.setStyleSheet(f"color: {sub_color}; background: transparent;")

        self._btn_ok.setStyleSheet(f"""
            QPushButton#startWarnDialogOkBtn {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {btn_border};
                border-radius: 10px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton#startWarnDialogOkBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#startWarnDialogOkBtn:pressed {{
                background-color: {btn_pressed};
            }}
            QPushButton#startWarnDialogOkBtn:focus {{
                border: 1px solid {focus_border};
            }}
        """)

        self._apply_icon(btn_text)

    def _detect_light_theme(self) -> bool:
        try:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            if tm and hasattr(tm, "_current_theme"):
                name = tm._current_theme or ""
                return "Светлая" in name or "light" in name.lower()
        except Exception:
            pass
        return False

    def paintEvent(self, event):
        pass

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent:
            try:
                pr = parent.geometry()
                x = pr.x() + (pr.width() - self.width()) // 2
                y = pr.y() + (pr.height() - self.height()) // 2
                self.move(x, y)
                return
            except Exception:
                pass

        screen = QApplication.primaryScreen()
        if screen:
            sr = screen.availableGeometry()
            self.move(
                sr.x() + (sr.width() - self.width()) // 2,
                sr.y() + (sr.height() - self.height()) // 2,
            )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


def show_start_strategy_warning(parent=None, subtitle: str = "") -> None:
    """Показывает предупреждение о необходимости выбрать стратегию."""
    dlg = StartStrategyWarningDialog(parent=parent, subtitle=subtitle)
    dlg.exec()


def ask_close_action(parent=None):
    """
    Возвращает действие закрытия приложения:
      - None  -> пользователь отменил
      - False -> закрыть только GUI
      - True  -> закрыть GUI + остановить DPI

    Если DPI-процесс не запущен, диалог не показывается и
    сразу возвращается False (закрыть только GUI).
    """
    is_dpi_running = True

    try:
        dpi_controller = getattr(parent, "dpi_controller", None)
        if dpi_controller and hasattr(dpi_controller, "is_running"):
            is_dpi_running = bool(dpi_controller.is_running())
    except Exception:
        pass

    if is_dpi_running and parent is not None:
        try:
            dpi_starter = getattr(parent, "dpi_starter", None)
            if dpi_starter and hasattr(dpi_starter, "check_process_running_wmi"):
                is_dpi_running = bool(dpi_starter.check_process_running_wmi(silent=True))
        except Exception:
            pass

    if not is_dpi_running:
        return False

    dlg = CloseDialog(parent)
    dlg.exec()
    return dlg.result_stop_dpi
