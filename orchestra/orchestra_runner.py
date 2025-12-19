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
import ipaddress
from typing import Optional, Callable, Dict, List
from datetime import datetime

from log import log
from config import MAIN_DIRECTORY, EXE_FOLDER, LUA_FOLDER, LOGS_FOLDER, BIN_FOLDER, REGISTRY_PATH, LISTS_FOLDER
from config.reg import reg, reg_enumerate_values, reg_delete_all_values

# Пути в реестре для хранения обученных стратегий (subkeys)
REGISTRY_ORCHESTRA = f"{REGISTRY_PATH}\\Orchestra"
REGISTRY_ORCHESTRA_TLS = f"{REGISTRY_ORCHESTRA}\\TLS"      # TLS стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HTTP = f"{REGISTRY_ORCHESTRA}\\HTTP"    # HTTP стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_UDP = f"{REGISTRY_ORCHESTRA}\\UDP"      # UDP стратегии: IP=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HISTORY = f"{REGISTRY_ORCHESTRA}\\History"  # История: domain=JSON (REG_SZ)
REGISTRY_ORCHESTRA_BLOCKED = f"{REGISTRY_ORCHESTRA}\\Blocked"  # Заблокированные: domain=JSON (REG_SZ, список стратегий)

# Максимальное количество лог-файлов оркестратора
MAX_ORCHESTRA_LOGS = 10

# Белый список по умолчанию - сайты которые НЕ нужно обрабатывать
# Эти сайты работают без DPI bypass или требуют особой обработки
# Встраиваются автоматически при load_whitelist() как системные (нельзя удалить)
DEFAULT_WHITELIST_DOMAINS = {
    # Российские сервисы (работают без bypass)
    "vk.com",
    "vk.ru",
    "vk-portal.net",
    "userapi.com",
    "mail.ru",
    "max.ru",
    "ok.ru",
    "yandex.ru",
    "ya.ru",
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
    # Образование
    "netschool.edu22.info",
    "edu22.info",
    # Конструкторы сайтов
    "tilda.ws",
    "tilda.cc",
    "tildacdn.com",
    # AI сервисы (обычно работают)
    "claude.ai",
    "anthropic.com",
    "claude.com",
    # ozon
    "ozon.ru",
    "ozonusercontent.com",
    # wb
    "wildberries.ru",
    "wb.ru",
    "wbbasket.ru"
}

# Домены для которых strategy=1 (pass) заблокирована по умолчанию - они точно заблокированы РКН
# При загрузке blocked_strategies автоматически добавляется s1 для этих доменов
DEFAULT_BLOCKED_PASS_DOMAINS = {
    # Discord
    "discord.com", "discordapp.com", "discord.gg", "discord.media", "discordapp.net",
    # YouTube / Google Video
    "youtube.com", "googlevideo.com", "ytimg.com", "yt3.ggpht.com", "youtu.be",
    "ggpht.com", "googleusercontent.com", "youtube-nocookie.com",
    # Google
    "google.com", "google.ru", "googleapis.com", "gstatic.com",
    "googleadservices.com", "googlesyndication.com", "googletagmanager.com",
    "googleanalytics.com", "google-analytics.com", "doubleclick.net",
    "dns.google", "withgoogle.com", "withyoutube.com",
    # Twitch
    "twitch.tv", "twitchcdn.net",
    # Twitter/X
    "twitter.com", "x.com", "twimg.com",
    # Instagram
    "instagram.com", "cdninstagram.com", "igcdn.com", "ig.me",
    # Facebook / Meta
    "facebook.com", "fbcdn.net", "fb.com", "fb.me",
    # WhatsApp
    "whatsapp.com", "whatsapp.net",
    # TikTok
    "tiktok.com", "tiktokcdn.com", "musical.ly",
    # Telegram
    "telegram.org", "t.me",
    # Spotify
    "spotify.com", "spotifycdn.com",
    # Netflix
    "netflix.com", "nflxvideo.net",
    # Steam
    "steampowered.com", "steamcommunity.com", "steamstatic.com",
    # Roblox
    "roblox.com", "rbxcdn.com",
    # Reddit
    "reddit.com", "redd.it", "redditmedia.com",
    # GitHub
    "github.com", "githubusercontent.com",
    # Rutracker
    "rutracker.org"
}


def _is_default_blocked_pass_domain(hostname: str) -> bool:
    """
    Проверяет, является ли домен дефолтно заблокированным для strategy=1.
    Внутренняя функция для load_blocked_strategies.
    """
    if not hostname:
        return False
    hostname = hostname.lower().strip()
    # Точное совпадение
    if hostname in DEFAULT_BLOCKED_PASS_DOMAINS:
        return True
    # Проверка субдоменов (cdn.discord.com -> discord.com)
    for domain in DEFAULT_BLOCKED_PASS_DOMAINS:
        if hostname.endswith("." + domain):
            return True
    return False


def _is_default_whitelist_domain(hostname: str) -> bool:
    """
    Проверяет, является ли домен системным в whitelist (нельзя удалить).
    Внутренняя функция для whitelist методов.
    """
    if not hostname:
        return False
    hostname = hostname.lower().strip()
    return hostname in DEFAULT_WHITELIST_DOMAINS


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

        # Заблокированные стратегии (чёрный список): {hostname: [strategy_list]}
        self.blocked_strategies: Dict[str, List[int]] = {}

        # Кэши ipset подсетей для UDP (игры/Discord/QUIC)
        self.ipset_networks: list[tuple[ipaddress._BaseNetwork, str]] = []

        # Белый список (exclude list) - домены которые НЕ обрабатываются
        self.user_whitelist: list = []  # Только пользовательские (из реестра)
        self.whitelist: set = set()     # Полный список (default + user) для генерации файла

        # Callbacks
        self.output_callback: Optional[Callable[[str], None]] = None
        self.lock_callback: Optional[Callable[[str, int], None]] = None
        self.unlock_callback: Optional[Callable[[str], None]] = None

        # Мониторинг активности (для подсказок пользователю)
        self.last_activity_time: Optional[float] = None
        self.inactivity_warning_shown: bool = False

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

            # Очистка доменов со strategy=1 для дефолтно заблокированных (youtube, google и т.д.)
            from config.reg import reg_delete_value
            blocked_cleaned = []
            for domain, strategy in list(self.locked_strategies.items()):
                if strategy == 1 and _is_default_blocked_pass_domain(domain):
                    blocked_cleaned.append(domain)
                    del self.locked_strategies[domain]
                    try:
                        reg_delete_value(REGISTRY_ORCHESTRA_TLS, domain)
                    except Exception:
                        pass
            for domain, strategy in list(self.http_locked_strategies.items()):
                if strategy == 1 and _is_default_blocked_pass_domain(domain):
                    blocked_cleaned.append(domain)
                    del self.http_locked_strategies[domain]
                    try:
                        reg_delete_value(REGISTRY_ORCHESTRA_HTTP, domain)
                    except Exception:
                        pass
            if blocked_cleaned:
                log(f"Очищено {len(blocked_cleaned)} доменов со strategy=1 (заблокирована по умолчанию): {', '.join(blocked_cleaned[:5])}{'...' if len(blocked_cleaned) > 5 else ''}", "INFO")

        except Exception as e:
            log(f"Ошибка загрузки стратегий из реестра: {e}", "DEBUG")

        # Загружаем историю
        self.load_history()

        # Загружаем заблокированные стратегии
        self.load_blocked_strategies()

        # Очистка конфликтов: если стратегия заблокирована И залочена - удаляем lock
        # Блокировка = приоритет над lock
        from config.reg import reg_delete_value
        conflicts_cleaned = []
        
        for domain, strategy in list(self.locked_strategies.items()):
            if self.is_strategy_blocked(domain, strategy):
                conflicts_cleaned.append((domain, strategy, "TLS"))
                del self.locked_strategies[domain]
                try:
                    reg_delete_value(REGISTRY_ORCHESTRA_TLS, domain)
                except Exception:
                    pass
        
        for domain, strategy in list(self.http_locked_strategies.items()):
            if self.is_strategy_blocked(domain, strategy):
                conflicts_cleaned.append((domain, strategy, "HTTP"))
                del self.http_locked_strategies[domain]
                try:
                    reg_delete_value(REGISTRY_ORCHESTRA_HTTP, domain)
                except Exception:
                    pass
        
        for ip, strategy in list(self.udp_locked_strategies.items()):
            if self.is_strategy_blocked(ip, strategy):
                conflicts_cleaned.append((ip, strategy, "UDP"))
                del self.udp_locked_strategies[ip]
                try:
                    reg_delete_value(REGISTRY_ORCHESTRA_UDP, ip)
                except Exception:
                    pass
        
        if conflicts_cleaned:
            log(f"Очищено {len(conflicts_cleaned)} конфликтующих LOCK (заблокированные стратегии):", "INFO")
            for domain, strategy, proto in conflicts_cleaned[:10]:
                log(f"  - {domain} strategy={strategy} [{proto}]", "INFO")
            if len(conflicts_cleaned) > 10:
                log(f"  - ... и ещё {len(conflicts_cleaned) - 10}", "INFO")

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

    def _get_best_strategy_from_history(self, hostname: str, exclude_strategy: int = None) -> Optional[int]:
        """
        Находит лучшую стратегию из истории для домена.

        Args:
            hostname: Домен для поиска
            exclude_strategy: Стратегия для исключения (например, 1)

        Returns:
            Номер лучшей стратегии или None если нет подходящих
        """
        if hostname not in self.strategy_history:
            return None

        best_strategy = None
        best_rate = -1

        for strat_key, data in self.strategy_history[hostname].items():
            strat_num = int(strat_key)

            # Пропускаем исключённую или заблокированную стратегию
            if exclude_strategy is not None and strat_num == exclude_strategy:
                continue
            if self.is_strategy_blocked(hostname, strat_num):
                continue

            successes = data.get('successes', 0)
            failures = data.get('failures', 0)
            total = successes + failures

            # Нужен хотя бы 1 тест
            if total == 0:
                continue

            rate = (successes / total) * 100

            # Выбираем стратегию с лучшим rate
            if rate > best_rate:
                best_rate = rate
                best_strategy = strat_num

        return best_strategy

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
        Этот файл хранится по пути H:\Privacy\zapret\lua\strategy-stats.lua
        Вызывает strategy_preload() и strategy_preload_history() для каждого домена.

        Returns:
            Путь к файлу или None если нет данных
        """
        has_tls = bool(self.locked_strategies)
        has_http = bool(self.http_locked_strategies)
        has_udp = bool(self.udp_locked_strategies)
        has_history = bool(self.strategy_history)

        # blocked_strategies уже содержит и дефолтные (s1 для DEFAULT_BLOCKED_PASS_DOMAINS)
        # и пользовательские блокировки - используем напрямую
        has_blocked = bool(self.blocked_strategies)

        if not has_tls and not has_http and not has_udp and not has_history and not has_blocked:
            return None

        lua_path = os.path.join(self.lua_path, "learned-strategies.lua")
        log(f"Генерация learned-strategies.lua: {lua_path}", "DEBUG")
        log(f"  TLS: {len(self.locked_strategies)}, HTTP: {len(self.http_locked_strategies)}, UDP: {len(self.udp_locked_strategies)}", "DEBUG")
        total_tls = len(self.locked_strategies)
        total_http = len(self.http_locked_strategies)
        total_udp = len(self.udp_locked_strategies)
        total_history = len(self.strategy_history)

        try:
            with open(lua_path, 'w', encoding='utf-8') as f:
                f.write("-- Auto-generated: preload strategies from registry\n")
                f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- TLS: {total_tls}, HTTP: {total_http}, UDP: {total_udp}, History: {total_history}\n\n")

                # Генерируем таблицу заблокированных стратегий для Lua
                if self.blocked_strategies:
                    f.write("-- Blocked strategies (default + user-defined)\n")
                    f.write("BLOCKED_STRATEGIES = {\n")
                    for hostname, strategies in self.blocked_strategies.items():
                        safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                        strat_list = ", ".join(str(s) for s in strategies)
                        f.write(f'    ["{safe_host}"] = {{{strat_list}}},\n')
                    f.write("}\n\n")

                    # Функция проверки заблокированных стратегий (учитываем субдомены)
                    f.write("-- Check if strategy is blocked for hostname (supports subdomains)\n")
                    f.write("function is_strategy_blocked(hostname, strategy)\n")
                    f.write("    if not hostname or not BLOCKED_STRATEGIES then return false end\n")
                    f.write("    hostname = hostname:lower()\n")
                    f.write("    local function check_host(h)\n")
                    f.write("        local blocked = BLOCKED_STRATEGIES[h]\n")
                    f.write("        if not blocked then return false end\n")
                    f.write("        for _, s in ipairs(blocked) do\n")
                    f.write("            if s == strategy then return true end\n")
                    f.write("        end\n")
                    f.write("        return false\n")
                    f.write("    end\n")
                    f.write("    -- точное совпадение\n")
                    f.write("    if check_host(hostname) then return true end\n")
                    f.write("    -- проверка по суффиксу домена\n")
                    f.write("    local dot = hostname:find('%.')\n")
                    f.write("    while dot do\n")
                    f.write("        local suffix = hostname:sub(dot + 1)\n")
                    f.write("        if check_host(suffix) then return true end\n")
                    f.write("        dot = hostname:find('%.', dot + 1)\n")
                    f.write("    end\n")
                    f.write("    return false\n")
                    f.write("end\n\n")
                else:
                    # Если нет заблокированных - функция всегда возвращает false
                    f.write("-- No blocked strategies\n")
                    f.write("BLOCKED_STRATEGIES = {}\n")
                    f.write("function is_strategy_blocked(hostname, strategy) return false end\n\n")

                # Предзагрузка TLS стратегий (с фильтрацией заблокированных)
                blocked_tls = 0
                for hostname, strategy in self.locked_strategies.items():
                    if self.is_strategy_blocked(hostname, strategy):
                        blocked_tls += 1
                        continue
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_host}", {strategy}, "tls")\n')

                # Предзагрузка HTTP стратегий (с фильтрацией заблокированных)
                blocked_http = 0
                for hostname, strategy in self.http_locked_strategies.items():
                    if self.is_strategy_blocked(hostname, strategy):
                        blocked_http += 1
                        continue
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_host}", {strategy}, "http")\n')

                # Предзагрузка UDP стратегий (с фильтрацией заблокированных)
                blocked_udp = 0
                for ip, strategy in self.udp_locked_strategies.items():
                    if self.is_strategy_blocked(ip, strategy):
                        blocked_udp += 1
                        continue
                    safe_ip = ip.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_ip}", {strategy}, "udp")\n')

                # Для доменов с заблокированной s1 из истории, которые НЕ залочены - preload с лучшей стратегией
                blocked_from_history = 0
                for hostname in self.strategy_history.keys():
                    # Пропускаем если уже залочен (обработан выше)
                    if hostname in self.locked_strategies or hostname in self.http_locked_strategies:
                        continue
                    # Только для доменов с заблокированной strategy=1
                    if not self.is_strategy_blocked(hostname, 1):
                        continue
                    # Находим лучшую стратегию (исключая strategy=1 и другие заблокированные)
                    best_strat = self._get_best_strategy_from_history(hostname, exclude_strategy=1)
                    if not best_strat:
                        continue
                    # Дополнительная защита: если стратегия заблокирована — пропускаем
                    if self.is_strategy_blocked(hostname, best_strat):
                        continue
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'strategy_preload("{safe_host}", {best_strat}, "tls")\n')
                    blocked_from_history += 1
                if blocked_from_history > 0:
                    log(f"Добавлено {blocked_from_history} доменов из истории (s1 заблокирована)", "DEBUG")

                # Предзагрузка истории (фильтруем заблокированные стратегии)
                history_skipped = 0
                for hostname, strategies in self.strategy_history.items():
                    safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                    for strat_key, data in strategies.items():
                        strat_num = int(strat_key) if isinstance(strat_key, str) else strat_key
                        # Пропускаем заблокированные стратегии
                        if self.is_strategy_blocked(hostname, strat_num):
                            history_skipped += 1
                            continue
                        s = data.get('successes', 0)
                        f_count = data.get('failures', 0)
                        f.write(f'strategy_preload_history("{safe_host}", {strat_key}, {s}, {f_count})\n')
                if history_skipped > 0:
                    log(f"Пропущено {history_skipped} записей истории (заблокированы)", "DEBUG")

                actual_tls = total_tls - blocked_tls
                actual_http = total_http - blocked_http
                actual_udp = total_udp - blocked_udp
                total_blocked = blocked_tls + blocked_http + blocked_udp
                f.write(f'\nDLOG("learned-strategies: loaded {actual_tls} TLS + {actual_http} HTTP + {actual_udp} UDP + {total_history} history (blocked: {total_blocked})")\n')

                # Install circular wrapper to apply preloaded strategies
                f.write('\n-- Install circular wrapper to apply preloaded strategies on first packet\n')
                f.write('install_circular_wrapper()\n')
                f.write('DLOG("learned-strategies: wrapper installed, circular=" .. tostring(circular ~= nil) .. ", original=" .. tostring(original_circular ~= nil))\n')

                # Debug: wrap circular again to see why APPLIED doesn't work
                f.write('\n-- DEBUG: extra wrapper to diagnose APPLIED issue\n')
                f.write('if circular and working_strategies then\n')
                f.write('    local _debug_circular = circular\n')
                f.write('    circular = function(ctx, desync)\n')
                f.write('        local hostname = standard_hostkey and standard_hostkey(desync) or "?"\n')
                f.write('        local askey = (desync and desync.arg and desync.arg.key and #desync.arg.key>0) and desync.arg.key or (desync and desync.func_instance or "?")\n')
                f.write('        local data = working_strategies[hostname]\n')
                f.write('        if data then\n')
                f.write('            local expected = get_autostate_key_by_payload and get_autostate_key_by_payload(data.payload_type) or "?"\n')
                f.write('            DLOG("DEBUG circular: host=" .. hostname .. " askey=" .. askey .. " expected=" .. expected .. " locked=" .. tostring(data.locked) .. " applied=" .. tostring(data.applied))\n')
                f.write('        end\n')
                f.write('        return _debug_circular(ctx, desync)\n')
                f.write('    end\n')
                f.write('    DLOG("learned-strategies: DEBUG wrapper installed")\n')
                f.write('end\n')

                # Wrap circular to skip blocked strategies during rotation
                if self.blocked_strategies:
                    f.write('\n-- Install blocked strategies filter for circular rotation\n')
                    f.write('local _blocked_wrap_installed = false\n')
                    f.write('local function install_blocked_filter()\n')
                    f.write('    if _blocked_wrap_installed then return end\n')
                    f.write('    _blocked_wrap_installed = true\n')
                    f.write('    if circular and type(circular) == "function" then\n')
                    f.write('        local original_circular = circular\n')
                    f.write('        circular = function(t, hostname, ...)\n')
                    f.write('            local result = original_circular(t, hostname, ...)\n')
                    f.write('            if result and hostname and is_strategy_blocked(hostname, result) then\n')
                    f.write('                local max_skip = 10\n')
                    f.write('                for i = 1, max_skip do\n')
                    f.write('                    result = original_circular(t, hostname, ...)\n')
                    f.write('                    if not result or not is_strategy_blocked(hostname, result) then break end\n')
                    f.write('                    DLOG("BLOCKED: skip strategy " .. result .. " for " .. hostname)\n')
                    f.write('                end\n')
                    f.write('            end\n')
                    f.write('            return result\n')
                    f.write('        end\n')
                    f.write('        DLOG("Blocked strategies filter installed for circular")\n')
                    f.write('    end\n')
                    f.write('end\n')
                    f.write('install_blocked_filter()\n')

            total_blocked = blocked_tls + blocked_http + blocked_udp
            block_info = f", заблокировано {total_blocked}" if total_blocked > 0 else ""

            log(f"Сгенерирован learned-strategies.lua ({total_tls} TLS + {total_http} HTTP + {total_udp} UDP + {total_history} history{block_info})", "DEBUG")
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

                if '--lua-desync=' in line:
                    strategy_num += 1
                    # Добавляем :strategy=N к КАЖДОМУ --lua-desync параметру в строке
                    parts = line.split(' ')
                    new_parts = []
                    for part in parts:
                        if part.startswith('--lua-desync='):
                            new_parts.append(f"{part}:strategy={strategy_num}")
                        else:
                            new_parts.append(part)
                    numbered_lines.append(' '.join(new_parts))
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
        Путь C:\ProgramData\ZapretTwoDev\lua\strategies-all.txt

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
        # === Паттерны для combined-detector.lua (circular_quality оркестратор) ===
        # strategy_quality: LOCK googlevideo.com -> strat=5 (successes=3 tests=5 rate=60%)
        lock_pattern = re.compile(r"strategy_quality: LOCK (\S+) -> strat=(\d+)")
        # circular_quality: AUTO-UNLOCK googlevideo.com after 3 consecutive fails
        unlock_pattern = re.compile(r"circular_quality: AUTO-UNLOCK (\S+) after")
        # strategy_quality: googlevideo.com strat=5 SUCCESS 3/5
        success_pattern = re.compile(r"strategy_quality: (\S+) strat=(\d+) SUCCESS (\d+)/(\d+)")
        # strategy_quality: googlevideo.com strat=5 FAIL 2/5
        fail_pattern = re.compile(r"strategy_quality: (\S+) strat=(\d+) FAIL (\d+)/(\d+)")
        # strategy_quality: RESET hostname (при сбросе обучения)
        reset_pattern = re.compile(r"strategy_quality: RESET (\S+)")

        # === Legacy паттерны для обратной совместимости ===
        legacy_lock_pattern = re.compile(r"LOCKED (\S+) to strategy=(\d+)(?:\s+\[(TLS|HTTP|UDP)\])?")
        legacy_unlock_pattern = re.compile(r"UNLOCKING (\S+)(?:\s+\[(TLS|HTTP|UDP)\])?")
        sticky_pattern = re.compile(r"STICKY (\S+) to strategy=(\d+)")
        preload_pattern = re.compile(r"PRELOADED (\S+) = strategy (\d+)(?:\s+\[(tls|http|udp)\])?")
        # LUA: strategy-stats: APPLIED youtube.com = strategy 15 [circular_quality_1_1]
        applied_pattern = re.compile(r"APPLIED (\S+) = strategy (\d+)(?:\s+\[([^\]]+)\])?")
        history_pattern = re.compile(r"HISTORY (\S+) strategy=(\d+) successes=(\d+) failures=(\d+) rate=(\d+)%")
        unsticky_pattern = re.compile(r"strategy-stats: UNSTICKY (\S+)(?:\s+\[(TLS|HTTP|UDP)\])?")

        # === Паттерны для circular_quality оркестратора ===
        # circular_quality: rotate to strategy N [stats]
        # In logs we may see "circular_quality: rotate to strategy N" (new)
        # or "circular: rotate strategy to N" (legacy in some LUA traces).
        rotate_pattern = re.compile(r"(?:circular_quality|circular): rotate (?:strategy )?to (?:strategy )?(\d+)")
        # circular_quality: current strategy N
        current_strategy_pattern = re.compile(r"circular_quality: current strategy (\d+)")
        # === Паттерны для стандартных детекторов zapret2 ===
        # automate: success detected / automate: failure detected
        automate_success_pattern = re.compile(r"automate: success detected")
        automate_failure_pattern = re.compile(r"automate: failure detected")
        # standard_failure_detector: incoming RST
        std_rst_pattern = re.compile(r"standard_failure_detector: incoming RST")
        # standard_failure_detector: retransmission N/M
        std_retrans_pattern = re.compile(r"standard_failure_detector: retransmission (\d+)/(\d+)")
        # standard_success_detector: treating connection as successful
        std_success_pattern = re.compile(r"standard_success_detector:.*successful")
        # LUA automate выводит hostname перед success_detector (для Keep-Alive соединений без SNI)
        # TCP: LUA: automate: host record key 'autostate.circular_quality_1_1.github.com'
        # UDP: LUA: automate: host record key 'autostate.circular_quality_3_1.udp_other_108.177.0.0'
        automate_hostkey_pattern = re.compile(r"LUA: automate: host record key 'autostate\.circular_quality_\d+_\d+\.(?:udp_other_)?([^']+)'")

        # === Паттерн для hostname из desync profile search ===
        # TCP: desync profile search for tcp ip=... port=443 l7proto=tls ssid='' hostname='youtube.com'
        # UDP: desync profile search for udp ip=... port=443 l7proto=quic/stun/discord/wireguard/unknown
        # Формат из desync.c: proto_name(l3proto) = tcp/udp, l7proto_str() = unknown/quic/stun/discord/wireguard/dht/etc
        hostname_pattern = re.compile(r"desync profile search for tcp ip=[\d.:]+ port=(\d+) l7proto=\S+ ssid='[^']*' hostname='([^']+)'")
        # UDP всегда имеет l7proto (unknown/quic/stun/discord/wireguard/dht), поддержка IPv4 и IPv6
        udp_pattern = re.compile(r"desync profile search for udp ip=([\d.:a-fA-F]+) port=(\d+) l7proto=(\S+)")
        # Fallback: извлекаем UDP IP из incoming пакета (когда profile search закэширован)
        # IP4: 151.101.1.140 => 192.168.1.100 proto=udp ttl=55 sport=443 dport=64028
        udp_incoming_ip_pattern = re.compile(r"IP4: ([\d.]+) => ([\d.]+) proto=udp ttl=\d+ sport=(\d+)")

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
        # Извлекаем connection_proto из любого dpi desync (для определения протокола перед RST)
        dpi_desync_proto_pattern = re.compile(r"dpi desync .* connection_proto=(\S+)")

        # Переменная для текущего протокола (80=HTTP, 443=TLS, udp=UDP)
        current_port = None
        current_proto = "tcp"  # tcp или udp
        current_l7proto = None  # quic, stun, discord, wireguard (для UDP)
        current_profile = 0  # номер профиля (3 или 4 = UDP)

        # Для отслеживания текущего хоста/IP и стратегии
        current_host = None
        current_strat = 1

        # Кэш IP → hostname для обработки Keep-Alive соединений без SNI
        # {ip: hostname} - последний известный hostname для каждого IP
        # Автоматически ограничивается до 1000 записей для экономии памяти
        ip_to_hostname_cache: dict[str, str] = {}
        # Также кэш IP для текущего пакета (из desync profile search)
        current_ip = None

        # Последняя реально применённая стратегия по хосту/протоколу (из LUA: strategy-stats: APPLIED ...)
        last_applied: dict[tuple[str, str], int] = {}
        # Последний "контекстный" домен по протоколу (чтобы привязать RST/retrans к домену)
        last_applied_host_by_proto: dict[str, str] = {}

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
                    # Также извлекаем IP для кэширования связки IP → hostname
                    match = hostname_pattern.search(line)
                    if match:
                        current_port, hostname = match.groups()
                        current_proto = "tcp"
                        
                        # Извлекаем IP из этой же строки для кэша
                        # Формат: "desync profile search for tcp ip=142.250.74.206 port=443 l7proto=tls hostname='youtube.com'"
                        ip_match = re.search(r'ip=([\d.]+)', line)
                        if ip_match:
                            current_ip = ip_match.group(1)
                        else:
                            current_ip = None
                        
                        # Игнорируем пустые hostname и IP-адреса
                        if hostname and not hostname.replace('.', '').isdigit():
                            # Применяем NLD-cut для группировки поддоменов
                            current_host = nld_cut(hostname, 2)
                            
                            # Сохраняем в кэш связку IP → hostname (для Keep-Alive соединений)
                            if current_ip and not current_ip.startswith(LOCAL_IP_PREFIXES):
                                # Логируем только если это новая запись или изменение
                                if current_ip not in ip_to_hostname_cache or ip_to_hostname_cache[current_ip] != current_host:
                                    log(f"[CACHE] Сохранен hostname {current_host} для IP {current_ip}", "DEBUG")
                                ip_to_hostname_cache[current_ip] = current_host
                                
                                # Ограничиваем размер кэша (каждые 100 записей проверяем размер)
                                if len(ip_to_hostname_cache) % 100 == 0 and len(ip_to_hostname_cache) > 1000:
                                    # Оставляем 500 последних (по порядку добавления в dict Python 3.7+)
                                    keys_to_keep = list(ip_to_hostname_cache.keys())[-500:]
                                    for key in list(ip_to_hostname_cache.keys()):
                                        if key not in keys_to_keep:
                                            del ip_to_hostname_cache[key]
                                    log(f"[CACHE] Очищен до {len(ip_to_hostname_cache)} записей", "DEBUG")
                        else:
                            current_host = None
                            # Пробуем восстановить hostname из кэша по IP
                            if current_ip and current_ip in ip_to_hostname_cache:
                                current_host = ip_to_hostname_cache[current_ip]
                        continue

                    # UDP: desync profile search for udp ip=1.2.3.4 port=443 l7proto=quic/stun/discord/wireguard
                    match = udp_pattern.search(line)
                    if match:
                        ip = match.group(1)
                        current_port = match.group(2)
                        l7proto = match.group(3)  # unknown, quic, stun, discord, wireguard, dht
                        current_proto = "udp"
                        current_l7proto = l7proto  # Сохраняем для LOCKED/UNLOCK
                        current_ip = ip  # Сохраняем для кэша
                        # Пропускаем локальные IP адреса
                        if ip.startswith(LOCAL_IP_PREFIXES):
                            current_host = None
                        else:
                            current_host = ip  # Для UDP используем IP напрямую
                        continue
                    
                    # UDP fallback: извлекаем IP из incoming UDP пакета (когда profile search закэширован)
                    match = udp_incoming_ip_pattern.search(line)
                    if match:
                        remote_ip = match.group(1)  # Источник (удалённый сервер)
                        sport = match.group(3)
                        # Устанавливаем UDP контекст только если current_proto ещё не UDP или IP изменился
                        if not remote_ip.startswith(LOCAL_IP_PREFIXES):
                            current_host = remote_ip
                            current_ip = remote_ip
                            current_port = sport
                            current_proto = "udp"
                            # current_l7proto остаётся от предыдущего пакета или будет установлен позже
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
                    
                    # Парсим connection_proto из dpi desync для TCP (профиль 1 и 2)
                    # Это нужно для правильного определения протокола перед RST/SUCCESS
                    # dpi desync ... connection_proto=tls/http
                    match = dpi_desync_proto_pattern.search(line)
                    if match:
                        connection_proto = match.group(1)
                        # Обновляем current_l7proto для TCP тоже (для RST/SUCCESS логирования)
                        current_l7proto = connection_proto
                        continue

                    # Записываем каждую строку в файл лога
                    if log_file:
                        try:
                            log_file.write(f"{line}\n")
                        except Exception:
                            pass

                    # Проверяем LOCK (новый формат: strategy_quality: LOCK hostname -> strat=N)
                    match = lock_pattern.search(line)
                    if not match:
                        # Пробуем legacy формат: LOCKED hostname to strategy=N [TLS]
                        match = legacy_lock_pattern.search(line)
                        ptype = match.group(3) if match and len(match.groups()) >= 3 else None
                    else:
                        ptype = None  # Новый формат без типа протокола

                    if match:
                        host = match.group(1)
                        strat = int(match.group(2))
                        log(f"[LOCK DEBUG] Найден LOCK: host={host}, strat={strat}, ptype={ptype}", "INFO")

                        # Определяем протокол: сначала из тега [TLS/HTTP/UDP], потом из current_proto
                        if ptype:
                            ptype_upper = ptype.upper()
                            is_http = (ptype_upper == "HTTP")
                            is_udp = (ptype_upper == "UDP")
                        else:
                            # Если тег не указан - определяем по current_l7proto (надежнее)
                            is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                            is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")

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

                        # Пропускаем заблокированные стратегии (не лочим их)
                        if self.is_strategy_blocked(host, strat):
                            continue

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

                    # Проверяем UNLOCK (новый формат: circular_quality: AUTO-UNLOCK hostname after)
                    match = unlock_pattern.search(line)
                    if not match:
                        # Пробуем legacy формат: UNLOCKING hostname [TLS]
                        match = legacy_unlock_pattern.search(line)
                        ptype = match.group(2) if match and len(match.groups()) >= 2 else None
                    else:
                        ptype = None  # Новый формат без типа протокола

                    # Также проверяем strategy_quality: RESET hostname
                    if not match:
                        match = reset_pattern.search(line)

                    if match:
                        host = match.group(1)

                        # Определяем протокол: сначала из тега, потом из current_l7proto
                        if ptype:
                            ptype_upper = ptype.upper()
                            is_http = (ptype_upper == "HTTP")
                            is_udp = (ptype_upper == "UDP")
                        else:
                            is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                            is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")

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

                    # Проверяем APPLIED (реально применённая стратегия)
                    # Пример: LUA: strategy-stats: APPLIED youtube.com = strategy 15 [circular_quality_1_1]
                    match = applied_pattern.search(line)
                    if match:
                        host = match.group(1)
                        strat = int(match.group(2))
                        tag = match.group(3) or ""  # circular_quality_1_1

                        # Нормализуем домен
                        host_key = nld_cut(host, 2)

                        # Определяем протокол из тега circular_quality_N_*
                        proto_key = None
                        m = re.match(r"circular_quality_(\d+)_", tag)
                        if m:
                            prof = int(m.group(1))
                            if prof == 2:
                                proto_key = "http"
                            elif prof == 3:
                                proto_key = "udp"
                            else:
                                proto_key = "tls"
                        else:
                            # fallback: по текущему протоколу
                            proto_key = "udp" if current_proto == "udp" else ("http" if current_port == "80" else "tls")

                        prev = last_applied.get((host_key, proto_key))
                        last_applied[(host_key, proto_key)] = strat
                        last_applied_host_by_proto[proto_key] = host_key

                        # Поднимаем "контекст" для следующих std_success/std_rst
                        current_host = host_key
                        if proto_key == "udp":
                            current_proto = "udp"
                            current_port = None
                        else:
                            current_proto = "tcp"
                            current_port = "80" if proto_key == "http" else "443"

                        # Пишем только первый APPLIED и смену стратегии (минимум шума, максимум пользы)
                        if prev is None or prev != strat:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            if prev is None:
                                msg = f"[{timestamp}] 🎯 APPLIED: {host_key} [{proto_key}] = strategy {strat}"
                            else:
                                msg = f"[{timestamp}] 🔄 APPLIED: {host_key} [{proto_key}] {prev} → {strat}"
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

                    # Проверяем SUCCESS - новый формат: strategy_quality: hostname strat=N SUCCESS X/Y
                    match = success_pattern.search(line)
                    if match:
                        host, strat, successes, total = match.groups()
                        strat = int(strat)

                        # Определяем протокол из current_l7proto (надежнее)
                        is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                        is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")

                        # Для UDP: конвертируем IP в /16 подсеть
                        # Для TCP: применяем NLD-cut для группировки
                        if is_udp:
                            host = ip_to_subnet16(host)
                        else:
                            host = nld_cut(host, 2)

                        self._increment_history(host, strat, is_success=True)
                        history_save_counter += 1

                        # Выводим в UI с протоколом
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if is_udp:
                            port_str = " UDP"
                        elif is_http:
                            port_str = " :80"
                        else:
                            port_str = " :443"
                        msg = f"[{timestamp}] ✓ SUCCESS: {host}{port_str} strategy={strat} ({successes}/{total})"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем каждые 5 событий
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue

                    # Проверяем FAIL - новый формат: strategy_quality: hostname strat=N FAIL X/Y
                    match = fail_pattern.search(line)
                    if match:
                        host, strat, successes, total = match.groups()
                        strat = int(strat)

                        # Определяем протокол из current_l7proto (надежнее)
                        is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                        is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")

                        # Для UDP: конвертируем IP в /16 подсеть
                        # Для TCP: применяем NLD-cut для группировки
                        if is_udp:
                            host = ip_to_subnet16(host)
                        else:
                            host = nld_cut(host, 2)

                        self._increment_history(host, strat, is_success=False)
                        history_save_counter += 1

                        # Выводим в UI с протоколом
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if is_udp:
                            port_str = " UDP"
                        elif is_http:
                            port_str = " :80"
                        else:
                            port_str = " :443"
                        msg = f"[{timestamp}] ✗ FAIL: {host}{port_str} strategy={strat} ({successes}/{total})"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем каждые 5 событий
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue

                    # Проверяем LUA automate host record key (выводится перед SUCCESS для Keep-Alive)
                    # TCP: LUA: automate: host record key 'autostate.circular_quality_1_1.github.com'
                    # UDP: LUA: automate: host record key 'autostate.circular_quality_3_1.udp_other_108.177.0.0'
                    match = automate_hostkey_pattern.search(line)
                    if match:
                        hostname = match.group(1)
                        if hostname:
                            # Для TCP: применяем nld_cut, для UDP (IP адрес) - НЕ перезаписываем current_host
                            # т.к. он уже установлен из "desync profile search for udp" с полным IP
                            if hostname.replace('.', '').replace(':', '').isdigit():
                                # Это IP адрес (UDP) - НЕ перезаписываем current_host (он уже полный из udp_pattern)
                                # automate hostkey для UDP содержит обрезанный /16 IP, игнорируем его
                                pass
                            else:
                                # Это домен (TCP) - применяем nld_cut и обновляем current_host
                                current_host = nld_cut(hostname, 2)
                                # Сохраняем в кэш если есть current_ip
                                if current_ip and not current_ip.startswith(LOCAL_IP_PREFIXES):
                                    if current_ip not in ip_to_hostname_cache or ip_to_hostname_cache[current_ip] != current_host:
                                        log(f"[AUTOMATE] Сохранен hostname {current_host} для IP {current_ip}", "DEBUG")
                                    ip_to_hostname_cache[current_ip] = current_host
                        continue

                    # Проверяем успех от стандартного детектора (TCP) или automate (UDP)
                    # TCP: "standard_success_detector:.*successful"
                    # UDP: "automate: success detected"
                    if std_success_pattern.search(line) or automate_success_pattern.search(line):
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Пытаемся восстановить hostname из кэша если current_host не установлен
                        work_host = current_host
                        if not work_host and current_ip and current_ip in ip_to_hostname_cache:
                            work_host = ip_to_hostname_cache[current_ip]
                            log(f"[CACHE] Восстановлен hostname {work_host} из кэша для IP {current_ip}", "DEBUG")
                        
                        # Записываем success в историю если знаем хост и стратегию
                        if work_host:
                            # Определяем протокол по current_l7proto (надежнее чем current_proto)
                            is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                            is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")

                            # Для UDP оставляем сырой IP (не режем /16), чтобы видеть конкретный адрес
                            # Для TCP: применяем NLD-cut
                            if is_udp:
                                lock_host = work_host  # raw IP
                            else:
                                lock_host = nld_cut(work_host, 2)

                            display_host = work_host if is_udp else lock_host
                            ipset_label = self._resolve_ipset_label(lock_host) if is_udp else None
                            # Heuristic: Discord STUN (common ports)
                            if is_udp and not ipset_label and current_l7proto and current_l7proto.lower() == "stun":
                                if current_port:
                                    try:
                                        port_int = int(str(current_port))
                                    except ValueError:
                                        port_int = None
                                    if port_int in (3478, 3479, 3480, 19302, 19303) or (50000 <= port_int <= 51000):
                                        ipset_label = "discord-stun"

                            # Берём реально применённую стратегию из APPLIED (иначе не логируем, чтобы не врать)
                            proto_key = "udp" if is_udp else ("http" if is_http else "tls")
                            applied_strat = last_applied.get((lock_host, proto_key))
                            if not applied_strat:
                                # Нет данных о применённой стратегии — пропускаем (иначе будет ложный strategy=1)
                                continue

                            # Если стратегия для домена заблокирована (в т.ч. дефолтно) — пропускаем учёт и лог
                            if self.is_strategy_blocked(lock_host, applied_strat):
                                continue

                            self._increment_history(lock_host, applied_strat, is_success=True)
                            history_save_counter += 1

                            # Считаем количество успехов для LOCK
                            host_key = f"{lock_host}:{applied_strat}"
                            if not hasattr(self, '_success_counts'):
                                self._success_counts = {}
                            self._success_counts[host_key] = self._success_counts.get(host_key, 0) + 1

                            # LOCK: UDP/STUN сразу после 1 успеха, TCP после 3 успехов
                            # UDP соединения короткие, нужно запоминать быстро
                            lock_threshold = 1 if is_udp else 3
                            if self._success_counts[host_key] >= lock_threshold:
                                # Пропускаем заблокированные стратегии (не лочим их)
                                if not self.is_strategy_blocked(lock_host, applied_strat):
                                    # Выбираем правильный словарь: UDP, HTTP или TLS
                                    if is_udp:
                                        target_dict = self.udp_locked_strategies
                                    elif is_http:
                                        target_dict = self.http_locked_strategies
                                    else:
                                        target_dict = self.locked_strategies

                                    prev_lock = target_dict.get(lock_host)
                                    
                                    # Логируем LOCK только если это первый раз или смена стратегии
                                    if prev_lock is None or prev_lock != applied_strat:
                                        target_dict[lock_host] = applied_strat  # Сохраняем новый lock

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
                                        proto_tag = ""
                                        if is_udp:
                                            proto_tag = f" [{current_l7proto.upper()}]" if current_l7proto else " [UDP]"
                                        label_str = f" [{ipset_label}]" if ipset_label else ""
                                        if prev_lock is not None:
                                            msg = f"[{timestamp}] 🔒 LOCKED: {display_host}{port_str}{label_str}{proto_tag} {prev_lock} → {applied_strat}"
                                        else:
                                            msg = f"[{timestamp}] 🔒 LOCKED: {display_host}{port_str}{label_str}{proto_tag} = strategy {applied_strat}"
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
                            label_str = f" [{ipset_label}]" if ipset_label else ""
                            proto_tag = f" [{current_l7proto.upper()}]" if (is_udp and current_l7proto) else (" [UDP]" if is_udp else "")
                            msg = f"[{timestamp}] ✓ SUCCESS: {display_host}{port_str}{label_str}{proto_tag} strategy={applied_strat}"
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
                        # Пытаемся определить домен и реально применённую стратегию
                        # Используем current_l7proto для надежного определения (он парсится из dpi desync)
                        is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                        is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")
                        proto_key = "udp" if is_udp else ("http" if is_http else "tls")

                        host_key = None
                        if current_host:
                            host_key = current_host if is_udp else nld_cut(current_host, 2)
                        elif current_ip and current_ip in ip_to_hostname_cache:
                            # Пытаемся восстановить hostname из кэша по IP
                            cached_host = ip_to_hostname_cache[current_ip]
                            host_key = cached_host if is_udp else nld_cut(cached_host, 2)
                            log(f"[CACHE] RST: Восстановлен hostname {cached_host} из кэша для IP {current_ip}", "DEBUG")
                        else:
                            host_key = last_applied_host_by_proto.get(proto_key)

                        applied_strat = last_applied.get((host_key, proto_key)) if host_key else None

                        if is_udp:
                            port_str = " UDP"
                        elif is_http:
                            port_str = " :80"
                        else:
                            port_str = " :443"

                        label_str = ""
                        proto_tag = ""
                        if is_udp:
                            label = self._resolve_ipset_label(host_key) if host_key else None
                            if label:
                                label_str = f" [{label}]"
                            proto_tag = f" [{current_l7proto.upper()}]" if current_l7proto else " [UDP]"

                        if host_key and applied_strat:
                            msg = f"[{timestamp}] ⚡ RST detected: {host_key}{port_str}{label_str}{proto_tag} strategy={applied_strat}"
                        elif host_key:
                            msg = f"[{timestamp}] ⚡ RST detected: {host_key}{port_str}{label_str}{proto_tag}"
                        else:
                            msg = f"[{timestamp}] ⚡ RST detected - DPI block"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # DUPLICATE REMOVED: std_success_pattern handler was here
                    # The correct handler is at lines 877-914 which saves to registry

                    # Проверяем ротацию стратегии
                    match = rotate_pattern.search(line)
                    if match:
                        new_strat = match.group(1)
                        timestamp = datetime.now().strftime("%H:%M:%S")

                        # Пытаемся определить хост для читаемого лога
                        host_for_log = current_host
                        # Определяем протокол для выбора host из last_applied_host_by_proto
                        is_udp = (current_l7proto and current_l7proto.lower() in ('discord', 'stun', 'quic', 'wireguard', 'dht', 'unknown')) and current_proto == "udp"
                        is_http = (current_l7proto == 'http') or (current_proto == "tcp" and current_port == "80")
                        proto_key = "udp" if is_udp else ("http" if is_http else "tls")

                        if not host_for_log:
                            host_for_log = last_applied_host_by_proto.get(proto_key)
                        if not host_for_log and current_ip and current_ip in ip_to_hostname_cache:
                            host_for_log = ip_to_hostname_cache[current_ip]

                        # Обновляем last_applied, чтобы SUCCESS писал актуальную стратегию
                        if host_for_log:
                            last_applied[(host_for_log, proto_key)] = int(new_strat)
                            last_applied_host_by_proto[proto_key] = host_for_log

                        if host_for_log:
                            msg = f"[{timestamp}] 🔄 Strategy rotated to {new_strat} ({host_for_log})"
                        else:
                            msg = f"[{timestamp}] 🔄 Strategy rotated to {new_strat}"

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

        # Генерируем circular-config.txt с абсолютными путями
        self._generate_circular_config()

        log("Оркестратор готов к запуску", "INFO")
        log("ℹ️ Оркестратор видит только НОВЫЕ соединения. Для тестирования:", "INFO")
        log("   • Перезапустите браузер или откройте приватное окно", "INFO")
        log("   • Очистите кэш (Ctrl+Shift+Del)", "INFO")
        log("   • Принудительная перезагрузка (Ctrl+F5)", "INFO")
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
            log(f"Командная строка: {' '.join(cmd)}", "DEBUG")

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
        # Загружаем blocked strategies если не загружены (для UI черного списка)
        if not self.blocked_strategies:
            self.load_blocked_strategies()

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

    def load_whitelist(self) -> set:
        """Загружает whitelist из реестра + добавляет системные домены"""
        # 1. Очищаем
        self.user_whitelist = []
        self.whitelist = set()
        
        # 2. Добавляем системные (DEFAULT_WHITELIST_DOMAINS)
        self.whitelist.update(DEFAULT_WHITELIST_DOMAINS)
        default_count = len(DEFAULT_WHITELIST_DOMAINS)
        
        # 3. Загружаем пользовательские из реестра
        try:
            data = reg(REGISTRY_ORCHESTRA, "Whitelist")
            if data:
                self.user_whitelist = json.loads(data)
                # Добавляем в объединённый whitelist
                self.whitelist.update(self.user_whitelist)
                log(f"Загружен whitelist: {default_count} системных + {len(self.user_whitelist)} пользовательских", "DEBUG")
            else:
                log(f"Загружен whitelist: {default_count} системных доменов", "DEBUG")
        except Exception as e:
            log(f"Ошибка загрузки whitelist: {e}", "DEBUG")
        
        return self.whitelist

    def save_whitelist(self):
        """Сохраняет пользовательский whitelist в реестр"""
        try:
            data = json.dumps(self.user_whitelist, ensure_ascii=False)
            reg(REGISTRY_ORCHESTRA, "Whitelist", data)
            log(f"Сохранено {len(self.user_whitelist)} пользовательских доменов в whitelist", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения whitelist: {e}", "ERROR")

    def is_default_whitelist_domain(self, domain: str) -> bool:
        """Проверяет, является ли домен системным (нельзя удалить)"""
        return _is_default_whitelist_domain(domain)

    def get_whitelist(self) -> list:
        """
        Возвращает полный whitelist (default + user) с пометками о типе.
        
        Returns:
            [{'domain': 'vk.com', 'is_default': True}, ...]
        """
        # Загружаем если ещё не загружен
        if not self.whitelist:
            self.load_whitelist()
        
        result = []
        for domain in sorted(self.whitelist):
            result.append({
                'domain': domain,
                'is_default': self.is_default_whitelist_domain(domain)
            })
        return result

    def add_to_whitelist(self, domain: str) -> bool:
        """Добавляет домен в пользовательский whitelist"""
        domain = domain.strip().lower()
        if not domain:
            return False

        # Загружаем текущий whitelist если ещё не загружен
        if not self.whitelist:
            self.load_whitelist()

        # Проверяем что не в системном списке
        if self.is_default_whitelist_domain(domain):
            log(f"Домен {domain} уже в системном whitelist", "DEBUG")
            return False

        # Проверяем что ещё не добавлен пользователем
        if domain in self.user_whitelist:
            log(f"Домен {domain} уже в пользовательском whitelist", "DEBUG")
            return False

        # Добавляем
        self.user_whitelist.append(domain)
        self.whitelist.add(domain)
        self.save_whitelist()
        # Регенерируем whitelist.txt чтобы он был актуален при следующем запуске
        self._generate_whitelist_file()
        log(f"Добавлен в whitelist: {domain}", "INFO")
        return True

    def remove_from_whitelist(self, domain: str) -> bool:
        """Удаляет домен из пользовательского whitelist"""
        domain = domain.strip().lower()

        # Загружаем текущий whitelist если ещё не загружен
        if not self.whitelist:
            self.load_whitelist()

        # Нельзя удалить системный домен
        if self.is_default_whitelist_domain(domain):
            log(f"Нельзя удалить {domain} из системного whitelist", "WARNING")
            return False

        # Проверяем что домен действительно добавлен пользователем
        if domain not in self.user_whitelist:
            log(f"Домен {domain} не найден в пользовательском whitelist", "DEBUG")
            return False

        # Удаляем
        self.user_whitelist.remove(domain)
        self.whitelist.discard(domain)
        self.save_whitelist()
        # Регенерируем whitelist.txt
        self._generate_whitelist_file()
        log(f"Удалён из whitelist: {domain}", "INFO")
        return True

    def _load_ipset_networks(self):
        """
        Загружает ipset подсети для определения игр/сервисов по IP (UDP/QUIC).
        Читает все ipset-*.txt и my-ipset.txt из папки lists.
        """
        if self.ipset_networks:
            return
        try:
            ipset_files = glob.glob(os.path.join(LISTS_FOLDER, "ipset-*.txt"))
            # Добавляем пользовательский ipset
            ipset_files.append(os.path.join(LISTS_FOLDER, "my-ipset.txt"))

            networks: list[tuple[ipaddress._BaseNetwork, str]] = []
            for path in ipset_files:
                if not os.path.exists(path):
                    continue
                base = os.path.basename(path)
                label = os.path.splitext(base)[0]
                if label.startswith("ipset-"):
                    label = label[len("ipset-"):]
                elif label == "my-ipset":
                    label = "my-ipset"
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            try:
                                net = ipaddress.ip_network(line, strict=False)
                                networks.append((net, label))
                            except ValueError:
                                continue
                except Exception as e:
                    log(f"Ошибка чтения {path}: {e}", "DEBUG")

            self.ipset_networks = networks
            if networks:
                log(f"Загружено {len(networks)} ipset подсетей ({len(ipset_files)} файлов)", "DEBUG")
        except Exception as e:
            log(f"Ошибка загрузки ipset подсетей: {e}", "DEBUG")

    def _resolve_ipset_label(self, ip: str) -> Optional[str]:
        """Возвращает имя ipset файла по IP, если найдено соответствие подсети."""
        if not ip or not self.ipset_networks:
            return None
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return None
        for net, label in self.ipset_networks:
            if ip_obj in net:
                return label
        return None

    def _generate_circular_config(self) -> bool:
        """Генерирует circular-config.txt с абсолютными путями к файлам стратегий"""
        try:
            # Загружаем ipset подсети (для отображения игр/сервисов по IP в UDP логах)
            self._load_ipset_networks()

            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write("--wf-tcp-out=80,443-65535\n")
                f.write("--wf-tcp-in=80,443-65535\n")
                # ВАЖНО: без явного UDP-фильтра WinDivert не ловит QUIC/STUN/WireGuard
                f.write("--wf-udp-out=1-65535\n")
                f.write("--wf-udp-in=1-65535\n")
                f.write("--wf-raw-part=@windivert.filter/windivert_part.stun_bidirectional.txt\n")
                f.write("--wf-raw-part=@windivert.filter/windivert_part.discord_bidirectional.txt\n")
                f.write("--wf-raw-part=@windivert.filter/windivert_part.quic_bidirectional.txt\n")
                f.write("--wf-raw-part=@windivert.filter/windivert_part.games_udp_bidirectional.txt\n")
                f.write("\n")
                f.write("--lua-init=@lua/zapret-lib.lua\n")
                f.write("--lua-init=@lua/zapret-antidpi.lua\n")
                f.write("--lua-init=@lua/zapret-auto.lua\n")
                f.write("--lua-init=@lua/custom_funcs.lua\n")
                f.write("--lua-init=@lua/silent-drop-detector.lua\n")
                f.write("--lua-init=@lua/strategy-stats.lua\n")
                f.write("--lua-init=@lua/combined-detector.lua\n")
                f.write("@lua/blobs.txt\n")
                f.write("\n")
                
                # Profile 1: TLS 443
                f.write("# Profile 1: TLS 443\n")
                f.write("--filter-tcp=443\n")
                f.write("--hostlist-exclude=lua/whitelist.txt\n")
                f.write("--in-range=-d1000\n")
                f.write("--out-range=-d1000\n")
                f.write("--lua-desync=circular_quality:fails=1:failure_detector=combined_failure_detector:success_detector=combined_success_detector:lock_successes=3:lock_tests=5:lock_rate=0.6:inseq=0x1000:nld=2\n")
                # НЕ отключаем входящий трафик - нужен для детектора успеха!
                # --in-range=x отключает входящий для всех стратегий
                # Вместо этого ограничим через -d для экономии CPU
                f.write("--in-range=-d1000\n")
                f.write("--out-range=-d1000\n")
                f.write("--payload=tls_client_hello\n")
                
                # Встраиваем TLS стратегии из файла
                if os.path.exists(self.strategies_path):
                    with open(self.strategies_path, 'r', encoding='utf-8') as strat_file:
                        for line in strat_file:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                f.write(line + "\n")
                
                f.write("\n")
                
                # Profile 2: HTTP 80
                f.write("# Profile 2: HTTP 80\n")
                f.write("--new\n")
                f.write("--filter-tcp=80\n")
                f.write("--hostlist-exclude=lua/whitelist.txt\n")
                f.write("--in-range=-d1000\n")
                f.write("--out-range=-d1000\n")
                f.write("--lua-desync=circular_quality:fails=1:failure_detector=combined_failure_detector:success_detector=combined_success_detector:lock_successes=3:lock_tests=5:lock_rate=0.6:inseq=0x1000:nld=2\n")
                # НЕ отключаем входящий трафик - нужен для детектора успеха!
                f.write("--in-range=-d1000\n")
                f.write("--out-range=-d1000\n")
                f.write("--payload=http_req\n")
                
                # Встраиваем HTTP стратегии из файла
                if os.path.exists(self.http_strategies_path):
                    with open(self.http_strategies_path, 'r', encoding='utf-8') as strat_file:
                        for line in strat_file:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                f.write(line + "\n")
                
                f.write("\n")
                
                # Profile 3: UDP
                f.write("# Profile 3: UDP (QUIC, STUN, Discord, WireGuard, Games)\n")
                f.write("--new\n")
                f.write("--filter-udp=443-65535\n")
                f.write("--payload=all\n")
                f.write("--in-range=-d100\n")
                f.write("--out-range=-d100\n")
                f.write("--lua-desync=circular_quality:fails=3:hostkey=udp_global_hostkey:failure_detector=udp_aggressive_failure_detector:success_detector=udp_protocol_success_detector:lock_successes=2:lock_tests=4:lock_rate=0.5:udp_fail_out=3:udp_fail_in=0:udp_in=1:nld=2\n")
                f.write("--in-range=-d100\n")
                f.write("--out-range=-d100\n")
                f.write("--payload=all\n")
                
                # Встраиваем UDP стратегии из файла
                if os.path.exists(self.udp_strategies_path):
                    with open(self.udp_strategies_path, 'r', encoding='utf-8') as strat_file:
                        for line in strat_file:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                f.write(line + "\n")
                
                f.write("\n")
                f.write("--debug=1\n")
            
            log(f"Сгенерирован circular-config.txt", "DEBUG")
            return True
            
        except Exception as e:
            log(f"Ошибка генерации circular-config.txt: {e}", "ERROR")
            return False

    def _generate_whitelist_file(self) -> bool:
        """Генерирует файл whitelist.txt для winws2 --hostlist-exclude"""
        try:
            # Загружаем whitelist если нужно
            if not self.whitelist:
                self.load_whitelist()

            with open(self.whitelist_path, 'w', encoding='utf-8') as f:
                f.write("# Orchestra whitelist - exclude these domains from DPI bypass\n")
                f.write("# System domains (built-in) + User domains (from registry)\n\n")
                for domain in sorted(self.whitelist):
                    f.write(f"{domain}\n")

            system_count = len(DEFAULT_WHITELIST_DOMAINS)
            user_count = len(self.user_whitelist)
            log(f"Сгенерирован whitelist.txt ({system_count} системных + {user_count} пользовательских = {len(self.whitelist)} всего)", "DEBUG")
            return True

        except Exception as e:
            log(f"Ошибка генерации whitelist: {e}", "ERROR")
            return False

    # ==================== BLOCKED STRATEGIES METHODS ====================

    def load_blocked_strategies(self):
        """Загружает заблокированные стратегии из реестра + дефолтные блокировки s1"""
        self.blocked_strategies = {}
        
        # 1. Добавляем дефолтные блокировки: strategy=1 для DEFAULT_BLOCKED_PASS_DOMAINS
        for domain in DEFAULT_BLOCKED_PASS_DOMAINS:
            self.blocked_strategies[domain] = [1]
        default_count = len(DEFAULT_BLOCKED_PASS_DOMAINS)
        
        # 2. Загружаем пользовательские блокировки из реестра (мержим с дефолтными)
        try:
            data = reg_enumerate_values(REGISTRY_ORCHESTRA_BLOCKED)
            for hostname, json_str in data.items():
                try:
                    strategies = json.loads(json_str)
                    if isinstance(strategies, list) and strategies:
                        user_blocked = [int(s) for s in strategies]
                        # Мержим с существующими (дефолтными)
                        if hostname in self.blocked_strategies:
                            existing = set(self.blocked_strategies[hostname])
                            existing.update(user_blocked)
                            self.blocked_strategies[hostname] = list(existing)
                        else:
                            self.blocked_strategies[hostname] = user_blocked
                except (json.JSONDecodeError, ValueError):
                    pass

            user_count = sum(len(s) for s in self.blocked_strategies.values()) - default_count
            if user_count > 0:
                log(f"Загружено {user_count} пользовательских блокировок + {default_count} дефолтных (s1 для заблокированных сайтов)", "DEBUG")
            else:
                log(f"Загружено {default_count} дефолтных блокировок (s1 для заблокированных сайтов)", "DEBUG")
        except Exception as e:
            log(f"Ошибка загрузки blocked strategies: {e}", "DEBUG")

    def save_blocked_strategies(self):
        """Сохраняет заблокированные стратегии в реестр (только пользовательские)"""
        try:
            # Сначала очищаем старые значения
            reg_delete_all_values(REGISTRY_ORCHESTRA_BLOCKED)

            # Сохраняем ТОЛЬКО пользовательские (исключаем дефолтные)
            saved_count = 0
            for hostname, strategies in self.blocked_strategies.items():
                # Фильтруем только пользовательские блокировки
                user_strategies = [s for s in strategies if not self.is_default_blocked(hostname, s)]
                
                if user_strategies:
                    json_str = json.dumps(user_strategies)
                    reg(REGISTRY_ORCHESTRA_BLOCKED, hostname, json_str)
                    saved_count += len(user_strategies)

            log(f"Сохранено {saved_count} пользовательских заблокированных стратегий", "DEBUG")
        except Exception as e:
            log(f"Ошибка сохранения blocked strategies: {e}", "ERROR")

    def get_blocked_strategies(self, hostname: str) -> List[int]:
        """
        Возвращает список заблокированных стратегий для домена.

        Args:
            hostname: Имя домена или IP

        Returns:
            Список номеров заблокированных стратегий
        """
        return self.blocked_strategies.get(hostname.lower(), [])

    def is_strategy_blocked(self, hostname: str, strategy: int) -> bool:
        """
        Проверяет, заблокирована ли стратегия для домена.

        Args:
            hostname: Имя домена или IP
            strategy: Номер стратегии

        Returns:
            True если стратегия заблокирована
        """
        if not hostname:
            return False
        hostname = hostname.lower()
        
        # Прямая проверка в blocked_strategies
        blocked = self.blocked_strategies.get(hostname, [])
        if strategy in blocked:
            return True
        
        # Для strategy=1 проверяем субдомены дефолтных блокировок
        # (cdn.youtube.com -> youtube.com заблокирован)
        if strategy == 1 and _is_default_blocked_pass_domain(hostname):
            return True
        
        return False

    def block_strategy(self, hostname: str, strategy: int, proto: str = "tls"):
        """
        Блокирует стратегию для домена (добавляет в чёрный список).

        Args:
            hostname: Имя домена или IP
            strategy: Номер стратегии
            proto: Протокол (tls/http/udp) - для информации в логах
        """
        hostname = hostname.lower()

        if hostname not in self.blocked_strategies:
            self.blocked_strategies[hostname] = []

        if strategy not in self.blocked_strategies[hostname]:
            self.blocked_strategies[hostname].append(strategy)
            self.blocked_strategies[hostname].sort()
            self.save_blocked_strategies()
            log(f"Заблокирована стратегия #{strategy} для {hostname} [{proto.upper()}]", "INFO")

            if self.output_callback:
                self.output_callback(f"[INFO] Заблокирована стратегия #{strategy} для {hostname}")

    def is_default_blocked(self, hostname: str, strategy: int) -> bool:
        """
        Проверяет, является ли блокировка дефолтной (из DEFAULT_BLOCKED_PASS_DOMAINS).
        Дефолтные блокировки нельзя удалить через GUI.

        Args:
            hostname: Имя домена или IP
            strategy: Номер стратегии

        Returns:
            True если это дефолтная блокировка (strategy=1 для заблокированных сайтов)
        """
        if strategy != 1:
            return False
        return _is_default_blocked_pass_domain(hostname)

    def unblock_strategy(self, hostname: str, strategy: int) -> bool:
        """
        Разблокирует стратегию для домена (удаляет из чёрного списка).
        Дефолтные блокировки (s1 для youtube, google и т.д.) не удаляются.

        Args:
            hostname: Имя домена или IP
            strategy: Номер стратегии

        Returns:
            True если разблокировка успешна, False если это дефолтная блокировка
        """
        hostname = hostname.lower()

        # Проверяем, не дефолтная ли это блокировка
        if self.is_default_blocked(hostname, strategy):
            log(f"Нельзя разблокировать дефолтную блокировку: {hostname} strategy={strategy}", "WARNING")
            return False

        if hostname in self.blocked_strategies:
            if strategy in self.blocked_strategies[hostname]:
                self.blocked_strategies[hostname].remove(strategy)
                
                # Если остались только дефолтные блокировки - удаляем весь ключ из памяти
                # (дефолтные будут добавлены заново при load_blocked_strategies)
                user_strategies = [s for s in self.blocked_strategies[hostname] if not self.is_default_blocked(hostname, s)]
                if not user_strategies:
                    del self.blocked_strategies[hostname]
                
                self.save_blocked_strategies()
                log(f"Разблокирована стратегия #{strategy} для {hostname}", "INFO")

                if self.output_callback:
                    self.output_callback(f"[INFO] Разблокирована стратегия #{strategy} для {hostname}")
                return True
        return False

    def clear_blocked_strategies(self):
        """
        Очищает пользовательский чёрный список стратегий.
        Дефолтные блокировки (s1 для youtube, google и т.д.) сохраняются.
        """
        # Считаем только пользовательские блокировки
        user_count = 0
        for hostname, strategies in list(self.blocked_strategies.items()):
            for strategy in list(strategies):
                if not self.is_default_blocked(hostname, strategy):
                    user_count += 1

        # Очищаем реестр (там только пользовательские)
        reg_delete_all_values(REGISTRY_ORCHESTRA_BLOCKED)

        # Перезагружаем blocked_strategies (останутся только дефолтные)
        self.load_blocked_strategies()

        log(f"Очищен пользовательский чёрный список ({user_count} записей)", "INFO")

        if self.output_callback:
            self.output_callback(f"[INFO] Очищен пользовательский чёрный список ({user_count} записей)")

    # ==================== LOCK/UNLOCK STRATEGIES METHODS ====================

    def lock_strategy(self, hostname: str, strategy: int, proto: str = "tls"):
        """
        Залочивает (фиксирует) стратегию для домена вручную.

        Args:
            hostname: Имя домена или IP
            strategy: Номер стратегии
            proto: Протокол (tls/http/udp)
        """
        hostname = hostname.lower()
        proto = proto.lower()

        # Выбираем нужный словарь и реестр
        if proto == "http":
            target_dict = self.http_locked_strategies
            reg_path = REGISTRY_ORCHESTRA_HTTP
        elif proto == "udp":
            target_dict = self.udp_locked_strategies
            reg_path = REGISTRY_ORCHESTRA_UDP
        else:  # tls
            target_dict = self.locked_strategies
            reg_path = REGISTRY_ORCHESTRA_TLS

        # Сохраняем стратегию
        target_dict[hostname] = strategy
        reg(reg_path, hostname, strategy)

        # Не инициализируем историю - пусть статистика наберётся сама
        # при реальном использовании стратегии

        log(f"Залочена стратегия #{strategy} для {hostname} [{proto.upper()}]", "INFO")

        if self.output_callback:
            self.output_callback(f"[INFO] 🔒 Залочена стратегия #{strategy} для {hostname} [{proto.upper()}]")

    def unlock_strategy(self, hostname: str, proto: str = "tls"):
        """
        Разлочивает (снимает фиксацию) стратегию для домена.

        Args:
            hostname: Имя домена или IP
            proto: Протокол (tls/http/udp)
        """
        hostname = hostname.lower()
        proto = proto.lower()

        # Выбираем нужный словарь и реестр
        if proto == "http":
            target_dict = self.http_locked_strategies
            reg_path = REGISTRY_ORCHESTRA_HTTP
        elif proto == "udp":
            target_dict = self.udp_locked_strategies
            reg_path = REGISTRY_ORCHESTRA_UDP
        else:  # tls
            target_dict = self.locked_strategies
            reg_path = REGISTRY_ORCHESTRA_TLS

        if hostname in target_dict:
            old_strategy = target_dict[hostname]
            del target_dict[hostname]
            # Удаляем из реестра
            try:
                reg(reg_path, hostname, None)  # None = удалить значение
            except Exception:
                pass  # Может не существовать

            log(f"Разлочена стратегия #{old_strategy} для {hostname} [{proto.upper()}]", "INFO")

            if self.output_callback:
                self.output_callback(f"[INFO] 🔓 Разлочена стратегия для {hostname} [{proto.upper()}] — начнётся переобучение")
