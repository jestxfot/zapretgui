# orchestra/orchestra_runner.py
"""
Circular Orchestra Runner - автоматическое обучение стратегий DPI bypass.

Использует circular orchestrator из F:\doc\zapret2\lua\zapret-auto.lua (файл менять этот нельзя) с:
- combined_failure_detector (RST injection + silent drop)
- strategy_stats (LOCK механизм после 3 успехов, UNLOCK после 2 failures)
- domain_grouping (группировка субдоменов)

При этом сам оркестратор (его исходный код) всегда хранится H:\Privacy\zapret\lua

Копировать в Program Data не нужно -  приложение берёт файлы напрямую из H:\Privacy\zapret\lua\.

Можешь посмотреть исходный код логов в исходном коде запрета F:\doc\zapret2\nfq2\desync.c

Логи - только Python - компактные для гуи чтобы не было огромных winws2 debug логов.
"""

import os
import subprocess
import threading
import re
import json
import glob
from typing import Optional, Callable, Dict, List
from datetime import datetime

from log import log
from config import MAIN_DIRECTORY, EXE_FOLDER, LUA_FOLDER, LOGS_FOLDER, BIN_FOLDER, REGISTRY_PATH
from config.reg import reg, reg_enumerate_values, reg_delete_all_values

# Пути в реестре для хранения обученных стратегий (subkeys)
REGISTRY_ORCHESTRA = f"{REGISTRY_PATH}\\Orchestra"
REGISTRY_ORCHESTRA_TLS = f"{REGISTRY_ORCHESTRA}\\TLS"      # TLS стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HTTP = f"{REGISTRY_ORCHESTRA}\\HTTP"    # HTTP стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_UDP = f"{REGISTRY_ORCHESTRA}\\UDP"      # UDP стратегии: IP=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HISTORY = f"{REGISTRY_ORCHESTRA}\\History"  # История: domain=JSON (REG_SZ)

# Максимальное количество лог-файлов оркестратора
MAX_ORCHESTRA_LOGS = 10

# Белый список по умолчанию - сайты которые НЕ нужно обрабатывать
# Эти сайты работают без DPI bypass или требуют особой обработки
DEFAULT_WHITELIST = [
    # Российские сервисы (работают без bypass)
    "vk.com",
    "vk.ru",
    "vk-portal.net",
    "userapi.com",
    "mail.ru",
    "max.ru",
    "ok.ru",
    "mail.ru",
    "yandex.ru",
    "yandex.by",
    "yandex.kz",
    "sberbank.ru",
    "nalog.ru",
    # Банки
    "tinkoff.ru",
    "alfabank.ru",
    "vtb.ru",
    # Государственные
    "mos.ru",
    "gosuslugi.ru",
    "government.ru",
    # Антивирусы и безопасность
    "kaspersky.ru",
    "kaspersky.com",
    "drweb.ru",
    "drweb.com",
    # Microsoft (обычно работает)
    "microsoft.com",
    "live.com",
    "office.com",
    # Локальные адреса
    "localhost",
    "127.0.0.1",

    "netschool.edu22.info",
    "edu22.info",

    "tilda.ws",
    "tilda.cc",
    "tildacdn.com"
]

# Локальные IP диапазоны (для UDP - проверяем IP напрямую)
LOCAL_IP_PREFIXES = (
    # IPv4
    "127.",        # Loopback
    "10.",         # Private Class A
    "192.168.",    # Private Class C
    "172.16.", "172.17.", "172.18.", "172.19.",  # Private Class B
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "169.254.",    # Link-local
    "0.",          # This network
    # IPv6
    "::1",         # Loopback
    "fe80:",       # Link-local
    "fc00:", "fd00:",  # Unique local (private)
)

# Константы для скрытого запуска процесса
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000
STARTF_USESHOWWINDOW = 0x00000001

# Multi-part TLDs (для корректного NLD-cut)
MULTI_PART_TLDS = {
    'co.uk', 'com.au', 'co.nz', 'co.jp', 'co.kr', 'co.in', 'co.za',
    'com.br', 'com.mx', 'com.ar', 'com.ru', 'com.ua', 'com.cn',
    'org.uk', 'org.au', 'net.au', 'gov.uk', 'ac.uk', 'edu.au',
}

def nld_cut(hostname: str, nld: int = 2) -> str:
    """
    Обрезает hostname до N-level domain (как standard_hostkey в lua).

    nld=2: "rr1---sn-xxx.googlevideo.com" -> "googlevideo.com"
    nld=2: "static.xx.fbcdn.net" -> "fbcdn.net"
    nld=2: "www.bbc.co.uk" -> "bbc.co.uk" (учитывает multi-part TLD)

    Args:
        hostname: полный hostname
        nld: количество уровней (по умолчанию 2)

    Returns:
        Обрезанный hostname
    """
    if not hostname:
        return hostname

    # IP адреса не обрезаем
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', hostname):
        return hostname

    parts = hostname.lower().split('.')
    if len(parts) <= nld:
        return hostname

    # Проверяем multi-part TLD (например .co.uk)
    if len(parts) >= 2:
        last_two = '.'.join(parts[-2:])
        if last_two in MULTI_PART_TLDS:
            # Для .co.uk и подобных берём на 1 уровень больше
            if len(parts) <= nld + 1:
                return hostname
            return '.'.join(parts[-(nld + 1):])

    return '.'.join(parts[-nld:])


def ip_to_subnet16(ip: str) -> str:
    """
    Конвертирует IP адрес в /16 подсеть (первые 2 октета).
    Используется для UDP чтобы группировать похожие IP (обычно один кластер серверов).

    Примеры:
        103.142.5.10 -> 103.142.0.0
        185.244.180.1 -> 185.244.0.0

    Args:
        ip: IP адрес

    Returns:
        IP с /16 маской (x.x.0.0) или оригинальный IP если не удалось распарсить
    """
    match = re.match(r'^(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}$', ip)
    if match:
        return f"{match.group(1)}.{match.group(2)}.0.0"
    return ip  # Не IP адрес - возвращаем как есть


class OrchestraRunner:
    """
    Runner для circular оркестратора с автоматическим обучением.

    Особенности:
    - Использует circular orchestrator (не mega_circular)
    - Детекция: RST injection + silent drop + SUCCESS по байтам (2KB)
    - LOCK после 3 успехов на одной стратегии
    - UNLOCK после 2 failures (автоматическое переобучение)
    - Группировка субдоменов (googlevideo.com, youtube.com и т.д.)
    - Python логи (компактные)
    """

    def __init__(self, zapret_path: str = None):
        if zapret_path is None:
            zapret_path = MAIN_DIRECTORY

        self.zapret_path = zapret_path
        self.winws_exe = os.path.join(EXE_FOLDER, "winws2.exe")
        self.lua_path = LUA_FOLDER
        self.logs_path = LOGS_FOLDER
        self.bin_path = BIN_FOLDER

        # Файлы конфигурации (в lua папке)
        self.config_path = os.path.join(self.lua_path, "circular-config.txt")
        self.blobs_path = os.path.join(self.lua_path, "blobs.txt")

        # TLS 443 стратегии
        self.strategies_source_path = os.path.join(self.lua_path, "strategies-source.txt")
        self.strategies_path = os.path.join(self.lua_path, "strategies-all.txt")

        # HTTP 80 стратегии
        self.http_strategies_source_path = os.path.join(self.lua_path, "strategies-http-source.txt")
        self.http_strategies_path = os.path.join(self.lua_path, "strategies-http-all.txt")

        # UDP стратегии (QUIC)
        self.udp_strategies_source_path = os.path.join(self.lua_path, "strategies-udp-source.txt")
        self.udp_strategies_path = os.path.join(self.lua_path, "strategies-udp-all.txt")

        # Discord Voice / STUN стратегии
        self.discord_strategies_source_path = os.path.join(self.lua_path, "strategies-discord-source.txt")
        self.discord_strategies_path = os.path.join(self.lua_path, "strategies-discord-all.txt")

        # Белый список (exclude hostlist)
        self.whitelist_path = os.path.join(self.lua_path, "whitelist.txt")

        # Debug log от winws2 (для детекции LOCKED/UNLOCKING)
        # Теперь используем уникальные имена с ID сессии
        self.current_log_id: Optional[str] = None
        self.debug_log_path: Optional[str] = None
        # Загружаем настройку сохранения debug файла из реестра
        saved_debug = reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile")
        self.keep_debug_file = bool(saved_debug)

        # Состояние
        self.running_process: Optional[subprocess.Popen] = None
        self.output_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Обученные стратегии (TLS, HTTP, UDP отдельно)
        self.locked_strategies: Dict[str, int] = {}      # TLS (tls_client_hello)
        self.http_locked_strategies: Dict[str, int] = {}  # HTTP (http)
        self.udp_locked_strategies: Dict[str, int] = {}   # UDP (QUIC, games)

        # История стратегий: {hostname: {strategy: {successes: N, failures: N}}}
        self.strategy_history: Dict[str, Dict[str, Dict[str, int]]] = {}

        # Пользовательский белый список (из реестра)
        self.user_whitelist: list = []

        # Callbacks
        self.output_callback: Optional[Callable[[str], None]] = None
        self.lock_callback: Optional[Callable[[str, int], None]] = None
        self.unlock_callback: Optional[Callable[[str], None]] = None

    def set_keep_debug_file(self, keep: bool):
        """Сохранять ли debug файл после остановки (для отладки)"""
        self.keep_debug_file = keep
        log(f"Debug файл будет {'сохранён' if keep else 'удалён'} после остановки", "DEBUG")

    def set_output_callback(self, callback: Callable[[str], None]):
        """Callback для получения строк лога"""
        print(f"[DEBUG set_output_callback] callback={callback}")  # DEBUG
        self.output_callback = callback

    def set_lock_callback(self, callback: Callable[[str, int], None]):
        """Callback при LOCK стратегии (hostname, strategy_num)"""
        self.lock_callback = callback

    def set_unlock_callback(self, callback: Callable[[str], None]):
        """Callback при UNLOCK стратегии (hostname)"""
        self.unlock_callback = callback

    # ==================== LOG ROTATION METHODS ====================

    def _generate_log_id(self) -> str:
        """
        Генерирует уникальный ID для лог-файла.
        Формат: YYYYMMDD_HHMMSS (только timestamp для читаемости)
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _generate_log_path(self, log_id: str) -> str:
        """Генерирует путь к лог-файлу по ID"""
        return os.path.join(self.logs_path, f"orchestra_{log_id}.log")

    def _get_all_orchestra_logs(self) -> List[dict]:
        """
        Возвращает список всех лог-файлов оркестратора.

        Returns:
            Список словарей с информацией о логах, отсортированный по дате (новые первые):
            [{'id': str, 'path': str, 'size': int, 'created': datetime, 'filename': str}, ...]
        """
        logs = []
        pattern = os.path.join(self.logs_path, "orchestra_*.log")

        for filepath in glob.glob(pattern):
            try:
                filename = os.path.basename(filepath)
                # Извлекаем ID из имени файла (orchestra_YYYYMMDD_HHMMSS_XXXX.log)
                log_id = filename.replace("orchestra_", "").replace(".log", "")

                stat = os.stat(filepath)

                # Парсим дату из ID (YYYYMMDD_HHMMSS)
                try:
                    created = datetime.strptime(log_id, "%Y%m%d_%H%M%S")
                except ValueError:
                    created = datetime.fromtimestamp(stat.st_mtime)

                logs.append({
                    'id': log_id,
                    'path': filepath,
                    'filename': filename,
                    'size': stat.st_size,
                    'created': created
                })
            except Exception as e:
                log(f"Ошибка чтения лог-файла {filepath}: {e}", "DEBUG")

        # Сортируем по дате создания (новые первые)
        logs.sort(key=lambda x: x['created'], reverse=True)
        return logs

    def _cleanup_old_logs(self) -> int:
        """
        Удаляет старые лог-файлы, оставляя только MAX_ORCHESTRA_LOGS штук.

        Returns:
            Количество удалённых файлов
        """
        logs = self._get_all_orchestra_logs()
        deleted = 0

        if len(logs) > MAX_ORCHESTRA_LOGS:
            # Удаляем самые старые (они в конце списка)
            logs_to_delete = logs[MAX_ORCHESTRA_LOGS:]

            for log_info in logs_to_delete:
                try:
                    os.remove(log_info['path'])
                    deleted += 1
                    log(f"Удалён старый лог: {log_info['filename']}", "DEBUG")
                except Exception as e:
                    log(f"Ошибка удаления лога {log_info['filename']}: {e}", "DEBUG")

        if deleted:
            log(f"Ротация логов оркестратора: удалено {deleted} файлов", "INFO")

        return deleted

    def get_log_history(self) -> List[dict]:
        """
        Возвращает историю логов для UI.

        Returns:
            Список словарей с информацией о логах (без полного пути)
        """
        logs = self._get_all_orchestra_logs()
        return [{
            'id': l['id'],
            'filename': l['filename'],
            'size': l['size'],
            'size_str': self._format_size(l['size']),
            'created': l['created'].strftime("%Y-%m-%d %H:%M:%S"),
            'is_current': l['id'] == self.current_log_id
        } for l in logs]

    def _format_size(self, size: int) -> str:
        """Форматирует размер файла в человекочитаемый вид"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def get_log_content(self, log_id: str) -> Optional[str]:
        """
        Возвращает содержимое лог-файла по ID.

        Args:
            log_id: ID лога

        Returns:
            Содержимое файла или None
        """
        log_path = self._generate_log_path(log_id)
        if not os.path.exists(log_path):
            return None

        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            log(f"Ошибка чтения лога {log_id}: {e}", "DEBUG")
            return None

    def delete_log(self, log_id: str) -> bool:
        """
        Удаляет лог-файл по ID.

        Args:
            log_id: ID лога

        Returns:
            True если удаление успешно
        """
        # Нельзя удалить текущий активный лог
        if log_id == self.current_log_id and self.is_running():
            log(f"Нельзя удалить активный лог: {log_id}", "WARNING")
            return False

        log_path = self._generate_log_path(log_id)
        if not os.path.exists(log_path):
            return False

        try:
            os.remove(log_path)
            log(f"Удалён лог: orchestra_{log_id}.log", "INFO")
            return True
        except Exception as e:
            log(f"Ошибка удаления лога {log_id}: {e}", "ERROR")
            return False

    def clear_all_logs(self) -> int:
        """
        Удаляет все лог-файлы оркестратора (кроме текущего активного).

        Returns:
            Количество удалённых файлов
        """
        logs = self._get_all_orchestra_logs()
        deleted = 0

        for log_info in logs:
            # Пропускаем текущий активный лог
            if log_info['id'] == self.current_log_id and self.is_running():
                continue

            try:
                os.remove(log_info['path'])
                deleted += 1
            except Exception:
                pass

        if deleted:
            log(f"Удалено {deleted} лог-файлов оркестратора", "INFO")

        return deleted

    def _create_startup_info(self):
        """Создает STARTUPINFO для скрытого запуска"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE
        return startupinfo

    def _migrate_old_registry_format(self):
        """Мигрирует старый формат (JSON в одном ключе) в новый (subkeys)"""
        try:
            # Проверяем есть ли старые данные
            old_tls = reg(REGISTRY_ORCHESTRA, "LearnedStrategies")
            old_http = reg(REGISTRY_ORCHESTRA, "LearnedStrategiesHTTP")
            old_history = reg(REGISTRY_ORCHESTRA, "StrategyHistory")

            migrated = False

            # Мигрируем TLS
            if old_tls and old_tls != "{}":
                try:
                    data = json.loads(old_tls)
                    for domain, strategy in data.items():
                        reg(REGISTRY_ORCHESTRA_TLS, domain, int(strategy))
                    reg(REGISTRY_ORCHESTRA, "LearnedStrategies", None)  # Удаляем старый ключ
                    migrated = True
                    log(f"Мигрировано {len(data)} TLS стратегий в новый формат", "INFO")
                except Exception:
                    pass

            # Мигрируем HTTP
            if old_http and old_http != "{}":
                try:
                    data = json.loads(old_http)
                    for domain, strategy in data.items():
                        reg(REGISTRY_ORCHESTRA_HTTP, domain, int(strategy))
                    reg(REGISTRY_ORCHESTRA, "LearnedStrategiesHTTP", None)  # Удаляем старый ключ
                    migrated = True
                    log(f"Мигрировано {len(data)} HTTP стратегий в новый формат", "INFO")
                except Exception:
                    pass

            # Мигрируем историю
            if old_history and old_history != "{}":
                try:
                    data = json.loads(old_history)
                    for domain, strategies in data.items():
                        json_str = json.dumps(strategies, ensure_ascii=False)
                        reg(REGISTRY_ORCHESTRA_HISTORY, domain, json_str)
                    reg(REGISTRY_ORCHESTRA, "StrategyHistory", None)  # Удаляем старый ключ
                    migrated = True
                    log(f"Мигрирована история для {len(data)} доменов в новый формат", "INFO")
                except Exception:
                    pass

            if migrated:
                log("Миграция реестра завершена", "INFO")

        except Exception as e:
            log(f"Ошибка миграции реестра: {e}", "DEBUG")

    def load_existing_strategies(self) -> Dict[str, int]:
        """Загружает ранее сохраненные стратегии и историю из реестра (subkeys)"""
        self.locked_strategies = {}
        self.http_locked_strategies = {}
        self.udp_locked_strategies = {}

        # Сначала мигрируем старый формат если есть
        self._migrate_old_registry_format()

        try:
            # TLS стратегии из REGISTRY_ORCHESTRA_TLS\{domain} = strategy
            tls_data = reg_enumerate_values(REGISTRY_ORCHESTRA_TLS)
            for domain, strategy in tls_data.items():
                self.locked_strategies[domain] = int(strategy)

            # HTTP стратегии из REGISTRY_ORCHESTRA_HTTP\{domain} = strategy
            http_data = reg_enumerate_values(REGISTRY_ORCHESTRA_HTTP)
            for domain, strategy in http_data.items():
                self.http_locked_strategies[domain] = int(strategy)

            # UDP стратегии из REGISTRY_ORCHESTRA_UDP\{ip} = strategy
            udp_data = reg_enumerate_values(REGISTRY_ORCHESTRA_UDP)
            for ip, strategy in udp_data.items():
                self.udp_locked_strategies[ip] = int(strategy)

            total = len(self.locked_strategies) + len(self.http_locked_strategies) + len(self.udp_locked_strategies)
            if total:
                log(f"Загружено {len(self.locked_strategies)} TLS + {len(self.http_locked_strategies)} HTTP + {len(self.udp_locked_strategies)} UDP стратегий", "INFO")

        except Exception as e:
            log(f"Ошибка загрузки стратегий из реестра: {e}", "DEBUG")

        # Загружаем историю
        self.load_history()

        return self.locked_strategies

    def save_strategies(self):
        """Сохраняет locked стратегии в реестр (subkeys: TLS, HTTP, UDP)"""
        try:
            # TLS стратегии - каждый домен отдельным значением
            for domain, strategy in self.locked_strategies.items():
                reg(REGISTRY_ORCHESTRA_TLS, domain, int(strategy))

            # HTTP стратегии - каждый домен отдельным значением
            for domain, strategy in self.http_locked_strategies.items():
                reg(REGISTRY_ORCHESTRA_HTTP, domain, int(strategy))

            # UDP стратегии - каждый IP отдельным значением
            for ip, strategy in self.udp_locked_strategies.items():
                reg(REGISTRY_ORCHESTRA_UDP, ip, int(strategy))

            log(f"Сохранено {len(self.locked_strategies)} TLS + {len(self.http_locked_strategies)} HTTP + {len(self.udp_locked_strategies)} UDP стратегий", "DEBUG")

        except Exception as e:
            log(f"Ошибка сохранения стратегий в реестр: {e}", "ERROR")

    def load_history(self):
        """Загружает историю стратегий из реестра (subkey: History\\{domain})"""
        self.strategy_history = {}
        try:
            # Каждый домен хранится как отдельное значение: domain = JSON
            history_data = reg_enumerate_values(REGISTRY_ORCHESTRA_HISTORY)
            for domain, json_str in history_data.items():
                try:
                    self.strategy_history[domain] = json.loads(json_str)
                except json.JSONDecodeError:
                    pass  # Пропускаем повреждённые записи

            total_domains = len(self.strategy_history)
            if total_domains:
                log(f"Загружена история для {total_domains} доменов", "DEBUG")
        except Exception as e:
            log(f"Ошибка загрузки истории: {e}", "DEBUG")
            self.strategy_history = {}

    def save_history(self):
        """Сохраняет историю стратегий в реестр (subkey: History\\{domain})"""
        try:
            # Каждый домен сохраняется как отдельное значение
            for domain, strategies in self.strategy_history.items():
                json_str = json.dumps(strategies, ensure_ascii=False)
                reg(REGISTRY_ORCHESTRA_HISTORY, domain, json_str)
            log(f"Сохранена история для {len(self.strategy_history)} доменов", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения истории: {e}", "ERROR")

    def update_history(self, hostname: str, strategy: int, successes: int, failures: int):
        """Обновляет историю для домена/стратегии (полная замена значений)"""
        if hostname not in self.strategy_history:
            self.strategy_history[hostname] = {}

        strat_key = str(strategy)
        self.strategy_history[hostname][strat_key] = {
            'successes': successes,
            'failures': failures
        }

    def _increment_history(self, hostname: str, strategy: int, is_success: bool):
        """Инкрементирует счётчик успехов или неудач для домена/стратегии"""
        if hostname not in self.strategy_history:
            self.strategy_history[hostname] = {}

        strat_key = str(strategy)
        if strat_key not in self.strategy_history[hostname]:
            self.strategy_history[hostname][strat_key] = {'successes': 0, 'failures': 0}

        if is_success:
            self.strategy_history[hostname][strat_key]['successes'] += 1
        else:
            self.strategy_history[hostname][strat_key]['failures'] += 1

    def get_history_for_domain(self, hostname: str) -> dict:
        """Возвращает историю стратегий для домена с рейтингами"""
        if hostname not in self.strategy_history:
            return {}

        result = {}
        for strat_key, data in self.strategy_history[hostname].items():
            s = data.get('successes', 0)
            f = data.get('failures', 0)
            total = s + f
            rate = int((s / total) * 100) if total > 0 else 0
            result[int(strat_key)] = {
                'successes': s,
                'failures': f,
                'rate': rate
            }
        return result

    def _generate_learned_lua(self) -> Optional[str]:
        """
        Генерирует learned-strategies.lua для предзагрузки в strategy-stats.lua.
        Вызывает strategy_preload() и strategy_preload_history() для каждого домена.

        Returns:
            Путь к файлу или None если нет данных
        """
        has_tls = bool(self.locked_strategies)
        has_http = bool(self.http_locked_strategies)
        has_udp = bool(self.udp_locked_strategies)
        has_history = bool(self.strategy_history)

        if not has_tls and not has_http and not has_udp and not has_history:
            return None

        lua_path = os.path.join(self.lua_path, "learned-strategies.lua")
        total_tls = len(self.locked_strategies)
        total_http = len(self.http_locked_strategies)
        total_udp = len(self.udp_locked_strategies)
        total_history = len(self.strategy_history)

        try:
            with open(lua_path, 'w', encoding='utf-8') as f:
                f.write("-- Auto-generated: preload strategies from registry\n")
                f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- TLS: {total_tls}, HTTP: {total_http}, UDP: {total_udp}, History: {total_history}\n\n")

                # Предзагрузка TLS стратегий
                for hostname, strategy in self.locked_strategies.items():
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_host}", {strategy}, "tls")\n')

                # Предзагрузка HTTP стратегий
                for hostname, strategy in self.http_locked_strategies.items():
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_host}", {strategy}, "http")\n')

                # Предзагрузка UDP стратегий
                for ip, strategy in self.udp_locked_strategies.items():
                    safe_ip = ip.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_ip}", {strategy}, "udp")\n')

                # Предзагрузка истории
                for hostname, strategies in self.strategy_history.items():
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    for strat_key, data in strategies.items():
                        s = data.get('successes', 0)
                        f_count = data.get('failures', 0)
                        f.write(f'strategy_preload_history("{safe_host}", {strat_key}, {s}, {f_count})\n')

                f.write(f'\nDLOG("learned-strategies: loaded {total_tls} TLS + {total_http} HTTP + {total_udp} UDP + {total_history} history")\n')

                # Install circular wrapper to apply preloaded strategies
                f.write('\n-- Install circular wrapper to apply preloaded strategies on first packet\n')
                f.write('install_circular_wrapper()\n')

            log(f"Сгенерирован learned-strategies.lua ({total_tls} TLS + {total_http} HTTP + {total_udp} UDP + {total_history} history)", "DEBUG")
            return lua_path

        except Exception as e:
            log(f"Ошибка генерации learned-strategies.lua: {e}", "ERROR")
            return None

    def _generate_single_numbered_file(self, source_path: str, output_path: str, name: str) -> int:
        """
        Генерирует один файл стратегий с автоматической нумерацией.

        Returns:
            Количество стратегий или -1 при ошибке
        """
        if not os.path.exists(source_path):
            log(f"Исходные стратегии не найдены: {source_path}", "ERROR")
            return -1

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            strategy_num = 0
            numbered_lines = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('--lua-desync='):
                    strategy_num += 1
                    numbered_lines.append(f"{line}:strategy={strategy_num}")
                else:
                    numbered_lines.append(line)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(numbered_lines) + '\n')

            log(f"Сгенерировано {strategy_num} {name} стратегий", "DEBUG")
            return strategy_num

        except Exception as e:
            log(f"Ошибка генерации {name} стратегий: {e}", "ERROR")
            return -1

    def _generate_numbered_strategies(self) -> bool:
        """
        Генерирует strategies-all.txt, strategies-http-all.txt и strategies-udp-all.txt с автоматической нумерацией.

        Returns:
            True если генерация успешна
        """
        # TLS стратегии (обязательные)
        tls_count = self._generate_single_numbered_file(
            self.strategies_source_path,
            self.strategies_path,
            "TLS"
        )
        if tls_count < 0:
            return False

        # HTTP стратегии (опциональные)
        if os.path.exists(self.http_strategies_source_path):
            http_count = self._generate_single_numbered_file(
                self.http_strategies_source_path,
                self.http_strategies_path,
                "HTTP"
            )
            if http_count < 0:
                log("HTTP стратегии не сгенерированы, продолжаем без них", "WARNING")
        else:
            log("HTTP source не найден, пропускаем", "DEBUG")

        # UDP стратегии (опциональные - для QUIC)
        if os.path.exists(self.udp_strategies_source_path):
            udp_count = self._generate_single_numbered_file(
                self.udp_strategies_source_path,
                self.udp_strategies_path,
                "UDP"
            )
            if udp_count < 0:
                log("UDP стратегии не сгенерированы, продолжаем без них", "WARNING")
        else:
            log("UDP source не найден, пропускаем", "DEBUG")

        # Discord Voice / STUN стратегии (опциональные)
        if os.path.exists(self.discord_strategies_source_path):
            discord_count = self._generate_single_numbered_file(
                self.discord_strategies_source_path,
                self.discord_strategies_path,
                "Discord"
            )
            if discord_count < 0:
                log("Discord стратегии не сгенерированы, продолжаем без них", "WARNING")
        else:
            log("Discord source не найден, пропускаем", "DEBUG")

        return True

    def _read_output(self):
        """Поток чтения stdout от winws2 (debug=1 выводит в консоль)"""
        # === Паттерны для strategy-stats.lua (кастомные события) ===
        lock_pattern = re.compile(r"LOCKED (\S+) to strategy=(\d+)(?:\s+\[(TLS|HTTP|UDP)\])?")
        unlock_pattern = re.compile(r"UNLOCKING (\S+)(?:\s+\[(TLS|HTTP|UDP)\])?")
        sticky_pattern = re.compile(r"STICKY (\S+) to strategy=(\d+)")
        preload_pattern = re.compile(r"PRELOADED (\S+) = strategy (\d+)(?:\s+\[(tls|http|udp)\])?")
        history_pattern = re.compile(r"HISTORY (\S+) strategy=(\d+) successes=(\d+) failures=(\d+) rate=(\d+)%")
        success_pattern = re.compile(r"strategy-stats: SUCCESS (\S+) strategy=(\d+).*?\[(TLS|HTTP|UDP)\]")
        fail_pattern = re.compile(r"strategy-stats: FAIL (\S+) strategy=(\d+).*?\[(TLS|HTTP|UDP)\]")
        unsticky_pattern = re.compile(r"strategy-stats: UNSTICKY (\S+)(?:\s+\[(TLS|HTTP|UDP)\])?")

        # === Паттерны для стандартных детекторов zapret2 ===
        # automate: success detected / automate: failure detected
        automate_success_pattern = re.compile(r"automate: success detected")
        automate_failure_pattern = re.compile(r"automate: failure detected")
        # circular: rotate strategy to N
        rotate_pattern = re.compile(r"circular: rotate strategy to (\d+)")
        # circular: current strategy N
        current_strategy_pattern = re.compile(r"circular: current strategy (\d+)")
        # standard_failure_detector: incoming RST
        std_rst_pattern = re.compile(r"standard_failure_detector: incoming RST")
        # standard_failure_detector: retransmission N/M
        std_retrans_pattern = re.compile(r"standard_failure_detector: retransmission (\d+)/(\d+)")
        # standard_success_detector: treating connection as successful
        std_success_pattern = re.compile(r"standard_success_detector:.*successful")

        # === Паттерн для hostname из desync profile search ===
        # TCP: desync profile search for tcp ip=... port=443 l7proto=tls ssid='' hostname='youtube.com'
        # UDP: desync profile search for udp ip=... port=443 l7proto=quic/stun/discord/wireguard/unknown
        # Формат из desync.c: proto_name(l3proto) = tcp/udp, l7proto_str() = unknown/quic/stun/discord/wireguard/dht/etc
        hostname_pattern = re.compile(r"desync profile search for tcp ip=[\d.:]+ port=(\d+) l7proto=\S+ ssid='[^']*' hostname='([^']+)'")
        # UDP всегда имеет l7proto (unknown/quic/stun/discord/wireguard/dht), поддержка IPv4 и IPv6
        udp_pattern = re.compile(r"desync profile search for udp ip=([\d.:a-fA-F]+) port=(\d+) l7proto=(\S+)")

        # === Альтернативный паттерн для UDP (client mode) ===
        # Profile 3/4 используют другой формат логов:
        # client mode desync profile/ipcache search target ip=34.0.240.240 port=50008
        # desync profile 3 (noname) matches  <-- определяем профиль
        # dpi desync src=34.0.240.240:50008 dst=192.168.1.100:57972 ... connection_proto=discord
        client_mode_ip_pattern = re.compile(r"client mode desync profile/ipcache search target ip=([\d.:a-fA-F]+) port=(\d+)")
        # "desync profile N (name) matches" - номер профиля (3 или 4 = UDP)
        desync_profile_pattern = re.compile(r"desync profile (\d+) \(\S+\) matches")
        # Извлекаем src, dst и connection_proto - выбираем не-локальный IP
        dpi_desync_udp_pattern = re.compile(r"dpi desync src=([\d.:a-fA-F]+):\d+ dst=([\d.:a-fA-F]+):\d+ .* connection_proto=(\S+)")

        # Переменная для текущего протокола (80=HTTP, 443=TLS, udp=UDP)
        current_port = None
        current_proto = "tcp"  # tcp или udp
        current_l7proto = None  # quic, stun, discord, wireguard (для UDP)
        current_profile = 0  # номер профиля (3 или 4 = UDP)

        # Для отслеживания текущего хоста/IP и стратегии
        current_host = None
        current_strat = 1

        # Счётчик для периодического сохранения истории
        history_save_counter = 0

        # Открываем файл для записи сырого debug лога (для отправки в техподдержку)
        log_file = None
        if self.debug_log_path:
            try:
                log_file = open(self.debug_log_path, 'w', encoding='utf-8', buffering=1)  # line buffered
                log_file.write(f"=== Orchestra Debug Log Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            except Exception as e:
                log(f"Не удалось открыть лог-файл: {e}", "WARNING")

        if self.running_process and self.running_process.stdout:
            try:
                for line in self.running_process.stdout:
                    if self.stop_event.is_set():
                        break

                    line = line.rstrip()
                    if not line:
                        continue

                    # Отслеживаем текущий hostname из desync profile search
                    # TCP: desync profile search for tcp ip=... port=443 l7proto=tls hostname='youtube.com'
                    match = hostname_pattern.search(line)
                    if match:
                        current_port, hostname = match.groups()
                        current_proto = "tcp"
                        # Игнорируем пустые hostname и IP-адреса
                        if hostname and not hostname.replace('.', '').isdigit():
                            # Применяем NLD-cut для группировки поддоменов
                            current_host = nld_cut(hostname, 2)
                        continue

                    # UDP: desync profile search for udp ip=1.2.3.4 port=443 l7proto=quic/stun/discord/wireguard
                    match = udp_pattern.search(line)
                    if match:
                        ip = match.group(1)
                        current_port = match.group(2)
                        l7proto = match.group(3)  # unknown, quic, stun, discord, wireguard, dht
                        current_proto = "udp"
                        current_l7proto = l7proto  # Сохраняем для LOCKED/UNLOCK
                        # Пропускаем локальные IP адреса
                        if ip.startswith(LOCAL_IP_PREFIXES):
                            current_host = None
                        else:
                            current_host = ip  # Для UDP используем IP напрямую
                        continue

                    # === Альтернативный паттерн для UDP (client mode / Profile 3,4) ===
                    # client mode desync profile/ipcache search target ip=34.0.240.240 port=50008
                    match = client_mode_ip_pattern.search(line)
                    if match:
                        ip = match.group(1)
                        current_port = match.group(2)
                        # Пока не знаем протокол, он будет в следующей строке dpi desync
                        # НЕ устанавливаем current_host сразу - ждём dpi desync строку
                        # current_l7proto будет установлен из dpi desync
                        continue

                    # "desync profile 3 (noname) matches" - определяем профиль (3 или 4 = UDP)
                    match = desync_profile_pattern.search(line)
                    if match:
                        current_profile = int(match.group(1))
                        continue

                    # dpi desync src=34.0.240.240:50008 dst=192.168.1.100:57972 ... connection_proto=discord
                    # Извлекаем src, dst и connection_proto - выбираем удалённый (не-локальный) IP
                    # Только для UDP профилей (3 = STUN/Discord, 4 = QUIC/DHT)
                    match = dpi_desync_udp_pattern.search(line)
                    if match and current_profile in (3, 4):
                        src_ip = match.group(1)
                        dst_ip = match.group(2)
                        connection_proto = match.group(3)  # discord, stun, wireguard, unknown
                        # Выбираем удалённый IP (не локальный)
                        if src_ip.startswith(LOCAL_IP_PREFIXES):
                            remote_ip = dst_ip
                        elif dst_ip.startswith(LOCAL_IP_PREFIXES):
                            remote_ip = src_ip
                        else:
                            # Оба не-локальные - берём src (обычно это сервер для incoming)
                            remote_ip = src_ip
                        # Пропускаем если удалённый IP тоже локальный
                        if not remote_ip.startswith(LOCAL_IP_PREFIXES):
                            current_proto = "udp"
                            current_l7proto = connection_proto  # discord, stun, etc.
                            current_host = remote_ip  # Для UDP используем IP напрямую
                        continue

                    # Записываем каждую строку в файл лога
                    if log_file:
                        try:
                            log_file.write(f"{line}\n")
                        except Exception:
                            pass

                    # Проверяем LOCKED
                    match = lock_pattern.search(line)
                    if match:
                        host, strat, ptype = match.groups()
                        strat = int(strat)

                        # Определяем протокол: сначала из тега [TLS/HTTP/UDP], потом из current_proto
                        if ptype:
                            ptype_upper = ptype.upper()
                            is_http = (ptype_upper == "HTTP")
                            is_udp = (ptype_upper == "UDP")
                        else:
                            # Если тег не указан - определяем по current_proto
                            is_udp = (current_proto == "udp")
                            is_http = (current_proto == "tcp" and current_port == "80")

                        # Для UDP: конвертируем IP в /16 подсеть
                        # Для TCP: применяем NLD-cut (googlevideo.com и т.д.)
                        if is_udp:
                            original_host = host
                            host = ip_to_subnet16(host)
                            if host != original_host:
                                log(f"UDP /16: {original_host} -> {host}", "DEBUG")
                        else:
                            host = nld_cut(host, 2)

                        # Пропускаем локальные IP для UDP
                        if is_udp and host.startswith(LOCAL_IP_PREFIXES):
                            continue

                        # Выбираем словарь: UDP, HTTP или TLS
                        if is_udp:
                            target_dict = self.udp_locked_strategies
                            # Определяем тип UDP протокола для отображения
                            if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                port_str = f" {current_l7proto.upper()}"
                            else:
                                port_str = " UDP"  # unknown и другие
                        elif is_http:
                            target_dict = self.http_locked_strategies
                            port_str = ":80"
                        else:
                            target_dict = self.locked_strategies
                            port_str = ":443"

                        if host not in target_dict or target_dict[host] != strat:
                            target_dict[host] = strat
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            msg = f"[{timestamp}] 🔒 LOCKED: {host}{port_str} = strategy {strat}"
                            log(msg, "INFO")
                            if self.output_callback:
                                self.output_callback(msg)
                            if self.lock_callback:
                                self.lock_callback(host, strat)
                            self.save_strategies()
                        continue

                    # Проверяем UNLOCKING
                    match = unlock_pattern.search(line)
                    if match:
                        host = match.group(1)
                        ptype = match.group(2) if len(match.groups()) > 1 else None

                        # Определяем протокол: сначала из тега, потом из current_proto
                        if ptype:
                            ptype_upper = ptype.upper()
                            is_http = (ptype_upper == "HTTP")
                            is_udp = (ptype_upper == "UDP")
                        else:
                            is_udp = (current_proto == "udp")
                            is_http = (current_proto == "tcp" and current_port == "80")

                        # Для UDP: конвертируем IP в /16 подсеть
                        # Для TCP: применяем NLD-cut (googlevideo.com и т.д.)
                        if is_udp:
                            host = ip_to_subnet16(host)
                        else:
                            host = nld_cut(host, 2)

                        # Выбираем словарь: UDP, HTTP или TLS
                        if is_udp:
                            target_dict = self.udp_locked_strategies
                            # Определяем тип UDP протокола для отображения
                            if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                port_str = f" {current_l7proto.upper()}"
                            else:
                                port_str = " UDP"  # unknown и другие
                        elif is_http:
                            target_dict = self.http_locked_strategies
                            port_str = ":80"
                        else:
                            target_dict = self.locked_strategies
                            port_str = ":443"

                        if host in target_dict:
                            del target_dict[host]
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            msg = f"[{timestamp}] 🔓 UNLOCKED: {host}{port_str} - re-learning..."
                            log(msg, "INFO")
                            if self.output_callback:
                                self.output_callback(msg)
                            if self.unlock_callback:
                                self.unlock_callback(host)
                            self.save_strategies()
                        continue

                    # Проверяем STICKY (первый успех - фиксация без полного LOCK)
                    match = sticky_pattern.search(line)
                    if match:
                        host, strat = match.groups()
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] STICKY: {host} → strategy {strat}"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # Проверяем PRELOADED (загрузка из файла при старте)
                    match = preload_pattern.search(line)
                    if match:
                        host = match.group(1)
                        strat = match.group(2)
                        ptype = match.group(3)  # tls или http (может быть None)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        ptype_str = f" [{ptype}]" if ptype else ""
                        msg = f"[{timestamp}] PRELOADED: {host} = strategy {strat}{ptype_str}"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # Проверяем HISTORY (статистика стратегий)
                    match = history_pattern.search(line)
                    if match:
                        host, strat, successes, failures, rate = match.groups()
                        # Применяем NLD-cut для группировки
                        host = nld_cut(host, 2)
                        strat = int(strat)
                        successes = int(successes)
                        failures = int(failures)
                        rate = int(rate)

                        # Обновляем историю
                        self.update_history(host, strat, successes, failures)

                        # Логируем с рейтингом
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] HISTORY: {host} strat={strat} ({successes}✓/{failures}✗) = {rate}%"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем историю периодически
                        self.save_history()
                        continue

                    # Проверяем SUCCESS - обновляем историю в реальном времени
                    match = success_pattern.search(line)
                    if match:
                        host, strat, ptype = match.groups()
                        # Применяем NLD-cut для группировки
                        host = nld_cut(host, 2)
                        strat = int(strat)
                        self._increment_history(host, strat, is_success=True)
                        history_save_counter += 1

                        # Выводим в UI с портом (HTTP=80, TLS=443)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        port = "80" if ptype == "HTTP" else "443"
                        msg = f"[{timestamp}] ✓ SUCCESS: {host} :{port} strategy={strat}"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем каждые 5 событий
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue

                    # Проверяем FAIL - обновляем историю в реальном времени
                    match = fail_pattern.search(line)
                    if match:
                        host, strat, ptype = match.groups()
                        is_udp = (ptype == "UDP")
                        # Для UDP: конвертируем IP в /16 подсеть
                        # Для TCP: применяем NLD-cut для группировки
                        if is_udp:
                            host = ip_to_subnet16(host)
                        else:
                            host = nld_cut(host, 2)
                        strat = int(strat)
                        self._increment_history(host, strat, is_success=False)
                        history_save_counter += 1

                        # Выводим в UI с портом (HTTP=80, TLS=443, UDP)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if is_udp:
                            port = "UDP"
                        elif ptype == "HTTP":
                            port = "80"
                        else:
                            port = "443"
                        msg = f"[{timestamp}] ✗ FAIL: {host} :{port} strategy={strat}"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем каждые 5 событий
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue

                    # Проверяем успех от стандартного детектора (TCP) или automate (UDP)
                    # TCP: "standard_success_detector:.*successful"
                    # UDP: "automate: success detected"
                    if std_success_pattern.search(line) or automate_success_pattern.search(line):
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        # Записываем success в историю если знаем хост и стратегию
                        if current_host and current_strat:
                            is_udp = (current_proto == "udp")
                            is_http = (current_proto == "tcp" and current_port == "80")

                            # Для UDP: конвертируем IP в /16 подсеть для группировки
                            # Для TCP: применяем NLD-cut
                            if is_udp:
                                lock_host = ip_to_subnet16(current_host)
                            else:
                                lock_host = nld_cut(current_host, 2)

                            self._increment_history(lock_host, current_strat, is_success=True)
                            history_save_counter += 1

                            # Считаем количество успехов для LOCK
                            host_key = f"{lock_host}:{current_strat}"
                            if not hasattr(self, '_success_counts'):
                                self._success_counts = {}
                            self._success_counts[host_key] = self._success_counts.get(host_key, 0) + 1

                            # LOCK: UDP/STUN сразу после 1 успеха, TCP после 3 успехов
                            # UDP соединения короткие, нужно запоминать быстро
                            lock_threshold = 1 if is_udp else 3
                            if self._success_counts[host_key] >= lock_threshold:
                                # Выбираем правильный словарь: UDP, HTTP или TLS
                                if is_udp:
                                    target_dict = self.udp_locked_strategies
                                elif is_http:
                                    target_dict = self.http_locked_strategies
                                else:
                                    target_dict = self.locked_strategies

                                if lock_host not in target_dict:
                                    target_dict[lock_host] = current_strat
                                    # Определяем тип для лога
                                    if is_udp:
                                        if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                            port_str = f" {current_l7proto.upper()}"
                                        else:
                                            port_str = " UDP"
                                    elif is_http:
                                        port_str = ":80"
                                    else:
                                        port_str = ":443"
                                    msg = f"[{timestamp}] 🔒 LOCKED: {lock_host}{port_str} = strategy {current_strat}"
                                    log(msg, "INFO")
                                    if self.output_callback:
                                        self.output_callback(msg)
                                    # Сохраняем стратегии и историю в реестр
                                    self.save_strategies()
                                    self.save_history()
                                    history_save_counter = 0  # Сбрасываем счётчик т.к. только что сохранили

                            # Определяем тип для лога SUCCESS
                            if is_udp:
                                if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                    port_str = f" {current_l7proto.upper()}"
                                else:
                                    port_str = " UDP"
                            elif is_http:
                                port_str = " :80"
                            else:
                                port_str = " :443"
                            msg = f"[{timestamp}] ✓ SUCCESS: {current_host}{port_str} strategy={current_strat}"
                            if self.output_callback:
                                self.output_callback(msg)
                        # Не показываем "Connection successful" без хоста - это спам

                        # Сохраняем периодически
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue
                    
                    # Проверяем RST от стандартного детектора
                    if std_rst_pattern.search(line):
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] ⚡ RST detected - DPI block"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # DUPLICATE REMOVED: std_success_pattern handler was here
                    # The correct handler is at lines 877-914 which saves to registry

                    # Проверяем ротацию стратегии - показываем только если есть хост
                    match = rotate_pattern.search(line)
                    if match and current_host:
                        new_strat = match.group(1)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] 🔄 Strategy rotated to {new_strat} ({current_host})"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # Отслеживаем текущую стратегию
                    match = current_strategy_pattern.search(line)
                    if match:
                        current_strat = int(match.group(1))
                        continue

                    # Проверяем UNSTICKY - стратегия сфейлилась после первого успеха
                    match = unsticky_pattern.search(line)
                    if match:
                        host = match.group(1)
                        ptype = match.group(2) if match.lastindex >= 2 else None
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        # Определяем тип протокола
                        if ptype:
                            ptype_upper = ptype.upper()
                            if ptype_upper == "UDP":
                                if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                    port_str = f" {current_l7proto.upper()}"
                                else:
                                    port_str = " UDP"
                            elif ptype_upper == "HTTP":
                                port_str = " :80"
                            else:
                                port_str = " :443"
                        else:
                            # По current_proto
                            if current_proto == "udp":
                                if current_l7proto and current_l7proto.lower() in ('stun', 'discord', 'wireguard', 'quic', 'dht'):
                                    port_str = f" {current_l7proto.upper()}"
                                else:
                                    port_str = " UDP"
                            elif current_port == "80":
                                port_str = " :80"
                            else:
                                port_str = " :443"
                        msg = f"[{timestamp}] 🔀 UNSTICKY: {host}{port_str} - resuming rotation"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # НЕ выводим сырые логи winws2 - только обработанные события выше
                    pass

            except Exception as e:
                import traceback
                log(f"Read output error: {e}", "DEBUG")
                log(f"Traceback: {traceback.format_exc()}", "DEBUG")
            finally:
                # Закрываем лог-файл
                if log_file:
                    try:
                        log_file.write(f"=== Orchestra Debug Log Ended {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                        log_file.close()
                    except Exception:
                        pass
                # Сохраняем историю при завершении
                if self.strategy_history:
                    self.save_history()

    def prepare(self) -> bool:
        """
        Проверяет наличие всех необходимых файлов.

        Returns:
            True если все файлы на месте
        """
        # Проверяем winws2.exe
        if not os.path.exists(self.winws_exe):
            log(f"winws2.exe не найден: {self.winws_exe}", "ERROR")
            return False

        # Проверяем Lua файлы
        required_lua_files = [
            "zapret-lib.lua",
            "zapret-antidpi.lua",
            "zapret-auto.lua",
            "silent-drop-detector.lua",
            "strategy-stats.lua",
            "combined-detector.lua",
        ]

        missing = []
        for lua_file in required_lua_files:
            path = os.path.join(self.lua_path, lua_file)
            if not os.path.exists(path):
                missing.append(lua_file)

        if missing:
            log(f"Отсутствуют Lua файлы: {', '.join(missing)}", "ERROR")
            return False

        if not os.path.exists(self.config_path):
            log(f"Конфиг не найден: {self.config_path}", "ERROR")
            return False

        # Генерируем strategies-all.txt с автоматической нумерацией
        if not self._generate_numbered_strategies():
            return False

        # Генерируем whitelist.txt
        self._generate_whitelist_file()

        log("Оркестратор готов к запуску", "INFO")
        return True

    def start(self) -> bool:
        """
        Запускает оркестратор.

        Returns:
            True если запуск успешен
        """
        if self.is_running():
            log("Оркестратор уже запущен", "WARNING")
            return False

        if not self.prepare():
            return False

        # Загружаем предыдущие стратегии и историю из реестра
        self.load_existing_strategies()

        # Инициализируем счётчики успехов из истории
        # Для доменов которые уже в locked - не важно (не будет повторного LOCK)
        # Для доменов в истории но не locked - продолжаем с сохранённого значения
        self._success_counts = {}
        for hostname, strategies in self.strategy_history.items():
            for strat_key, data in strategies.items():
                successes = data.get('successes', 0)
                if successes > 0:
                    host_key = f"{hostname}:{strat_key}"
                    self._success_counts[host_key] = successes

        # Логируем загруженные данные
        total_locked = len(self.locked_strategies) + len(self.http_locked_strategies) + len(self.udp_locked_strategies)
        total_history = len(self.strategy_history)
        if total_locked or total_history:
            log(f"Загружено из реестра: {len(self.locked_strategies)} TLS + {len(self.http_locked_strategies)} HTTP + {len(self.udp_locked_strategies)} UDP стратегий, история для {total_history} доменов", "INFO")

        # Генерируем уникальный ID для этой сессии логов
        self.current_log_id = self._generate_log_id()
        self.debug_log_path = self._generate_log_path(self.current_log_id)
        log(f"Создан лог-файл: orchestra_{self.current_log_id}.log", "DEBUG")

        # Выполняем ротацию старых логов
        self._cleanup_old_logs()

        # Сбрасываем stop event
        self.stop_event.clear()

        # Генерируем learned-strategies.lua для предзагрузки в strategy-stats.lua
        learned_lua = self._generate_learned_lua()

        try:
            # Запускаем winws2 с @config_file
            cmd = [self.winws_exe, f"@{self.config_path}"]

            # Добавляем предзагрузку стратегий из реестра
            if learned_lua:
                cmd.append(f"--lua-init=@{learned_lua}")

            # Debug: выводим в stdout для парсинга, записываем в файл вручную в _read_output
            cmd.append("--debug=1")

            log_msg = f"Запуск: winws2.exe @{os.path.basename(self.config_path)}"
            if total_locked:
                log_msg += f" ({total_locked} стратегий из реестра)"
            log(log_msg, "INFO")

            self.running_process = subprocess.Popen(
                cmd,
                cwd=self.zapret_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=self._create_startup_info(),
                creationflags=CREATE_NO_WINDOW,
                text=True,
                bufsize=1
            )

            # Чтение stdout (парсим LOCKED/UNLOCKING для UI)
            self.output_thread = threading.Thread(target=self._read_output, daemon=True)
            self.output_thread.start()

            log(f"Оркестратор запущен (PID: {self.running_process.pid})", "INFO")

            print(f"[DEBUG start] output_callback={self.output_callback}")  # DEBUG
            if self.output_callback:
                print("[DEBUG start] calling output_callback...")  # DEBUG
                self.output_callback(f"[INFO] Оркестратор запущен (PID: {self.running_process.pid})")
                self.output_callback(f"[INFO] Лог сессии: {self.current_log_id}")
                if self.locked_strategies:
                    self.output_callback(f"[INFO] Загружено {len(self.locked_strategies)} стратегий")

            return True

        except Exception as e:
            log(f"Ошибка запуска оркестратора: {e}", "ERROR")
            return False

    def stop(self) -> bool:
        """
        Останавливает оркестратор.

        Returns:
            True если остановка успешна
        """
        if not self.is_running():
            log("Оркестратор не запущен", "DEBUG")
            return True

        try:
            self.stop_event.set()

            self.running_process.terminate()
            try:
                self.running_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.running_process.kill()
                self.running_process.wait()

            # Сохраняем стратегии и историю
            self.save_strategies()
            self.save_history()

            # Лог оркестратора всегда сохраняется (для отправки в техподдержку)
            # Ротация старых логов выполняется при следующем запуске (_cleanup_old_logs)

            log(f"Оркестратор остановлен. Сохранено {len(self.locked_strategies)} стратегий, история для {len(self.strategy_history)} доменов", "INFO")
            if self.current_log_id:
                log(f"Лог сессии сохранён: orchestra_{self.current_log_id}.log", "DEBUG")

            if self.output_callback:
                self.output_callback(f"[INFO] Оркестратор остановлен")
                if self.current_log_id:
                    self.output_callback(f"[INFO] Лог сохранён: {self.current_log_id}")

            # Сбрасываем ID текущего лога
            self.current_log_id = None
            self.running_process = None
            return True

        except Exception as e:
            log(f"Ошибка остановки оркестратора: {e}", "ERROR")
            return False

    def is_running(self) -> bool:
        """Проверяет, запущен ли оркестратор"""
        if self.running_process is None:
            return False
        return self.running_process.poll() is None

    def get_pid(self) -> Optional[int]:
        """Возвращает PID процесса или None"""
        if self.running_process is not None:
            return self.running_process.pid
        return None

    def get_locked_strategies(self) -> Dict[str, int]:
        """Возвращает словарь locked стратегий {hostname: strategy_num}"""
        return self.locked_strategies.copy()

    def clear_learned_data(self) -> bool:
        """
        Очищает данные обучения для переобучения с нуля (TLS, HTTP, UDP и история).

        Returns:
            True если очистка успешна
        """
        try:
            # Очищаем subkeys (удаляем все значения в каждом)
            reg_delete_all_values(REGISTRY_ORCHESTRA_TLS)
            reg_delete_all_values(REGISTRY_ORCHESTRA_HTTP)
            reg_delete_all_values(REGISTRY_ORCHESTRA_UDP)
            reg_delete_all_values(REGISTRY_ORCHESTRA_HISTORY)
            log("Очищены обученные стратегии и история в реестре", "INFO")

            self.locked_strategies = {}
            self.http_locked_strategies = {}
            self.udp_locked_strategies = {}
            self.strategy_history = {}

            if self.output_callback:
                self.output_callback("[INFO] Данные обучения и история сброшены")

            return True

        except Exception as e:
            log(f"Ошибка очистки данных обучения: {e}", "ERROR")
            return False

    def get_learned_data(self) -> dict:
        """
        Возвращает данные обучения в формате для UI.

        Returns:
            Словарь {
                'tls': {hostname: [strategy]},
                'http': {hostname: [strategy]},
                'udp': {ip: [strategy]},
                'history': {hostname: {strategy: {successes, failures, rate}}}
            }
        """
        # Загружаем актуальные данные если еще не загружены
        if not self.locked_strategies and not self.http_locked_strategies and not self.udp_locked_strategies:
            self.load_existing_strategies()

        # Подготавливаем историю с рейтингами
        history_with_rates = {}
        for hostname, strategies in self.strategy_history.items():
            history_with_rates[hostname] = {}
            for strat_key, data in strategies.items():
                s = data.get('successes', 0)
                f = data.get('failures', 0)
                total = s + f
                rate = int((s / total) * 100) if total > 0 else 0
                history_with_rates[hostname][int(strat_key)] = {
                    'successes': s,
                    'failures': f,
                    'rate': rate
                }

        return {
            'tls': {host: [strat] for host, strat in self.locked_strategies.items()},
            'http': {host: [strat] for host, strat in self.http_locked_strategies.items()},
            'udp': {ip: [strat] for ip, strat in self.udp_locked_strategies.items()},
            'history': history_with_rates
        }

    # ==================== WHITELIST METHODS ====================

    def load_whitelist(self) -> list:
        """Загружает пользовательский whitelist из реестра"""
        self.user_whitelist = []
        try:
            data = reg(REGISTRY_ORCHESTRA, "Whitelist")
            if data:
                self.user_whitelist = json.loads(data)
                log(f"Загружено {len(self.user_whitelist)} пользовательских доменов в whitelist", "DEBUG")
        except Exception as e:
            log(f"Ошибка загрузки whitelist: {e}", "DEBUG")
        return self.user_whitelist

    def save_whitelist(self):
        """Сохраняет пользовательский whitelist в реестр"""
        try:
            data = json.dumps(self.user_whitelist, ensure_ascii=False)
            reg(REGISTRY_ORCHESTRA, "Whitelist", data)
            log(f"Сохранено {len(self.user_whitelist)} доменов в whitelist", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения whitelist: {e}", "ERROR")

    def get_full_whitelist(self) -> dict:
        """
        Возвращает полный whitelist (default + user) для UI.

        Returns:
            {'default': [...], 'user': [...]}
        """
        if not self.user_whitelist:
            self.load_whitelist()
        return {
            'default': list(DEFAULT_WHITELIST),
            'user': list(self.user_whitelist)
        }

    def add_to_whitelist(self, domain: str) -> bool:
        """Добавляет домен в пользовательский whitelist"""
        domain = domain.strip().lower()
        if not domain:
            return False

        # Проверяем что не в default списке
        if domain in DEFAULT_WHITELIST:
            log(f"Домен {domain} уже в базовом whitelist", "DEBUG")
            return False

        if domain not in self.user_whitelist:
            self.user_whitelist.append(domain)
            self.save_whitelist()
            log(f"Добавлен в whitelist: {domain}", "INFO")
            return True
        return False

    def remove_from_whitelist(self, domain: str) -> bool:
        """Удаляет домен из пользовательского whitelist"""
        domain = domain.strip().lower()

        # Нельзя удалить из default списка
        if domain in DEFAULT_WHITELIST:
            log(f"Нельзя удалить {domain} из базового whitelist", "WARNING")
            return False

        if domain in self.user_whitelist:
            self.user_whitelist.remove(domain)
            self.save_whitelist()
            log(f"Удалён из whitelist: {domain}", "INFO")
            return True
        return False

    def _generate_whitelist_file(self) -> bool:
        """Генерирует файл whitelist.txt для winws2 --hostlist-exclude"""
        try:
            # Загружаем user whitelist если нужно
            if not self.user_whitelist:
                self.load_whitelist()

            # Объединяем default + user
            all_domains = set(DEFAULT_WHITELIST) | set(self.user_whitelist)

            with open(self.whitelist_path, 'w', encoding='utf-8') as f:
                f.write("# Orchestra whitelist - exclude these domains from DPI bypass\n")
                f.write("# Default domains (from Python code) + User domains (from registry)\n\n")
                for domain in sorted(all_domains):
                    f.write(f"{domain}\n")

            log(f"Сгенерирован whitelist.txt ({len(all_domains)} доменов)", "DEBUG")
            return True

        except Exception as e:
            log(f"Ошибка генерации whitelist: {e}", "ERROR")
            return False
