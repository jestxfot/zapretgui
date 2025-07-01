# dns.py

import os
import subprocess
import threading
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                            QPushButton, QRadioButton, QLineEdit, QMessageBox,
                            QGroupBox, QButtonGroup, QApplication, QCheckBox, QProgressBar, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from log import log
from functools import lru_cache
from dns_force import DNSForceManager
from typing import List, Tuple, Dict
import json

# Предопределенные DNS-серверы с поддержкой IPv6
PREDEFINED_DNS = {
    "Quad9": {
        "ipv4": ["9.9.9.9", "149.112.112.112"],
        "ipv6": ["2620:fe::fe", "2620:fe::9"]
    },
    "Quad9 ECS": {
        "ipv4": ["9.9.9.11", "149.112.112.11"],
        "ipv6": ["2620:fe::11", "2620:fe::fe:11"]
    },
    "Quad9 No Malware blocking": {
        "ipv4": ["9.9.9.10", "149.112.112.10"],
        "ipv6": ["2620:fe::10", "2620:fe::fe:10"]
    },
    "Xbox DNS": {
        "ipv4": ["176.99.11.77", "80.78.247.254"],
        "ipv6": []  # Xbox DNS не предоставляет IPv6
    },
    "Google": {
        "ipv4": ["8.8.8.8", "8.8.4.4"],
        "ipv6": ["2001:4860:4860::8888", "2001:4860:4860::8844"]
    },
    "Dns.SB": {
        "ipv4": ["185.222.222.222", "45.11.45.11"],
        "ipv6": ["2a09::", "2a11::"]
    },
    "OpenDNS": {
        "ipv4": ["208.67.222.222", "208.67.220.220"],
        "ipv6": ["2620:119:35::35", "2620:119:53::53"]
    },
    "AdGuard": {
        "ipv4": ["94.140.14.14", "94.140.15.15"],
        "ipv6": ["2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"]
    },
    "Cloudflare": {
        "ipv4": ["1.1.1.1", "1.0.0.1"],
        "ipv6": ["2606:4700:4700::1111", "2606:4700:4700::1001"]
    }
}

def _normalize_alias(alias: str) -> str:
    """
    Приводит InterfaceAlias к единому виду:
      • NBSP (U+00A0) → обычный пробел
      • убираем LRM/RLM, табы, крайние пробелы
    """
    if not isinstance(alias, str):
        return alias
    repl = (
        ('\u00A0', ' '),  # NBSP
        ('\u200E', ''),   # LRM
        ('\u200F', ''),   # RLM
        ('\t',     ' '),
    )
    for bad, good in repl:
        alias = alias.replace(bad, good)
    return alias.strip()

@lru_cache(maxsize=1)
def _get_dynamic_exclusions() -> list[str]:
    """
    Берёт список исключаемых адаптеров из DNSForceManager.
    Если не удаётся – возвращает пустой список.
    """
    try:
        mgr = DNSForceManager()
        return mgr.get_excluded_adapters()
    except Exception:
        return []

def refresh_exclusion_cache() -> None:
    """
    Сбрасывает lru-кэш списка исключаемых адаптеров.
    Вызывать после изменения реестра или DEFAULT_EXCLUSIONS.
    """
    _get_dynamic_exclusions.cache_clear()

class DNSManager:
    """Класс для управления DNS настройками в Windows с поддержкой IPv6"""
    
    def __init__(self):
        # Кэшируем WMI соединение
        try:
            import wmi
            self.wmi_conn = wmi.WMI()
        except Exception:
            self.wmi_conn = None
    
    @staticmethod
    def should_ignore_adapter(name: str, description: str) -> bool:
        name = _normalize_alias(name)
        description = _normalize_alias(description)
        for pattern in _get_dynamic_exclusions():
            if pattern in name.lower() or pattern in description.lower():
                return True
        return False

    @staticmethod
    def get_network_adapters_fast(
            include_ignored: bool = False,
            include_disconnected: bool = True
        ) -> List[Tuple[str, str]]:
        """Быстро получаем сетевые адаптеры через WMI"""
        try:
            import wmi
            c = wmi.WMI()

            adapters: list[tuple[str, str]] = []

            for a in c.Win32_NetworkAdapter(PhysicalAdapter=True):
                if not a.NetConnectionID or not a.Description:
                    continue

                if not include_disconnected:
                    if a.NetConnectionStatus != 2:
                        continue

                name_raw  = a.NetConnectionID
                name_norm = _normalize_alias(name_raw)
                desc = a.Description

                if include_ignored or not DNSManager.should_ignore_adapter(name_norm, desc):
                    adapters.append((name_raw, desc))

            return adapters

        except ImportError:
            return DNSManager.get_network_adapters_powershell_fallback(
                include_ignored=include_ignored,
                include_disconnected=include_disconnected
            )
        except Exception as e:
            log(f"WMI-ошибка, fallback: {e}", "DEBUG")
            return DNSManager.get_network_adapters_powershell_fallback(
                include_ignored=include_ignored,
                include_disconnected=include_disconnected
            )
    
    @staticmethod
    def get_network_adapters_powershell_fallback(
            include_ignored: bool = False,
            include_disconnected: bool = True
        ):
        """Fallback через PowerShell."""
        try:
            status_filter = '' if include_disconnected else ' | Where-Object {$_.Status -eq "Up"}'

            command = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                f'Get-NetAdapter{status_filter} | '
                'Select-Object Name,InterfaceDescription | ConvertTo-Json'
            ]
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                log(f"PowerShell ошибка: {result.stderr}", "❌ ERROR")
                return []
            
            adapters = []
            adapter_list = json.loads(result.stdout)
            if not isinstance(adapter_list, list):
                adapter_list = [adapter_list]
                
            for adapter in adapter_list:
                name_raw  = adapter.get('Name', '')
                name_norm = _normalize_alias(name_raw)
                description = adapter.get('InterfaceDescription', '')
                
                if include_ignored or not DNSManager.should_ignore_adapter(name_norm, description):
                    adapters.append((name_raw, description))
                    
            return adapters
            
        except subprocess.TimeoutExpired:
            log("Таймаут при получении адаптеров", "❌ ERROR")
            return []
        except Exception as e:
            log(f"Ошибка fallback: {e}", "❌ ERROR")
            return []

    def get_all_dns_info_fast(self, adapter_names: list[str]) -> dict[str, dict[str, list[str]]]:
        """
        Одним PowerShell-скриптом берёт IPv4 и IPv6 DNS всех адаптеров.
        Возвращает: {adapter_name: {"ipv4": [...], "ipv6": [...]}}
        """
        if not adapter_names:
            return {}

        adapter_list = "','".join(adapter_names)

        ps_script = fr'''
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

        $adapters = @('{adapter_list}')
        $result   = @{{}}

        foreach ($a in $adapters) {{
            $adapterInfo = @{{
                "ipv4" = @()
                "ipv6" = @()
            }}

            # IPv4
            $dnsv4 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                -AddressFamily IPv4 -ErrorAction SilentlyContinue |
                Select -ExpandProperty ServerAddresses

            if (-not $dnsv4) {{
                $dnsv4 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                    -AddressFamily IPv4 -PolicyStore PersistentStore `
                    -ErrorAction SilentlyContinue |
                    Select -ExpandProperty ServerAddresses
            }}

            # IPv6
            $dnsv6 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                -AddressFamily IPv6 -ErrorAction SilentlyContinue |
                Select -ExpandProperty ServerAddresses

            if (-not $dnsv6) {{
                $dnsv6 = Get-DnsClientServerAddress -InterfaceAlias "$a" `
                    -AddressFamily IPv6 -PolicyStore PersistentStore `
                    -ErrorAction SilentlyContinue |
                    Select -ExpandProperty ServerAddresses
            }}

            if ($dnsv4) {{ $adapterInfo["ipv4"] = $dnsv4 }}
            if ($dnsv6) {{ $adapterInfo["ipv6"] = $dnsv6 }}

            $result[$a] = $adapterInfo
        }}

        $result | ConvertTo-Json -Depth 3
        '''

        try:
            run = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8'
            )

            if run.returncode:
                log(f"bulk-DNS error: {run.stderr}", "DEBUG")
                return self._get_dns_fallback(adapter_names)

            raw = json.loads(run.stdout or '{}')

            dns_data = {}
            for adapter_raw, info in raw.items():
                adapter_clean = _normalize_alias(adapter_raw)
                dns_data[adapter_clean] = {
                    "ipv4": info.get("ipv4", []),
                    "ipv6": info.get("ipv6", [])
                }

            return { _normalize_alias(n): dns_data.get(_normalize_alias(n), {"ipv4": [], "ipv6": []})
                    for n in adapter_names }

        except subprocess.TimeoutExpired:
            log("bulk-DNS timeout → fallback", "⚠ WARNING")
            return self._get_dns_fallback(adapter_names)
        except Exception as e:
            log(f"bulk-DNS exception: {e}", "DEBUG")
            return self._get_dns_fallback(adapter_names)

    def _get_dns_fallback(self, adapter_names: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """Fallback - получаем DNS по одному адаптеру"""
        dns_info = {}
        for name in adapter_names:
            try:
                dns_servers_v4 = self.get_current_dns(name, address_family="IPv4")
                dns_servers_v6 = self.get_current_dns(name, address_family="IPv6")
                dns_info[name] = {
                    "ipv4": dns_servers_v4,
                    "ipv6": dns_servers_v6
                }
            except Exception:
                dns_info[name] = {"ipv4": [], "ipv6": []}
        return dns_info
        
    @staticmethod
    def get_network_adapters(include_ignored: bool = False,
                            include_disconnected: bool = True):
        """Обратная совместимость + новый флаг"""
        return DNSManager.get_network_adapters_fast(
            include_ignored=include_ignored,
            include_disconnected=include_disconnected
        )

    @staticmethod
    def get_current_dns(adapter_name, address_family="IPv4"):
        """Получает текущие DNS-серверы для указанного адаптера и семейства адресов"""
        try:
            adapter_name_escaped = adapter_name.replace("'", "''")
            
            command = [
                'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                f'''
                try {{
                    $dns = Get-DnsClientServerAddress -InterfaceAlias '{adapter_name_escaped}' -AddressFamily {address_family} -ErrorAction Stop
                    if ($dns -and $dns.ServerAddresses) {{
                        $dns.ServerAddresses -join "`n"
                    }}
                }} catch {{
                    # Пустой вывод при ошибке
                }}
                '''
            ]
            
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0x08000000
                
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=5,
                creationflags=creationflags
            )
            
            if result.returncode != 0:
                return []
            
            dns_servers = [ip.strip() for ip in result.stdout.strip().splitlines() if ip.strip()]
            
            # Фильтруем только валидные адреса
            valid_dns = []
            for ip in dns_servers:
                if address_family == "IPv4" and '.' in ip:
                    octets = ip.split('.')
                    if len(octets) == 4 and all(o.isdigit() for o in octets):
                        valid_dns.append(ip)
                elif address_family == "IPv6" and ':' in ip:
                    # Базовая проверка IPv6
                    valid_dns.append(ip)
            
            return valid_dns
            
        except subprocess.TimeoutExpired:
            log(f"Таймаут при получении DNS для '{adapter_name}'", "DNS")
            return []
        except Exception as e:
            log(f"Ошибка при получении DNS-серверов для '{adapter_name}': {str(e)}", "DNS")
            return []

    @staticmethod
    def set_custom_dns(adapter_name, primary_dns, secondary_dns=None, address_family="IPv4"):
        """Устанавливает пользовательские DNS-серверы для указанного адаптера и семейства адресов"""
        try:
            dns_servers = f'"{primary_dns}"'
            if secondary_dns:
                dns_servers = f'"{primary_dns}","{secondary_dns}"'
            
            adapter_name_escaped = adapter_name.replace("'", "''")
            
            # Если устанавливаем IPv6, нужно убедиться что адаптер поддерживает IPv6
            command = f'''powershell -ExecutionPolicy Bypass -Command "
                $ErrorActionPreference = 'Stop'; 
                try {{ 
                    Set-DnsClientServerAddress -InterfaceAlias '{adapter_name_escaped}' -ServerAddresses {dns_servers}
                }} catch {{ 
                    $_.Exception.Message 
                }}"'''
            
            result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8')
            
            if result.returncode != 0 or result.stderr or (result.stdout and "Exception" in result.stdout):
                error_msg = result.stderr if result.stderr else result.stdout
                log(f"Ошибка установки {address_family} DNS-серверов: {error_msg}", level="DNS")
                return False, f"Ошибка установки {address_family} DNS-серверов: {error_msg}"
            
            return True, f"{address_family} DNS-серверы успешно установлены для {adapter_name}"
        except Exception as e:
            error_msg = str(e)
            log(f"Исключение при установке {address_family} DNS-серверов: {error_msg}", level="DNS")
            return False, f"Ошибка при установке {address_family} DNS-серверов: {error_msg}"
    
    @staticmethod
    def set_auto_dns(adapter_name, address_family=None):
        """
        Устанавливает автоматическое получение DNS-серверов для указанного адаптера.
        Если address_family=None, сбрасывает и IPv4 и IPv6
        """
        try:
            adapter_name_escaped = adapter_name.replace("'", "''")
            
            if address_family:
                # Сброс только для конкретного семейства адресов
                command = f'''powershell -ExecutionPolicy Bypass -Command "
                    $ErrorActionPreference = 'Stop'; 
                    try {{ 
                        Set-DnsClientServerAddress -InterfaceAlias '{adapter_name_escaped}' -ResetServerAddresses
                    }} catch {{ 
                        $_.Exception.Message 
                    }}"'''
            else:
                # Сброс для обоих семейств адресов
                command = f'''powershell -ExecutionPolicy Bypass -Command "
                    $ErrorActionPreference = 'Stop'; 
                    try {{ 
                        Set-DnsClientServerAddress -InterfaceAlias '{adapter_name_escaped}' -ResetServerAddresses
                    }} catch {{ 
                        $_.Exception.Message 
                    }}"'''
            
            result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8')
            
            if result.returncode != 0 or result.stderr or (result.stdout and "Exception" in result.stdout):
                error_msg = result.stderr if result.stderr else result.stdout
                log(f"Ошибка сброса DNS-серверов: {error_msg}", level="DNS")
                return False, f"Ошибка сброса DNS-серверов: {error_msg}"
            
            family_text = f"{address_family} " if address_family else ""
            return True, f"{family_text}DNS-серверы сброшены на автоматические для {adapter_name}"
        except Exception as e:
            error_msg = str(e)
            log(f"Исключение при сбросе DNS-серверов: {error_msg}", level="DNS")
            return False, f"Ошибка при сбросе DNS-серверов: {error_msg}"
        
    @staticmethod
    def flush_dns_cache():
        """Очищает кэш DNS для быстрого применения новых настроек"""
        try:
            command = 'ipconfig /flushdns'
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                log(f"Ошибка при очистке кэша DNS: {result.stderr}", level="DNS")
                return False, f"Ошибка при очистке кэша DNS: {result.stderr}"
            
            return True, "Кэш DNS успешно очищен"
        except Exception as e:
            log(f"Ошибка при очистке кэша DNS: {str(e)}", level="DNS")
            return False, f"Ошибка при очистке кэша DNS: {str(e)}"
    
class DNSSettingsDialog(QDialog):
    # Добавляем сигналы для уведомления о завершении загрузки
    adapters_loaded = pyqtSignal(list)
    dns_info_loaded = pyqtSignal(dict)
    
    def __init__(self, parent=None, common_style=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка DNS-серверов")
        self.setMinimumWidth(600)
        self.dns_manager = DNSManager()
        
        # Сохраняем переданный стиль или используем стандартный
        self.common_style = common_style or "color: #333;"
        
        # Сначала создаем базовый интерфейс с индикатором загрузки
        self.init_loading_ui()
        
        # Запускаем загрузку данных в отдельном потоке
        self.load_data_thread = threading.Thread(target=self.load_data_in_background)
        self.load_data_thread.daemon = True
        self.load_data_thread.start()
    
    def init_loading_ui(self):
        """Инициализация интерфейса с индикатором загрузки"""
        layout = QVBoxLayout()
        
        # Сообщение о загрузке
        loading_label = QLabel("Получение списка сетевых адаптеров и настроек DNS...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading_label)
        
        # Индикатор прогресса
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # Подключаем сигналы
        self.adapters_loaded.connect(self.on_adapters_loaded)
        self.dns_info_loaded.connect(self.on_dns_info_loaded)
    
    def load_data_in_background(self):
        """Оптимизированная загрузка данных"""
        try:
            from dns import refresh_exclusion_cache
            refresh_exclusion_cache()

            # 1. Быстро получаем все адаптеры (WMI)
            all_adapters = self.dns_manager.get_network_adapters_fast(
                include_ignored=True,
                include_disconnected=True
            )
            
            filtered_adapters = []
            for name, desc in all_adapters:
                if not self.dns_manager.should_ignore_adapter(name, desc):
                    filtered_adapters.append((name, desc))
            
            self.all_adapters = all_adapters
            self.adapters = filtered_adapters
            self.adapters_loaded.emit(filtered_adapters)
            
            # 2. Быстро получаем DNS для всех адаптеров ОДНИМ запросом
            adapter_names = [name for name, _ in all_adapters]
            dns_info = self.dns_manager.get_all_dns_info_fast(adapter_names)
            
            self.dns_info_loaded.emit(dns_info)
            
        except Exception as e:
            log(f"Ошибка при быстрой загрузке данных: {str(e)}", level="❌ ERROR")
            self._load_data_slow_fallback()

    def _load_data_slow_fallback(self):
        """Fallback к старому медленному методу"""
        try:
            all_adapters = DNSManager.get_network_adapters_powershell_fallback(include_ignored=True)
            filtered_adapters = [(name, desc) for name, desc in all_adapters 
                            if not DNSManager.should_ignore_adapter(name, desc)]
            
            self.all_adapters = all_adapters
            self.adapters = filtered_adapters
            self.adapters_loaded.emit(filtered_adapters)
            
            # DNS по одному адаптеру (медленно)
            dns_info = {}
            for name, _ in all_adapters:
                dns_servers_v4 = DNSManager().get_current_dns(name, "IPv4")
                dns_servers_v6 = DNSManager().get_current_dns(name, "IPv6")
                dns_info[name] = {
                    "ipv4": dns_servers_v4,
                    "ipv6": dns_servers_v6
                }
            
            self.dns_info_loaded.emit(dns_info)
        except Exception as e:
            log(f"Критическая ошибка загрузки DNS данных: {e}", "❌ ERROR")

    def on_adapters_loaded(self, adapters):
        """Обработчик загрузки списка адаптеров"""
        self.adapters = adapters
        if hasattr(self, 'dns_info'):
            self.init_full_ui()
    
    def on_dns_info_loaded(self, dns_info):
        """Обработчик загрузки информации о DNS"""
        self.dns_info = dns_info
        if hasattr(self, 'adapters'):
            self.init_full_ui()
    
    def init_full_ui(self):
        """Инициализация полного интерфейса после загрузки данных"""
        # Удаляем текущий интерфейс загрузки
        QWidget().setLayout(self.layout())

        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса с поддержкой IPv6"""
        layout = QVBoxLayout()
        
        # Группа для выбора адаптера
        self.adapter_group = QGroupBox("Сетевой адаптер")
        adapter_layout = QVBoxLayout()
        
        # Комбобокс для выбора адаптера с применением стиля
        self.adapter_combo = QComboBox()
        self.adapter_combo.setStyleSheet(self.common_style)
        self.refresh_adapters()
        adapter_layout.addWidget(self.adapter_combo)
        
        # Кнопка обновления списка адаптеров
        refresh_button = QPushButton("Обновить список")
        refresh_button.clicked.connect(self.refresh_adapters)
        adapter_layout.addWidget(refresh_button)
        
        self.adapter_group.setLayout(adapter_layout)
        layout.addWidget(self.adapter_group)
        
        # Флажок для применения ко всем адаптерам - устанавливаем True по умолчанию
        self.apply_all_check = QCheckBox("Применить настройки ко всем сетевым адаптерам")
        self.apply_all_check.setChecked(True)
        self.apply_all_check.stateChanged.connect(self.toggle_adapter_visibility)
        layout.addWidget(self.apply_all_check)
        
        # Создаем вкладки для IPv4 и IPv6
        self.tabs = QTabWidget()
        
        # Вкладка IPv4
        self.ipv4_tab = QWidget()
        self.init_ipv4_tab()
        self.tabs.addTab(self.ipv4_tab, "IPv4")
        
        # Вкладка IPv6
        self.ipv6_tab = QWidget()
        self.init_ipv6_tab()
        self.tabs.addTab(self.ipv6_tab, "IPv6")
        
        layout.addWidget(self.tabs)
        
        # Отображение текущих DNS-серверов
        current_dns_label = QLabel("Текущие DNS-серверы:")
        layout.addWidget(current_dns_label)
        
        self.current_dns_value = QLabel()
        self.current_dns_value.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.current_dns_value)
        
        # Кнопки ОК и Отмена
        buttons_layout = QHBoxLayout()
        
        apply_button = QPushButton("Применить")
        apply_button.clicked.connect(self.apply_dns_settings)
        buttons_layout.addWidget(apply_button)
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Подключаем обработчик изменения выбранного адаптера
        self.adapter_combo.currentIndexChanged.connect(self.update_current_dns)
        
        # Обновляем информацию о текущих DNS
        self.update_current_dns()
        
        # Применяем начальное состояние видимости адаптера
        self.toggle_adapter_visibility()

        # Применяем стиль к тексту в интерфейсе
        self.adapter_group.setStyleSheet(self.common_style)
        current_dns_label.setStyleSheet(self.common_style)
        self.apply_all_check.setStyleSheet(self.common_style)

    def init_ipv4_tab(self):
        """Инициализация вкладки IPv4"""
        layout = QVBoxLayout()
        
        # Радиокнопка для автоматических DNS
        self.auto_dns_v4_radio = QRadioButton("Получать адреса DNS-серверов автоматически")
        layout.addWidget(self.auto_dns_v4_radio)
        
        # Радиокнопка для предустановленных DNS
        self.predefined_dns_v4_radio = QRadioButton("Использовать предустановленные DNS-серверы:")
        layout.addWidget(self.predefined_dns_v4_radio)
        
        # Комбобокс для выбора предустановленных DNS
        self.predefined_dns_v4_combo = QComboBox()
        self.predefined_dns_v4_combo.setStyleSheet(self.common_style)
        for name, dns_data in PREDEFINED_DNS.items():
            if dns_data["ipv4"]:  # Добавляем только если есть IPv4 адреса
                self.predefined_dns_v4_combo.addItem(name)
        layout.addWidget(self.predefined_dns_v4_combo)
        
        # Радиокнопка для пользовательских DNS
        self.custom_dns_v4_radio = QRadioButton("Использовать следующие адреса DNS-серверов:")
        layout.addWidget(self.custom_dns_v4_radio)
        
        # Поля для ввода пользовательских DNS
        custom_dns_layout = QHBoxLayout()
        
        custom_dns_layout.addWidget(QLabel("Основной DNS:"))
        self.primary_dns_v4_edit = QLineEdit()
        self.primary_dns_v4_edit.setPlaceholderText("Например: 8.8.8.8")
        custom_dns_layout.addWidget(self.primary_dns_v4_edit)
        
        custom_dns_layout.addWidget(QLabel("Дополнительный DNS:"))
        self.secondary_dns_v4_edit = QLineEdit()
        self.secondary_dns_v4_edit.setPlaceholderText("Например: 8.8.4.4")
        custom_dns_layout.addWidget(self.secondary_dns_v4_edit)
        
        layout.addLayout(custom_dns_layout)
        
        # Группируем радиокнопки
        self.dns_v4_button_group = QButtonGroup()
        self.dns_v4_button_group.addButton(self.auto_dns_v4_radio)
        self.dns_v4_button_group.addButton(self.predefined_dns_v4_radio)
        self.dns_v4_button_group.addButton(self.custom_dns_v4_radio)
        
        # По умолчанию выбираем предустановленные DNS
        self.predefined_dns_v4_radio.setChecked(True)
        
        # Применяем стили
        self.auto_dns_v4_radio.setStyleSheet(self.common_style)
        self.predefined_dns_v4_radio.setStyleSheet(self.common_style)
        self.custom_dns_v4_radio.setStyleSheet(self.common_style)
        self.primary_dns_v4_edit.setStyleSheet(self.common_style)
        self.secondary_dns_v4_edit.setStyleSheet(self.common_style)
        
        layout.addStretch()
        self.ipv4_tab.setLayout(layout)

    def init_ipv6_tab(self):
        """Инициализация вкладки IPv6"""
        layout = QVBoxLayout()
        
        # Радиокнопка для автоматических DNS
        self.auto_dns_v6_radio = QRadioButton("Получать адреса DNS-серверов автоматически")
        layout.addWidget(self.auto_dns_v6_radio)
        
        # Радиокнопка для предустановленных DNS
        self.predefined_dns_v6_radio = QRadioButton("Использовать предустановленные DNS-серверы:")
        layout.addWidget(self.predefined_dns_v6_radio)
        
        # Комбобокс для выбора предустановленных DNS
        self.predefined_dns_v6_combo = QComboBox()
        self.predefined_dns_v6_combo.setStyleSheet(self.common_style)
        for name, dns_data in PREDEFINED_DNS.items():
            if dns_data["ipv6"]:  # Добавляем только если есть IPv6 адреса
                self.predefined_dns_v6_combo.addItem(name)
        layout.addWidget(self.predefined_dns_v6_combo)
        
        # Радиокнопка для пользовательских DNS
        self.custom_dns_v6_radio = QRadioButton("Использовать следующие адреса DNS-серверов:")
        layout.addWidget(self.custom_dns_v6_radio)
        
        # Поля для ввода пользовательских DNS
        custom_dns_layout = QHBoxLayout()
        
        custom_dns_layout.addWidget(QLabel("Основной DNS:"))
        self.primary_dns_v6_edit = QLineEdit()
        self.primary_dns_v6_edit.setPlaceholderText("Например: 2001:4860:4860::8888")
        custom_dns_layout.addWidget(self.primary_dns_v6_edit)
        
        custom_dns_layout.addWidget(QLabel("Дополнительный DNS:"))
        self.secondary_dns_v6_edit = QLineEdit()
        self.secondary_dns_v6_edit.setPlaceholderText("Например: 2001:4860:4860::8844")
        custom_dns_layout.addWidget(self.secondary_dns_v6_edit)
        
        layout.addLayout(custom_dns_layout)
        
        # Группируем радиокнопки
        self.dns_v6_button_group = QButtonGroup()
        self.dns_v6_button_group.addButton(self.auto_dns_v6_radio)
        self.dns_v6_button_group.addButton(self.predefined_dns_v6_radio)
        self.dns_v6_button_group.addButton(self.custom_dns_v6_radio)
        
        # По умолчанию выбираем автоматические DNS для IPv6
        self.auto_dns_v6_radio.setChecked(True)
        
        # Применяем стили
        self.auto_dns_v6_radio.setStyleSheet(self.common_style)
        self.predefined_dns_v6_radio.setStyleSheet(self.common_style)
        self.custom_dns_v6_radio.setStyleSheet(self.common_style)
        self.primary_dns_v6_edit.setStyleSheet(self.common_style)
        self.secondary_dns_v6_edit.setStyleSheet(self.common_style)
        
        layout.addStretch()
        self.ipv6_tab.setLayout(layout)

    def toggle_adapter_visibility(self):
        if hasattr(self, 'dns_info'):
            apply_to_all = self.apply_all_check.isChecked()
            self.adapter_group.setVisible(not apply_to_all)

            if apply_to_all:
                if hasattr(self, 'all_adapters') and hasattr(self, 'dns_info'):
                    adapters = self.adapters
                    all_adapters = self.all_adapters

                    if adapters:
                        dns_info_lines = []

                        # ── АКТИВНЫЕ ───────────────────────────────────────────
                        for name, desc in adapters[:3]:
                            clean = _normalize_alias(name)
                            dns_data = self.dns_info.get(clean, {"ipv4": [], "ipv6": []})
                            
                            ipv4_text = ", ".join(dns_data["ipv4"]) if dns_data["ipv4"] else "Автоматически (DHCP)"
                            ipv6_text = ", ".join(dns_data["ipv6"]) if dns_data["ipv6"] else "Автоматически (DHCP)"
                            
                            dns_info_lines.append(f"{name}:")
                            dns_info_lines.append(f"  IPv4: {ipv4_text}")
                            dns_info_lines.append(f"  IPv6: {ipv6_text}")

                        if len(adapters) > 3:
                            dns_info_lines.append(f"...и ещё {len(adapters) - 3} активных адаптеров")

                        # ── ИГНОРИРУЕМЫЕ ──────────────────────────────────────
                        ignored = [(n, d) for n, d in all_adapters
                                if self.dns_manager.should_ignore_adapter(n, d)]

                        if ignored:
                            dns_info_lines.append("\nИгнорируемые адаптеры (настройки не будут применены):")
                            for name, desc in ignored[:2]:
                                clean = _normalize_alias(name)
                                dns_data = self.dns_info.get(clean, {"ipv4": [], "ipv6": []})
                                
                                ipv4_text = ", ".join(dns_data["ipv4"]) if dns_data["ipv4"] else "Автоматически (DHCP)"
                                ipv6_text = ", ".join(dns_data["ipv6"]) if dns_data["ipv6"] else "Автоматически (DHCP)"
                                
                                dns_info_lines.append(f"{name}: IPv4: {ipv4_text}, IPv6: {ipv6_text}")

                            if len(ignored) > 2:
                                dns_info_lines.append(f"...и ещё {len(ignored) - 2} игнорируемых адаптеров")

                        self.current_dns_value.setText("\n".join(dns_info_lines))
                    else:
                        self.current_dns_value.setText("Не найдено подходящих сетевых адаптеров для применения настроек")
                else:
                    self.current_dns_value.setText("Загрузка информации о DNS...")
            else:
                self.update_current_dns()
    
    def refresh_adapters(self):
        """Обновляет список доступных сетевых адаптеров"""
        current_adapter = self.adapter_combo.currentText()
        
        self.adapter_combo.clear()
        
        adapters = getattr(self, 'adapters', self.dns_manager.get_network_adapters())
        
        if not adapters:
            QMessageBox.warning(self, "Предупреждение", "Не найдено активных сетевых адаптеров.")
            return
        
        adapter_names = []
        for name, description in adapters:
            adapter_text = f"{name} ({description})"
            self.adapter_combo.addItem(adapter_text, userData=name)
            adapter_names.append(adapter_text)
        
        if current_adapter in adapter_names:
            self.adapter_combo.setCurrentText(current_adapter)
            
    def update_current_dns(self, force_refresh=False):
        """Обновляет информацию о текущих DNS-серверах для выбранного адаптера"""
        if self.apply_all_check.isChecked():
            return

        if self.adapter_combo.count() == 0:
            self.current_dns_value.setText("Нет доступных адаптеров")
            return

        raw_name = self.adapter_combo.currentData()

        if not raw_name:
            self.current_dns_value.setText("Неизвестный адаптер")
            return

        clean_name = _normalize_alias(raw_name)

        need_refresh = (
            force_refresh
            or not hasattr(self, 'dns_info')
            or clean_name not in self.dns_info
        )

        if need_refresh:
            dns_v4 = self.dns_manager.get_current_dns(raw_name, "IPv4")
            dns_v6 = self.dns_manager.get_current_dns(raw_name, "IPv6")
            
            if not hasattr(self, 'dns_info'):
                self.dns_info = {}
            self.dns_info[clean_name] = {"ipv4": dns_v4, "ipv6": dns_v6}
        else:
            dns_data = self.dns_info.get(clean_name, {"ipv4": [], "ipv6": []})

        # Форматируем вывод
        dns_data = self.dns_info.get(clean_name, {"ipv4": [], "ipv6": []})
        
        lines = []
        if dns_data["ipv4"]:
            lines.append(f"IPv4: {', '.join(dns_data['ipv4'])}")
        else:
            lines.append("IPv4: Автоматически (DHCP)")
            
        if dns_data["ipv6"]:
            lines.append(f"IPv6: {', '.join(dns_data['ipv6'])}")
        else:
            lines.append("IPv6: Автоматически (DHCP)")
            
        self.current_dns_value.setText("\n".join(lines))

    def apply_dns_settings(self):
        """Применяет выбранные настройки DNS для IPv4 и IPv6"""
        # Получаем выбранные адаптеры
        adapters = []
        if self.apply_all_check.isChecked():
            adapters = [name for name, desc in self.adapters]
        else:
            if self.adapter_combo.count() == 0:
                QMessageBox.warning(self, "Ошибка", "Нет доступных сетевых адаптеров.")
                return
                
            adapter_name = self.adapter_combo.currentData()
            if not adapter_name:
                QMessageBox.warning(self, "Ошибка", "Выберите сетевой адаптер.")
                return
                
            adapters.append(adapter_name)
        
        success_count = 0
        error_messages = []
        
        for adapter_name in adapters:
            ipv4_success = True
            ipv6_success = True
            
            # Применяем настройки IPv4
            if self.auto_dns_v4_radio.isChecked():
                success, message = self.dns_manager.set_auto_dns(adapter_name, "IPv4")
                ipv4_success = success
            elif self.predefined_dns_v4_radio.isChecked():
                predefined_name = self.predefined_dns_v4_combo.currentText()
                if predefined_name in PREDEFINED_DNS:
                    dns_servers = PREDEFINED_DNS[predefined_name]["ipv4"]
                    if len(dns_servers) >= 2:
                        success, message = self.dns_manager.set_custom_dns(adapter_name, dns_servers[0], dns_servers[1], "IPv4")
                    elif len(dns_servers) == 1:
                        success, message = self.dns_manager.set_custom_dns(adapter_name, dns_servers[0], None, "IPv4")
                    else:
                        success = False
                        message = "Нет IPv4 адресов для выбранного DNS сервера"
                    ipv4_success = success
            elif self.custom_dns_v4_radio.isChecked():
                primary = self.primary_dns_v4_edit.text().strip()
                secondary = self.secondary_dns_v4_edit.text().strip()
                
                if not primary:
                    error_messages.append(f"{adapter_name}: Необходимо указать основной IPv4 DNS-сервер.")
                    continue
                
                success, message = self.dns_manager.set_custom_dns(adapter_name, primary, secondary if secondary else None, "IPv4")
                ipv4_success = success
            
            # Применяем настройки IPv6
            if self.auto_dns_v6_radio.isChecked():
                success, message = self.dns_manager.set_auto_dns(adapter_name, "IPv6")
                ipv6_success = success
            elif self.predefined_dns_v6_radio.isChecked():
                predefined_name = self.predefined_dns_v6_combo.currentText()
                if predefined_name in PREDEFINED_DNS:
                    dns_servers = PREDEFINED_DNS[predefined_name]["ipv6"]
                    if len(dns_servers) >= 2:
                        success, message = self.dns_manager.set_custom_dns(adapter_name, dns_servers[0], dns_servers[1], "IPv6")
                    elif len(dns_servers) == 1:
                        success, message = self.dns_manager.set_custom_dns(adapter_name, dns_servers[0], None, "IPv6")
                    else:
                        success = False
                        message = "Нет IPv6 адресов для выбранного DNS сервера"
                    ipv6_success = success
            elif self.custom_dns_v6_radio.isChecked():
                primary = self.primary_dns_v6_edit.text().strip()
                secondary = self.secondary_dns_v6_edit.text().strip()
                
                if primary:  # IPv6 может быть не настроен, поэтому не требуем обязательно
                    success, message = self.dns_manager.set_custom_dns(adapter_name, primary, secondary if secondary else None, "IPv6")
                    ipv6_success = success
            
            if ipv4_success and ipv6_success:
                success_count += 1
            else:
                if not ipv4_success:
                    error_messages.append(f"{adapter_name}: Ошибка IPv4 - {message}")
                if not ipv6_success:
                    error_messages.append(f"{adapter_name}: Ошибка IPv6 - {message}")

        # Обновляем кэш DNS информации после применения настроек
        if success_count > 0:
            # Очищаем DNS кэш системы
            dns_flush_success, dns_flush_message = self.dns_manager.flush_dns_cache()
            if not dns_flush_success:
                log(f"Предупреждение: {dns_flush_message}", level="DNS")
            
            # Даем время системе применить настройки
            QApplication.processEvents()
            import time
            time.sleep(0.5)
            
            # Обновляем наш кэш с актуальными данными
            all_adapter_names = [_normalize_alias(name) for name, _ in self.all_adapters]
            self.dns_info = self.dns_manager.get_all_dns_info_fast(all_adapter_names)
            
            # Перерисовываем интерфейс с новыми данными
            if self.apply_all_check.isChecked():
                self.toggle_adapter_visibility()
            else:
                self.update_current_dns(force_refresh=True)
        
        # Выводим результат
        if success_count == len(adapters):
            message = f"Настройки DNS успешно применены для {success_count} адаптера(ов)."
            if success_count > 0:
                message += "\nКэш DNS очищен для ускорения применения настроек."
            QMessageBox.information(self, "Успех", message)
            self.accept()
        elif success_count > 0:
            QMessageBox.warning(self, "Частичный успех", 
                            f"Настройки DNS применены для {success_count} из {len(adapters)} адаптера(ов).\n"
                            f"Кэш DNS очищен для ускорения применения настроек.\n\n"
                            f"Ошибки:\n{chr(10).join(error_messages)}")
        else:
            QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось применить настройки DNS ни к одному из адаптеров.\n\n"
                            f"Ошибки:\n{chr(10).join(error_messages)}")
            
def refresh_exclusion_cache():
    _get_dynamic_exclusions.cache_clear()