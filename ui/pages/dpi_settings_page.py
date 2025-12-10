# ui/pages/dpi_settings_page.py
"""Страница настроек DPI"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QCheckBox, QSpinBox)
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, ActionButton
from log import log


class Win11ToggleSwitch(QCheckBox):
    """Toggle Switch в стиле Windows 11"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._circle_position = 4.0
        self._color_blend = 0.0  # Для совместимости с servers_page версией
        
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(150)
        
        self.stateChanged.connect(self._animate)
        
    def _get_circle_position(self):
        return self._circle_position
        
    def _set_circle_position(self, pos):
        self._circle_position = pos
        self.update()
        
    circle_position = pyqtProperty(float, _get_circle_position, _set_circle_position)
    
    def _get_color_blend(self):
        return self._color_blend
    
    def _set_color_blend(self, value):
        self._color_blend = value
        self.update()
    
    color_blend = pyqtProperty(float, _get_color_blend, _set_color_blend)
    
    def _animate(self, state):
        if not self._animation:
            return
        self._animation.stop()
        if state:
            self._animation.setStartValue(self._circle_position)
            self._animation.setEndValue(self.width() - 18)
        else:
            self._animation.setStartValue(self._circle_position)
            self._animation.setEndValue(4.0)
        self._animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        if self.isChecked():
            bg_color = QColor("#60cdff")
        else:
            bg_color = QColor(80, 80, 80)
            
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 11, 11)
        painter.fillPath(path, bg_color)
        
        # Рамка
        painter.setPen(QColor(100, 100, 100) if not self.isChecked() else Qt.GlobalColor.transparent)
        painter.drawPath(path)
        
        # Круг
        circle_color = QColor("#ffffff")
        painter.setBrush(circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(self._circle_position, 4, 14, 14))
        
        painter.end()
        
    def hitButton(self, pos):
        return self.rect().contains(pos)


class Win11ToggleRow(QWidget):
    """Строка с toggle switch в стиле Windows 11"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, icon_name: str, title: str, description: str = "", 
                 icon_color: str = "#60cdff", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        icon_label.setFixedSize(22, 22)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        text_layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                }
            """)
            text_layout.addWidget(desc_label)
            
        layout.addLayout(text_layout, 1)
        
        # Toggle
        self.toggle = Win11ToggleSwitch()
        self.toggle.toggled.connect(self.toggled.emit)
        layout.addWidget(self.toggle)
        
    def setChecked(self, checked: bool, block_signals: bool = False):
        if block_signals:
            self.toggle.blockSignals(True)
        self.toggle.setChecked(checked)
        if block_signals:
            self.toggle.blockSignals(False)
            # Обновляем позицию круга без анимации
            self.toggle._circle_position = (self.toggle.width() - 18) if checked else 4.0
            self.toggle.update()
        
    def isChecked(self) -> bool:
        return self.toggle.isChecked()


class Win11RadioOption(QWidget):
    """Радио-опция в стиле Windows 11"""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str, description: str, icon_name: str = None, 
                 icon_color: str = "#60cdff", recommended: bool = False, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._selected = False
        self._hover = False
        self._recommended = recommended
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Радио-круг
        self.radio_circle = QWidget()
        self.radio_circle.setFixedSize(20, 20)
        layout.addWidget(self.radio_circle)
        
        # Иконка (опционально)
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(24, 24))
            icon_label.setFixedSize(28, 28)
            layout.addWidget(icon_label)
        
        # Текстовый блок
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок с бейджем
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        title_layout.addWidget(title_label)
        
        if recommended:
            badge = QLabel("рекомендуется")
            badge.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: #60cdff;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 6px;
                    border-radius: 3px;
                }
            """)
            title_layout.addWidget(badge)
        
        title_layout.addStretch()
        text_layout.addLayout(title_layout)
        
        # Описание
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
                line-height: 1.3;
            }
        """)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        self._update_style()
        
    def setSelected(self, selected: bool):
        self._selected = selected
        self._update_style()
        
    def isSelected(self) -> bool:
        return self._selected
        
    def _update_style(self):
        if self._selected:
            bg = "rgba(96, 205, 255, 0.15)"
            border = "rgba(96, 205, 255, 0.6)"
        elif self._hover:
            bg = "rgba(255, 255, 255, 0.06)"
            border = "rgba(255, 255, 255, 0.15)"
        else:
            bg = "rgba(255, 255, 255, 0.03)"
            border = "rgba(255, 255, 255, 0.08)"
            
        self.setStyleSheet(f"""
            Win11RadioOption {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        self.update()
        
    def enterEvent(self, event):
        self._hover = True
        self._update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hover = False
        self._update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Рисуем радио-круг
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Позиция круга
        circle_x = 12 + 10  # margin + half width
        circle_y = self.height() // 2
        
        # Внешний круг
        if self._selected:
            painter.setPen(QColor("#60cdff"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.setPen(QColor(100, 100, 100))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
        painter.drawEllipse(circle_x - 8, circle_y - 8, 16, 16)
        
        # Внутренний круг (если выбран)
        if self._selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#60cdff"))
            painter.drawEllipse(circle_x - 4, circle_y - 4, 8, 8)
            
        painter.end()


class Win11NumberRow(QWidget):
    """Строка с числовым вводом в стиле Windows 11"""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, icon_name: str, title: str, description: str = "", 
                 icon_color: str = "#60cdff", min_val: int = 0, max_val: int = 999,
                 default_val: int = 10, suffix: str = "", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
        icon_label.setFixedSize(22, 22)
        layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        text_layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                }
            """)
            text_layout.addWidget(desc_label)
            
        layout.addLayout(text_layout, 1)
        
        # SpinBox
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setSuffix(suffix)
        self.spinbox.setFixedWidth(80)
        self.spinbox.setFixedHeight(28)
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 2px 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QSpinBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.3);
            }
            QSpinBox:focus {
                border: 1px solid #60cdff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
                background: none;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 0px;
                height: 0px;
            }
        """)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.spinbox)
        
    def setValue(self, value: int, block_signals: bool = False):
        if block_signals:
            self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        if block_signals:
            self.spinbox.blockSignals(False)
        
    def value(self) -> int:
        return self.spinbox.value()


class DpiSettingsPage(BasePage):
    """Страница настроек DPI"""
    
    launch_method_changed = pyqtSignal(str)
    filters_changed = pyqtSignal()  # Сигнал при изменении фильтров
    
    def __init__(self, parent=None):
        super().__init__("Настройки DPI", "Параметры обхода блокировок", parent)
        self._build_ui()
        self._load_settings()
        
    def _build_ui(self):
        """Строит UI страницы"""
        
        # Метод запуска
        method_card = SettingsCard("Метод запуска стратегий")
        method_layout = QVBoxLayout()
        method_layout.setSpacing(10)
        
        method_desc = QLabel("Выберите способ запуска обхода блокировок")
        method_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        method_layout.addWidget(method_desc)
        
        # Zapret 2 (direct) - рекомендуется
        self.method_direct = Win11RadioOption(
            "Zapret 2", 
            "Прямой запуск с гибкими настройками. Поддерживает фильтры трафика, out-range и раздельные стратегии.",
            icon_name="mdi.rocket-launch",
            icon_color="#60cdff",
            recommended=True
        )
        self.method_direct.clicked.connect(lambda: self._select_method("direct"))
        method_layout.addWidget(self.method_direct)
        
        # Zapret 1 (bat)
        self.method_bat = Win11RadioOption(
            "Zapret 1", 
            "Запуск через .bat файлы. Классический метод, использует готовые скрипты из папки zapret.",
            icon_name="mdi.file-code",
            icon_color="#ff9800"
        )
        self.method_bat.clicked.connect(lambda: self._select_method("bat"))
        method_layout.addWidget(self.method_bat)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); margin: 8px 0;")
        separator.setFixedHeight(1)
        method_layout.addWidget(separator)
        
        # ─────────────────────────────────────────────────────────────────────
        # OUT-RANGE НАСТРОЙКИ (только для Zapret 2)
        # ─────────────────────────────────────────────────────────────────────
        self.out_range_container = QWidget()
        out_range_layout = QVBoxLayout(self.out_range_container)
        out_range_layout.setContentsMargins(0, 0, 0, 0)
        out_range_layout.setSpacing(6)
        
        out_range_label = QLabel("Лимит пакетов (--out-range)")
        out_range_label.setStyleSheet("color: #60cdff; font-size: 12px; font-weight: 600;")
        out_range_layout.addWidget(out_range_label)
        
        out_range_desc = QLabel("Сколько пакетов обрабатывать (0 = без лимита)")
        out_range_desc.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; margin-bottom: 4px;")
        out_range_layout.addWidget(out_range_desc)
        
        self.out_range_discord = Win11NumberRow(
            "mdi.discord", "Discord", 
            "Лимит пакетов для Discord трафика", "#7289da",
            min_val=0, max_val=999, default_val=10)
        out_range_layout.addWidget(self.out_range_discord)
        
        self.out_range_youtube = Win11NumberRow(
            "mdi.youtube", "YouTube", 
            "Лимит пакетов для YouTube трафика", "#ff0000",
            min_val=0, max_val=999, default_val=10)
        out_range_layout.addWidget(self.out_range_youtube)
        
        method_layout.addWidget(self.out_range_container)
        
        # Разделитель 2
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); margin: 8px 0;")
        separator2.setFixedHeight(1)
        method_layout.addWidget(separator2)
        
        # Перезапуск Discord
        self.discord_restart_toggle = Win11ToggleRow(
            "mdi.discord", "Перезапуск Discord", 
            "Автоперезапуск при смене стратегии", "#7289da")
        method_layout.addWidget(self.discord_restart_toggle)
        
        method_card.add_layout(method_layout)
        self.layout.addWidget(method_card)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ФИЛЬТРЫ ПЕРЕХВАТА ТРАФИКА
        # ═══════════════════════════════════════════════════════════════════════
        self.filters_card = SettingsCard("ФИЛЬТРЫ ПЕРЕХВАТА ТРАФИКА")
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(6)
        
        # ─────────────────────────────────────────────────────────────────────
        # TCP ПОРТЫ (HTTP/HTTPS)
        # ─────────────────────────────────────────────────────────────────────
        tcp_section = QLabel("TCP порты (HTTP/HTTPS)")
        tcp_section.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: 600; padding-top: 8px;")
        filters_layout.addWidget(tcp_section)
        
        self.tcp_80_toggle = Win11ToggleRow(
            "fa5s.globe", "Port 80 (HTTP)", 
            "Перехват HTTP трафика", "#4CAF50")
        filters_layout.addWidget(self.tcp_80_toggle)
        
        self.tcp_443_toggle = Win11ToggleRow(
            "fa5s.lock", "Port 443 (HTTPS/TLS)", 
            "Перехват HTTPS трафика", "#4CAF50")
        filters_layout.addWidget(self.tcp_443_toggle)
        
        self.tcp_all_ports_toggle = Win11ToggleRow(
            "fa5s.bolt", "Ports 444-65535 (game filter)", 
            "⚠ Высокая нагрузка на CPU", "#ff9800")
        filters_layout.addWidget(self.tcp_all_ports_toggle)
        
        # ─────────────────────────────────────────────────────────────────────
        # UDP ПОРТЫ (нагружает CPU)
        # ─────────────────────────────────────────────────────────────────────
        udp_section = QLabel("UDP порты (нагружает CPU)")
        udp_section.setStyleSheet("color: #ff9800; font-size: 12px; font-weight: 600; padding-top: 16px;")
        filters_layout.addWidget(udp_section)
        
        self.udp_443_toggle = Win11ToggleRow(
            "fa5s.fire", "Port 443 (QUIC)", 
            "YouTube QUIC и HTTP/3", "#ff9800")
        filters_layout.addWidget(self.udp_443_toggle)
        
        self.udp_all_ports_toggle = Win11ToggleRow(
            "fa5s.bolt", "Ports 444-65535 (game filter)", 
            "⚠ Очень высокая нагрузка", "#f44336")
        filters_layout.addWidget(self.udp_all_ports_toggle)
        
        # ─────────────────────────────────────────────────────────────────────
        # RAW-PART ФИЛЬТРЫ (экономят CPU)
        # ─────────────────────────────────────────────────────────────────────
        raw_section = QLabel("Raw-part фильтры (экономят CPU)")
        raw_section.setStyleSheet("color: #2196F3; font-size: 12px; font-weight: 600; padding-top: 16px;")
        filters_layout.addWidget(raw_section)
        
        self.raw_discord_toggle = Win11ToggleRow(
            "mdi.discord", "Discord Media", 
            "Голосовые каналы Discord", "#7289da")
        filters_layout.addWidget(self.raw_discord_toggle)
        
        self.raw_stun_toggle = Win11ToggleRow(
            "fa5s.phone", "STUN (голосовые звонки)", 
            "Discord, Telegram звонки", "#00bcd4")
        filters_layout.addWidget(self.raw_stun_toggle)
        
        self.raw_wireguard_toggle = Win11ToggleRow(
            "fa5s.shield-alt", "WireGuard (VPN)", 
            "Обход блокировки VPN", "#e91e63")
        filters_layout.addWidget(self.raw_wireguard_toggle)
        
        self.filters_card.add_layout(filters_layout)
        self.layout.addWidget(self.filters_card)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
        # ═══════════════════════════════════════════════════════════════════════
        self.advanced_card = SettingsCard("ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ")
        advanced_layout = QVBoxLayout()
        advanced_layout.setSpacing(6)
        
        # Описание
        advanced_desc = QLabel("⚠ Изменяйте только если знаете что делаете")
        advanced_desc.setStyleSheet("color: #ff9800; font-size: 11px; padding-bottom: 8px;")
        advanced_layout.addWidget(advanced_desc)
        
        # WSSize
        self.wssize_toggle = Win11ToggleRow(
            "fa5s.ruler-horizontal", "Включить --wssize", 
            "Добавляет параметр размера окна TCP", "#9c27b0")
        advanced_layout.addWidget(self.wssize_toggle)
        
        # Allzone hostlist
        self.allzone_toggle = Win11ToggleRow(
            "fa5s.list-alt", "Использовать allzone.txt", 
            "Заменяет other.txt на расширенный список", "#ff5722")
        advanced_layout.addWidget(self.allzone_toggle)
        
        # Применить ко всем сайтам
        self.remove_hostlists_toggle = Win11ToggleRow(
            "fa5s.globe-americas", "Применить ко всем сайтам", 
            "Убирает привязку к хост-листам", "#2196F3")
        advanced_layout.addWidget(self.remove_hostlists_toggle)
        
        # Применить ко всем IP
        self.remove_ipsets_toggle = Win11ToggleRow(
            "fa5s.network-wired", "Применить ко всем IP", 
            "Убирает привязку к IP-спискам", "#009688")
        advanced_layout.addWidget(self.remove_ipsets_toggle)
        
        # Debug лог
        self.debug_log_toggle = Win11ToggleRow(
            "mdi.file-document-outline", "Включить лог-файл (--debug)", 
            "Записывает логи winws в папку logs", "#00bcd4")
        advanced_layout.addWidget(self.debug_log_toggle)
        
        self.advanced_card.add_layout(advanced_layout)
        self.layout.addWidget(self.advanced_card)
        
        self.layout.addStretch()
        
    def _load_settings(self):
        """Загружает настройки"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            # Устанавливаем выбранный метод
            self._update_method_selection(method)
            
            # Discord restart setting
            self._load_discord_restart_setting()
            
            # Out-range settings
            self._load_out_range_settings()
                    
            self._update_filters_visibility()
            self._load_filter_settings()
            
        except Exception as e:
            log(f"Ошибка загрузки настроек DPI: {e}", "WARNING")
    
    def _update_method_selection(self, method: str):
        """Обновляет визуальное состояние выбора метода"""
        self.method_direct.setSelected(method == "direct")
        self.method_bat.setSelected(method == "bat")
    
    def _select_method(self, method: str):
        """Обработчик выбора метода"""
        try:
            from strategy_menu import set_strategy_launch_method
            set_strategy_launch_method(method)
            self._update_method_selection(method)
            self._update_filters_visibility()
            self.launch_method_changed.emit(method)
        except Exception as e:
            log(f"Ошибка смены метода: {e}", "ERROR")
    
    def _load_discord_restart_setting(self):
        """Загружает настройку перезапуска Discord"""
        try:
            from discord.discord_restart import get_discord_restart_setting, set_discord_restart_setting
            
            # Загружаем текущее значение (по умолчанию True), блокируя сигналы
            self.discord_restart_toggle.setChecked(get_discord_restart_setting(default=True), block_signals=True)
            
            # Подключаем сигнал сохранения
            self.discord_restart_toggle.toggled.connect(self._on_discord_restart_changed)
            
        except Exception as e:
            log(f"Ошибка загрузки настройки Discord: {e}", "WARNING")
    
    def _on_discord_restart_changed(self, enabled: bool):
        """Обработчик изменения настройки перезапуска Discord"""
        try:
            from discord.discord_restart import set_discord_restart_setting
            set_discord_restart_setting(enabled)
            status = "включён" if enabled else "отключён"
            log(f"Автоперезапуск Discord {status}", "INFO")
        except Exception as e:
            log(f"Ошибка сохранения настройки Discord: {e}", "ERROR")
    
    def _load_out_range_settings(self):
        """Загружает настройки out-range"""
        try:
            from strategy_menu import (
                get_out_range_discord, set_out_range_discord,
                get_out_range_youtube, set_out_range_youtube
            )
            
            # Загружаем значения (блокируем сигналы)
            self.out_range_discord.setValue(get_out_range_discord(), block_signals=True)
            self.out_range_youtube.setValue(get_out_range_youtube(), block_signals=True)
            
            # Подключаем сигналы сохранения
            self.out_range_discord.valueChanged.connect(self._on_out_range_discord_changed)
            self.out_range_youtube.valueChanged.connect(self._on_out_range_youtube_changed)
            
        except Exception as e:
            log(f"Ошибка загрузки настроек out-range: {e}", "WARNING")
    
    def _on_out_range_discord_changed(self, value: int):
        """Обработчик изменения out-range для Discord"""
        try:
            from strategy_menu import set_out_range_discord
            set_out_range_discord(value)
            log(f"Out-range Discord: -d{value}", "DEBUG")
            # Обновляем командную строку
            self.filters_changed.emit()
            # Перезапускаем DPI асинхронно
            self._restart_dpi_async()
        except Exception as e:
            log(f"Ошибка сохранения out-range Discord: {e}", "ERROR")
    
    def _on_out_range_youtube_changed(self, value: int):
        """Обработчик изменения out-range для YouTube"""
        try:
            from strategy_menu import set_out_range_youtube
            set_out_range_youtube(value)
            log(f"Out-range YouTube: -d{value}", "DEBUG")
            # Обновляем командную строку
            self.filters_changed.emit()
            # Перезапускаем DPI асинхронно
            self._restart_dpi_async()
        except Exception as e:
            log(f"Ошибка сохранения out-range YouTube: {e}", "ERROR")
    
    def _get_app(self):
        """Получает ссылку на главное приложение"""
        try:
            # Ищем через parent виджетов
            widget = self
            while widget:
                if hasattr(widget, 'dpi_controller'):
                    return widget
                if hasattr(widget, 'parent_app'):
                    return widget.parent_app
                widget = widget.parent()
            
            # Пробуем через QApplication
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if hasattr(app, 'dpi_controller'):
                return app
                
            # Пробуем через main_window
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'parent_app'):
                    return widget.parent_app
        except:
            pass
        return None
    
    def _restart_dpi_async(self):
        """Асинхронно перезапускает DPI если он запущен"""
        try:
            app = self._get_app()
            if not app or not hasattr(app, 'dpi_controller'):
                log("DPI контроллер не найден для перезапуска", "DEBUG")
                return
            
            # Проверяем, запущен ли процесс
            if not app.dpi_starter.check_process_running_wmi(silent=True):
                log("DPI не запущен, перезапуск не требуется", "DEBUG")
                return
                
            log("🔄 Перезапуск DPI после изменения out-range...", "INFO")
            
            # Асинхронно останавливаем
            app.dpi_controller.stop_dpi_async()
            
            # Запускаем таймер для проверки остановки и перезапуска
            self._restart_check_count = 0
            if not hasattr(self, '_restart_timer') or self._restart_timer is None:
                self._restart_timer = QTimer(self)
                self._restart_timer.timeout.connect(self._check_stopped_and_restart)
            self._restart_timer.start(300)  # Проверяем каждые 300мс
            
        except Exception as e:
            log(f"Ошибка перезапуска DPI: {e}", "ERROR")
    
    def _check_stopped_and_restart(self):
        """Проверяет остановку DPI и запускает заново"""
        try:
            app = self._get_app()
            if not app:
                self._restart_timer.stop()
                return
                
            self._restart_check_count += 1
            
            # Максимум 30 проверок (9 секунд)
            if self._restart_check_count > 30:
                self._restart_timer.stop()
                log("⚠️ Таймаут ожидания остановки DPI", "WARNING")
                self._start_dpi_after_stop()
                return
            
            # Проверяем, остановлен ли процесс
            if not app.dpi_starter.check_process_running_wmi(silent=True):
                self._restart_timer.stop()
                # Небольшая пауза и запуск
                QTimer.singleShot(200, self._start_dpi_after_stop)
                
        except Exception as e:
            if hasattr(self, '_restart_timer'):
                self._restart_timer.stop()
            log(f"Ошибка проверки остановки: {e}", "ERROR")
    
    def _start_dpi_after_stop(self):
        """Запускает DPI после остановки"""
        try:
            app = self._get_app()
            if not app or not hasattr(app, 'dpi_controller'):
                return
                
            from strategy_menu import get_strategy_launch_method
            launch_method = get_strategy_launch_method()
            
            if launch_method == "direct":
                # Прямой запуск - берём текущие настройки
                from strategy_menu import get_direct_strategy_selections
                from strategy_menu.strategy_lists_separated import combine_strategies
                
                selections = get_direct_strategy_selections()
                combined = combine_strategies(**selections)
                
                # Формируем данные в правильном формате
                selected_mode = {
                    'is_combined': True,
                    'name': combined.get('description', 'Перезапуск'),
                    'args': combined.get('args', ''),
                    'category_strategies': combined.get('category_strategies', {})
                }
                app.dpi_controller.start_dpi_async(selected_mode=selected_mode)
            else:
                # BAT режим
                app.dpi_controller.start_dpi_async()
                
            log("✅ DPI перезапущен с новыми настройками out-range", "INFO")
            
        except Exception as e:
            log(f"Ошибка запуска DPI: {e}", "ERROR")
        
    def _load_filter_settings(self):
        """Загружает настройки фильтров"""
        try:
            from strategy_menu import (
                get_wf_tcp_80_enabled, set_wf_tcp_80_enabled,
                get_wf_tcp_443_enabled, set_wf_tcp_443_enabled,
                get_wf_tcp_all_ports_enabled, set_wf_tcp_all_ports_enabled,
                get_wf_udp_443_enabled, set_wf_udp_443_enabled,
                get_wf_udp_all_ports_enabled, set_wf_udp_all_ports_enabled,
                get_wf_raw_discord_media_enabled, set_wf_raw_discord_media_enabled,
                get_wf_raw_stun_enabled, set_wf_raw_stun_enabled,
                get_wf_raw_wireguard_enabled, set_wf_raw_wireguard_enabled,
                get_wssize_enabled, set_wssize_enabled,
                get_allzone_hostlist_enabled, set_allzone_hostlist_enabled,
                get_remove_hostlists_enabled, set_remove_hostlists_enabled,
                get_remove_ipsets_enabled, set_remove_ipsets_enabled,
                get_debug_log_enabled, set_debug_log_enabled
            )
            
            # TCP (блокируем сигналы при загрузке)
            self.tcp_80_toggle.setChecked(get_wf_tcp_80_enabled(), block_signals=True)
            self.tcp_443_toggle.setChecked(get_wf_tcp_443_enabled(), block_signals=True)
            self.tcp_all_ports_toggle.setChecked(get_wf_tcp_all_ports_enabled(), block_signals=True)
            
            # UDP
            self.udp_443_toggle.setChecked(get_wf_udp_443_enabled(), block_signals=True)
            self.udp_all_ports_toggle.setChecked(get_wf_udp_all_ports_enabled(), block_signals=True)
            
            # Raw-part
            self.raw_discord_toggle.setChecked(get_wf_raw_discord_media_enabled(), block_signals=True)
            self.raw_stun_toggle.setChecked(get_wf_raw_stun_enabled(), block_signals=True)
            self.raw_wireguard_toggle.setChecked(get_wf_raw_wireguard_enabled(), block_signals=True)
            
            # Дополнительные настройки
            self.wssize_toggle.setChecked(get_wssize_enabled(), block_signals=True)
            self.allzone_toggle.setChecked(get_allzone_hostlist_enabled(), block_signals=True)
            self.remove_hostlists_toggle.setChecked(get_remove_hostlists_enabled(), block_signals=True)
            self.remove_ipsets_toggle.setChecked(get_remove_ipsets_enabled(), block_signals=True)
            self.debug_log_toggle.setChecked(get_debug_log_enabled(), block_signals=True)
            
            # Подключаем сигналы сохранения
            self.tcp_80_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_80_enabled, v))
            self.tcp_443_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_443_enabled, v))
            self.tcp_all_ports_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_all_ports_enabled, v))
            
            self.udp_443_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_udp_443_enabled, v))
            self.udp_all_ports_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_udp_all_ports_enabled, v))
            
            self.raw_discord_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_discord_media_enabled, v))
            self.raw_stun_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_stun_enabled, v))
            self.raw_wireguard_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_wireguard_enabled, v))
            
            # Дополнительные настройки - сигналы
            self.wssize_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wssize_enabled, v))
            self.allzone_toggle.toggled.connect(lambda v: self._on_filter_changed(set_allzone_hostlist_enabled, v))
            self.remove_hostlists_toggle.toggled.connect(lambda v: self._on_filter_changed(set_remove_hostlists_enabled, v))
            self.remove_ipsets_toggle.toggled.connect(lambda v: self._on_filter_changed(set_remove_ipsets_enabled, v))
            self.debug_log_toggle.toggled.connect(lambda v: self._on_filter_changed(set_debug_log_enabled, v))
            
        except Exception as e:
            log(f"Ошибка загрузки фильтров: {e}", "WARNING")
            import traceback
            log(traceback.format_exc(), "DEBUG")
                
    def _on_filter_changed(self, setter_func, value):
        """Обработчик изменения фильтра"""
        setter_func(value)
        self.filters_changed.emit()
        
    def _update_filters_visibility(self):
        """Обновляет видимость фильтров"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            is_direct = method == "direct"
            self.filters_card.setVisible(is_direct)
            self.advanced_card.setVisible(is_direct)
            self.out_range_container.setVisible(is_direct)
        except:
            pass
