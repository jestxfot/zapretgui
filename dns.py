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
    Возвращает список исключаемых адаптеров из DNSForceManager.
    Теперь только из DEFAULT_EXCLUSIONS, без реестра.
    """
    try:
        mgr = DNSForceManager()
        return mgr.get_excluded_adapters()
    except Exception:
        # Fallback - возвращаем базовые исключения
        return [
            "vmware", "openvpn", "virtualbox", "hyper-v", "vmnet",
            "radmin vpn", "hamachi", "loopback", "teredo", "isatap",
            "docker", "wsl", "vethernet", "outline-tap"
        ]

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

        ps_script = r'''
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

            if ($dnsv4) {{ $adapterInfo["ipv4"] = @($dnsv4 | ForEach-Object {{ $_.ToString() }}) }}
            if ($dnsv6) {{ $adapterInfo["ipv6"] = @($dnsv6 | ForEach-Object {{ $_.ToString() }}) }}

            $result[$a] = $adapterInfo
        }}

        $result | ConvertTo-Json -Depth 3
        '''.format(adapter_list=adapter_list)

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
        """Упрощенная установка DNS"""
        
        log(f"DEBUG: Начинаем установку {address_family} DNS для '{adapter_name}': {primary_dns}, {secondary_dns}", "DEBUG")
        
        if address_family == "IPv4":
            # ========== IPv4: netsh (основной) + PowerShell (fallback) ==========
            log(f"DEBUG: Пробуем установить IPv4 DNS через netsh (основной метод)...", "DEBUG")
            success, msg = DNSManager._set_ipv4_via_netsh(adapter_name, primary_dns, secondary_dns)
            
            if success:
                return True, msg
            
            # Fallback к PowerShell
            log(f"DEBUG: Пробуем установить IPv4 DNS через PowerShell (fallback)...", "DEBUG")
            return DNSManager._set_ipv4_via_powershell(adapter_name, primary_dns, secondary_dns)
        
        else:  # IPv6
            # ========== IPv6: только PowerShell (простой) ==========
            log(f"DEBUG: Устанавливаем IPv6 DNS через PowerShell...", "DEBUG")
            return DNSManager._set_ipv6_via_powershell(adapter_name, primary_dns, secondary_dns)

    @staticmethod
    def _set_ipv4_via_netsh(adapter_name, primary_dns, secondary_dns=None):
        """Простая установка IPv4 через netsh"""
        try:
            cmd = f'netsh interface ipv4 set dnsservers "{adapter_name}" static {primary_dns} primary'
            log(f"DEBUG: netsh команда IPv4: {cmd}", "DEBUG")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', timeout=10)
            log(f"DEBUG: netsh IPv4 первичный - код: {result.returncode}, stderr: '{result.stderr.strip()}'", "DEBUG")
            
            if result.returncode != 0:
                return False, f"netsh IPv4 ошибка: {result.stderr}"
            
            if secondary_dns:
                cmd2 = f'netsh interface ipv4 add dnsservers "{adapter_name}" {secondary_dns} index=2'
                log(f"DEBUG: netsh команда IPv4 (вторичный): {cmd2}", "DEBUG")
                result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, encoding='cp866', timeout=10)
                log(f"DEBUG: netsh IPv4 вторичный - код: {result2.returncode}", "DEBUG")
            
            return True, "netsh: IPv4 DNS установлены"
            
        except Exception as e:
            return False, f"netsh IPv4 ошибка: {e}"

    @staticmethod
    def _set_ipv4_via_powershell(adapter_name, primary_dns, secondary_dns=None):
        """Простая установка IPv4 через PowerShell"""
        try:
            if secondary_dns:
                dns_array = f"@('{primary_dns}','{secondary_dns}')"
            else:
                dns_array = f"@('{primary_dns}')"
            
            command = f'''powershell -ExecutionPolicy Bypass -NoProfile -Command "
                Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4 -ServerAddresses {dns_array}"'''
            
            result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8', timeout=15)
            
            if result.returncode == 0:
                return True, "PowerShell: IPv4 DNS установлены"
            else:
                return False, f"PowerShell IPv4 ошибка: {result.stderr}"
                
        except Exception as e:
            return False, f"PowerShell IPv4 ошибка: {e}"
    
    @staticmethod
    def _set_ipv6_dns_with_no_validate(adapter_name, primary_dns, secondary_dns=None):
        """Установка IPv6 DNS с отключенной валидацией"""
        try:
            cmd = f'netsh interface ipv6 set dnsservers "{adapter_name}" static {primary_dns} primary validate=no'
            log(f"DEBUG: netsh IPv6 (validate=no): {cmd}", "DEBUG")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
            log(f"DEBUG: netsh IPv6 результат - код: {result.returncode}, stdout: '{result.stdout.strip()}', stderr: '{result.stderr.strip()}'", "DEBUG")
            
            if result.returncode != 0:
                return False, f"netsh IPv6 ошибка: {result.stderr}"
            
            # Добавляем вторичный DNS
            if secondary_dns:
                cmd2 = f'netsh interface ipv6 add dnsservers "{adapter_name}" {secondary_dns} index=2 validate=no'
                log(f"DEBUG: netsh IPv6 вторичный: {cmd2}", "DEBUG")
                
                result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
                log(f"DEBUG: netsh IPv6 вторичный результат - код: {result2.returncode}, stderr: '{result2.stderr.strip()}'", "DEBUG")
            
            return True, "IPv6 DNS установлены через netsh (validate=no)"
            
        except subprocess.TimeoutExpired:
            return False, "Таймаут netsh IPv6 команды (validate=no)"
        except Exception as e:
            return False, f"netsh IPv6 исключение: {e}"

    @staticmethod
    def _set_ipv6_dns_force(adapter_name, primary_dns, secondary_dns=None):
        """Принудительная установка IPv6 DNS через очистку и добавление"""
        try:
            # Метод 1: Сначала очищаем все DNS
            cmd_clear = f'netsh interface ipv6 delete dnsservers "{adapter_name}" all'
            log(f"DEBUG: netsh IPv6 очистка: {cmd_clear}", "DEBUG")
            
            result_clear = subprocess.run(cmd_clear, shell=True, capture_output=True, text=True, encoding='cp866', timeout=10)
            log(f"DEBUG: netsh IPv6 очистка - код: {result_clear.returncode}", "DEBUG")
            
            # Добавляем первый DNS
            cmd_add1 = f'netsh interface ipv6 add dnsservers "{adapter_name}" {primary_dns} index=1 validate=no'
            log(f"DEBUG: netsh IPv6 добавление primary: {cmd_add1}", "DEBUG")
            
            result1 = subprocess.run(cmd_add1, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
            log(f"DEBUG: netsh IPv6 primary результат - код: {result1.returncode}, stderr: '{result1.stderr.strip()}'", "DEBUG")
            
            if result1.returncode != 0:
                return False, f"Ошибка добавления первичного IPv6 DNS: {result1.stderr}"
            
            # Добавляем второй DNS
            if secondary_dns:
                cmd_add2 = f'netsh interface ipv6 add dnsservers "{adapter_name}" {secondary_dns} index=2 validate=no'
                log(f"DEBUG: netsh IPv6 добавление secondary: {cmd_add2}", "DEBUG")
                
                result2 = subprocess.run(cmd_add2, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
                log(f"DEBUG: netsh IPv6 secondary результат - код: {result2.returncode}, stderr: '{result2.stderr.strip()}'", "DEBUG")
            
            return True, "IPv6 DNS установлены принудительно (clear + add)"
            
        except subprocess.TimeoutExpired:
            return False, "Таймаут netsh IPv6 принудительной команды"
        except Exception as e:
            return False, f"Принудительная установка IPv6 ошибка: {e}"

    @staticmethod
    def _set_ipv6_dns_via_add(adapter_name, primary_dns, secondary_dns=None):
        """Установка IPv6 DNS только через add команды (без set)"""
        try:
            # Сначала пробуем удалить существующие (игнорируем ошибки)
            try:
                cmd_remove = f'netsh interface ipv6 delete dnsservers "{adapter_name}" all'
                subprocess.run(cmd_remove, shell=True, capture_output=True, text=True, encoding='cp866', timeout=5)
            except:
                pass
            
            # Добавляем DNS только через add команды
            cmd_add1 = f'netsh interface ipv6 add dnsservers "{adapter_name}" {primary_dns} index=1'
            log(f"DEBUG: netsh IPv6 add (без validate): {cmd_add1}", "DEBUG")
            
            result1 = subprocess.run(cmd_add1, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
            log(f"DEBUG: netsh IPv6 add primary - код: {result1.returncode}, stderr: '{result1.stderr.strip()}'", "DEBUG")
            
            if result1.returncode != 0:
                return False, f"Ошибка добавления IPv6 DNS через add: {result1.stderr}"
            
            # Добавляем вторичный
            if secondary_dns:
                cmd_add2 = f'netsh interface ipv6 add dnsservers "{adapter_name}" {secondary_dns} index=2'
                log(f"DEBUG: netsh IPv6 add secondary: {cmd_add2}", "DEBUG")
                
                result2 = subprocess.run(cmd_add2, shell=True, capture_output=True, text=True, encoding='cp866', timeout=15)
                log(f"DEBUG: netsh IPv6 add secondary - код: {result2.returncode}", "DEBUG")
            
            return True, "IPv6 DNS установлены через add команды"
            
        except subprocess.TimeoutExpired:
            return False, "Таймаут netsh IPv6 add команд"
        except Exception as e:
            return False, f"IPv6 add команды ошибка: {e}"

    @staticmethod
    def _set_ipv6_via_powershell(adapter_name, primary_dns, secondary_dns=None):
        """Простая установка IPv6 через PowerShell"""
        try:
            if secondary_dns:
                dns_array = f"@('{primary_dns}','{secondary_dns}')"
            else:
                dns_array = f"@('{primary_dns}')"
            
            command = f'''powershell -ExecutionPolicy Bypass -NoProfile -Command "
                Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv6 -ServerAddresses {dns_array}"'''
            
            result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8', timeout=15)
            
            if result.returncode == 0:
                return True, "PowerShell: IPv6 DNS установлены"
            else:
                return False, f"PowerShell IPv6 ошибка: {result.stderr}"
                
        except Exception as e:
            return False, f"PowerShell IPv6 ошибка: {e}"

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
        
        # Проверяем IPv6 подключение СРАЗУ
        self.ipv6_available = self.check_ipv6_connectivity()
        log(f"DEBUG: IPv6 подключение: {'доступно' if self.ipv6_available else 'недоступно'}", "DEBUG")
        
        # Сначала создаем базовый интерфейс с индикатором загрузки
        self.init_loading_ui()
        
        # Запускаем загрузку данных в отдельном потоке
        self.load_data_thread = threading.Thread(target=self.load_data_in_background)
        self.load_data_thread.daemon = True
        self.load_data_thread.start()

    @staticmethod
    def check_ipv6_connectivity():
        """Быстрая проверка доступности IPv6 подключения"""
        try:
            result = subprocess.run(
                ['ping', '-6', '-n', '1', '-w', '1500', '2001:4860:4860::8888'],
                capture_output=True, 
                text=True, 
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except:
            return False
        
    def check_ipv6_in_background(self):
        """Проверяем IPv6 подключение в фоне"""
        try:
            # Быстрая проверка IPv6
            result = subprocess.run(
                ['ping', '-6', '-n', '1', '-w', '2000', '2001:4860:4860::8888'],
                capture_output=True, 
                text=True, 
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.ipv6_available = (result.returncode == 0)
            log(f"DEBUG: IPv6 подключение: {'доступно' if self.ipv6_available else 'недоступно'}", "DEBUG")
        except:
            self.ipv6_available = False
            log("DEBUG: IPv6 подключение: недоступно (ошибка проверки)", "DEBUG")

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
                # ИСПРАВЛЕНО: убрали создание экземпляра
                dns_servers_v4 = DNSManager.get_current_dns(name, "IPv4")
                dns_servers_v6 = DNSManager.get_current_dns(name, "IPv6")
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
        
        # Флажок для применения ко всем адаптерам
        self.apply_all_check = QCheckBox("Применить настройки ко всем сетевым адаптерам")
        self.apply_all_check.setChecked(True)
        self.apply_all_check.stateChanged.connect(self.toggle_adapter_visibility)
        layout.addWidget(self.apply_all_check)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка IPv4 (всегда есть)
        self.ipv4_tab = QWidget()
        self.init_ipv4_tab()
        self.tabs.addTab(self.ipv4_tab, "IPv4")
        
        # Вкладка IPv6 (только если IPv6 доступен)
        if self.ipv6_available:
            self.ipv6_tab = QWidget()
            self.init_ipv6_tab()
            self.tabs.addTab(self.ipv6_tab, "IPv6")
            log("DEBUG: IPv6 вкладка добавлена (IPv6 доступен)", "DEBUG")
        else:
            # Создаем заглушку для IPv6 (чтобы код не ломался)
            self.ipv6_tab = None
            self.auto_dns_v6_radio = None
            self.predefined_dns_v6_radio = None
            self.custom_dns_v6_radio = None
            
            # Добавляем информационное сообщение
            ipv6_info = QLabel(
                "ℹ️ IPv6 подключение недоступно - настройки IPv6 скрыты.\n"
                "Для IPv6 DNS будет использоваться автоматический режим."
            )
            ipv6_info.setStyleSheet(
                "color: #856404; background-color: #fff3cd; padding: 10px; "
                "border: 1px solid #ffeaa7; border-radius: 5px; margin: 5px;"
            )
            layout.addWidget(ipv6_info)
            log("DEBUG: IPv6 вкладка скрыта (IPv6 недоступен)", "DEBUG")
        
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
        if not self.ipv6_available:
            return  # Не создаем вкладку если IPv6 недоступен
    
        layout = QVBoxLayout()

        # Информационная панель (заполняется после проверки IPv6)
        self.ipv6_info_label = QLabel("Проверка IPv6 подключения...")
        self.ipv6_info_label.setStyleSheet("padding: 5px; border-radius: 3px;")
        layout.addWidget(self.ipv6_info_label)
        
        # Обновляем информацию когда проверка завершится
        QTimer.singleShot(3000, self.update_ipv6_info)  # Через 3 сек обновляем
                
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
                log(f"DEBUG: Добавлен IPv6 DNS: {name} -> {dns_data['ipv6']}", "DEBUG")
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

    def update_ipv6_info(self):
        """Обновляет информацию об IPv6 состоянии"""
        if self.ipv6_available is True:
            self.ipv6_info_label.setText("✅ IPv6 подключение доступно")
            self.ipv6_info_label.setStyleSheet("color: green; background-color: #d4edda; padding: 5px; border-radius: 3px;")
        elif self.ipv6_available is False:
            self.ipv6_info_label.setText("⚠ IPv6 подключение недоступно (IPv6 DNS могут не работать)")
            self.ipv6_info_label.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 5px; border-radius: 3px;")
        else:
            self.ipv6_info_label.setText("⏳ Проверка IPv6 подключения...")
            self.ipv6_info_label.setStyleSheet("color: #6c757d; background-color: #f8f9fa; padding: 5px; border-radius: 3px;")

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
            if self.ipv6_available:
                dns_v6 = self.dns_manager.get_current_dns(raw_name, "IPv6")
            else:
                dns_v6 = []
            
            if not hasattr(self, 'dns_info'):
                self.dns_info = {}
            self.dns_info[clean_name] = {"ipv4": dns_v4, "ipv6": dns_v6}

        # Форматируем вывод
        dns_data = self.dns_info.get(clean_name, {"ipv4": [], "ipv6": []})
        
        lines = []
        if dns_data["ipv4"]:
            lines.append(f"IPv4: {', '.join(dns_data['ipv4'])}")
        else:
            lines.append("IPv4: Автоматически (DHCP)")
            
        if self.ipv6_available:
            if dns_data["ipv6"]:
                lines.append(f"IPv6: {', '.join(dns_data['ipv6'])}")
            else:
                lines.append("IPv6: Автоматически (DHCP)")
        else:
            lines.append("IPv6: Недоступен")
            
        self.current_dns_value.setText("\n".join(lines))

    def apply_dns_settings(self):
        """Упрощенная логика применения DNS"""
        
        # Отключаем принудительный DNS
        try:
            from dns_force import DNSForceManager
            force_mgr = DNSForceManager()
            if force_mgr.is_force_dns_enabled():
                force_mgr.set_force_dns_enabled(False)
                log("⚠ Принудительный DNS отключен на время изменения настроек", "DEBUG")
        except Exception as e:
            log(f"Ошибка отключения принудительного DNS: {e}", "DEBUG")
        
        # Получаем адаптеры
        adapters = []
        if self.apply_all_check.isChecked():
            adapters = [name for name, desc in self.adapters]
            log(f"DEBUG: Применяем ко всем адаптерам: {adapters}", "DEBUG")
        else:
            if self.adapter_combo.count() == 0:
                QMessageBox.warning(self, "Ошибка", "Нет доступных сетевых адаптеров.")
                return
            adapter_name = self.adapter_combo.currentData()
            if not adapter_name:
                QMessageBox.warning(self, "Ошибка", "Выберите сетевой адаптер.")
                return
            adapters.append(adapter_name)
            log(f"DEBUG: Применяем к адаптеру: {adapter_name}", "DEBUG")
        
        success_count = 0
        error_messages = []
        
        for adapter_name in adapters:
            log(f"DEBUG: Обрабатываем адаптер '{adapter_name}'", "DEBUG")
            
            # Логируем текущие DNS
            current_v4 = DNSManager.get_current_dns(adapter_name, "IPv4")
            if self.ipv6_available:
                current_v6 = DNSManager.get_current_dns(adapter_name, "IPv6")
                log(f"DEBUG: Текущие DNS для '{adapter_name}' - IPv4: {current_v4}, IPv6: {current_v6}", "DEBUG")
            else:
                log(f"DEBUG: Текущие DNS для '{adapter_name}' - IPv4: {current_v4}, IPv6: пропущено (недоступно)", "DEBUG")
            
            ipv4_success = True
            ipv6_success = True
            
            # ========== IPv4 ==========
            if self.auto_dns_v4_radio.isChecked():
                log(f"DEBUG: Устанавливаем автоматический IPv4 DNS для '{adapter_name}'", "DEBUG")
                success, message = DNSManager.set_auto_dns(adapter_name, "IPv4")
                ipv4_success = success
                log(f"DEBUG: Результат автоматического IPv4: {success}, {message}", "DEBUG")
            elif self.predefined_dns_v4_radio.isChecked():
                predefined_name = self.predefined_dns_v4_combo.currentText()
                log(f"DEBUG: Устанавливаем предустановленный IPv4 DNS '{predefined_name}' для '{adapter_name}'", "DEBUG")
                dns_servers = PREDEFINED_DNS[predefined_name]["ipv4"]
                log(f"DEBUG: IPv4 серверы: {dns_servers}", "DEBUG")
                
                primary = dns_servers[0] if len(dns_servers) > 0 else None
                secondary = dns_servers[1] if len(dns_servers) > 1 else None
                
                if primary:
                    success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary, "IPv4")
                    ipv4_success = success
                    log(f"DEBUG: Результат предустановленного IPv4: {success}, {message}", "DEBUG")
            elif self.custom_dns_v4_radio.isChecked():
                primary = self.primary_dns_v4_edit.text().strip()
                secondary = self.secondary_dns_v4_edit.text().strip() or None
                log(f"DEBUG: Устанавливаем пользовательский IPv4 DNS для '{adapter_name}': {primary}, {secondary}", "DEBUG")
                
                if not primary:
                    error_messages.append(f"{adapter_name}: Необходимо указать основной IPv4 DNS-сервер.")
                    continue
                
                success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary, "IPv4")
                ipv4_success = success
                log(f"DEBUG: Результат пользовательского IPv4: {success}, {message}", "DEBUG")
            
            # ========== IPv6 (только если доступен) ==========
            if self.ipv6_available:
                if self.auto_dns_v6_radio.isChecked():
                    log(f"DEBUG: Устанавливаем автоматический IPv6 DNS для '{adapter_name}'", "DEBUG")
                    success, message = DNSManager.set_auto_dns(adapter_name, "IPv6")
                    ipv6_success = success
                    log(f"DEBUG: Результат автоматического IPv6: {success}, {message}", "DEBUG")
                elif self.predefined_dns_v6_radio.isChecked():
                    predefined_name = self.predefined_dns_v6_combo.currentText()
                    log(f"DEBUG: Устанавливаем предустановленный IPv6 DNS '{predefined_name}' для '{adapter_name}'", "DEBUG")
                    dns_servers = PREDEFINED_DNS[predefined_name]["ipv6"]
                    log(f"DEBUG: IPv6 серверы: {dns_servers}", "DEBUG")
                    
                    primary = dns_servers[0] if len(dns_servers) > 0 else None
                    secondary = dns_servers[1] if len(dns_servers) > 1 else None
                    
                    if primary:
                        success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary, "IPv6")
                        ipv6_success = success
                        log(f"DEBUG: Результат предустановленного IPv6: {success}, {message}", "DEBUG")
                elif self.custom_dns_v6_radio.isChecked():
                    primary = self.primary_dns_v6_edit.text().strip()
                    secondary = self.secondary_dns_v6_edit.text().strip() or None
                    log(f"DEBUG: Устанавливаем пользовательский IPv6 DNS для '{adapter_name}': {primary}, {secondary}", "DEBUG")
                    
                    if primary:
                        success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary, "IPv6")
                        ipv6_success = success
                        log(f"DEBUG: Результат пользовательского IPv6: {success}, {message}", "DEBUG")
            else:
                log(f"DEBUG: IPv6 настройки пропущены для '{adapter_name}' (IPv6 недоступен)", "DEBUG")
            
            # Подсчет успехов
            if ipv4_success and ipv6_success:
                success_count += 1
            else:
                if not ipv4_success:
                    error_messages.append(f"{adapter_name}: Ошибка IPv4 - {message}")
                if not ipv6_success and self.ipv6_available:
                    error_messages.append(f"{adapter_name}: Ошибка IPv6 - {message}")
        
        # Обновляем интерфейс
        if success_count > 0:
            DNSManager.flush_dns_cache()
            QApplication.processEvents()
            
            # Обновляем кэш
            all_adapter_names = [_normalize_alias(name) for name, _ in self.all_adapters]
            self.dns_info = self.dns_manager.get_all_dns_info_fast(all_adapter_names)
            
            if self.apply_all_check.isChecked():
                self.toggle_adapter_visibility()
            else:
                self.update_current_dns(force_refresh=True)
        
        # Результат
        if success_count == len(adapters):
            message = f"Настройки DNS успешно применены для {success_count} адаптера(ов)."
            if not self.ipv6_available:
                message += "\n(IPv6 настройки пропущены - IPv6 недоступен)"
            QMessageBox.information(self, "Успех", message)
            self.accept()
        elif success_count > 0:
            QMessageBox.warning(self, "Частичный успех", 
                            f"Настройки применены для {success_count} из {len(adapters)} адаптера(ов).\n\n"
                            f"Ошибки:\n{chr(10).join(error_messages)}")
        else:
            QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось применить настройки DNS ни к одному из адаптеров.\n\n"
                            f"Ошибки:\n{chr(10).join(error_messages)}")

    def _apply_dns_settings_internal(self):
        """Применяет выбранные настройки DNS для IPv4 и IPv6"""
        
        # Проверяем и отключаем принудительный DNS
        try:
            from dns_force import DNSForceManager
            force_mgr = DNSForceManager()
            if force_mgr.is_force_dns_enabled():
                force_mgr.set_force_dns_enabled(False)
                log("⚠ Принудительный DNS отключен на время изменения настроек", "DEBUG")
        except Exception as e:
            log(f"Ошибка отключения принудительного DNS: {e}", "DEBUG")
        
        # Получаем выбранные адаптеры
        adapters = []
        if self.apply_all_check.isChecked():
            adapters = [name for name, desc in self.adapters]
            log(f"DEBUG: Применяем ко всем адаптерам: {adapters}", "DEBUG")
        else:
            if self.adapter_combo.count() == 0:
                QMessageBox.warning(self, "Ошибка", "Нет доступных сетевых адаптеров.")
                return
                
            adapter_name = self.adapter_combo.currentData()
            if not adapter_name:
                QMessageBox.warning(self, "Ошибка", "Выберите сетевой адаптер.")
                return
                
            adapters.append(adapter_name)
            log(f"DEBUG: Применяем к адаптеру: {adapter_name}", "DEBUG")
        
        success_count = 0
        error_messages = []
        
        for adapter_name in adapters:
            log(f"DEBUG: Обрабатываем адаптер '{adapter_name}'", "DEBUG")
            
            # Проверяем текущие DNS ПЕРЕД изменением
            current_v4 = DNSManager.get_current_dns(adapter_name, "IPv4")
            current_v6 = DNSManager.get_current_dns(adapter_name, "IPv6")
            log(f"DEBUG: Текущие DNS для '{adapter_name}' - IPv4: {current_v4}, IPv6: {current_v6}", "DEBUG")
            
            ipv4_success = True
            ipv6_success = True
            
            # ========== ПРИМЕНЯЕМ НАСТРОЙКИ IPv4 ==========
            if self.auto_dns_v4_radio.isChecked():
                log(f"DEBUG: Устанавливаем автоматический IPv4 DNS для '{adapter_name}'", "DEBUG")
                success, message = DNSManager.set_auto_dns(adapter_name, "IPv4")
                ipv4_success = success
                log(f"DEBUG: Результат автоматического IPv4: {success}, {message}", "DEBUG")
            elif self.predefined_dns_v4_radio.isChecked():
                predefined_name = self.predefined_dns_v4_combo.currentText()
                log(f"DEBUG: Устанавливаем предустановленный IPv4 DNS '{predefined_name}' для '{adapter_name}'", "DEBUG")
                if predefined_name in PREDEFINED_DNS:
                    dns_servers = PREDEFINED_DNS[predefined_name]["ipv4"]
                    log(f"DEBUG: IPv4 серверы: {dns_servers}", "DEBUG")
                    if len(dns_servers) >= 2:
                        success, message = DNSManager.set_custom_dns(adapter_name, dns_servers[0], dns_servers[1], "IPv4")
                    elif len(dns_servers) == 1:
                        success, message = DNSManager.set_custom_dns(adapter_name, dns_servers[0], None, "IPv4")
                    else:
                        success = False
                        message = "Нет IPv4 адресов для выбранного DNS сервера"
                    ipv4_success = success
                    log(f"DEBUG: Результат предустановленного IPv4: {success}, {message}", "DEBUG")
            elif self.custom_dns_v4_radio.isChecked():
                primary = self.primary_dns_v4_edit.text().strip()
                secondary = self.secondary_dns_v4_edit.text().strip()
                log(f"DEBUG: Устанавливаем пользовательский IPv4 DNS для '{adapter_name}': {primary}, {secondary}", "DEBUG")
                
                if not primary:
                    error_messages.append(f"{adapter_name}: Необходимо указать основной IPv4 DNS-сервер.")
                    continue
                
                success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary if secondary else None, "IPv4")
                ipv4_success = success
                log(f"DEBUG: Результат пользовательского IPv4: {success}, {message}", "DEBUG")
            
            # ========== ПРИМЕНЯЕМ НАСТРОЙКИ IPv6 ==========
            log(f"DEBUG: Проверяем состояние IPv6 радиокнопок:", "DEBUG")
            log(f"DEBUG: auto_dns_v6_radio.isChecked() = {self.auto_dns_v6_radio.isChecked()}", "DEBUG")
            log(f"DEBUG: predefined_dns_v6_radio.isChecked() = {self.predefined_dns_v6_radio.isChecked()}", "DEBUG")
            log(f"DEBUG: custom_dns_v6_radio.isChecked() = {self.custom_dns_v6_radio.isChecked()}", "DEBUG")

            if self.auto_dns_v6_radio.isChecked():
                log(f"DEBUG: Устанавливаем автоматический IPv6 DNS для '{adapter_name}'", "DEBUG")
                success, message = DNSManager.set_auto_dns(adapter_name, "IPv6")
                ipv6_success = success
                log(f"DEBUG: Результат автоматического IPv6: {success}, {message}", "DEBUG")
            elif self.predefined_dns_v6_radio.isChecked():
                predefined_name = self.predefined_dns_v6_combo.currentText()
                log(f"DEBUG: Устанавливаем предустановленный IPv6 DNS '{predefined_name}' для '{adapter_name}'", "DEBUG")
                if predefined_name in PREDEFINED_DNS:
                    dns_servers = PREDEFINED_DNS[predefined_name]["ipv6"]
                    log(f"DEBUG: IPv6 серверы: {dns_servers}", "DEBUG")
                    if len(dns_servers) >= 2:
                        success, message = DNSManager.set_custom_dns(adapter_name, dns_servers[0], dns_servers[1], "IPv6")
                    elif len(dns_servers) == 1:
                        success, message = DNSManager.set_custom_dns(adapter_name, dns_servers[0], None, "IPv6")
                    else:
                        success = False
                        message = "Нет IPv6 адресов для выбранного DNS сервера"
                    ipv6_success = success
                    log(f"DEBUG: Результат предустановленного IPv6: {success}, {message}", "DEBUG")
            elif self.custom_dns_v6_radio.isChecked():
                primary = self.primary_dns_v6_edit.text().strip()
                secondary = self.secondary_dns_v6_edit.text().strip()
                log(f"DEBUG: Устанавливаем пользовательский IPv6 DNS для '{adapter_name}': {primary}, {secondary}", "DEBUG")
                
                if primary:  # IPv6 может быть не настроен, поэтому не требуем обязательно
                    success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary if secondary else None, "IPv6")
                    ipv6_success = success
                    log(f"DEBUG: Результат пользовательского IPv6: {success}, {message}", "DEBUG")
            elif self.custom_dns_v6_radio.isChecked():
                primary = self.primary_dns_v6_edit.text().strip()
                secondary = self.secondary_dns_v6_edit.text().strip()
                log(f"DEBUG: Устанавливаем пользовательский IPv6 DNS для '{adapter_name}': {primary}, {secondary}", "DEBUG")
                
                if primary:  # IPv6 может быть не настроен, поэтому не требуем обязательно
                    success, message = DNSManager.set_custom_dns(adapter_name, primary, secondary if secondary else None, "IPv6")
                    ipv6_success = success
                    log(f"DEBUG: Результат пользовательского IPv6: {success}, {message}", "DEBUG")
            
            # ========== ПРОВЕРКА РЕЗУЛЬТАТОВ ==========
            import time
            time.sleep(1)
            
            # Проверяем IPv4
            immediate_v4 = DNSManager.get_current_dns(adapter_name, "IPv4")
            log(f"DEBUG: НЕМЕДЛЕННАЯ проверка IPv4 для '{adapter_name}': {immediate_v4}", "DEBUG")
            
            # Проверяем IPv6
            immediate_v6 = DNSManager.get_current_dns(adapter_name, "IPv6")
            log(f"DEBUG: НЕМЕДЛЕННАЯ проверка IPv6 для '{adapter_name}': {immediate_v6}", "DEBUG")
            
            time.sleep(2)
            
            delayed_v4 = DNSManager.get_current_dns(adapter_name, "IPv4")
            delayed_v6 = DNSManager.get_current_dns(adapter_name, "IPv6")
            log(f"DEBUG: ОТЛОЖЕННАЯ проверка IPv4 для '{adapter_name}': {delayed_v4}", "DEBUG")
            log(f"DEBUG: ОТЛОЖЕННАЯ проверка IPv6 для '{adapter_name}': {delayed_v6}", "DEBUG")
            
            if immediate_v4 != delayed_v4:
                log(f"⚠ WARNING: IPv4 DNS были изменены внешним процессом! Было: {immediate_v4}, стало: {delayed_v4}", "WARNING")
            
            if immediate_v6 != delayed_v6:
                log(f"⚠ WARNING: IPv6 DNS были изменены внешним процессом! Было: {immediate_v6}, стало: {delayed_v6}", "WARNING")
            
            if ipv4_success and ipv6_success:
                success_count += 1
            else:
                if not ipv4_success:
                    error_messages.append(f"{adapter_name}: Ошибка IPv4 - {message}")
                if not ipv6_success:
                    error_messages.append(f"{adapter_name}: Ошибка IPv6 - {message}")

        # ========== ОБНОВЛЯЕМ ИНТЕРФЕЙС ==========
        if success_count > 0:
            # Очищаем DNS кэш системы
            dns_flush_success, dns_flush_message = DNSManager.flush_dns_cache()
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
        
        # ========== ВЫВОДИМ РЕЗУЛЬТАТ ==========
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