# dns_force.py

import subprocess
import winreg
from typing import List, Tuple, Optional, Dict
from log import log
import re

from PyQt6.QtCore import QThread, pyqtSignal

# Добавьте эту константу после импортов
if hasattr(subprocess, 'CREATE_NO_WINDOW'):
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0x08000000

class DNSForceManager:
    """Менеджер принудительной установки DNS серверов с поддержкой IPv6"""
    
    REGISTRY_PATH = r"Software\Zapret"
    FORCE_DNS_KEY = "ForceDNS"
    EXCLUDED_ADAPTERS_KEY = "ExcludedAdapters"
    
    # DNS серверы для IPv4
    DNS_PRIMARY = "9.9.9.9"
    DNS_SECONDARY = "149.112.112.112"  # Запасной DNS от Quad9
    
    # DNS серверы для IPv6
    DNS_PRIMARY_V6 = "2620:fe::fe"
    DNS_SECONDARY_V6 = "2620:fe::9"  # Запасной DNS от Quad9 для IPv6

    # Список исключений по умолчанию
    DEFAULT_EXCLUSIONS = [
        # Виртуальные адаптеры
        "vmware",
        "outline-tap0",
        "outline-tap1",
        "outline-tap2",
        "outline-tap3",
        "outline-tap4",
        "outline-tap5",
        "outline-tap6",
        "outline-tap7",
        "outline-tap8",
        "outline-tap9",
        "openvpn",
        "virtualbox",
        "hyper-v",
        "vmnet",
        
        # VPN адаптеры
        "radmin vpn",
        "hamachi",
        "openvpn",
        "nordvpn",
        "expressvpn",
        "surfshark",
        "pritunl",
        "zerotier",
        "tailscale",
        
        # Системные/служебные
        "loopback",
        "teredo",
        "isatap",
        "6to4",
        "Сетевые подключения Bluetooth",
        
        # Другие виртуальные
        "docker",
        "wsl",
        "vethernet"
    ]

    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self._adapter_cache = None
        self._cache_timestamp = 0
        self._ensure_default_exclusions()

    def _ensure_default_exclusions(self):
        """Создает список исключений по умолчанию, если его нет"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                winreg.QueryValueEx(key, self.EXCLUDED_ADAPTERS_KEY)
        except FileNotFoundError:
            # Ключ не существует, создаем с настройками по умолчанию
            self.set_excluded_adapters(self.DEFAULT_EXCLUSIONS)
        except Exception:
            pass

    def get_excluded_adapters(self) -> list[str]:
        """
        Возвращает список подстрок-фильтров.
        • Сначала DEFAULT_EXCLUSIONS
        • Затем + то, что в реестре HKCU\Software\Zapret\ExcludedAdapters
          (через «;» либо переносы строк)
        """
        exclusions: set[str] = set(x.lower() for x in self.DEFAULT_EXCLUSIONS)

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                fr"{self.REGISTRY_PATH}",
                0, winreg.KEY_READ
            ) as key:
                raw, _ = winreg.QueryValueEx(key, self.EXCLUDED_ADAPTERS_KEY)
                # «outline;myvpn;test» или с переводами строк
                extra = [part.strip().lower() for part in raw.replace('\n', ';').split(';')]
                exclusions.update(filter(None, extra))
        except FileNotFoundError:
            # ключ или параметр отсутствуют – просто используем дефолт
            pass
        except Exception as e:
            log(f"DNSForce: не удалось прочитать список исключений: {e}", "DEBUG")

        final = sorted(exclusions)
        return final

    def set_excluded_adapters(self, exclusions: List[str]):
        """Сохраняет список исключенных адаптеров в реестр"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                import json
                value = json.dumps([e.lower() for e in exclusions], ensure_ascii=False)
                winreg.SetValueEx(key, self.EXCLUDED_ADAPTERS_KEY, 0, winreg.REG_SZ, value)
            log(f"Список исключений обновлен: {len(exclusions)} записей", "DNS")
        except Exception as e:
            log(f"Ошибка сохранения списка исключений: {e}", "❌ ERROR")

    def add_adapter_to_exclusions(self, adapter_name: str):
        """Добавляет адаптер в список исключений"""
        exclusions = self.get_excluded_adapters()
        adapter_lower = adapter_name.lower()
        
        if adapter_lower not in exclusions:
            exclusions.append(adapter_lower)
            self.set_excluded_adapters(exclusions)
            log(f"Адаптер '{adapter_name}' добавлен в исключения", "DNS")
            return True
        return False

    def remove_adapter_from_exclusions(self, adapter_name: str):
        """Удаляет адаптер из списка исключений"""
        exclusions = self.get_excluded_adapters()
        adapter_lower = adapter_name.lower()
        
        if adapter_lower in exclusions:
            exclusions.remove(adapter_lower)
            self.set_excluded_adapters(exclusions)
            log(f"Адаптер '{adapter_name}' удален из исключений", "DNS")
            return True
        return False
    
    def is_adapter_excluded(self, adapter_name: str) -> bool:
        """Проверяет, находится ли адаптер в списке исключений"""
        exclusions = self.get_excluded_adapters()
        adapter_lower = adapter_name.lower()
        
        # Проверяем точное совпадение
        if adapter_lower in exclusions:
            return True
        
        # Проверяем частичное совпадение (для паттернов типа "vmware", "vpn")
        for exclusion in exclusions:
            if exclusion in adapter_lower:
                return True
        
        return False
            
    def _set_status(self, text: str):
        """Обновляет статус, если есть callback"""
        if self.status_callback:
            self.status_callback(text)
        log(f"DNSForce: {text}", "DNS")
    
    def is_force_dns_enabled(self) -> bool:
        """
        Возвращает True, если функция включена.
        Если ключ отсутствует – считаем, что она ВКЛЮЧЕНА (значение по умолчанию).
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                value, _ = winreg.QueryValueEx(key, self.FORCE_DNS_KEY)
                return bool(value)
        except FileNotFoundError:
            return True          # ← Новое поведение: «включено» по умолчанию
        except OSError:
            return True
        except Exception as e:
            log(f"Ошибка чтения ForceDNS: {e}", "❌ ERROR")
            return True
    
    def ensure_default_force_dns():
        """Создаёт ключ ForceDNS=1, если он отсутствует."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DNSForceManager.REGISTRY_PATH):
                pass       # ключ уже есть
        except FileNotFoundError:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DNSForceManager.REGISTRY_PATH) as key:
                winreg.SetValueEx(key, DNSForceManager.FORCE_DNS_KEY, 0,
                                winreg.REG_DWORD, 1)
            
    def set_force_dns_enabled(self, enabled: bool):
        """Устанавливает значение опции принудительного DNS в реестре"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                winreg.SetValueEx(key, self.FORCE_DNS_KEY, 0, winreg.REG_DWORD, int(enabled))
            log(f"ForceDNS установлен в {enabled}", "DNS")
        except Exception as e:
            log(f"Ошибка записи настройки ForceDNS: {e}", "❌ ERROR")
    
    def get_network_adapters(self, include_disconnected: bool = False, apply_exclusions: bool = True, use_cache: bool = True) -> List[str]:
        """
        Возвращает список сетевых интерфейсов.
        
        Args:
            include_disconnected: Если True, включает также отключенные адаптеры
            apply_exclusions: Если True, применяет список исключений
        
        Returns:
            List[str]: Список имен адаптеров
        """
        # Используем кеш, если он свежий (менее 6000 секунд)
        import time
        if use_cache and self._adapter_cache and (time.time() - self._cache_timestamp < 6000):
            return self._adapter_cache
        
        adapters: list[str] = []

        try:
            res = subprocess.run(
                ['netsh', 'interface', 'show', 'interface'],
                capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW
            )
            if res.returncode != 0:
                log(f"netsh error: {res.stderr}", "❌ ERROR")
                return adapters

            for line in res.stdout.splitlines()[3:]:          # пропускаем шапку
                line = line.rstrip()
                if not line:
                    continue

                # режем по «≥2 пробела»
                parts = re.split(r'\s{2,}', line)
                if len(parts) < 4:
                    continue

                admin_state, conn_state, _type, iface_name = parts[:4]

                # Проверяем административное состояние
                admin_state = admin_state.lower()
                if admin_state not in ('enabled', 'разрешен'):
                    log(f"Пропускаем отключенный администратором интерфейс: {iface_name}", "DEBUG")
                    continue

                # Проверяем состояние подключения
                conn_state = conn_state.lower()
                
                # Если include_disconnected=False, пропускаем отключенные
                if not include_disconnected and conn_state not in ('connected', 'подключен'):
                    log(f"Пропускаем отключенный интерфейс: {iface_name} (состояние: {conn_state})", "DEBUG")
                    continue

                # Применяем список исключений
                if apply_exclusions and self.is_adapter_excluded(iface_name):
                    log(f"Пропускаем исключенный интерфейс: {iface_name}", "DNS")
                    continue

                adapters.append(iface_name)
                
                # Логируем с указанием состояния
                status = "активный" if conn_state in ('connected', 'подключен') else "отключенный"
                log(f"Найден {status} интерфейс: {iface_name}", "DNS")

        except Exception as e:
            log(f"get_network_adapters error: {e}", "❌ ERROR")

        self._adapter_cache = adapters
        self._cache_timestamp = time.time()

        return adapters

    def get_all_adapters_with_status(self) -> List[dict]:
        """Возвращает все адаптеры с их статусом и информацией об исключениях"""
        all_adapters = []
        
        try:
            res = subprocess.run(
                ['netsh', 'interface', 'show', 'interface'],
                capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW
            )
            if res.returncode != 0:
                return all_adapters

            for line in res.stdout.splitlines()[3:]:
                line = line.rstrip()
                if not line:
                    continue

                parts = re.split(r'\s{2,}', line)
                if len(parts) < 4:
                    continue

                admin_state, conn_state, _type, iface_name = parts[:4]
                
                adapter_info = {
                    'name': iface_name,
                    'admin_state': admin_state,
                    'connection_state': conn_state,
                    'type': _type,
                    'excluded': self.is_adapter_excluded(iface_name),
                    'current_dns_v4': self.get_dns_for_adapter(iface_name, 'ipv4'),
                    'current_dns_v6': self.get_dns_for_adapter(iface_name, 'ipv6')
                }
                
                all_adapters.append(adapter_info)
                
        except Exception as e:
            log(f"Ошибка получения списка адаптеров: {e}", "❌ ERROR")
        
        return all_adapters
        
    def set_dns_for_adapter(self, adapter_name: str, primary_dns: str, secondary_dns: Optional[str] = None, ip_version: str = 'ipv4') -> bool:
        """Устанавливает DNS серверы для конкретного адаптера (поддерживает IPv4 и IPv6)"""
        try:
            # Определяем команду в зависимости от версии IP
            interface_type = 'ipv4' if ip_version == 'ipv4' else 'ipv6'
            
            # Вариант 1: Использовать name= без дополнительных кавычек
            cmd_primary = [
                'netsh', 'interface', interface_type, 'set', 'dnsservers',
                f'name={adapter_name}',  # БЕЗ дополнительных кавычек!
                'static', primary_dns, 'primary'
            ]
            
            result = subprocess.run(cmd_primary, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                # Вариант 2: Если не сработало, пробуем с экранированием
                log(f"Первая попытка не удалась для {ip_version}, пробуем альтернативный метод", "DNS")
                
                # Используем shell=True для корректной обработки пробелов
                cmd_str = f'netsh interface {interface_type} set dnsservers "{adapter_name}" static {primary_dns} primary'
                result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    log(f"Ошибка установки первичного {ip_version} DNS для {adapter_name}: {result.stderr}", "❌ ERROR")
                    return False
            
            # Устанавливаем вторичный DNS, если указан
            if secondary_dns:
                cmd_secondary = [
                    'netsh', 'interface', interface_type, 'add', 'dnsservers',
                    f'name={adapter_name}',  # Также без дополнительных кавычек
                    secondary_dns, 'index=2'
                ]
                
                result = subprocess.run(cmd_secondary, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
                if result.returncode != 0:
                    # Альтернативный метод для вторичного DNS
                    cmd_str = f'netsh interface {interface_type} add dnsservers "{adapter_name}" {secondary_dns} index=2'
                    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
                    
                    if result.returncode != 0:
                        log(f"Ошибка установки вторичного {ip_version} DNS для {adapter_name}: {result.stderr}", "⚠ WARNING")
            
            log(f"{ip_version.upper()} DNS успешно установлен для {adapter_name}: {primary_dns}", "DNS")
            return True
            
        except Exception as e:
            log(f"Ошибка при установке {ip_version} DNS для {adapter_name}: {e}", "❌ ERROR")
            return False
    
    def get_dns_for_adapter(self, adapter_name: str, ip_version: str = 'ipv4') -> List[str]:
        """Получает текущие DNS серверы для адаптера (поддерживает IPv4 и IPv6)"""
        dns_servers = []
        try:
            interface_type = 'ipv4' if ip_version == 'ipv4' else 'ipv6'
            
            # Используем shell=True для корректной обработки пробелов
            cmd = f'netsh interface {interface_type} show dnsservers "{adapter_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and any(char.isdigit() for char in line):
                        # Извлекаем IP адрес
                        parts = line.split()
                        for part in parts:
                            if ip_version == 'ipv4' and '.' in part and all(c.isdigit() or c == '.' for c in part):
                                dns_servers.append(part)
                            elif ip_version == 'ipv6' and ':' in part:
                                # Для IPv6 адресов
                                dns_servers.append(part)
            
            return dns_servers
            
        except Exception as e:
            log(f"Ошибка при получении {ip_version} DNS для {adapter_name}: {e}", "❌ ERROR")
            return dns_servers

    def reset_dns_to_auto(self, adapter_name: str, ip_version: Optional[str] = None) -> bool:
        """
        Сбрасывает DNS адаптера на автоматическое получение.
        Если ip_version не указан, сбрасывает и IPv4, и IPv6
        """
        try:
            if ip_version:
                # Сброс для конкретной версии IP
                interface_type = 'ipv4' if ip_version == 'ipv4' else 'ipv6'
                cmd = f'netsh interface {interface_type} set dnsservers "{adapter_name}" dhcp'
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
                if result.returncode == 0:
                    log(f"{ip_version.upper()} DNS для {adapter_name} сброшен на автоматический", "DNS")
                    return True
                else:
                    log(f"Ошибка сброса {ip_version} DNS для {adapter_name}: {result.stderr}", "❌ ERROR")
                    return False
            else:
                # Сброс для обеих версий IP
                success = True
                for version in ['ipv4', 'ipv6']:
                    cmd = f'netsh interface {version} set dnsservers "{adapter_name}" dhcp'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
                    if result.returncode != 0:
                        log(f"Ошибка сброса {version} DNS для {adapter_name}: {result.stderr}", "❌ ERROR")
                        success = False
                
                if success:
                    log(f"DNS для {adapter_name} сброшен на автоматический (IPv4 и IPv6)", "DNS")
                return success
                
        except Exception as e:
            log(f"Ошибка при сбросе DNS для {adapter_name}: {e}", "❌ ERROR")
            return False
    
    def force_dns_on_all_adapters(self, include_disconnected: bool = True, enable_ipv6: bool = True) -> Tuple[int, int]:
        """
        Принудительно устанавливает DNS на всех подходящих адаптерах.
        Поддерживает установку как IPv4, так и IPv6 DNS.
        
        Args:
            include_disconnected: Если True, устанавливает DNS также на отключенных адаптерах
            enable_ipv6: Если True, также устанавливает IPv6 DNS серверы
            
        Returns:
            Tuple[int, int]: (успешно_изменено, всего_адаптеров)
        """
        if not self.is_force_dns_enabled():
            log("Принудительная установка DNS отключена в настройках", "DNS")
            return (0, 0)
        
        self._set_status("Получение списка сетевых адаптеров...")
        adapters = self.get_network_adapters(include_disconnected=include_disconnected)
        
        if not adapters:
            self._set_status("Не найдено сетевых адаптеров")
            return (0, 0)
        
        success_count = 0
        
        for adapter in adapters:
            self._set_status(f"Установка DNS для {adapter}...")
            
            # Проверяем текущие DNS
            current_dns_v4 = self.get_dns_for_adapter(adapter, 'ipv4')
            log(f"Текущие IPv4 DNS для {adapter}: {current_dns_v4}", "DNS")
            
            # Устанавливаем IPv4 DNS
            ipv4_success = self.set_dns_for_adapter(adapter, self.DNS_PRIMARY, self.DNS_SECONDARY, 'ipv4')
            
            # Устанавливаем IPv6 DNS, если включено
            ipv6_success = True
            if enable_ipv6:
                current_dns_v6 = self.get_dns_for_adapter(adapter, 'ipv6')
                log(f"Текущие IPv6 DNS для {adapter}: {current_dns_v6}", "DNS")
                ipv6_success = self.set_dns_for_adapter(adapter, self.DNS_PRIMARY_V6, self.DNS_SECONDARY_V6, 'ipv6')
            
            if ipv4_success and ipv6_success:
                success_count += 1
                
                # Проверяем, что DNS действительно изменился
                new_dns_v4 = self.get_dns_for_adapter(adapter, 'ipv4')
                log(f"Новые IPv4 DNS для {adapter}: {new_dns_v4}", "DNS")
                
                if enable_ipv6:
                    new_dns_v6 = self.get_dns_for_adapter(adapter, 'ipv6')
                    log(f"Новые IPv6 DNS для {adapter}: {new_dns_v6}", "DNS")
            else:
                log(f"Не удалось полностью установить DNS для {adapter}", "⚠ WARNING")
        
        self._set_status(f"DNS установлен на {success_count} из {len(adapters)} адаптеров")
        return (success_count, len(adapters))

    def get_adapter_info(self, adapter_name: str) -> dict:
        """Получает подробную информацию об адаптере включая IPv6"""
        info = {
            'name': adapter_name,
            'connected': False,
            'type': 'unknown',
            'dns_v4': [],
            'dns_v6': []
        }
        
        try:
            # Получаем состояние интерфейса
            cmd = ['netsh', 'interface', 'show', 'interface']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if adapter_name in line:
                        parts = re.split(r'\s{2,}', line.strip())
                        if len(parts) >= 4:
                            conn_state = parts[1].lower()
                            info['connected'] = conn_state in ('connected', 'подключен')
                            
                            # Определяем тип адаптера
                            if 'беспроводн' in adapter_name.lower() or 'wi-fi' in adapter_name.lower():
                                info['type'] = 'wireless'
                            elif 'ethernet' in adapter_name.lower():
                                info['type'] = 'ethernet'
                            elif 'vpn' in adapter_name.lower():
                                info['type'] = 'vpn'
                            elif 'vmware' in adapter_name.lower():
                                info['type'] = 'virtual'
            
            # Получаем текущие DNS для IPv4 и IPv6
            info['dns_v4'] = self.get_dns_for_adapter(adapter_name, 'ipv4')
            info['dns_v6'] = self.get_dns_for_adapter(adapter_name, 'ipv6')
            
        except Exception as e:
            log(f"Ошибка получения информации об адаптере {adapter_name}: {e}", "❌ ERROR")
        
        return info
    
    def backup_current_dns(self) -> dict:
        """Создает резервную копию текущих DNS настроек всех адаптеров (IPv4 и IPv6)"""
        backup = {}
        adapters = self.get_network_adapters()
        
        for adapter in adapters:
            dns_servers_v4 = self.get_dns_for_adapter(adapter, 'ipv4')
            dns_servers_v6 = self.get_dns_for_adapter(adapter, 'ipv6')
            
            if dns_servers_v4 or dns_servers_v6:
                backup[adapter] = {
                    'ipv4': dns_servers_v4,
                    'ipv6': dns_servers_v6
                }
                log(f"Сохранены DNS для {adapter}: IPv4={dns_servers_v4}, IPv6={dns_servers_v6}", "DNS")
        
        # Сохраняем в реестр
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                import json
                backup_json = json.dumps(backup, ensure_ascii=False)
                winreg.SetValueEx(key, "DNSBackup", 0, winreg.REG_SZ, backup_json)
                log("Резервная копия DNS сохранена в реестр", "DNS")
        except Exception as e:
            log(f"Ошибка сохранения резервной копии DNS: {e}", "❌ ERROR")
        
        return backup
    
    def restore_dns_from_backup(self) -> bool:
        """Восстанавливает DNS настройки из резервной копии (IPv4 и IPv6)"""
        try:
            # Читаем резервную копию из реестра
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                backup_json, _ = winreg.QueryValueEx(key, "DNSBackup")
                import json
                backup = json.loads(backup_json)
            
            success = True
            for adapter, dns_data in backup.items():
                # Восстанавливаем IPv4
                if isinstance(dns_data, dict):
                    # Новый формат с разделением IPv4/IPv6
                    ipv4_servers = dns_data.get('ipv4', [])
                    ipv6_servers = dns_data.get('ipv6', [])
                    
                    if ipv4_servers:
                        if not self.set_dns_for_adapter(adapter, ipv4_servers[0], 
                                                       ipv4_servers[1] if len(ipv4_servers) > 1 else None, 'ipv4'):
                            success = False
                    
                    if ipv6_servers:
                        if not self.set_dns_for_adapter(adapter, ipv6_servers[0], 
                                                       ipv6_servers[1] if len(ipv6_servers) > 1 else None, 'ipv6'):
                            success = False
                else:
                    # Старый формат (только IPv4)
                    if dns_data:
                        if not self.set_dns_for_adapter(adapter, dns_data[0], 
                                                       dns_data[1] if len(dns_data) > 1 else None, 'ipv4'):
                            success = False
            
            return success
            
        except Exception as e:
            log(f"Ошибка восстановления DNS из резервной копии: {e}", "❌ ERROR")
            return False

def apply_force_dns_if_enabled(status_callback=None, enable_ipv6=True):
    """
    Вспомогательная функция для быстрого применения принудительного DNS.
    
    Args:
        status_callback: Функция обратного вызова для обновления статуса
        enable_ipv6: Если True, также устанавливает IPv6 DNS
    """
    manager = DNSForceManager(status_callback)
    if manager.is_force_dns_enabled():
        log("Применяем принудительные DNS настройки...", "DNS")
        success, total = manager.force_dns_on_all_adapters(enable_ipv6=enable_ipv6)
        log(f"Принудительный DNS применен: {success}/{total} адаптеров", "DNS")
        return success > 0
    return False

def ensure_default_force_dns():
    """
    Создаёт ключ HKCU\Software\Zapret\ForceDNS = 1,
    если его ещё нет (по умолчанию опция включена).
    """
    import winreg
    from log import log

    try:
        path = DNSForceManager.REGISTRY_PATH
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path):
            return          # ключ уже есть
    except FileNotFoundError:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
                winreg.SetValueEx(key, DNSForceManager.FORCE_DNS_KEY,
                                  0, winreg.REG_DWORD, 1)
            log("Создан ключ ForceDNS = 1 (значение по умолчанию)", "DNS")
        except Exception as e:
            log(f"Не удалось создать ключ ForceDNS: {e}", "❌ ERROR")