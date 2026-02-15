# ui/pages/appearance_page.py
"""Страница настроек оформления - темы"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QScrollArea, QCheckBox, QSlider,
    QStyle, QStyleOption, QStyleOptionSlider,
)
from PyQt6.QtGui import QWheelEvent, QPainter, QColor
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from ui.theme import get_theme_tokens


class PreciseSlider(QSlider):
    """Слайдер с точным управлением колёсиком мыши (1 шаг за скролл)"""

    def _value_from_pos(self, pos) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
        )

        if self.orientation() == Qt.Orientation.Horizontal:
            # Привязываем значение к позиции курсора как к центру хэндла.
            # Так "ползунок" визуально следует за курсором и на 100% нет ощущения сдвига влево.
            slider_min = groove.left()
            slider_max = groove.right()
            x = pos.x()
            x = max(slider_min, min(x, slider_max))
            span = max(1, slider_max - slider_min)
            return QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), x - slider_min, span, opt.upsideDown
            )

        slider_min = groove.top()
        slider_max = groove.bottom()
        y = pos.y()
        y = max(slider_min, min(y, slider_max))
        span = max(1, slider_max - slider_min)
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), y - slider_min, span, opt.upsideDown
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.setValue(self._value_from_pos(event.position().toPoint()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown() and (event.buttons() & Qt.MouseButton.LeftButton):
            self.setValue(self._value_from_pos(event.position().toPoint()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isSliderDown() and event.button() == Qt.MouseButton.LeftButton:
            self.setValue(self._value_from_pos(event.position().toPoint()))
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        # Определяем направление скролла
        delta = event.angleDelta().y()
        if delta > 0:
            self.setValue(self.value() + 1)
        elif delta < 0:
            self.setValue(self.value() - 1)
        event.accept()


class AcrylicSlider(PreciseSlider):
    """Обычный QSlider со стилем через QSS (более предсказуемый и всегда видимый)."""

    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.setFixedHeight(22)
        self._track_height = 6.0
        self._handle_diameter = 12.0
        self._tokens = None
        # Делаем максимально контрастным для тёмных тем (включая "Темная синяя")
        # и для полупрозрачного окна/карточек.
        self.setStyleSheet(
            """
            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background: transparent;
            }
            QSlider::sub-page:horizontal {
                height: 6px;
                border-radius: 3px;
                background: transparent;
            }
            QSlider::add-page:horizontal {
                height: 6px;
                border-radius: 3px;
                background: transparent;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -6px 0px;
                border-radius: 8px;
                background: transparent;
                border: none;
            }
            QSlider::handle:horizontal:hover {
                background: transparent;
            }
            QSlider::groove:horizontal:disabled {
                background: transparent;
            }
            QSlider::sub-page:horizontal:disabled {
                background: transparent;
            }
            QSlider::handle:horizontal:disabled {
                background: transparent;
                border: none;
            }
            """
        )

    def set_theme_tokens(self, tokens) -> None:
        self._tokens = tokens
        self.update()

    def paintEvent(self, event):  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
        )

        track_h = float(self._track_height)
        track_y = groove.center().y() - (track_h / 2.0)
        track_rect = QRectF(groove.left(), track_y, groove.width(), track_h)
        track_radius = track_h / 2.0

        enabled = self.isEnabled()
        tokens = self._tokens
        if tokens is None:
            tokens = get_theme_tokens("Темная синяя")

        accent = QColor(tokens.accent_hex)
        accent_hover = QColor(tokens.accent_hover_hex)
        if not enabled:
            accent.setAlphaF(0.45)
            accent_hover.setAlphaF(0.45)

        if tokens.is_light:
            track_bg = QColor(0, 0, 0, int(255 * 0.14))
            track_remaining = QColor(0, 0, 0, int(255 * 0.06))
        else:
            track_bg = QColor(255, 255, 255, int(255 * 0.20))
            track_remaining = QColor(255, 255, 255, int(255 * 0.12))
        if not enabled:
            track_bg.setAlphaF(0.12)
            track_remaining.setAlphaF(0.08)

        # Фон трека
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_bg)
        painter.drawRoundedRect(track_rect, track_radius, track_radius)

        # Заполненная часть
        span = self.maximum() - self.minimum()
        ratio = 0.0 if span <= 0 else (self.value() - self.minimum()) / float(span)
        ratio = max(0.0, min(1.0, ratio))
        fill_w = track_rect.width() * ratio

        # Незаполненная часть (отрисуем поверх фона, чтобы быть чуть темнее)
        if fill_w < track_rect.width():
            remaining_rect = QRectF(track_rect.left() + fill_w, track_rect.top(), track_rect.width() - fill_w, track_rect.height())
            painter.setBrush(track_remaining)
            painter.drawRoundedRect(remaining_rect, track_radius, track_radius)

        if fill_w > 0.0:
            fill_rect = QRectF(track_rect.left(), track_rect.top(), fill_w, track_rect.height())
            painter.setBrush(accent_hover if self.underMouse() else accent)
            painter.drawRoundedRect(fill_rect, track_radius, track_radius)

        # Хэндл — чистая синяя точка без обводки
        handle_d = float(self._handle_diameter)
        cx = track_rect.left() + fill_w
        cx_min = track_rect.left() + (handle_d / 2.0)
        cx_max = track_rect.right() - (handle_d / 2.0)
        cx = max(cx_min, min(cx, cx_max))
        cy = track_rect.center().y()
        handle_rect = QRectF(cx - handle_d / 2.0, cy - handle_d / 2.0, handle_d, handle_d)
        painter.setBrush(accent_hover if (self.underMouse() or self.isSliderDown()) else accent)
        painter.drawEllipse(handle_rect)

def _theme_preview_color(theme_name: str) -> str:
    # "Полностью черная" лучше показывать как чёрную (а не button_color).
    if theme_name == "Полностью черная":
        return "#0a0a0a"
    try:
        return get_theme_tokens(theme_name).accent_hex
    except Exception:
        return "#333333"


class ThemeCard(QFrame):
    """Карточка выбора темы"""
    
    clicked = pyqtSignal(str)  # Сигнал клика с именем темы
    
    def __init__(self, name: str, color: str, is_premium: bool = False, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.is_premium = is_premium
        self._selected = False
        self._hovered = False
        self._enabled = True
        
        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("themeCard")
        # Нужно для корректной отрисовки background/border из stylesheet
        # в кастомных paintEvent/на некоторых стилях Windows.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Цветовой прямоугольник
        self.color_widget = QWidget()
        self.color_widget.setFixedHeight(36)
        self.color_widget.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
        """)
        layout.addWidget(self.color_widget)
        
        # Название
        name_layout = QHBoxLayout()
        name_layout.setSpacing(4)
        
        # Сокращаем длинные названия
        display_name = name
        if len(name) > 12:
            display_name = name[:11] + "…"
        
        self.name_label = QLabel(display_name)
        self.name_label.setObjectName("themeCardName")
        self.name_label.setToolTip(name)
        name_layout.addWidget(self.name_label)
        
        if is_premium:
            premium_icon = QLabel()
            premium_icon.setPixmap(qta.icon('fa5s.star', color='#ffc107').pixmap(10, 10))
            premium_icon.setToolTip("Премиум-тема")
            name_layout.addWidget(premium_icon)
            
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        self._update_style()

    def paintEvent(self, event):
        """
        Надёжная отрисовка карточки через стиль Qt.

        На некоторых связках Windows + PyQt6 можно словить TypeError из-за
        некорректных аргументов drawRoundedRect в кастомной отрисовке.
        Здесь используем стандартный механизм QStyle/stylesheet.
        """
        painter = QPainter(self)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        
    def _update_style(self):
        # All visuals are controlled by the global theme QSS. We only expose state.
        self.setProperty("selected", bool(self._selected))
        self.setProperty("hovered", bool(self._hovered))

        # Ensure style sheet re-evaluates dynamic properties.
        try:
            self.style().unpolish(self)
            self.style().polish(self)
        except Exception:
            pass
        self.update()
        
        # Затемняем превью цвета если disabled
        if hasattr(self, 'color_widget'):
            if self._enabled:
                self.color_widget.setStyleSheet(f"""
                    background-color: {self.color};
                    border-radius: 4px;
                """)
            else:
                self.color_widget.setStyleSheet(f"""
                    background-color: {self.color};
                    border-radius: 4px;
                    opacity: 0.3;
                """)
        
    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.setEnabled(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor)
        self._update_style()
        
    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


class AppearancePage(BasePage):
    """Страница настроек оформления"""

    # Сигнал смены темы
    theme_changed = pyqtSignal(str)
    # Сигнал изменения состояния гирлянды
    garland_changed = pyqtSignal(bool)
    # Сигнал изменения состояния снежинок
    snowflakes_changed = pyqtSignal(bool)
    # Сигнал изменения состояния эффекта размытия
    blur_effect_changed = pyqtSignal(bool)
    # Сигнал изменения прозрачности окна (0-100)
    opacity_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__("Оформление", "Настройка внешнего вида приложения", parent)

        self._theme_cards = {}  # name -> ThemeCard
        self._current_theme = None
        self._is_premium = False
        self._garland_checkbox = None
        self._snowflakes_checkbox = None
        self._blur_effect_checkbox = None
        self._opacity_slider = None
        self._opacity_label = None
        self._blur_icon_label = None
        self._opacity_icon_label = None

        self._build_ui()
        
    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # СТАНДАРТНЫЕ ТЕМЫ
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Стандартные темы")
        
        standard_card = SettingsCard()
        
        standard_layout = QVBoxLayout()
        standard_layout.setSpacing(12)
        
        # Описание
        desc = QLabel("Выберите тему оформления для приложения.")
        desc.setProperty("tone", "muted")
        desc.setStyleSheet("font-size: 12px;")
        desc.setWordWrap(True)
        standard_layout.addWidget(desc)
        
        # Галерея стандартных тем
        standard_themes_layout = QGridLayout()
        standard_themes_layout.setSpacing(8)
        
        standard_themes = [
            ("Темная синяя", False),
            ("Темная бирюзовая", False),
            ("Темная янтарная", False),
            ("Темная розовая", False),
            ("Светлая синяя", False),
            ("Светлая бирюзовая", False),
        ]
        
        for i, (name, is_premium) in enumerate(standard_themes):
            color = _theme_preview_color(name)
            card = ThemeCard(name, color, is_premium=is_premium)
            card.clicked.connect(self._on_theme_clicked)
            row = i // 4
            col = i % 4
            standard_themes_layout.addWidget(card, row, col)
            self._theme_cards[name] = card
            
        standard_layout.addLayout(standard_themes_layout)
        standard_card.add_layout(standard_layout)
        
        self.add_widget(standard_card)
        
        self.add_spacing(16)
        
        # ═══════════════════════════════════════════════════════════
        # ПРЕМИУМ ТЕМЫ
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Премиум темы")
        
        premium_card = SettingsCard()
        
        premium_layout = QVBoxLayout()
        premium_layout.setSpacing(12)
        
        premium_desc = QLabel(
            "Дополнительные темы доступны подписчикам Zapret Premium. "
            "Включая AMOLED темы и уникальные стили."
        )
        premium_desc.setProperty("tone", "muted")
        premium_desc.setStyleSheet("font-size: 11px;")
        premium_desc.setWordWrap(True)
        premium_layout.addWidget(premium_desc)
        
        # Галерея премиум тем
        premium_themes_layout = QGridLayout()
        premium_themes_layout.setSpacing(8)
        
        premium_themes = [
            ("РКН Тян", True),
            ("РКН Тян 2", True),
            ("AMOLED Синяя", True),
            ("AMOLED Зеленая", True),
            ("AMOLED Фиолетовая", True),
            ("AMOLED Красная", True),
            ("Полностью черная", True),
        ]
        
        for i, (name, is_premium) in enumerate(premium_themes):
            color = _theme_preview_color(name)
            card = ThemeCard(name, color, is_premium=is_premium)
            card.clicked.connect(self._on_theme_clicked)
            card.set_enabled(False)  # По умолчанию заблокированы до проверки премиума
            row = i // 4
            col = i % 4
            premium_themes_layout.addWidget(card, row, col)
            self._theme_cards[name] = card
            
        premium_layout.addLayout(premium_themes_layout)
        
        # Кнопка подписки
        from ui.sidebar import ActionButton
        sub_btn_layout = QHBoxLayout()
        
        self.subscription_btn = ActionButton("Управление подпиской", "fa5s.star")
        self.subscription_btn.setFixedHeight(36)
        sub_btn_layout.addWidget(self.subscription_btn)
        
        sub_btn_layout.addStretch()
        premium_layout.addLayout(sub_btn_layout)
        
        premium_card.add_layout(premium_layout)
        self.add_widget(premium_card)
        
        self.add_spacing(16)
        
        # ═══════════════════════════════════════════════════════════
        # НОВОГОДНЕЕ ОФОРМЛЕНИЕ (Premium)
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Новогоднее оформление")
        
        garland_card = SettingsCard()
        
        garland_layout = QVBoxLayout()
        garland_layout.setSpacing(12)
        
        # Описание
        garland_desc = QLabel(
            "Праздничная гирлянда с мерцающими огоньками в верхней части окна. "
            "Доступно только для подписчиков Premium."
        )
        garland_desc.setProperty("tone", "muted")
        garland_desc.setStyleSheet("font-size: 11px;")
        garland_desc.setWordWrap(True)
        garland_layout.addWidget(garland_desc)
        
        # Переключатель
        garland_row = QHBoxLayout()
        garland_row.setSpacing(12)
        
        garland_icon = QLabel()
        garland_icon.setPixmap(qta.icon('fa5s.holly-berry', color='#ff6b6b').pixmap(20, 20))
        garland_row.addWidget(garland_icon)
        
        garland_label = QLabel("Новогодняя гирлянда")
        garland_label.setProperty("tone", "primary")
        garland_label.setStyleSheet("font-size: 13px;")
        garland_row.addWidget(garland_label)
        
        premium_badge = QLabel("⭐ Premium")
        premium_badge.setStyleSheet("""
            color: #ffc107;
            font-size: 10px;
            font-weight: bold;
            background-color: rgba(255, 193, 7, 0.15);
            padding: 2px 6px;
            border-radius: 4px;
        """)
        garland_row.addWidget(premium_badge)
        
        garland_row.addStretch()
        
        self._garland_checkbox = QCheckBox()
        self._garland_checkbox.setEnabled(False)  # Включается только при премиуме
        self._garland_checkbox.setObjectName("garlandSwitch")
        self._garland_checkbox.stateChanged.connect(self._on_garland_changed)
        garland_row.addWidget(self._garland_checkbox)
        
        garland_layout.addLayout(garland_row)
        
        garland_card.add_layout(garland_layout)
        self.add_widget(garland_card)
        
        # ═══════════════════════════════════════════════════════════
        # СНЕЖИНКИ (Premium)
        # ═══════════════════════════════════════════════════════════
        snowflakes_card = SettingsCard()
        
        snowflakes_layout = QVBoxLayout()
        snowflakes_layout.setSpacing(12)
        
        # Описание
        snowflakes_desc = QLabel(
            "Мягко падающие снежинки по всему окну. "
            "Создаёт уютную зимнюю атмосферу."
        )
        snowflakes_desc.setProperty("tone", "muted")
        snowflakes_desc.setStyleSheet("font-size: 11px;")
        snowflakes_desc.setWordWrap(True)
        snowflakes_layout.addWidget(snowflakes_desc)
        
        # Переключатель
        snowflakes_row = QHBoxLayout()
        snowflakes_row.setSpacing(12)
        
        snowflakes_icon = QLabel()
        snowflakes_icon.setPixmap(qta.icon('fa5s.snowflake', color='#87ceeb').pixmap(20, 20))
        snowflakes_row.addWidget(snowflakes_icon)
        
        snowflakes_label = QLabel("Снежинки")
        snowflakes_label.setProperty("tone", "primary")
        snowflakes_label.setStyleSheet("font-size: 13px;")
        snowflakes_row.addWidget(snowflakes_label)
        
        snowflakes_badge = QLabel("⭐ Premium")
        snowflakes_badge.setStyleSheet("""
            color: #ffc107;
            font-size: 10px;
            font-weight: bold;
            background-color: rgba(255, 193, 7, 0.15);
            padding: 2px 6px;
            border-radius: 4px;
        """)
        snowflakes_row.addWidget(snowflakes_badge)
        
        snowflakes_row.addStretch()
        
        self._snowflakes_checkbox = QCheckBox()
        self._snowflakes_checkbox.setEnabled(False)  # Включается только при премиуме
        self._snowflakes_checkbox.setObjectName("snowflakesSwitch")
        self._snowflakes_checkbox.stateChanged.connect(self._on_snowflakes_changed)
        snowflakes_row.addWidget(self._snowflakes_checkbox)
        
        snowflakes_layout.addLayout(snowflakes_row)
        
        snowflakes_card.add_layout(snowflakes_layout)
        self.add_widget(snowflakes_card)

        self.add_spacing(16)

        # ═══════════════════════════════════════════════════════════
        # ЭФФЕКТ РАЗМЫТИЯ (Acrylic/Mica)
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Эффект окна")

        blur_card = SettingsCard()

        blur_layout = QVBoxLayout()
        blur_layout.setSpacing(12)

        # Описание
        blur_desc = QLabel(
            "Матовое размытие фона окна (Acrylic). "
            "Позволяет видеть размытое содержимое за окном. "
            "Требует Windows 10 1803+ или Windows 11."
        )
        blur_desc.setProperty("tone", "muted")
        blur_desc.setStyleSheet("font-size: 11px;")
        blur_desc.setWordWrap(True)
        blur_layout.addWidget(blur_desc)

        # Переключатель
        blur_row = QHBoxLayout()
        blur_row.setSpacing(12)

        blur_icon = QLabel()
        self._blur_icon_label = blur_icon
        blur_icon.setPixmap(qta.icon('fa5s.magic', color=get_theme_tokens().accent_hex).pixmap(20, 20))
        blur_row.addWidget(blur_icon)

        blur_label = QLabel("Размытие фона (Acrylic)")
        blur_label.setProperty("tone", "primary")
        blur_label.setStyleSheet("font-size: 13px;")
        blur_row.addWidget(blur_label)

        blur_row.addStretch()

        self._blur_effect_checkbox = QCheckBox()
        self._blur_effect_checkbox.setObjectName("blurSwitch")
        self._blur_effect_checkbox.stateChanged.connect(self._on_blur_effect_changed)
        blur_row.addWidget(self._blur_effect_checkbox)

        blur_layout.addLayout(blur_row)

        # Предупреждение о совместимости
        from ui.theme import BlurEffect
        if not BlurEffect.is_supported():
            warning_label = QLabel("⚠️ Эффект недоступен на вашей системе")
            warning_label.setStyleSheet("color: #ff9800; font-size: 10px;")
            blur_layout.addWidget(warning_label)
            self._blur_effect_checkbox.setEnabled(False)

        blur_card.add_layout(blur_layout)
        self.add_widget(blur_card)

        # ═══════════════════════════════════════════════════════════
        # ПРОЗРАЧНОСТЬ ОКНА
        # ═══════════════════════════════════════════════════════════
        opacity_card = SettingsCard()

        opacity_layout = QVBoxLayout()
        opacity_layout.setSpacing(12)

        # Описание
        opacity_desc = QLabel(
            "Настройка прозрачности всего окна приложения. "
            "При 0% окно полностью прозрачное, при 100% — непрозрачное."
        )
        opacity_desc.setProperty("tone", "muted")
        opacity_desc.setStyleSheet("font-size: 11px;")
        opacity_desc.setWordWrap(True)
        opacity_layout.addWidget(opacity_desc)

        # Строка с иконкой, названием и значением
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(12)

        opacity_icon = QLabel()
        self._opacity_icon_label = opacity_icon
        opacity_icon.setPixmap(qta.icon('fa5s.adjust', color=get_theme_tokens().accent_hex).pixmap(20, 20))
        opacity_row.addWidget(opacity_icon)

        opacity_title = QLabel("Прозрачность окна")
        opacity_title.setProperty("tone", "primary")
        opacity_title.setStyleSheet("font-size: 13px;")
        opacity_row.addWidget(opacity_title)

        opacity_row.addStretch()

        self._opacity_label = QLabel("100%")
        self._opacity_label.setProperty("tone", "muted")
        self._opacity_label.setStyleSheet("font-size: 12px; min-width: 40px;")
        self._opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opacity_row.addWidget(self._opacity_label)

        opacity_layout.addLayout(opacity_row)

        # Слайдер
        self._opacity_slider = AcrylicSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.set_theme_tokens(get_theme_tokens())
        self._opacity_slider.setMinimum(0)
        self._opacity_slider.setMaximum(100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.setSingleStep(1)
        self._opacity_slider.setPageStep(5)  # Page Up/Down меняет на 5%
        self._opacity_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self._opacity_slider)

        opacity_card.add_layout(opacity_layout)
        self.add_widget(opacity_card)

        self.add_spacing(16)

    def _apply_theme_tokens(self, theme_name: str) -> None:
        """Refresh local, non-QSS parts (pixmap icons, custom painted widgets)."""
        try:
            tokens = get_theme_tokens(theme_name)
        except Exception:
            tokens = get_theme_tokens("Темная синяя")

        if self._opacity_slider is not None:
            self._opacity_slider.set_theme_tokens(tokens)

        if self._blur_icon_label is not None:
            self._blur_icon_label.setPixmap(qta.icon('fa5s.magic', color=tokens.accent_hex).pixmap(20, 20))

        if self._opacity_icon_label is not None:
            self._opacity_icon_label.setPixmap(qta.icon('fa5s.adjust', color=tokens.accent_hex).pixmap(20, 20))

    def _on_blur_effect_changed(self, state):
        """Обработчик изменения состояния эффекта размытия"""
        enabled = state == Qt.CheckState.Checked.value

        # Сохраняем в реестр
        from config.reg import set_blur_effect_enabled
        set_blur_effect_enabled(enabled)

        # Уведомляем главное окно
        self.blur_effect_changed.emit(enabled)

        from log import log
        log(f"Эффект размытия {'включён' if enabled else 'выключен'}", "DEBUG")

    def _on_opacity_changed(self, value: int):
        """Обработчик изменения прозрачности окна"""
        # Обновляем лейбл
        if self._opacity_label:
            self._opacity_label.setText(f"{value}%")

        # Сохраняем в реестр
        from config.reg import set_window_opacity
        set_window_opacity(value)

        # Уведомляем главное окно
        self.opacity_changed.emit(value)

        from log import log
        log(f"Прозрачность окна: {value}%", "DEBUG")

    def _on_snowflakes_changed(self, state):
        """Обработчик изменения состояния снежинок"""
        enabled = state == Qt.CheckState.Checked.value
        
        # Сохраняем в реестр
        from config.reg import set_snowflakes_enabled
        set_snowflakes_enabled(enabled)
        
        # Уведомляем главное окно
        self.snowflakes_changed.emit(enabled)
        
    def _on_garland_changed(self, state):
        """Обработчик изменения состояния гирлянды"""
        enabled = state == Qt.CheckState.Checked.value
        
        # Сохраняем в реестр
        from config.reg import set_garland_enabled
        set_garland_enabled(enabled)
        
        # Эмитим сигнал
        self.garland_changed.emit(enabled)
        
    def _on_theme_clicked(self, theme_name: str):
        """Обработчик клика по карточке темы"""
        # Проверяем, является ли тема премиум и заблокирована ли она
        card = self._theme_cards.get(theme_name)
        if card and card.is_premium and not self._is_premium:
            # Просто игнорируем клик - карточка уже визуально disabled
            return
            
        # Устанавливаем выбранную тему
        self._select_theme(theme_name)
        
        # Эмитим сигнал смены темы
        self.theme_changed.emit(theme_name)
        
    def _select_theme(self, theme_name: str):
        """Визуально выделяет выбранную тему"""
        # Снимаем выделение со старой темы
        if self._current_theme and self._current_theme in self._theme_cards:
            self._theme_cards[self._current_theme].set_selected(False)
            
        # Выделяем новую тему
        if theme_name in self._theme_cards:
            self._theme_cards[theme_name].set_selected(True)
            self._current_theme = theme_name
            
    def set_current_theme(self, theme_name: str):
        """Устанавливает текущую тему (без эмита сигнала)"""
        # Очищаем название от суффиксов
        clean_name = theme_name
        suffixes = [" (заблокировано)", " (AMOLED Premium)", " (Pure Black Premium)"]
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, "")
            
        self._select_theme(clean_name)
        self._apply_theme_tokens(clean_name)
        
    def set_premium_status(self, is_premium: bool):
        """Устанавливает статус премиум-подписки"""
        self._is_premium = is_premium
        
        # Обновляем состояние карточек премиум тем
        premium_themes = ["РКН Тян", "РКН Тян 2", "AMOLED Синяя", "AMOLED Зеленая", 
                         "AMOLED Фиолетовая", "AMOLED Красная", "Полностью черная"]
        
        for name in premium_themes:
            if name in self._theme_cards:
                # Включаем/выключаем карточки в зависимости от премиум статуса
                self._theme_cards[name].set_enabled(is_premium)
        
        # Включаем/выключаем чекбоксы новогоднего оформления
        from config.reg import get_garland_enabled, get_snowflakes_enabled, get_blur_effect_enabled

        # Загружаем настройку эффекта размытия (не зависит от премиума)
        if self._blur_effect_checkbox and self._blur_effect_checkbox.isEnabled():
            self._blur_effect_checkbox.blockSignals(True)
            self._blur_effect_checkbox.setChecked(get_blur_effect_enabled())
            self._blur_effect_checkbox.blockSignals(False)
        
        if self._garland_checkbox:
            self._garland_checkbox.setEnabled(is_premium)
            self._garland_checkbox.blockSignals(True)
            if is_premium:
                # При появлении премиума - восстанавливаем сохранённое состояние
                self._garland_checkbox.setChecked(get_garland_enabled())
            else:
                # При потере премиума - выключаем визуально
                self._garland_checkbox.setChecked(False)
            self._garland_checkbox.blockSignals(False)
                
        if self._snowflakes_checkbox:
            self._snowflakes_checkbox.setEnabled(is_premium)
            self._snowflakes_checkbox.blockSignals(True)
            if is_premium:
                # При появлении премиума - восстанавливаем сохранённое состояние
                self._snowflakes_checkbox.setChecked(get_snowflakes_enabled())
            else:
                # При потере премиума - выключаем визуально
                self._snowflakes_checkbox.setChecked(False)
            self._snowflakes_checkbox.blockSignals(False)
                
        # Если нет премиума и гирлянда включена - выключаем
        if not is_premium and self._garland_checkbox and self._garland_checkbox.isChecked():
            self._garland_checkbox.blockSignals(True)
            self._garland_checkbox.setChecked(False)
            self._garland_checkbox.blockSignals(False)
            from config.reg import set_garland_enabled
            set_garland_enabled(False)
            self.garland_changed.emit(False)
            
        # Если нет премиума и снежинки включены - выключаем
        if not is_premium and self._snowflakes_checkbox and self._snowflakes_checkbox.isChecked():
            self._snowflakes_checkbox.blockSignals(True)
            self._snowflakes_checkbox.setChecked(False)
            self._snowflakes_checkbox.blockSignals(False)
            from config.reg import set_snowflakes_enabled
            set_snowflakes_enabled(False)
            self.snowflakes_changed.emit(False)
            
    def set_garland_state(self, enabled: bool):
        """Устанавливает состояние чекбокса гирлянды (без эмита сигнала)"""
        if self._garland_checkbox:
            self._garland_checkbox.blockSignals(True)
            self._garland_checkbox.setChecked(enabled)
            self._garland_checkbox.blockSignals(False)
    
    def set_snowflakes_state(self, enabled: bool):
        """Устанавливает состояние чекбокса снежинок (без эмита сигнала)"""
        if self._snowflakes_checkbox:
            self._snowflakes_checkbox.blockSignals(True)
            self._snowflakes_checkbox.setChecked(enabled)
            self._snowflakes_checkbox.blockSignals(False)

    def set_blur_effect_state(self, enabled: bool):
        """Устанавливает состояние чекбокса эффекта размытия (без эмита сигнала)"""
        if self._blur_effect_checkbox:
            self._blur_effect_checkbox.blockSignals(True)
            self._blur_effect_checkbox.setChecked(enabled)
            self._blur_effect_checkbox.blockSignals(False)

    def set_opacity_value(self, value: int):
        """Устанавливает значение слайдера прозрачности (без эмита сигнала)"""
        if self._opacity_slider:
            self._opacity_slider.blockSignals(True)
            self._opacity_slider.setValue(value)
            self._opacity_slider.blockSignals(False)
        if self._opacity_label:
            self._opacity_label.setText(f"{value}%")

    def update_themes(self, themes: list, current_theme: str = None):
        """Обновляет текущую выбранную тему (для совместимости)"""
        if current_theme:
            self.set_current_theme(current_theme)
