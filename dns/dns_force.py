# dns_force.py
"""
Менеджер принудительной установки DNS.
Теперь тянет DNSManager из dns_core, так что никаких колец.
"""
from __future__ import annotations
import subprocess
import winreg
import re
import time
from typing import List, Tuple, Optional

from log import log
from dns import DNSManager, DEFAULT_EXCLUSIONS               # ← главное изменение!
from utils import run_hidden

# PyQt сигналы нужны только если вы запускаете из GUI потока
from PyQt6.QtCore import QThread, pyqtSignal

from async_workers import DNSBatchWorker, DNSSetWorker
from PyQt6.QtCore import QEventLoop

# Добавьте эту константу после импортов
if hasattr(subprocess, 'CREATE_NO_WINDOW'):
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0x08000000

class DNSForceManager:
    """Менеджер принудительной установки DNS серверов с поддержкой IPv6"""
    
    REGISTRY_PATH = r"Software\ZapretReg2"
    FORCE_DNS_KEY = "ForceDNS"
    
    # DNS серверы для IPv4
    DNS_PRIMARY = "9.9.9.9"
    DNS_SECONDARY = "149.112.112.112"
    
    # DNS серверы для IPv6
    DNS_PRIMARY_V6 = "2620:fe::fe"
    DNS_SECONDARY_V6 = "2620:fe::9"

    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self._adapter_cache = None
        self._cache_timestamp = 0
        # Проверяем IPv6 при инициализации
        self.ipv6_available = self.check_ipv6_connectivity()

    @staticmethod
    def check_ipv6_connectivity():
        """Проверяет доступность IPv6 подключения"""
        try:
            result = run_hidden(
                ['C:\\Windows\\System32\\ping.exe', '-6', '-n', '1', '-w', '1500', '2001:4860:4860::8888'],
                capture_output=True, 
                text=True, 
                creationflags=CREATE_NO_WINDOW
            )
            is_available = (result.returncode == 0)
            log(f"DEBUG: IPv6 connectivity check: {'available' if is_available else 'unavailable'}", "DEBUG")
            return is_available
        except:
            log("DEBUG: IPv6 connectivity check failed", "DEBUG")
            return False

    def get_excluded_adapters(self) -> list[str]:
        """
        Возвращает список подстрок-фильтров только из DEFAULT_EXCLUSIONS.
        Реестр больше не используется.
        """
        return [x.lower() for x in DEFAULT_EXCLUSIONS]
    
    def is_adapter_excluded(self, adapter_name: str) -> bool:
        """Проверяет, находится ли адаптер в списке исключений"""
        exclusions = self.get_excluded_adapters()
        adapter_lower = adapter_name.lower()
        
        # Проверяем частичное совпадение
        for exclusion in exclusions:
            if exclusion in adapter_lower:
                log(f"Адаптер '{adapter_name}' исключен по паттерну '{exclusion}'", "DEBUG")
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
            return True
        except OSError:
            return True
        except Exception as e:
            log(f"Ошибка чтения ForceDNS: {e}", "❌ ERROR")
            return True
    
    def set_force_dns_enabled(self, enabled: bool):
        """Устанавливает значение опции принудительного DNS в реестре"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH) as key:
                winreg.SetValueEx(key, self.FORCE_DNS_KEY, 0, winreg.REG_DWORD, int(enabled))
            log(f"ForceDNS установлен в {enabled}", "DNS")
        except Exception as e:
            log(f"Ошибка записи настройки ForceDNS: {e}", "❌ ERROR")

    # ------------------------------------------------------------------ #
    #  Новый вариант: используем DNSManager.get_network_adapters_fast
    # ------------------------------------------------------------------ #
    def get_network_adapters(
        self,
        include_disconnected: bool = False,
        apply_exclusions: bool = True,
        use_cache: bool = True
    ) -> List[str]:
        """
        Возвращает список интерфейсов, используя универсальный метод из dns.py.
        Дополнительно применяет собственный список исключений (по желанию).
        """
        import time
        if use_cache and self._adapter_cache and (time.time() - self._cache_timestamp < 6000):
            return self._adapter_cache

        # Берём (name, description) через DNSManager
        pairs: list[tuple[str, str]] = DNSManager.get_network_adapters_fast(
            include_ignored=False,                # не включаем системные/виртуальные
            include_disconnected=include_disconnected
        )

        adapters: list[str] = []
        for name, desc in pairs:
            if apply_exclusions and self.is_adapter_excluded(name):
                log(f"Пропускаем исключенный интерфейс: {name}", "DNS")
                continue
            adapters.append(name)
            log(f"Найден интерфейс: {name}", "DNS")

        self._adapter_cache = adapters
        self._cache_timestamp = time.time()
        return adapters

    def set_dns_for_adapter(self, adapter_name: str, primary_dns: str, secondary_dns: Optional[str] = None, ip_version: str = 'ipv4') -> bool:
        """Упрощенная установка DNS серверов для конкретного адаптера"""
        try:
            interface_type = 'ipv4' if ip_version == 'ipv4' else 'ipv6'
            
            # Простая команда установки DNS
            cmd = f'netsh interface {interface_type} set dnsservers "{adapter_name}" static {primary_dns} primary'
            log(f"DEBUG: Устанавливаем {ip_version} DNS: {cmd}", "DEBUG")
            
            result = run_hidden(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW, timeout=10)
            
            if result.returncode != 0:
                log(f"Ошибка установки первичного {ip_version} DNS для {adapter_name}: {result.stderr}", "❌ ERROR")
                return False
            
            # Устанавливаем вторичный DNS, если указан
            if secondary_dns:
                cmd2 = f'netsh interface {interface_type} add dnsservers "{adapter_name}" {secondary_dns} index=2'
                log(f"DEBUG: Добавляем вторичный {ip_version} DNS: {cmd2}", "DEBUG")
                
                result2 = run_hidden(cmd2, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW, timeout=10)
                if result2.returncode != 0:
                    log(f"Предупреждение: не удалось добавить вторичный {ip_version} DNS: {result2.stderr}", "⚠ WARNING")
            
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
            
            cmd = f'netsh interface {interface_type} show dnsservers "{adapter_name}"'
            result = run_hidden(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW, timeout=5)
            
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
                                dns_servers.append(part)
            
            return dns_servers
            
        except Exception as e:
            log(f"Ошибка при получении {ip_version} DNS для {adapter_name}: {e}", "❌ ERROR")
            return dns_servers

    def reset_dns_to_auto(self, adapter_name: str, ip_version: Optional[str] = None) -> bool:
        """Сбрасывает DNS адаптера на автоматическое получение"""
        try:
            if ip_version:
                # Сброс для конкретной версии IP
                interface_type = 'ipv4' if ip_version == 'ipv4' else 'ipv6'
                cmd = f'netsh interface {interface_type} set dnsservers "{adapter_name}" dhcp'
                
                result = run_hidden(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW, timeout=10)
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
                    result = run_hidden(cmd, shell=True, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW, timeout=10)
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
        """Принудительно устанавливает DNS на всех подходящих адаптерах с проверкой IPv6"""
        if not self.is_force_dns_enabled():
            log("Принудительная установка DNS отключена в настройках", "DNS")
            return (0, 0)
        
        self._set_status("Получение списка сетевых адаптеров...")
        adapters = self.get_network_adapters(include_disconnected=include_disconnected)
        
        log(f"DEBUG: Найдено адаптеров для принудительного DNS: {adapters}", "DEBUG")
        
        if not adapters:
            self._set_status("Не найдено сетевых адаптеров")
            return (0, 0)
        
        # Проверяем IPv6 если нужно устанавливать IPv6 DNS
        if enable_ipv6 and not self.ipv6_available:
            log("DEBUG: IPv6 DNS пропущены - IPv6 подключение недоступно", "DEBUG")
            enable_ipv6 = False
        
        success_count = 0
        
        for adapter in adapters:
            log(f"DEBUG: Принудительная установка DNS для '{adapter}'", "DEBUG")
            self._set_status(f"Установка DNS для {adapter}...")
            
            # Устанавливаем IPv4 DNS
            ipv4_success = self.set_dns_for_adapter(adapter, self.DNS_PRIMARY, self.DNS_SECONDARY, 'ipv4')
            log(f"DEBUG: Результат установки IPv4 для {adapter}: {ipv4_success}", "DEBUG")
            
            # Устанавливаем IPv6 DNS, если включено и доступно
            ipv6_success = True
            if enable_ipv6:
                ipv6_success = self.set_dns_for_adapter(adapter, self.DNS_PRIMARY_V6, self.DNS_SECONDARY_V6, 'ipv6')
                log(f"DEBUG: Результат установки IPv6 для {adapter}: {ipv6_success}", "DEBUG")
            else:
                log(f"DEBUG: IPv6 DNS пропущены для {adapter} (IPv6 недоступен)", "DEBUG")
            
            if ipv4_success and ipv6_success:
                success_count += 1
            else:
                log(f"Не удалось полностью установить DNS для {adapter}", "⚠ WARNING")
        
        status_msg = f"DNS установлен на {success_count} из {len(adapters)} адаптеров"
        if not self.ipv6_available:
            status_msg += " (IPv6 пропущен)"
        
        self._set_status(status_msg)
        return (success_count, len(adapters))

    def get_all_adapters_with_status(self) -> List[dict]:
        """Возвращает все адаптеры с их статусом и информацией об исключениях"""
        all_adapters = []
        
        try:
            res = run_hidden(
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
                    'current_dns_v6': self.get_dns_for_adapter(iface_name, 'ipv6') if self.ipv6_available else []
                }
                
                all_adapters.append(adapter_info)
                
        except Exception as e:
            log(f"Ошибка получения списка адаптеров: {e}", "❌ ERROR")
        
        return all_adapters

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
            result = run_hidden(cmd, capture_output=True, text=True, encoding='cp866', creationflags=CREATE_NO_WINDOW)
            
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
            if self.ipv6_available:
                info['dns_v6'] = self.get_dns_for_adapter(adapter_name, 'ipv6')
            else:
                info['dns_v6'] = []
            
        except Exception as e:
            log(f"Ошибка получения информации об адаптере {adapter_name}: {e}", "❌ ERROR")
        
        return info
    
    def backup_current_dns(self) -> dict:
        """Создает резервную копию текущих DNS настроек всех адаптеров (IPv4 и IPv6)"""
        backup = {}
        adapters = self.get_network_adapters()
        
        for adapter in adapters:
            dns_servers_v4 = self.get_dns_for_adapter(adapter, 'ipv4')
            dns_servers_v6 = self.get_dns_for_adapter(adapter, 'ipv6') if self.ipv6_available else []
            
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
                    
                    # Восстанавливаем IPv6 только если доступен
                    if ipv6_servers and self.ipv6_available:
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

class AsyncDNSForceManager(DNSForceManager):
    """Асинхронная версия DNSForceManager"""
    
    def force_dns_on_all_adapters_async(self, callback=None):
        """Асинхронно устанавливает DNS на всех адаптерах"""
        if not self.is_force_dns_enabled():
            log("Принудительная установка DNS отключена", "DNS")
            if callback:
                callback(0, 0)
            return
        
        adapters = self.get_network_adapters()
        if not adapters:
            if callback:
                callback(0, 0)
            return
        
        # Создаем воркер для пакетной установки
        from PyQt6.QtCore import QThread
        thread = QThread()
        worker = DNSBatchWorker(self, adapters)
        worker.moveToThread(thread)
        
        # Подключаем сигналы
        thread.started.connect(worker.run)
        worker.progress.connect(lambda msg: log(msg, "DNS"))
        
        if callback:
            worker.finished.connect(callback)
        
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        # Запускаем
        thread.start()
        return thread
    
def apply_force_dns_if_enabled_async(callback=None):
    """Асинхронная версия применения DNS"""
    manager = AsyncDNSForceManager()
    
    if manager.is_force_dns_enabled():
        log("Применяем принудительные DNS настройки (асинхронно)...", "DNS")
        
        def on_done(success, total):
            log(f"DNS применен: {success}/{total} адаптеров", "DNS")
            if callback:
                callback(success > 0)
        
        manager.force_dns_on_all_adapters_async(on_done)
        return True
    return False

def ensure_default_force_dns():
    """
    Создаёт ключ HKCU\Software\ZapretReg2\ForceDNS = 1,
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