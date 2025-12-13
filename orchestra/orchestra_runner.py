# orchestra/orchestra_runner.py
"""
Circular Orchestra Runner - автоматическое обучение стратегий DPI bypass.

Использует circular orchestrator из zapret-auto.lua (файл менять этот нельзя) с:
- combined_failure_detector (RST injection + silent drop)
- strategy_stats (LOCK механизм после 3 успехов, UNLOCK после 2 failures)
- domain_grouping (группировка субдоменов)

Логи - только Python (компактные), без огромных winws2 debug логов.
"""

import os
import subprocess
import threading
import re
import json
from typing import Optional, Callable, Dict
from datetime import datetime

from log import log
from config import MAIN_DIRECTORY, EXE_FOLDER, LUA_FOLDER, LOGS_FOLDER, BIN_FOLDER, REGISTRY_PATH
from config.reg import reg, reg_enumerate_values, reg_delete_all_values

# Пути в реестре для хранения обученных стратегий (subkeys)
REGISTRY_ORCHESTRA = f"{REGISTRY_PATH}\\Orchestra"
REGISTRY_ORCHESTRA_TLS = f"{REGISTRY_ORCHESTRA}\\TLS"      # TLS стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HTTP = f"{REGISTRY_ORCHESTRA}\\HTTP"    # HTTP стратегии: domain=strategy (REG_DWORD)
REGISTRY_ORCHESTRA_HISTORY = f"{REGISTRY_ORCHESTRA}\\History"  # История: domain=JSON (REG_SZ)

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
]

# Константы для скрытого запуска процесса
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000
STARTF_USESHOWWINDOW = 0x00000001


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

        # Белый список (exclude hostlist)
        self.whitelist_path = os.path.join(self.lua_path, "whitelist.txt")

        # Debug log от winws2 (для детекции LOCKED/UNLOCKING)
        self.debug_log_path = os.path.join(self.logs_path, "winws2_orchestra.log")
        # Загружаем настройку сохранения debug файла из реестра
        saved_debug = reg(f"{REGISTRY_PATH}\\Orchestra", "KeepDebugFile")
        self.keep_debug_file = bool(saved_debug)

        # Состояние
        self.running_process: Optional[subprocess.Popen] = None
        self.output_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Обученные стратегии (TLS и HTTP отдельно)
        self.locked_strategies: Dict[str, int] = {}      # TLS (tls_client_hello)
        self.http_locked_strategies: Dict[str, int] = {}  # HTTP (http)

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

            total = len(self.locked_strategies) + len(self.http_locked_strategies)
            if total:
                log(f"Загружено {len(self.locked_strategies)} TLS + {len(self.http_locked_strategies)} HTTP стратегий", "INFO")

        except Exception as e:
            log(f"Ошибка загрузки стратегий из реестра: {e}", "DEBUG")

        # Загружаем историю
        self.load_history()

        return self.locked_strategies

    def save_strategies(self):
        """Сохраняет locked стратегии в реестр (subkeys: TLS и HTTP)"""
        try:
            # TLS стратегии - каждый домен отдельным значением
            for domain, strategy in self.locked_strategies.items():
                reg(REGISTRY_ORCHESTRA_TLS, domain, int(strategy))

            # HTTP стратегии - каждый домен отдельным значением
            for domain, strategy in self.http_locked_strategies.items():
                reg(REGISTRY_ORCHESTRA_HTTP, domain, int(strategy))

            log(f"Сохранено {len(self.locked_strategies)} TLS + {len(self.http_locked_strategies)} HTTP стратегий", "DEBUG")

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
        Генерирует learned-strategies.lua для предзагрузки стратегий и истории в winws2.

        Returns:
            Путь к файлу или None если нет данных
        """
        # Авто-LOCK: если в истории есть домен с >= 3 успехов, добавляем в locked_strategies
        LOCK_THRESHOLD = 3
        for hostname, strategies in self.strategy_history.items():
            # Пропускаем если уже есть locked стратегия для этого домена
            if hostname in self.locked_strategies:
                continue

            # Ищем стратегию с максимальным числом успехов (>= порога)
            best_strat = None
            best_successes = 0
            for strat_key, data in strategies.items():
                successes = data.get('successes', 0)
                if successes >= LOCK_THRESHOLD and successes > best_successes:
                    best_strat = int(strat_key)
                    best_successes = successes

            if best_strat is not None:
                self.locked_strategies[hostname] = best_strat
                log(f"Авто-LOCK из истории: {hostname} = strategy {best_strat} ({best_successes} успехов)", "INFO")

        # Сохраняем авто-locked стратегии в реестр
        if self.locked_strategies or self.http_locked_strategies:
            self.save_strategies()

        has_strategies = self.locked_strategies or self.http_locked_strategies
        has_history = bool(self.strategy_history)

        if not has_strategies and not has_history:
            return None

        lua_path = os.path.join(self.lua_path, "learned-strategies.lua")
        total_tls = len(self.locked_strategies)
        total_http = len(self.http_locked_strategies)
        total_history = len(self.strategy_history)

        try:
            with open(lua_path, 'w', encoding='utf-8') as f:
                f.write("-- Auto-generated: preload learned strategies and history\n")
                f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- TLS: {total_tls}, HTTP: {total_http}, History domains: {total_history}\n\n")

                # TLS/HTTP strategy_preload ПОЛНОСТЬЮ ОТКЛЮЧЕН
                # Проблема: даже без создания autostate, вызовы strategy_preload крашат winws2
                # Возможные причины:
                # 1. Слишком много вызовов подряд перегружают Lua
                # 2. Какой-то конфликт в working_strategies таблице
                # 3. Проблема в самом winws2 при большом количестве preload записей
                #
                # История (strategy_preload_history) работает - она только заполняет статистику
                # без влияния на runtime поведение circular

                # История стратегий (для рейтинга и выбора лучшей)
                if self.strategy_history:
                    f.write("\n-- Strategy history (for ratings)\n")
                    for hostname, strategies in self.strategy_history.items():
                        safe_host = hostname.replace('\\', '\\\\').replace('"', '\\"')
                        for strat_key, data in strategies.items():
                            s = data.get('successes', 0)
                            f_count = data.get('failures', 0)
                            f.write(f'strategy_preload_history("{safe_host}", {strat_key}, {s}, {f_count})\n')

                f.write(f"\nDLOG(\"learned-strategies: preloaded {total_tls} TLS + {total_http} HTTP + {total_history} history\")\n")

            log(f"Сгенерирован learned-strategies.lua ({total_tls} TLS + {total_http} HTTP + {total_history} history)", "DEBUG")
            return lua_path

        except Exception as e:
            log(f"Ошибка генерации learned-strategies.lua: {e}", "ERROR")
            return None

    def _clear_debug_log(self):
        """Очищает предыдущий debug log"""
        try:
            if os.path.exists(self.debug_log_path):
                os.remove(self.debug_log_path)
        except Exception as e:
            log(f"Не удалось очистить debug.log: {e}", "DEBUG")

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
        Генерирует strategies-all.txt и strategies-http-all.txt с автоматической нумерацией.

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

        return True

    def _read_output(self):
        """Поток чтения stdout от winws2 (debug=1 выводит в консоль)"""
        # Patterns now include optional [TLS]/[HTTP] tag
        lock_pattern = re.compile(r"LOCKED (\S+) to strategy=(\d+)(?:\s+\[(TLS|HTTP)\])?")
        unlock_pattern = re.compile(r"UNLOCKING (\S+)(?:\s+\[(TLS|HTTP)\])?")
        sticky_pattern = re.compile(r"STICKY (\S+) to strategy=(\d+)")
        preload_pattern = re.compile(r"PRELOADED (\S+) = strategy (\d+)(?:\s+\[(tls|http)\])?")
        # HISTORY hostname strategy=N successes=X failures=Y rate=Z%
        history_pattern = re.compile(r"HISTORY (\S+) strategy=(\d+) successes=(\d+) failures=(\d+) rate=(\d+)%")
        # SUCCESS hostname strategy=N count=X [LOCKED]
        success_pattern = re.compile(r"strategy-stats: SUCCESS (\S+) strategy=(\d+)")
        # FAIL hostname strategy=N
        fail_pattern = re.compile(r"strategy-stats: FAIL (\S+) strategy=(\d+)")

        # Счётчик для периодического сохранения истории
        history_save_counter = 0

        # Открываем файл для записи если нужно
        debug_file = None
        if self.keep_debug_file:
            try:
                os.makedirs(os.path.dirname(self.debug_log_path), exist_ok=True)
                debug_file = open(self.debug_log_path, 'w', encoding='utf-8')
            except Exception as e:
                log(f"Не удалось открыть debug файл: {e}", "WARNING")

        if self.running_process and self.running_process.stdout:
            try:
                for line in self.running_process.stdout:
                    if self.stop_event.is_set():
                        break

                    line = line.rstrip()
                    if not line:
                        continue

                    # Пишем в файл если нужно
                    if debug_file:
                        try:
                            debug_file.write(line + '\n')
                            debug_file.flush()
                        except:
                            pass

                    # Проверяем LOCKED
                    match = lock_pattern.search(line)
                    if match:
                        host, strat, ptype = match.groups()
                        strat = int(strat)
                        is_http = (ptype and ptype.upper() == "HTTP")

                        # Выбираем словарь: HTTP или TLS
                        target_dict = self.http_locked_strategies if is_http else self.locked_strategies

                        if host not in target_dict or target_dict[host] != strat:
                            target_dict[host] = strat
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            proto_tag = " [HTTP]" if is_http else ""
                            msg = f"[{timestamp}] LOCKED: {host} = strategy {strat}{proto_tag}"
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
                        is_http = (ptype and ptype.upper() == "HTTP")

                        # Выбираем словарь
                        target_dict = self.http_locked_strategies if is_http else self.locked_strategies

                        if host in target_dict:
                            del target_dict[host]
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            proto_tag = " [HTTP]" if is_http else ""
                            msg = f"[{timestamp}] UNLOCKED: {host}{proto_tag} - re-learning..."
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
                        host, strat = match.groups()
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] PRELOADED: {host} = strategy {strat}"
                        if self.output_callback:
                            self.output_callback(msg)
                        continue

                    # Проверяем HISTORY (статистика стратегий)
                    match = history_pattern.search(line)
                    if match:
                        host, strat, successes, failures, rate = match.groups()
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
                        host, strat = match.groups()
                        strat = int(strat)
                        self._increment_history(host, strat, is_success=True)
                        history_save_counter += 1

                        # Выводим в UI
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] ✓ SUCCESS: {host} strategy={strat}"
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
                        host, strat = match.groups()
                        strat = int(strat)
                        self._increment_history(host, strat, is_success=False)
                        history_save_counter += 1

                        # Выводим в UI
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] ✗ FAIL: {host} strategy={strat}"
                        if self.output_callback:
                            self.output_callback(msg)

                        # Сохраняем каждые 5 событий
                        if history_save_counter >= 5:
                            self.save_history()
                            history_save_counter = 0
                        continue

                    # НЕ выводим сырые логи winws2 - только обработанные события выше
                    # (LOCKED, UNLOCKED, SUCCESS, FAIL)
                    pass

            except Exception as e:
                log(f"Read output error: {e}", "DEBUG")
            finally:
                # Сохраняем историю при завершении
                if self.strategy_history:
                    self.save_history()
                if debug_file:
                    try:
                        debug_file.close()
                    except:
                        pass

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
            "domain-grouping.lua",
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

        # Загружаем предыдущие стратегии
        self.load_existing_strategies()

        # Генерируем Lua файл для предзагрузки стратегий
        # NOTE: strategy_preload отключен, генерируется только history
        learned_lua = self._generate_learned_lua()

        # Сбрасываем stop event
        self.stop_event.clear()

        try:
            # Запускаем winws2 с @config_file + debug=1 (вывод в stdout для парсинга)
            cmd = [self.winws_exe, f"@{self.config_path}"]

            # Добавляем предзагрузку стратегий если есть
            if learned_lua:
                cmd.append(f"--lua-init=@{learned_lua}")

            cmd.append("--debug=1")

            log_msg = f"Запуск: winws2.exe @{os.path.basename(self.config_path)}"
            if learned_lua:
                log_msg += f" +{len(self.locked_strategies)} preloaded"
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

            # Чтение stdout (парсим LOCKED/UNLOCKING, опционально пишем в файл)
            self.output_thread = threading.Thread(target=self._read_output, daemon=True)
            self.output_thread.start()

            log(f"Оркестратор запущен (PID: {self.running_process.pid})", "INFO")

            print(f"[DEBUG start] output_callback={self.output_callback}")  # DEBUG
            if self.output_callback:
                print("[DEBUG start] calling output_callback...")  # DEBUG
                self.output_callback(f"[INFO] Оркестратор запущен (PID: {self.running_process.pid})")
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

            # Удаляем debug файл если не нужно сохранять
            if not self.keep_debug_file:
                self._clear_debug_log()

            log(f"Оркестратор остановлен. Сохранено {len(self.locked_strategies)} стратегий, история для {len(self.strategy_history)} доменов", "INFO")

            if self.output_callback:
                self.output_callback(f"[INFO] Оркестратор остановлен")

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
        Очищает данные обучения для переобучения с нуля (TLS, HTTP и история).

        Returns:
            True если очистка успешна
        """
        try:
            # Очищаем subkeys (удаляем все значения в каждом)
            reg_delete_all_values(REGISTRY_ORCHESTRA_TLS)
            reg_delete_all_values(REGISTRY_ORCHESTRA_HTTP)
            reg_delete_all_values(REGISTRY_ORCHESTRA_HISTORY)
            log("Очищены обученные стратегии и история в реестре", "INFO")

            self.locked_strategies = {}
            self.http_locked_strategies = {}
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
                'history': {hostname: {strategy: {successes, failures, rate}}}
            }
        """
        # Загружаем актуальные данные если еще не загружены
        if not self.locked_strategies and not self.http_locked_strategies:
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
