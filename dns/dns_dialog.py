# dns/dns_dialog.py
"""
Компактный диалог настройки DNS с вкладками (полностью переработанный)
"""
import os
import subprocess
import threading
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QMessageBox, QGroupBox, QApplication,
    QCheckBox, QProgressBar, QScrollArea, QRadioButton, QButtonGroup,
    QFrame, QSizePolicy, QGridLayout, QTabWidget, QTextBrowser, QStyle
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette, QColor
from log import log
from .dns_force import DNSForceManager
from .dns_core import DNSManager, _normalize_alias, refresh_exclusion_cache
from typing import List, Tuple, Dict, Optional
from utils import run_hidden

# ══════════════════════════════════════════════════════════════════════
#  DNS провайдеры
# ══════════════════════════════════════════════════════════════════════

DNS_PROVIDERS = {
    "Популярные": {
        "Cloudflare": {
            "ipv4": ["1.1.1.1", "1.0.0.1"],
            "ipv6": ["2606:4700:4700::1111", "2606:4700:4700::1001"],
            "desc": "Быстрый и приватный"
        },
        "Google DNS": {
            "ipv4": ["8.8.8.8", "8.8.4.4"],
            "ipv6": ["2001:4860:4860::8888", "2001:4860:4860::8844"],
            "desc": "Надежный от Google"
        },
        "Dns.SB": {
            "ipv4": ["185.222.222.222", "45.11.45.11"],
            "ipv6": ["2a09::", "2a11::"],
            "desc": "Без цензуры"
        },
    },
    "Безопасные": {
        "Quad9": {
            "ipv4": ["9.9.9.9", "149.112.112.112"],
            "ipv6": ["2620:fe::fe", "2620:fe::9"],
            "desc": "Блокировка вредоносных"
        },
        "AdGuard": {
            "ipv4": ["94.140.14.14", "94.140.15.15"],
            "ipv6": ["2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"],
            "desc": "Блокировка рекламы"
        },
        "OpenDNS": {
            "ipv4": ["208.67.222.222", "208.67.220.220"],
            "ipv6": ["2620:119:35::35", "2620:119:53::53"],
            "desc": "Родительский контроль"
        },
        "dnsdoh.art": {
            "ipv4": ["194.180.189.33", "194.180.189.33"],
            "ipv6": [],
            "desc": "Максимальная приватность"
        }
    },
    "Для доступа к ИИ": {
        "Xbox DNS": {
            "ipv4": ["176.99.11.77", "80.78.247.254"],
            "ipv6": [],
            "desc": "Для ChatGPT, Gemini и т.д."
        },
        "Comss DNS": {
            "ipv4": ["83.220.169.155", "212.109.195.93"],
            "ipv6": [],
            "desc": "Для ChatGPT, Gemini и т.д."
        },
        "dns.malw.link": {
            "ipv4": ["84.21.189.133", "64.188.98.242"],
            "ipv6": ["2a12:bec4:1460:d5::2", "2a01:ecc0:2c1:2::2"],
            "desc": "Для ChatGPT, Gemini и т.д."
        },
    }
}

# ══════════════════════════════════════════════════════════════════════
#  Генератор стилей
# ══════════════════════════════════════════════════════════════════════
def radio_slot_width(rb: QRadioButton) -> int:
    s = rb.style()
    ind = s.pixelMetric(QStyle.PixelMetric.PM_ExclusiveIndicatorWidth, None, rb)
    gap = s.pixelMetric(QStyle.PixelMetric.PM_CheckBoxLabelSpacing, None, rb)
    return ind + gap + 2  # +2 маленький запас

class CompactStyleGenerator:
    """Генератор компактных стилей"""
    
    def __init__(self, theme_name: str = "Темная синяя"):
        self.theme_name = theme_name
        self.is_dark = ("Темная" in theme_name or "AMOLED" in theme_name or 
                       "Полностью черная" in theme_name or "РКН Тян" in theme_name)
        self.is_amoled = "AMOLED" in theme_name
        self.is_pure_black = "Полностью черная" in theme_name
        self._setup_colors()
    
    def _setup_colors(self):
        """Настраивает цвета"""
        if self.is_pure_black:
            self.bg_primary = "#000000"
            self.bg_secondary = "#0a0a0a"
            self.bg_card = "#1a1a1a"
            self.bg_hover = "#2a2a2a"
            self.text_primary = "#ffffff"
            self.text_secondary = "#999999"
            self.border = "#333333"
            self.accent = "#404040"
            self.current_bg = "#0a2a0a"
            self.current_border = "#2a6a2a"
        elif self.is_amoled:
            self.bg_primary = "#000000"
            self.bg_secondary = "#000000"
            self.bg_card = "#0a0a0a"
            self.bg_hover = "#1a1a1a"
            self.text_primary = "#ffffff"
            self.text_secondary = "#888888"
            self.border = "#1a1a1a"
            self.accent = "#1a1a1a"
            self.current_bg = "#001a00"
            self.current_border = "#00ff00"
        elif self.is_dark:
            self.bg_primary = "#1e1e1e"
            self.bg_secondary = "#252525"
            self.bg_card = "#2d2d2d"
            self.bg_hover = "#3a3a3a"
            self.text_primary = "#ffffff"
            self.text_secondary = "#999999"
            self.border = "#404040"
            self.accent = "#2196F3"
            self.current_bg = "#1b3e20"
            self.current_border = "#4caf50"
        else:
            self.bg_primary = "#ffffff"
            self.bg_secondary = "#f5f5f5"
            self.bg_card = "#fafafa"
            self.bg_hover = "#eeeeee"
            self.text_primary = "#212121"
            self.text_secondary = "#666666"
            self.border = "#dddddd"
            self.accent = "#2196f3"
            self.current_bg = "#e8f5e9"
            self.current_border = "#4caf50"

# ══════════════════════════════════════════════════════════════════════
#  Компактная карточка DNS
# ══════════════════════════════════════════════════════════════════════

class CompactDNSCard(QFrame):
    """Компактная карточка DNS провайдера без рамок"""
    
    def __init__(self, name: str, data: dict, is_current: bool = False, 
                 style_gen: CompactStyleGenerator = None):
        super().__init__()
        self.name = name
        self.data = data
        self.is_current = is_current
        self.style_gen = style_gen or CompactStyleGenerator()
        self.setup_ui()
    
    def setup_ui(self):
        """Интерфейс карточки"""
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Радиокнопка
        self.radio = QRadioButton(self.name)
        self.radio.setMinimumWidth(120)   # чтобы колонка названий осталась такой же
        layout.addWidget(self.radio)
        
        # Название (без ограничения ширины)
        name_label = QLabel(self.name)
        name_label.setMinimumWidth(120)
        layout.addWidget(name_label)
        
        # DNS адрес
        dns_label = QLabel(f"{self.data['ipv4'][0]}")
        dns_label.setMinimumWidth(120)
        layout.addWidget(dns_label)
        
        # Описание
        desc_label = QLabel(self.data.get("desc", ""))
        layout.addWidget(desc_label, 1)
        
        # Метка текущий
        if self.is_current:
            current_label = QLabel("✓ Текущий")
            current_label.setStyleSheet(f"""
                color: {self.style_gen.current_border};
                font-weight: bold;
            """)
            layout.addWidget(current_label)
        
        self.setLayout(layout)
        self.mousePressEvent = lambda e: self.radio.setChecked(True)

# ══════════════════════════════════════════════════════════════════════
#  Карточка адаптера
# ══════════════════════════════════════════════════════════════════════

class AdapterCard(QFrame):
    """Карточка сетевого адаптера"""
    
    def __init__(self, name: str, desc: str, dns_info: dict, doh_info: dict = None,
                 style_gen: CompactStyleGenerator = None):
        super().__init__()
        self.adapter_name = name
        self.adapter_desc = desc
        self.dns_info = dns_info
        self.doh_info = doh_info or {'supported': False, 'enabled': False}
        self.style_gen = style_gen or CompactStyleGenerator()
        self.setup_ui()
    
    def setup_ui(self):
        """Интерфейс карточки адаптера"""
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Чекбокс
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setFixedWidth(20)
        layout.addWidget(self.checkbox)
        
        # Информация об адаптере
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        # Название адаптера
        name_label = QLabel(self.adapter_name)
        name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # Текущий DNS (первичный и вторичный)
        current_dns = self.dns_info.get("ipv4", [])
        
        if current_dns:
            # Первичный DNS
            primary_dns = current_dns[0]
            primary_label = QLabel(f"🔵 Первичный: {primary_dns}")
            info_layout.addWidget(primary_label)
            
            # Вторичный DNS (если есть)
            if len(current_dns) > 1:
                secondary_dns = current_dns[1]
                secondary_label = QLabel(f"🟢 Вторичный: {secondary_dns}")
                info_layout.addWidget(secondary_label)
            else:
                no_secondary_label = QLabel("🟢 Вторичный: не настроен")
                no_secondary_label.setStyleSheet(f"color: {self.style_gen.text_secondary};")
                info_layout.addWidget(no_secondary_label)
        else:
            # DHCP (автоматически)
            dhcp_label = QLabel("🔄 DHCP (Автоматически)")
            dhcp_label.setStyleSheet(f"color: {self.style_gen.text_secondary};")
            info_layout.addWidget(dhcp_label)
        
        # DoH статус
        doh_label = self._create_doh_label()
        info_layout.addWidget(doh_label)
        
        layout.addLayout(info_layout, 1)
        
        self.setLayout(layout)
    
    def _create_doh_label(self) -> QLabel:
        """Создает метку с информацией о DoH"""
        if not self.doh_info.get('supported', False):
            label = QLabel("🔒 DoH: не поддерживается системой")
            label.setStyleSheet(f"color: {self.style_gen.text_secondary}; font-size: 9pt;")
            return label
        
        if self.doh_info.get('enabled', False):
            template = self.doh_info.get('template', 'unknown')
            # Сокращаем URL для отображения
            short_template = template.replace('https://', '').replace('/dns-query', '')
            label = QLabel(f"🔒 DoH: ✅ Включен ({short_template})")
            label.setStyleSheet(f"color: #4caf50; font-size: 9pt; font-weight: bold;")
        else:
            label = QLabel("🔒 DoH: ❌ Выключен")
            label.setStyleSheet(f"color: {self.style_gen.text_secondary}; font-size: 9pt;")
        
        return label

# ══════════════════════════════════════════════════════════════════════
#  Главный диалог DNS
# ══════════════════════════════════════════════════════════════════════

class DNSSettingsDialog(QDialog):
    """Диалог настройки DNS с вкладками"""
    
    adapters_loaded = pyqtSignal(list)
    dns_info_loaded = pyqtSignal(dict)
    
    _instance = None
    _is_initialized = False
    
    @classmethod
    def get_instance(cls, parent=None, theme_name: str = "Темная синяя"):
        """Singleton"""
        if cls._instance is None:
            log("Создание нового экземпляра DNSSettingsDialog", "DEBUG")
            cls._instance = cls(parent, theme_name)
        else:
            log("Переиспользование DNSSettingsDialog", "DEBUG")
        return cls._instance
    
    def __init__(self, parent=None, theme_name: str = "Темная синяя"):
        if self._is_initialized:
            return
        
        super().__init__(parent)
        
        try:
            self.force_dns_active = DNSForceManager().is_force_dns_enabled()
        except:
            self.force_dns_active = False
        
        self.setWindowTitle("Настройки DNS")
        self.setMinimumSize(710, 600)
        self.setModal(False)
        
        self.style_gen = CompactStyleGenerator(theme_name)
        
        self.dns_manager = DNSManager()
        self.ipv6_available = self.check_ipv6_connectivity()
        
        self.init_loading_ui()
        
        self.load_data_thread = threading.Thread(target=self.load_data_in_background, daemon=True)
        self.load_data_thread.start()
        
        self._is_initialized = True
        log("DNSSettingsDialog инициализирован", "DEBUG")
    
    @staticmethod
    def check_ipv6_connectivity():
        """Проверка IPv6"""
        try:
            result = run_hidden(
                ['ping', '-6', '-n', '1', '-w', '1000', '2001:4860:4860::8888'],
                capture_output=True, text=True, timeout=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except:
            return False
    
    def init_loading_ui(self):
        """Экран загрузки"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_label = QLabel("⏳ Загрузка информации о сети...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet(f"font-size: 10pt; color: {self.style_gen.text_primary};")
        layout.addWidget(loading_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        self.adapters_loaded.connect(self.on_adapters_loaded)
        self.dns_info_loaded.connect(self.on_dns_info_loaded)
    
    def load_data_in_background(self):
        """Загрузка данных"""
        try:
            refresh_exclusion_cache()
            
            all_adapters = self.dns_manager.get_network_adapters_fast(
                include_ignored=True,
                include_disconnected=True
            )
            
            filtered_adapters = [
                (name, desc) for name, desc in all_adapters
                if not self.dns_manager.should_ignore_adapter(name, desc)
            ]
            
            self.all_adapters = all_adapters
            self.adapters = filtered_adapters
            self.adapters_loaded.emit(filtered_adapters)
            
            adapter_names = [name for name, _ in all_adapters]
            dns_info = self.dns_manager.get_all_dns_info_fast(adapter_names)
            
            self.dns_info_loaded.emit(dns_info)
            
        except Exception as e:
            log(f"Ошибка загрузки: {e}", "ERROR")
    
    def on_adapters_loaded(self, adapters):
        self.adapters = adapters
        if hasattr(self, 'dns_info'):
            self.init_full_ui()
    
    def on_dns_info_loaded(self, dns_info):
        self.dns_info = dns_info
        if hasattr(self, 'adapters'):
            self.init_full_ui()
    
    def init_full_ui(self):
        """Полный интерфейс"""
        QWidget().setLayout(self.layout())
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Предупреждение
        if self.force_dns_active:
            warn = QLabel("⚠️ Принудительный DNS включён - сначала отключите его")
            warn.setWordWrap(True)
            main_layout.addWidget(warn)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        
        self.dns_tab = QWidget()
        self._init_dns_tab()
        self.tab_widget.addTab(self.dns_tab, "🌐 DNS Серверы")
        
        self.settings_tab = QWidget()
        self._init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Сетевые адаптеры")
        
        self.info_tab = QWidget()
        self._init_info_tab()
        self.tab_widget.addTab(self.info_tab, "ℹ️ Информация")
        
        main_layout.addWidget(self.tab_widget, 1)
        
        # Кнопки
        self._create_control_buttons()
        main_layout.addWidget(self.buttons_widget)
        
        self.setLayout(main_layout)
        
        if self.force_dns_active:
            self.dns_tab.setEnabled(False)
            self.apply_button.setEnabled(False)
    
    def _init_dns_tab(self):
        """Вкладка DNS серверов"""
        layout = QVBoxLayout(self.dns_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # DNS провайдеры
        dns_label = QLabel("Выберите DNS провайдера:")
        layout.addWidget(dns_label)
        
        # Скролл
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(6)              # расстояние между карточками
        scroll_layout.setContentsMargins(8, 8, 8, 8)  # отступы от края «серой области»
        
        self.dns_button_group = QButtonGroup()
        
        # Авто
        auto_card = QFrame()
        auto_card.setFixedHeight(40)
        auto_card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        auto_layout = QHBoxLayout()
        auto_layout.setContentsMargins(10, 5, 10, 5)
        auto_layout.setSpacing(15)
        
        self.auto_dns_radio = QRadioButton()
        self.auto_dns_radio.setFixedWidth(radio_slot_width(self.auto_dns_radio))
        auto_layout.addWidget(self.auto_dns_radio)
        
        auto_label = QLabel("Автоматически (DHCP)")
        auto_layout.addWidget(auto_label)
        auto_layout.addStretch()
        
        auto_card.setLayout(auto_layout)
        auto_card.mousePressEvent = lambda e: self.auto_dns_radio.setChecked(True)
        scroll_layout.addWidget(auto_card)
        
        self.dns_button_group.addButton(self.auto_dns_radio)
        
        # Провайдеры
        current_dns_v4, _ = self.get_current_dns_for_comparison()
        self.dns_cards = {}
        
        for category, providers in DNS_PROVIDERS.items():
            # Разделитель категории
            cat_separator = QFrame()
            cat_separator.setFixedHeight(25)
            cat_layout = QHBoxLayout()
            cat_layout.setContentsMargins(10, 0, 10, 0)
            
            cat_label = QLabel(category)
            cat_layout.addWidget(cat_label)
            cat_separator.setLayout(cat_layout)
            
            scroll_layout.addWidget(cat_separator)
            
            for provider_name, provider_data in providers.items():
                is_current = self.is_current_dns(provider_data['ipv4'], current_dns_v4)
                
                card = CompactDNSCard(provider_name, provider_data, is_current, self.style_gen)
                
                self.dns_button_group.addButton(card.radio)
                self.dns_cards[provider_name] = card
                
                if is_current:
                    card.radio.setChecked(True)
                
                scroll_layout.addWidget(card)
        
        # Пользовательский
        custom_separator = QFrame()
        custom_separator.setFixedHeight(25)
        custom_sep_layout = QHBoxLayout()
        custom_sep_layout.setContentsMargins(10, 0, 10, 0)
        
        custom_cat_label = QLabel("Пользовательский")
        custom_sep_layout.addWidget(custom_cat_label)
        custom_separator.setLayout(custom_sep_layout)
        
        scroll_layout.addWidget(custom_separator)
        
        custom_frame = QFrame()
        custom_frame.setFixedHeight(75)
        custom_layout = QVBoxLayout()
        custom_layout.setContentsMargins(10, 8, 10, 8)
        custom_layout.setSpacing(5)
        
        custom_radio_layout = QHBoxLayout()
        custom_radio_layout.setSpacing(15)
        
        self.custom_dns_radio = QRadioButton()
        self.custom_dns_radio.setFixedWidth(20)
        self.custom_dns_radio.setFixedWidth(radio_slot_width(self.custom_dns_radio))
        
        custom_label = QLabel("Свои DNS адреса")
        custom_radio_layout.addWidget(custom_label)
        custom_radio_layout.addStretch()
        
        custom_layout.addLayout(custom_radio_layout)
        
        self.dns_button_group.addButton(self.custom_dns_radio)
        
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(5)
        
        self.custom_ipv4_primary = QLineEdit()
        self.custom_ipv4_primary.setPlaceholderText("Основной: 8.8.8.8")
        inputs_layout.addWidget(self.custom_ipv4_primary)
        
        self.custom_ipv4_secondary = QLineEdit()
        self.custom_ipv4_secondary.setPlaceholderText("Дополнительный: 8.8.4.4")
        inputs_layout.addWidget(self.custom_ipv4_secondary)
        
        custom_layout.addLayout(inputs_layout)
        custom_frame.setLayout(custom_layout)
        scroll_layout.addWidget(custom_frame)
        
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        
        layout.addWidget(scroll, 1)
        
        # Инфо
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        self.update_info()

    def toggle_force_dns(self, state):
        """Включает/выключает принудительный DNS"""
        from PyQt6.QtCore import Qt
        enabled = (state == Qt.CheckState.Checked.value)
        
        try:
            from dns.dns_force import DNSForceManager
            manager = DNSForceManager(status_callback=self._update_status_if_exists)
            
            if enabled:
                # Подтверждение включения
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Принудительный DNS")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText(
                    "Включить принудительную установку DNS?\n\n"
                    "Это действие изменит DNS-серверы на всех активных "
                    "сетевых адаптерах (Ethernet и Wi-Fi)."
                )
                msg_box.setInformativeText(
                    f"DNS-серверы:\n"
                    f"• IPv4: {manager.DNS_PRIMARY}, {manager.DNS_SECONDARY}\n"
                    f"• IPv6: {manager.DNS_PRIMARY_V6}, {manager.DNS_SECONDARY_V6}\n\n"
                    "Обеспечивают:\n"
                    "• Защиту от вредоносных сайтов\n"
                    "• Конфиденциальность запросов\n"
                    "• Обход некоторых блокировок\n\n"
                    "Текущие настройки DNS будут сохранены для восстановления."
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._revert_checkbox(False)
                    return
                
                # Включаем через менеджер
                success, count_ok, count_total, message = manager.enable_force_dns(
                    include_disconnected=True
                )
                
                if success:
                    QMessageBox.information(self, "DNS установлен", message)
                    self.force_dns_active = True
                    self._toggle_dns_tab(False)  # Блокируем вкладку DNS
                    self._update_force_dns_warning()
                else:
                    QMessageBox.warning(self, "Ошибка", message)
                    self._revert_checkbox(False)
                    
            else:
                # Отключение принудительного DNS
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Отключение принудительного DNS")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText("Как отключить принудительный DNS?")
                
                restore_btn = msg_box.addButton(
                    "Восстановить из резервной копии", 
                    QMessageBox.ButtonRole.AcceptRole
                )
                auto_btn = msg_box.addButton(
                    "Переключить на автоматический", 
                    QMessageBox.ButtonRole.AcceptRole
                )
                cancel_btn = msg_box.addButton(
                    "Отмена", 
                    QMessageBox.ButtonRole.RejectRole
                )
                
                msg_box.setDefaultButton(restore_btn)
                msg_box.exec()
                
                clicked_btn = msg_box.clickedButton()
                
                if clicked_btn == cancel_btn:
                    self._revert_checkbox(True)
                    return
                
                # Отключаем через менеджер
                restore_from_backup = (clicked_btn == restore_btn)
                success, message = manager.disable_force_dns(restore_from_backup)
                
                if success:
                    QMessageBox.information(self, "DNS восстановлен", message)
                else:
                    QMessageBox.warning(self, "Ошибка", message)
                
                self.force_dns_active = False
                self._toggle_dns_tab(True)  # Разблокируем вкладку DNS
                self._update_force_dns_warning()
                
        except Exception as e:
            log(f"Ошибка при переключении Force DNS: {e}", "ERROR")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Произошла ошибка при изменении настроек DNS:\n{e}"
            )
            self._revert_checkbox(not enabled)

    def _revert_checkbox(self, checked: bool):
        """Откатывает состояние чекбокса"""
        self.force_dns_checkbox.blockSignals(True)
        self.force_dns_checkbox.setChecked(checked)
        self.force_dns_checkbox.blockSignals(False)

    def _toggle_dns_tab(self, enabled: bool):
        """Включает/выключает вкладку DNS серверов"""
        if hasattr(self, 'dns_tab'):
            self.dns_tab.setEnabled(enabled)
        if hasattr(self, 'apply_button'):
            self.apply_button.setEnabled(enabled)

    def _update_status_if_exists(self, text: str):
        """Вспомогательный метод для обновления статуса (если родитель поддерживает)"""
        if hasattr(self.parent(), 'set_status'):
            self.parent().set_status(text)

    def _update_force_dns_warning(self):
        """Обновляет предупреждение о принудительном DNS"""
        if hasattr(self, 'force_dns_warning'):
            if self.force_dns_active:
                self.force_dns_warning.show()
            else:
                self.force_dns_warning.hide()

    def _init_settings_tab(self):
        """Вкладка настроек - список адаптеров"""
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # === ПРИНУДИТЕЛЬНЫЙ DNS ===
        force_dns_frame = QFrame()
        force_dns_frame.setFrameShape(QFrame.Shape.Box)
        force_dns_layout = QVBoxLayout()
        force_dns_layout.setContentsMargins(10, 10, 10, 10)
        force_dns_layout.setSpacing(8)
        
        # Чекбокс
        self.force_dns_checkbox = QCheckBox("🔒 Принудительный DNS (DNS.SB + OpenDNS)")
        self.force_dns_checkbox.setChecked(self.force_dns_active)
        self.force_dns_checkbox.stateChanged.connect(self.toggle_force_dns)
        force_dns_layout.addWidget(self.force_dns_checkbox)
        
        # Описание
        from dns.dns_force import DNSForceManager
        temp_manager = DNSForceManager()
        force_dns_info = QLabel(
            f"Автоматически устанавливает защищённые DNS-серверы на все активные адаптеры:\n"
            f"• IPv4: {temp_manager.DNS_PRIMARY} (Dns.SB), {temp_manager.DNS_SECONDARY} (OpenDNS)\n"
            f"• IPv6: {temp_manager.DNS_PRIMARY_V6} (Dns.SB), {temp_manager.DNS_SECONDARY_V6} (OpenDNS)\n\n"
            f"Преимущества:\n"
            f"• Защита от вредоносных сайтов\n"
            f"• Конфиденциальность запросов\n"
            f"• Обход некоторых блокировок"
        )
        force_dns_info.setWordWrap(True)
        force_dns_info.setStyleSheet(f"color: {self.style_gen.text_secondary}; font-size: 9pt;")
        force_dns_layout.addWidget(force_dns_info)
        
        force_dns_frame.setLayout(force_dns_layout)
        layout.addWidget(force_dns_frame)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # === DoH ИНФОРМАЦИЯ ===
        from dns.dns_core import is_doh_supported
        
        if is_doh_supported():
            doh_info_frame = QFrame()
            doh_info_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.style_gen.bg_card};
                    border: 1px solid {self.style_gen.border};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            doh_info_layout = QHBoxLayout()
            
            doh_icon = QLabel("🔒")
            doh_icon.setStyleSheet("font-size: 20pt;")
            doh_info_layout.addWidget(doh_icon)
            
            doh_text = QLabel(
                "DNS over HTTPS (DoH) поддерживается\n"
                "DoH будет автоматически включен для поддерживаемых DNS-серверов"
            )
            doh_text.setWordWrap(True)
            doh_text.setStyleSheet(f"color: {self.style_gen.text_secondary}; font-size: 9pt;")
            doh_info_layout.addWidget(doh_text, 1)
            
            doh_info_frame.setLayout(doh_info_layout)
            layout.addWidget(doh_info_frame)
        else:
            # Показываем предупреждение только если это Windows 10
            import platform
            win_ver = platform.version()
            if "10." in win_ver:
                doh_warning = QLabel(
                    "⚠️ DNS over HTTPS (DoH) не поддерживается вашей версией Windows.\n"
                    "Требуется Windows 11 или Windows 10 build 19628+"
                )
                doh_warning.setWordWrap(True)
                doh_warning.setStyleSheet(f"""
                    color: #ff9800;
                    background-color: {self.style_gen.bg_hover};
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 9pt;
                """)
                layout.addWidget(doh_warning)
        
        # Разделитель
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)
        
        # Заголовок
        title_label = QLabel("Выберите сетевые адаптеры для изменения DNS")
        layout.addWidget(title_label)
        
        # Кнопки управления
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.select_all_btn = QPushButton("✓ Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all_adapters)
        controls_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("✗ Снять все")
        self.deselect_all_btn.clicked.connect(self.deselect_all_adapters)
        controls_layout.addWidget(self.deselect_all_btn)
        
        controls_layout.addStretch()
        
        # Счетчик выбранных
        self.selected_count_label = QLabel()
        controls_layout.addWidget(self.selected_count_label)
        
        layout.addLayout(controls_layout)
        
        # Скролл со списком адаптеров
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(6)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        
        # Создаем карточки адаптеров с DoH информацией
        self.adapter_cards = []
        
        for name, desc in self.adapters:
            clean = _normalize_alias(name)
            dns_data = self.dns_info.get(clean, {"ipv4": []})
            
            # Получаем DoH информацию
            doh_data = self.dns_manager.get_doh_info(name)
            
            card = AdapterCard(name, desc, dns_data, doh_data, self.style_gen)
            card.checkbox.stateChanged.connect(self.update_selected_count)
            
            self.adapter_cards.append(card)
            scroll_layout.addWidget(card)
        
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        
        layout.addWidget(scroll, 1)
        
        # IPv6 информация
        ipv6_info = QLabel(f"IPv6: {'✅ Доступен' if self.ipv6_available else '❌ Недоступен'} (будет применен автоматически)")
        ipv6_info.setWordWrap(True)
        layout.addWidget(ipv6_info)
        
        self.update_selected_count()

    def select_all_adapters(self):
        """Выбрать все адаптеры"""
        for card in self.adapter_cards:
            card.checkbox.setChecked(True)
    
    def deselect_all_adapters(self):
        """Снять выбор со всех адаптеров"""
        for card in self.adapter_cards:
            card.checkbox.setChecked(False)
    
    def update_selected_count(self):
        """Обновляет счетчик выбранных адаптеров"""
        count = sum(1 for card in self.adapter_cards if card.checkbox.isChecked())
        total = len(self.adapter_cards)
        
        self.selected_count_label.setText(f"Выбрано: {count} из {total}")
        
        # Обновляем инфо в DNS вкладке
        self.update_info()
    
    def _init_info_tab(self):
        """Вкладка информации"""
        layout = QVBoxLayout(self.info_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        info_browser = QTextBrowser()
        
        info_html = f"""
        <h3 style='color: {self.style_gen.accent};'>Текущие настройки DNS</h3>
        <p><b>Активных адаптеров:</b> {len(self.adapters)}</p>
        """
        
        for name, desc in self.adapters[:5]:
            clean = _normalize_alias(name)
            dns_data = self.dns_info.get(clean, {"ipv4": []})
            
            if dns_data["ipv4"]:
                primary = dns_data["ipv4"][0]
                secondary = dns_data["ipv4"][1] if len(dns_data["ipv4"]) > 1 else "не настроен"
                info_html += f"<p><b>{name}:</b><br>🔵 Первичный: {primary}<br>🟢 Вторичный: {secondary}</p>"
            else:
                info_html += f"<p><b>{name}:</b><br>🔄 DHCP (Автоматически)</p>"
        
        if len(self.adapters) > 5:
            info_html += f"<p><i>... и еще {len(self.adapters) - 5} адаптеров</i></p>"
        
        info_html += f"""
        <h3 style='color: {self.style_gen.accent}; margin-top: 20px;'>О DNS</h3>
        <p>DNS (Domain Name System) преобразует доменные имена в IP-адреса.</p>
        <p><b>Преимущества смены DNS:</b></p>
        <ul>
        <li>Повышение скорости загрузки</li>
        <li>Обход блокировок</li>
        <li>Дополнительная безопасность</li>
        </ul>
        """
        
        info_browser.setHtml(info_html)
        layout.addWidget(info_browser)
    
    def _create_control_buttons(self):
        """Кнопки управления"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.apply_button = QPushButton("✅ Применить")
        self.apply_button.setMinimumHeight(32)
        self.apply_button.clicked.connect(self.apply_dns_settings)
        buttons_layout.addWidget(self.apply_button)
        
        cancel_button = QPushButton("❌ Отмена")
        cancel_button.setMinimumHeight(32)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(buttons_layout)
    
    def get_current_dns_for_comparison(self) -> Tuple[List[str], List[str]]:
        """Получает текущий DNS для первого выбранного адаптера"""
        if hasattr(self, 'adapter_cards'):
            for card in self.adapter_cards:
                if card.checkbox.isChecked():
                    clean = _normalize_alias(card.adapter_name)
                    dns_data = self.dns_info.get(clean, {"ipv4": [], "ipv6": []})
                    return dns_data.get("ipv4", []), dns_data.get("ipv6", [])
        
        # Fallback на первый адаптер
        if self.adapters:
            name = self.adapters[0][0]
            clean = _normalize_alias(name)
            dns_data = self.dns_info.get(clean, {"ipv4": [], "ipv6": []})
            return dns_data.get("ipv4", []), dns_data.get("ipv6", [])
        
        return [], []
    
    def is_current_dns(self, provider_ipv4, current_ipv4) -> bool:
        return (len(provider_ipv4) > 0 and len(current_ipv4) > 0 and provider_ipv4[0] == current_ipv4[0])
    
    def update_info(self):
        """Обновляет информационную строку в DNS вкладке"""
        if not hasattr(self, 'adapter_cards'):
            self.info_label.setText("Перейдите на вкладку 'Сетевые адаптеры' для выбора")
            return
        
        count = sum(1 for card in self.adapter_cards if card.checkbox.isChecked())
        
        if count == 0:
            self.info_label.setText("⚠️ Выберите хотя бы один адаптер на вкладке 'Сетевые адаптеры'")
        else:
            self.info_label.setText(f"📡 DNS будет применен к {count} адаптерам")
    
    def apply_dns_settings(self):
        """Применяет настройки DNS"""
        if self.force_dns_active:
            QMessageBox.warning(self, "Ошибка", "Отключите принудительный DNS перед изменением.")
            return
        
        # Получаем выбранные адаптеры
        selected_adapters = [
            card.adapter_name for card in self.adapter_cards 
            if card.checkbox.isChecked()
        ]
        
        if not selected_adapters:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один адаптер на вкладке 'Сетевые адаптеры'.")
            return
        
        if self.auto_dns_radio.isChecked():
            self.apply_auto_dns(selected_adapters)
        elif self.custom_dns_radio.isChecked():
            self.apply_custom_dns(selected_adapters)
        else:
            self.apply_provider_dns(selected_adapters)
    
    def apply_auto_dns(self, adapters):
        success = 0
        for adapter in adapters:
            ok_v4, _ = self.dns_manager.set_auto_dns(adapter, "IPv4")
            ok_v6, _ = self.dns_manager.set_auto_dns(adapter, "IPv6") if self.ipv6_available else (True, "")
            if ok_v4 and ok_v6:
                success += 1
        self.show_result(success, len(adapters))
    
    def apply_provider_dns(self, adapters):
        """Применяет DNS от провайдера с автоматическим включением DoH"""
        selected = None
        for name, card in self.dns_cards.items():
            if card.radio.isChecked():
                selected = name
                break
        
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите DNS провайдера.")
            return
        
        provider_data = None
        for cat, providers in DNS_PROVIDERS.items():
            if selected in providers:
                provider_data = providers[selected]
                break
        
        if not provider_data:
            return
        
        from dns.dns_core import is_doh_supported, get_doh_template_for_dns
        doh_supported = is_doh_supported()
        
        success = 0
        doh_enabled = 0
        
        for adapter in adapters:
            ipv4 = provider_data['ipv4']
            primary_dns = ipv4[0]
            secondary_dns = ipv4[1] if len(ipv4) > 1 else None
            
            # Устанавливаем DNS
            ok, _ = self.dns_manager.set_custom_dns(
                adapter, primary_dns, secondary_dns, "IPv4"
            )
            
            if ok:
                success += 1
                
                # Пытаемся включить DoH если поддерживается
                if doh_supported and get_doh_template_for_dns(primary_dns):
                    doh_ok, _ = self.dns_manager.set_doh(adapter, primary_dns, True)
                    if doh_ok:
                        doh_enabled += 1
        
        # Показываем результат
        self.dns_manager.flush_dns_cache()
        
        if success == len(adapters):
            msg = f"DNS успешно применен ({success} адаптеров)"
            if doh_enabled > 0:
                msg += f"\n🔒 DoH включен на {doh_enabled} адаптерах"
            QMessageBox.information(self, "Успех", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", f"Применено: {success}/{len(adapters)}")

    def apply_custom_dns(self, adapters):
        """Применяет пользовательский DNS с DoH"""
        primary = self.custom_ipv4_primary.text().strip()
        secondary = self.custom_ipv4_secondary.text().strip() or None
        
        if not primary:
            QMessageBox.warning(self, "Ошибка", "Укажите основной DNS.")
            return
        
        from dns.dns_core import is_doh_supported, get_doh_template_for_dns
        doh_supported = is_doh_supported()
        has_doh_template = get_doh_template_for_dns(primary) is not None
        
        success = 0
        doh_enabled = 0
        
        for adapter in adapters:
            ok, _ = self.dns_manager.set_custom_dns(adapter, primary, secondary, "IPv4")
            if ok:
                success += 1
                
                # Включаем DoH если возможно
                if doh_supported and has_doh_template:
                    doh_ok, _ = self.dns_manager.set_doh(adapter, primary, True)
                    if doh_ok:
                        doh_enabled += 1
        
        # Показываем результат
        self.dns_manager.flush_dns_cache()
        
        if success == len(adapters):
            msg = f"DNS успешно применен ({success} адаптеров)"
            if doh_enabled > 0:
                msg += f"\n🔒 DoH включен на {doh_enabled} адаптерах"
            elif doh_supported and not has_doh_template:
                msg += "\n⚠️ DoH не доступен для указанного DNS"
            QMessageBox.information(self, "Успех", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", f"Применено: {success}/{len(adapters)}")
    
    def show_result(self, success, total):
        self.dns_manager.flush_dns_cache()
        
        if success == total:
            QMessageBox.information(self, "Успех", f"DNS успешно применен ({success} адаптеров)")
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", f"Применено: {success}/{total}")
    
    def reject(self):
        self.hide()
        log("Диалог DNS скрыт", "INFO")
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()