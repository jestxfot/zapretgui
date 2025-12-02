# ui/pages/dpi_settings_page.py
"""Страница настроек DPI"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QComboBox, QCheckBox)
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
    
    def _animate(self, state):
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
        
    def setChecked(self, checked: bool):
        self.toggle.setChecked(checked)
        
    def isChecked(self) -> bool:
        return self.toggle.isChecked()


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
        method_layout.setSpacing(12)
        
        method_desc = QLabel("Выберите способ запуска обхода блокировок")
        method_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        method_layout.addWidget(method_desc)
        
        self.method_combo = QComboBox()
        self.method_combo.addItem("Zapret 2 (рекомендуется)", "direct")
        self.method_combo.addItem("Zapret 1 (через .bat файлы)", "bat")
        self.method_combo.setFixedHeight(40)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                selection-background-color: rgba(96, 205, 255, 0.3);
                color: #ffffff;
                padding: 4px;
            }
        """)
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_layout.addWidget(self.method_combo)
        
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
        
        self.raw_quic_toggle = Win11ToggleRow(
            "mdi.youtube", "QUIC Initial (YouTube)", 
            "Для YouTube и HTTP/3", "#f44336")
        filters_layout.addWidget(self.raw_quic_toggle)
        
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
        
        self.advanced_card.add_layout(advanced_layout)
        self.layout.addWidget(self.advanced_card)
        
        self.layout.addStretch()
        
    def _load_settings(self):
        """Загружает настройки"""
        try:
            from strategy_menu import get_strategy_launch_method
            method = get_strategy_launch_method()
            
            for i in range(self.method_combo.count()):
                if self.method_combo.itemData(i) == method:
                    self.method_combo.blockSignals(True)
                    self.method_combo.setCurrentIndex(i)
                    self.method_combo.blockSignals(False)
                    break
                    
            self._update_filters_visibility()
            self._load_filter_settings()
            
        except Exception as e:
            log(f"Ошибка загрузки настроек DPI: {e}", "WARNING")
            
    def _load_filter_settings(self):
        """Загружает настройки фильтров"""
        try:
            from strategy_menu import (
                get_wf_tcp_80_enabled, set_wf_tcp_80_enabled,
                get_wf_tcp_443_enabled, set_wf_tcp_443_enabled,
                get_wf_tcp_all_ports_enabled, set_wf_tcp_all_ports_enabled,
                get_wf_udp_443_enabled, set_wf_udp_443_enabled,
                get_wf_udp_all_ports_enabled, set_wf_udp_all_ports_enabled,
                get_wf_raw_quic_initial_enabled, set_wf_raw_quic_initial_enabled,
                get_wf_raw_discord_media_enabled, set_wf_raw_discord_media_enabled,
                get_wf_raw_stun_enabled, set_wf_raw_stun_enabled,
                get_wf_raw_wireguard_enabled, set_wf_raw_wireguard_enabled,
                get_wssize_enabled, set_wssize_enabled,
                get_allzone_hostlist_enabled, set_allzone_hostlist_enabled,
                get_remove_hostlists_enabled, set_remove_hostlists_enabled,
                get_remove_ipsets_enabled, set_remove_ipsets_enabled
            )
            
            # TCP
            self.tcp_80_toggle.setChecked(get_wf_tcp_80_enabled())
            self.tcp_443_toggle.setChecked(get_wf_tcp_443_enabled())
            self.tcp_all_ports_toggle.setChecked(get_wf_tcp_all_ports_enabled())
            
            # UDP
            self.udp_443_toggle.setChecked(get_wf_udp_443_enabled())
            self.udp_all_ports_toggle.setChecked(get_wf_udp_all_ports_enabled())
            
            # Raw-part
            self.raw_quic_toggle.setChecked(get_wf_raw_quic_initial_enabled())
            self.raw_discord_toggle.setChecked(get_wf_raw_discord_media_enabled())
            self.raw_stun_toggle.setChecked(get_wf_raw_stun_enabled())
            self.raw_wireguard_toggle.setChecked(get_wf_raw_wireguard_enabled())
            
            # Дополнительные настройки
            self.wssize_toggle.setChecked(get_wssize_enabled())
            self.allzone_toggle.setChecked(get_allzone_hostlist_enabled())
            self.remove_hostlists_toggle.setChecked(get_remove_hostlists_enabled())
            self.remove_ipsets_toggle.setChecked(get_remove_ipsets_enabled())
            
            # Подключаем сигналы сохранения
            self.tcp_80_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_80_enabled, v))
            self.tcp_443_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_443_enabled, v))
            self.tcp_all_ports_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_tcp_all_ports_enabled, v))
            
            self.udp_443_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_udp_443_enabled, v))
            self.udp_all_ports_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_udp_all_ports_enabled, v))
            
            self.raw_quic_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_quic_initial_enabled, v))
            self.raw_discord_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_discord_media_enabled, v))
            self.raw_stun_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_stun_enabled, v))
            self.raw_wireguard_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wf_raw_wireguard_enabled, v))
            
            # Дополнительные настройки - сигналы
            self.wssize_toggle.toggled.connect(lambda v: self._on_filter_changed(set_wssize_enabled, v))
            self.allzone_toggle.toggled.connect(lambda v: self._on_filter_changed(set_allzone_hostlist_enabled, v))
            self.remove_hostlists_toggle.toggled.connect(lambda v: self._on_filter_changed(set_remove_hostlists_enabled, v))
            self.remove_ipsets_toggle.toggled.connect(lambda v: self._on_filter_changed(set_remove_ipsets_enabled, v))
            
        except Exception as e:
            log(f"Ошибка загрузки фильтров: {e}", "WARNING")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            
    def _on_method_changed(self, index):
        """Обработчик смены метода"""
        method = self.method_combo.itemData(index)
        if method:
            try:
                from strategy_menu import set_strategy_launch_method
                set_strategy_launch_method(method)
                self._update_filters_visibility()
                self.launch_method_changed.emit(method)
            except Exception as e:
                log(f"Ошибка смены метода: {e}", "ERROR")
                
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
        except:
            pass
