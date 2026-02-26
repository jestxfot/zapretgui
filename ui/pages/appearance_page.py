# ui/pages/appearance_page.py
"""Страница настроек оформления - темы"""

from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QColor
import qtawesome as qta

from .base_page import BasePage
from ui.compat_widgets import SettingsCard, ActionButton, SettingsRow
from ui.theme import get_theme_tokens

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, ColorPickerButton, setThemeColor,
        CheckBox, SegmentedWidget, RadioButton, Slider,
    )
    _HAS_FLUENT_LABELS = True
    _HAS_COLOR_PICKER = True
except ImportError:
    from PyQt6.QtWidgets import QCheckBox as CheckBox, QRadioButton as RadioButton, QSlider as Slider
    SegmentedWidget = None
    _HAS_FLUENT_LABELS = False
    _HAS_COLOR_PICKER = False


class AppearancePage(BasePage):
    """Страница настроек оформления"""

    # Сигнал смены режима отображения
    display_mode_changed = pyqtSignal(str)   # "dark" / "light" / "system"
    # Сигнал смены фонового пресета
    background_preset_changed = pyqtSignal(str)  # "standard" / "amoled" / "rkn_chan"
    # Сигнал изменения состояния гирлянды
    garland_changed = pyqtSignal(bool)
    # Сигнал изменения состояния снежинок
    snowflakes_changed = pyqtSignal(bool)
    # Сигнал изменения прозрачности окна (0-100)
    opacity_changed = pyqtSignal(int)
    # Сигнал изменения акцентного цвета (hex string)
    accent_color_changed = pyqtSignal(str)
    # Сигнал запроса обновления фона окна (при смене тонировки или акцента)
    background_refresh_needed = pyqtSignal()
    # Сигнал изменения Mica-эффекта
    mica_changed = pyqtSignal(bool)
    # Сигнал изменения анимаций интерфейса
    animations_changed = pyqtSignal(bool)
    # Сигнал изменения плавной прокрутки
    smooth_scroll_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Оформление", "Настройка внешнего вида приложения", parent)

        self._display_mode_seg = None    # SegmentedWidget
        self._bg_radio_standard = None   # RadioButton
        self._bg_radio_amoled = None     # RadioButton
        self._bg_radio_rkn_chan = None   # RadioButton
        self._is_premium = False
        self._garland_checkbox = None
        self._snowflakes_checkbox = None
        self._opacity_slider = None
        self._opacity_label = None
        self._opacity_icon_label = None
        self._garland_icon_label = None
        self._snowflakes_icon_label = None
        self._color_picker_btn = None
        self._follow_windows_accent_cb = None
        self._tinted_bg_cb = None
        self._tinted_intensity_container = None
        self._tinted_intensity_slider = None
        self._tinted_intensity_value_label = None
        self._mica_switch = None
        self._animations_switch = None
        self._smooth_scroll_switch = None

        self._build_ui()

    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # РЕЖИМ ОТОБРАЖЕНИЯ
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Режим отображения")

        display_card = SettingsCard()
        display_layout = QVBoxLayout()
        display_layout.setSpacing(12)

        display_desc = CaptionLabel("Выберите светлый или тёмный режим интерфейса.")
        display_desc.setWordWrap(True)
        display_layout.addWidget(display_desc)

        try:
            self._display_mode_seg = SegmentedWidget()
            self._display_mode_seg.addItem("dark", "🌙 Тёмный", lambda: self._on_display_mode_changed("dark"))
            self._display_mode_seg.addItem("light", "☀️ Светлый", lambda: self._on_display_mode_changed("light"))
            self._display_mode_seg.addItem("system", "⚙ Авто", lambda: self._on_display_mode_changed("system"))
            self._display_mode_seg.setCurrentItem("dark")
            display_layout.addWidget(self._display_mode_seg)
        except Exception:
            self._display_mode_seg = None

        display_card.add_layout(display_layout)
        self.add_widget(display_card)

        self.add_spacing(16)

        # ═══════════════════════════════════════════════════════════
        # ФОН ОКНА
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Фон окна")

        bg_card = SettingsCard()
        bg_layout = QVBoxLayout()
        bg_layout.setSpacing(12)

        bg_desc = CaptionLabel(
            "Стандартный фон соответствует режиму отображения. "
            "AMOLED и РКН Тян доступны подписчикам Premium."
        )
        bg_desc.setWordWrap(True)
        bg_layout.addWidget(bg_desc)

        # Standard row
        self._bg_radio_standard = RadioButton()
        self._bg_radio_standard.setText("Стандартный")
        self._bg_radio_standard.setChecked(True)
        self._bg_radio_standard.toggled.connect(lambda checked: self._on_bg_preset_toggled("standard", checked))
        bg_layout.addWidget(self._bg_radio_standard)

        # AMOLED row
        amoled_row = QHBoxLayout()
        self._bg_radio_amoled = RadioButton()
        self._bg_radio_amoled.setText("AMOLED — чёрный")
        self._bg_radio_amoled.setEnabled(False)
        self._bg_radio_amoled.toggled.connect(lambda checked: self._on_bg_preset_toggled("amoled", checked))
        amoled_row.addWidget(self._bg_radio_amoled)
        amoled_badge = QLabel("⭐ Premium")
        amoled_badge.setStyleSheet("color: #b45309; font-size: 10px; font-weight: bold; background: rgba(255,193,7,0.15); padding: 2px 6px; border-radius: 4px;")
        amoled_row.addWidget(amoled_badge)
        amoled_row.addStretch()
        bg_layout.addLayout(amoled_row)

        # РКН Тян row
        rkn_row = QHBoxLayout()
        self._bg_radio_rkn_chan = RadioButton()
        self._bg_radio_rkn_chan.setText("РКН Тян")
        self._bg_radio_rkn_chan.setEnabled(False)
        self._bg_radio_rkn_chan.toggled.connect(lambda checked: self._on_bg_preset_toggled("rkn_chan", checked))
        rkn_row.addWidget(self._bg_radio_rkn_chan)
        rkn_badge = QLabel("⭐ Premium")
        rkn_badge.setStyleSheet("color: #b45309; font-size: 10px; font-weight: bold; background: rgba(255,193,7,0.15); padding: 2px 6px; border-radius: 4px;")
        rkn_row.addWidget(rkn_badge)
        rkn_row.addStretch()
        bg_layout.addLayout(rkn_row)

        # Mica is always enabled on Win11 — no user toggle needed.

        bg_card.add_layout(bg_layout)
        self.add_widget(bg_card)

        self.add_spacing(16)

        # ═══════════════════════════════════════════════════════════
        # НОВОГОДНЕЕ ОФОРМЛЕНИЕ (Premium)
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Новогоднее оформление")

        garland_card = SettingsCard()
        garland_layout = QVBoxLayout()
        garland_layout.setSpacing(12)

        garland_desc = CaptionLabel(
            "Праздничная гирлянда с мерцающими огоньками в верхней части окна. "
            "Доступно только для подписчиков Premium."
        )
        garland_desc.setWordWrap(True)
        garland_layout.addWidget(garland_desc)

        garland_row = QHBoxLayout()
        garland_row.setSpacing(12)

        garland_icon = QLabel()
        self._garland_icon_label = garland_icon
        garland_icon.setPixmap(qta.icon('fa5s.holly-berry', color=get_theme_tokens().accent_hex).pixmap(20, 20))
        garland_row.addWidget(garland_icon)

        garland_label = BodyLabel("Новогодняя гирлянда")
        garland_row.addWidget(garland_label)

        premium_badge = QLabel("⭐ Premium")
        premium_badge.setStyleSheet("color: #b45309; font-size: 10px; font-weight: bold; background-color: rgba(255, 193, 7, 0.15); padding: 2px 6px; border-radius: 4px;")
        garland_row.addWidget(premium_badge)

        garland_row.addStretch()

        self._garland_checkbox = CheckBox()
        self._garland_checkbox.setEnabled(False)
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

        snowflakes_desc = CaptionLabel(
            "Мягко падающие снежинки по всему окну. "
            "Создаёт уютную зимнюю атмосферу."
        )
        snowflakes_desc.setWordWrap(True)
        snowflakes_layout.addWidget(snowflakes_desc)

        snowflakes_row = QHBoxLayout()
        snowflakes_row.setSpacing(12)

        snowflakes_icon = QLabel()
        self._snowflakes_icon_label = snowflakes_icon
        snowflakes_icon.setPixmap(qta.icon('fa5s.snowflake', color=get_theme_tokens().accent_hex).pixmap(20, 20))
        snowflakes_row.addWidget(snowflakes_icon)

        snowflakes_label = BodyLabel("Снежинки")
        snowflakes_row.addWidget(snowflakes_label)

        snowflakes_badge = QLabel("⭐ Premium")
        snowflakes_badge.setStyleSheet("color: #b45309; font-size: 10px; font-weight: bold; background-color: rgba(255, 193, 7, 0.15); padding: 2px 6px; border-radius: 4px;")
        snowflakes_row.addWidget(snowflakes_badge)

        snowflakes_row.addStretch()

        self._snowflakes_checkbox = CheckBox()
        self._snowflakes_checkbox.setEnabled(False)
        self._snowflakes_checkbox.setObjectName("snowflakesSwitch")
        self._snowflakes_checkbox.stateChanged.connect(self._on_snowflakes_changed)
        snowflakes_row.addWidget(self._snowflakes_checkbox)

        snowflakes_layout.addLayout(snowflakes_row)
        snowflakes_card.add_layout(snowflakes_layout)
        self.add_widget(snowflakes_card)

        self.add_spacing(16)

        # ═══════════════════════════════════════════════════════════
        # ПРОЗРАЧНОСТЬ ОКНА
        # ═══════════════════════════════════════════════════════════
        opacity_card = SettingsCard()
        opacity_layout = QVBoxLayout()
        opacity_layout.setSpacing(12)

        opacity_desc = CaptionLabel(
            "Настройка прозрачности всего окна приложения. "
            "При 0% окно полностью прозрачное, при 100% — непрозрачное."
        )
        opacity_desc.setWordWrap(True)
        opacity_layout.addWidget(opacity_desc)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(12)

        opacity_icon = QLabel()
        self._opacity_icon_label = opacity_icon
        opacity_icon.setPixmap(qta.icon('fa5s.adjust', color=get_theme_tokens().accent_hex).pixmap(20, 20))
        opacity_row.addWidget(opacity_icon)

        opacity_title = BodyLabel("Прозрачность окна")
        opacity_row.addWidget(opacity_title)

        opacity_row.addStretch()

        self._opacity_label = CaptionLabel("100%")
        self._opacity_label.setMinimumWidth(40)
        self._opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opacity_row.addWidget(self._opacity_label)

        opacity_layout.addLayout(opacity_row)

        self._opacity_slider = Slider(Qt.Orientation.Horizontal)
        self._opacity_slider.setMinimum(0)
        self._opacity_slider.setMaximum(100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.setSingleStep(1)
        self._opacity_slider.setPageStep(5)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self._opacity_slider)

        opacity_card.add_layout(opacity_layout)
        self.add_widget(opacity_card)

        self.add_spacing(16)

        # ═══════════════════════════════════════════════════════════
        # АКЦЕНТНЫЙ ЦВЕТ (qfluentwidgets setThemeColor)
        # ═══════════════════════════════════════════════════════════
        if _HAS_COLOR_PICKER:
            self.add_section_title("Акцентный цвет")

            accent_card = SettingsCard()
            accent_layout = QVBoxLayout()
            accent_layout.setSpacing(12)

            accent_desc = CaptionLabel(
                "Цвет акцентных элементов интерфейса: кнопок, иконок, индикаторов. "
                "Изменяет цвет нативных компонентов WinUI."
            )
            accent_desc.setWordWrap(True)
            accent_layout.addWidget(accent_desc)

            accent_row = SettingsRow("fa5s.palette", "Цвет акцента", "")
            self._color_picker_btn = ColorPickerButton(QColor("#0078d4"), "Выбрать цвет")
            self._color_picker_btn.colorChanged.connect(self._on_accent_color_changed)
            accent_row.set_control(self._color_picker_btn)
            accent_layout.addWidget(accent_row)

            win_accent_row = SettingsRow("fa5s.windows", "Акцент из Windows",
                "Автоматически использовать системный акцентный цвет Windows")
            self._follow_windows_accent_cb = CheckBox()
            self._follow_windows_accent_cb.stateChanged.connect(self._on_follow_windows_accent_changed)
            win_accent_row.set_control(self._follow_windows_accent_cb)
            accent_layout.addWidget(win_accent_row)

            tinted_bg_row = SettingsRow("fa5s.fill-drip", "Тонировать фон акцентным цветом",
                "Фон окна окрашивается в оттенок акцентного цвета")
            self._tinted_bg_cb = CheckBox()
            self._tinted_bg_cb.stateChanged.connect(self._on_tinted_bg_changed)
            tinted_bg_row.set_control(self._tinted_bg_cb)
            accent_layout.addWidget(tinted_bg_row)

            self._tinted_intensity_container = QWidget()
            intensity_row_layout = QHBoxLayout(self._tinted_intensity_container)
            intensity_row_layout.setContentsMargins(8, 0, 8, 0)
            intensity_row_layout.setSpacing(8)
            intensity_label = CaptionLabel("Интенсивность тонировки:")
            self._tinted_intensity_slider = Slider(Qt.Orientation.Horizontal)
            self._tinted_intensity_slider.setRange(0, 30)
            self._tinted_intensity_slider.setValue(15)
            self._tinted_intensity_value_label = CaptionLabel("15")
            self._tinted_intensity_slider.valueChanged.connect(self._on_tinted_intensity_changed)
            intensity_row_layout.addWidget(intensity_label)
            intensity_row_layout.addWidget(self._tinted_intensity_slider, 1)
            intensity_row_layout.addWidget(self._tinted_intensity_value_label)
            accent_layout.addWidget(self._tinted_intensity_container)

            accent_card.add_layout(accent_layout)
            self.add_widget(accent_card)

            self.add_spacing(16)
            self._load_accent_color()
            self._load_extra_accent_settings()

        # ═══════════════════════════════════════════════════════════
        # ПРОИЗВОДИТЕЛЬНОСТЬ
        # ═══════════════════════════════════════════════════════════
        self.add_section_title("Производительность")

        perf_card = SettingsCard()
        perf_layout = QVBoxLayout()
        perf_layout.setSpacing(12)

        try:
            from qfluentwidgets import SwitchButton

            anim_row = SettingsRow("fa5s.film", "Анимации интерфейса",
                "Анимации кнопок, переходов и элементов WinUI")
            self._animations_switch = SwitchButton()
            self._animations_switch.checkedChanged.connect(self._on_animations_changed)
            anim_row.set_control(self._animations_switch)
            perf_layout.addWidget(anim_row)

            scroll_row = SettingsRow("fa5s.mouse", "Плавная прокрутка",
                "Инерционная прокрутка страниц настроек")
            self._smooth_scroll_switch = SwitchButton()
            self._smooth_scroll_switch.checkedChanged.connect(self._on_smooth_scroll_changed)
            scroll_row.set_control(self._smooth_scroll_switch)
            perf_layout.addWidget(scroll_row)
        except Exception:
            pass

        perf_card.add_layout(perf_layout)
        self.add_widget(perf_card)
        self.add_spacing(16)
        self._load_performance_settings()

        # Load saved display mode and bg preset
        self._load_display_mode()
        self._load_bg_preset()

    def _load_display_mode(self):
        """Load saved display mode from registry."""
        try:
            from config.reg import get_display_mode
            mode = get_display_mode()
            if self._display_mode_seg is not None:
                self._display_mode_seg.blockSignals(True)
                try:
                    self._display_mode_seg.setCurrentItem(mode)
                except Exception:
                    pass
                self._display_mode_seg.blockSignals(False)
        except Exception:
            pass

    def _on_display_mode_changed(self, mode: str):
        """Handle display mode toggle."""
        try:
            from config.reg import set_display_mode
            set_display_mode(mode)
        except Exception:
            pass
        try:
            from qfluentwidgets import setTheme, Theme
            if mode == "light":
                setTheme(Theme.LIGHT)
            elif mode == "dark":
                setTheme(Theme.DARK)
            elif mode == "system":
                setTheme(Theme.AUTO)
        except Exception:
            pass
        # Update window background colors for the new mode
        try:
            from ui.theme import apply_window_background
            win = self.window()
            if win is not None:
                apply_window_background(win)
        except Exception:
            pass
        self.display_mode_changed.emit(mode)

    def _load_bg_preset(self):
        """Load saved background preset from registry."""
        try:
            from config.reg import get_background_preset
            preset = get_background_preset()
            self._apply_bg_preset_ui(preset)
        except Exception:
            pass

    def _apply_bg_preset_ui(self, preset: str):
        """Update RadioButton selection without emitting signals."""
        for radio, key in [
            (self._bg_radio_standard, "standard"),
            (self._bg_radio_amoled, "amoled"),
            (self._bg_radio_rkn_chan, "rkn_chan"),
        ]:
            if radio is not None:
                radio.blockSignals(True)
                radio.setChecked(key == preset)
                radio.blockSignals(False)

    def _on_bg_preset_toggled(self, preset: str, checked: bool):
        """Handle background preset RadioButton toggle."""
        if not checked:
            return
        try:
            from config.reg import set_background_preset
            set_background_preset(preset)
        except Exception:
            pass
        if self._mica_switch:
            self._mica_switch.setEnabled(preset == "standard")
        # AMOLED and РКН Тян require dark mode — force it automatically
        if preset in ("amoled", "rkn_chan"):
            self._on_display_mode_changed("dark")
            if self._display_mode_seg is not None:
                self._display_mode_seg.blockSignals(True)
                try:
                    self._display_mode_seg.setCurrentItem("dark")
                except Exception:
                    pass
                self._display_mode_seg.blockSignals(False)
        self.background_preset_changed.emit(preset)

    def _on_mica_changed(self, checked: bool):
        """Handle Mica SwitchButton toggle."""
        self.mica_changed.emit(checked)

    def set_mica_state(self, enabled: bool):
        """Set Mica SwitchButton state without triggering signal."""
        if self._mica_switch:
            self._mica_switch.blockSignals(True)
            self._mica_switch.setChecked(enabled)
            self._mica_switch.blockSignals(False)

    def _load_mica_state(self):
        """Load Mica state from registry."""
        try:
            from config.reg import get_mica_enabled, get_background_preset
            self.set_mica_state(get_mica_enabled())
            # Disable switch if non-standard preset is active
            if self._mica_switch:
                preset = get_background_preset()
                self._mica_switch.setEnabled(preset == "standard")
        except Exception:
            pass

    def _apply_theme_tokens(self, theme_name: str) -> None:
        """Refresh qtawesome icon labels on theme change."""
        try:
            tokens = get_theme_tokens(theme_name)
        except Exception:
            tokens = get_theme_tokens()
        self._refresh_accent_icons(tokens)

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

    def _on_accent_color_changed(self, color: QColor):
        """Обработчик изменения акцентного цвета через ColorPickerButton."""
        if not _HAS_COLOR_PICKER:
            return
        try:
            setThemeColor(color)
        except Exception:
            pass
        hex_color = color.name()
        try:
            from config.reg import set_accent_color
            set_accent_color(hex_color)
        except Exception:
            pass
        self.accent_color_changed.emit(hex_color)
        # If tinted bg is active, trigger window background refresh
        try:
            from config.reg import get_tinted_background
            if get_tinted_background():
                self.background_refresh_needed.emit()
        except Exception:
            pass

    def changeEvent(self, event):  # noqa: N802
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if hasattr(self, '_garland_icon_label'):
                self._refresh_accent_icons()
        super().changeEvent(event)

    def _refresh_accent_icons(self, tokens=None):
        """Обновляет иконки страницы при смене акцентного цвета."""
        if tokens is None:
            tokens = get_theme_tokens()
        for lbl, icon_name, size in (
            (self._garland_icon_label,   'fa5s.holly-berry', 20),
            (self._snowflakes_icon_label, 'fa5s.snowflake',  20),
            (self._opacity_icon_label,    'fa5s.adjust',     20),
        ):
            if lbl is not None:
                lbl.setPixmap(qta.icon(icon_name, color=tokens.accent_hex).pixmap(size, size))

    def _load_extra_accent_settings(self):
        """Загружает настройки Follow Windows Accent и Tinted Background."""
        if not _HAS_COLOR_PICKER:
            return
        try:
            from config.reg import (get_follow_windows_accent, get_tinted_background,
                                     get_tinted_background_intensity)
            follow = get_follow_windows_accent()
            tinted = get_tinted_background()
            intensity = get_tinted_background_intensity()

            if self._follow_windows_accent_cb is not None:
                self._follow_windows_accent_cb.blockSignals(True)
                self._follow_windows_accent_cb.setChecked(follow)
                self._follow_windows_accent_cb.blockSignals(False)

            if self._tinted_bg_cb is not None:
                self._tinted_bg_cb.blockSignals(True)
                self._tinted_bg_cb.setChecked(tinted)
                self._tinted_bg_cb.blockSignals(False)

            if self._tinted_intensity_slider is not None:
                self._tinted_intensity_slider.blockSignals(True)
                self._tinted_intensity_slider.setValue(intensity)
                self._tinted_intensity_slider.blockSignals(False)

            if self._tinted_intensity_value_label is not None:
                self._tinted_intensity_value_label.setText(str(intensity))

            if self._tinted_intensity_container is not None:
                self._tinted_intensity_container.setVisible(tinted)

            # If follow_windows is on: apply Windows accent now and disable picker
            if follow:
                self._apply_windows_accent()
                if self._color_picker_btn is not None:
                    self._color_picker_btn.setEnabled(False)
        except Exception:
            pass

    def _on_follow_windows_accent_changed(self, state):
        """Обработчик переключения 'Акцент из Windows'."""
        enabled = state == Qt.CheckState.Checked.value
        try:
            from config.reg import set_follow_windows_accent
            set_follow_windows_accent(enabled)
        except Exception:
            pass
        if enabled:
            self._apply_windows_accent()
            if self._color_picker_btn is not None:
                self._color_picker_btn.setEnabled(False)
        else:
            if self._color_picker_btn is not None:
                self._color_picker_btn.setEnabled(True)

    def _apply_windows_accent(self):
        """Читает системный акцент Windows и применяет его."""
        try:
            from config.reg import get_windows_system_accent, set_accent_color
            hex_color = get_windows_system_accent()
            if hex_color:
                color = QColor(hex_color)
                if color.isValid():
                    setThemeColor(color)
                    set_accent_color(hex_color)
                    if self._color_picker_btn is not None:
                        self._color_picker_btn.setColor(color)
                    self.accent_color_changed.emit(hex_color)
                    self.background_refresh_needed.emit()
        except Exception:
            pass

    def _on_tinted_bg_changed(self, state):
        """Обработчик переключения 'Тонировать фон'."""
        enabled = state == Qt.CheckState.Checked.value
        try:
            from config.reg import set_tinted_background
            set_tinted_background(enabled)
        except Exception:
            pass
        if self._tinted_intensity_container is not None:
            self._tinted_intensity_container.setVisible(enabled)
        self.background_refresh_needed.emit()

    def _on_tinted_intensity_changed(self, value: int):
        """Обработчик изменения интенсивности тонировки."""
        try:
            from config.reg import set_tinted_background_intensity
            set_tinted_background_intensity(value)
        except Exception:
            pass
        if self._tinted_intensity_value_label is not None:
            self._tinted_intensity_value_label.setText(str(value))
        self.background_refresh_needed.emit()

    def _load_accent_color(self):
        """Загружает сохранённый акцентный цвет и применяет его."""
        if not _HAS_COLOR_PICKER or self._color_picker_btn is None:
            return
        try:
            from config.reg import get_accent_color
            hex_color = get_accent_color()
            if hex_color:
                color = QColor(hex_color)
                if color.isValid():
                    self._color_picker_btn.setColor(color)
                    setThemeColor(color)
        except Exception:
            pass

    def set_current_theme(self, theme_name: str):
        """No-op: theme selection removed. Kept for backward compatibility."""
        pass

    def update_themes(self, themes: list, current_theme: str = None):
        """No-op: theme selection removed. Kept for backward compatibility."""
        pass

    def set_premium_status(self, is_premium: bool):
        """Update premium status — unlocks AMOLED/РКН Тян bg presets."""
        self._is_premium = is_premium

        # Unlock/lock premium bg preset radio buttons
        if self._bg_radio_amoled is not None:
            self._bg_radio_amoled.setEnabled(is_premium)
        if self._bg_radio_rkn_chan is not None:
            self._bg_radio_rkn_chan.setEnabled(is_premium)

        # If premium lost and a premium preset is active, switch back to standard
        if not is_premium:
            try:
                from config.reg import get_background_preset, set_background_preset
                current_preset = get_background_preset()
                if current_preset in ("amoled", "rkn_chan"):
                    set_background_preset("standard")
                    self._apply_bg_preset_ui("standard")
                    self.background_preset_changed.emit("standard")
            except Exception:
                pass

        # Update garland/snowflakes checkboxes (unchanged logic)
        from config.reg import get_garland_enabled, get_snowflakes_enabled

        if self._garland_checkbox:
            self._garland_checkbox.setEnabled(is_premium)
            self._garland_checkbox.blockSignals(True)
            if is_premium:
                self._garland_checkbox.setChecked(get_garland_enabled())
            else:
                self._garland_checkbox.setChecked(False)
            self._garland_checkbox.blockSignals(False)

        if self._snowflakes_checkbox:
            self._snowflakes_checkbox.setEnabled(is_premium)
            self._snowflakes_checkbox.blockSignals(True)
            if is_premium:
                self._snowflakes_checkbox.setChecked(get_snowflakes_enabled())
            else:
                self._snowflakes_checkbox.setChecked(False)
            self._snowflakes_checkbox.blockSignals(False)

        if not is_premium and self._garland_checkbox and self._garland_checkbox.isChecked():
            self._garland_checkbox.blockSignals(True)
            self._garland_checkbox.setChecked(False)
            self._garland_checkbox.blockSignals(False)
            from config.reg import set_garland_enabled
            set_garland_enabled(False)
            self.garland_changed.emit(False)

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

    def set_opacity_value(self, value: int):
        """Устанавливает значение слайдера прозрачности (без эмита сигнала)"""
        if self._opacity_slider:
            self._opacity_slider.blockSignals(True)
            self._opacity_slider.setValue(value)
            self._opacity_slider.blockSignals(False)
        if self._opacity_label:
            self._opacity_label.setText(f"{value}%")

    def _on_animations_changed(self, enabled: bool):
        """Handle animations SwitchButton toggle."""
        try:
            from config.reg import set_animations_enabled
            set_animations_enabled(enabled)
        except Exception:
            pass
        self.animations_changed.emit(enabled)

    def _on_smooth_scroll_changed(self, enabled: bool):
        """Handle smooth scroll SwitchButton toggle."""
        try:
            from config.reg import set_smooth_scroll_enabled
            set_smooth_scroll_enabled(enabled)
        except Exception:
            pass
        self.smooth_scroll_changed.emit(enabled)

    def _load_performance_settings(self):
        """Load animations and smooth scroll state from registry into switches."""
        try:
            from config.reg import get_animations_enabled, get_smooth_scroll_enabled
            anim = get_animations_enabled()
            smooth = get_smooth_scroll_enabled()
            if self._animations_switch is not None:
                self._animations_switch.blockSignals(True)
                self._animations_switch.setChecked(anim)
                self._animations_switch.blockSignals(False)
            if self._smooth_scroll_switch is not None:
                self._smooth_scroll_switch.blockSignals(True)
                self._smooth_scroll_switch.setChecked(smooth)
                self._smooth_scroll_switch.blockSignals(False)
        except Exception:
            pass
