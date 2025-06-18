# manager.py
#
# «Ленивый» StrategyManager:
#   • при создании НЕ лезет в сеть (если preload=False);
#   • при первом вызове preload_strategies() / get_strategies_list()
#     всё скачивает и помечает already_loaded=True;
#   • второй и последующие вызовы preload_strategies() ничего не делают.
#
# Добавлены:
#   • параметр   preload: bool = False   в __init__
#   • флаг       self._loaded
#   • свойство   already_loaded
#   • ранний return в preload_strategies()
#
# Остальной код – ваш прежний, лишь слегка отформатирован для компакт-
# ности.  Логика скачивания .bat-файлов, проверка версий и т. д.
# сохранена 1-в-1.

import os, time, json, requests, subprocess
from urllib.parse import urljoin
from log import log
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import signal

from config.backup_urls import URL_SOURCES
SW_HIDE          = 0
CREATE_NO_WINDOW = 0x08000000


class StrategyManager:
    """
    Управление «стратегиями» (bat-файлами) на GitHub / GitFlic.
    """

    # ─────────────────────────────── init ──────────────────────────────
    def __init__(self,
                 local_dir: str,
                 status_callback=None,
                 json_url: str | None = None,
                 preload: bool = False) -> None:
        """
        local_dir      – куда сохраняем bat-файлы и index.json
        status_callback– функция-коллбек для сообщений в GUI / консоль
        json_url       – прямая ссылка на index.json (если есть)
        preload        – True ⇒ сразу скачивать index + bat-файлы
        """
        self.local_dir       = local_dir
        self.status_callback = status_callback
        self.json_url        = json_url

        self.strategies_cache: dict[str, dict] = {}
        self.cache_loaded = False  # Флаг что кэш уже загружен
        self.last_update_time = 0
        self.update_interval  = 3600          # 1 ч

        # Добавляем настройки для обработки зависаний
        self.download_timeout = 30  # таймаут для скачивания
        self.max_retries = 3        # максимум попыток
        self.retry_delay = 2        # задержка между попытками

        # Добавляем поддержку резервных источников
        self.current_source_index = 0
        self.url_sources = URL_SOURCES
        self.failed_sources = set()  # Источники, которые не работают

        os.makedirs(self.local_dir, exist_ok=True)

        # ленивая загрузка: ничего не качаем, только если явно попросили
        self._loaded = False
        if preload:
            # Проверяем настройку автозагрузки перед preload
            from config.reg import get_strategy_autoload
            if get_strategy_autoload():
                self.preload_strategies()
            else:
                log("Автозагрузка стратегий отключена - пропуск preload", "INFO")

    def _get_next_working_source(self):
        """Находит следующий рабочий источник"""
        for i, source in enumerate(self.url_sources):
            if i not in self.failed_sources:
                return i, source
        return None, None

    def _download_strategies_index(self) -> dict:
        """Внутренний метод для скачивания index.json с резервными источниками."""
        # Проверяем настройку автозагрузки
        from config.reg import get_strategy_autoload
        if not get_strategy_autoload():
            log("Автозагрузка стратегий отключена - прерываем загрузку", "INFO")
            self.set_status("Автозагрузка стратегий отключена")
            return self._load_local_cache()

        self.set_status("Получение списка стратегий…")
        
        # Пробуем все доступные источники
        for source_index, source in enumerate(self.url_sources):
            if source_index in self.failed_sources:
                continue
                
            index_url = source["json_url"]
            source_name = source["name"]
            
            log(f"Пробуем источник {source_name}: {index_url}", "DEBUG")
            self.set_status(f"Подключение к {source_name}...")

            last_error = None
            for attempt in range(self.max_retries):
                try:
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                        'Cache-Control': 'no-cache',
                        'Connection': 'close'
                    })
                    
                    response = session.get(
                        index_url, 
                        timeout=(15, 45),
                        stream=False
                    )
                    response.raise_for_status()
                    
                    if len(response.content) == 0:
                        raise ValueError("Получен пустой ответ")
                    
                    # ИСПРАВЛЕНИЕ: Сохраняем результат в переменные класса
                    result = response.json()
                    self.strategies_cache = result
                    self.cache_loaded = True
                    self.last_update_time = time.time()
                    self._loaded = True
                    
                    # Сохраняем на диск
                    self.save_strategies_index(result)
                    
                    # Обновляем текущий рабочий источник
                    self.current_source_index = source_index
                    
                    self.set_status(f"Получено стратегий: {len(result)} ({source_name})")
                    log(f"OK с {source_name}, {len(result)} шт.", "INFO")
                    return result

                except Exception as e:
                    last_error = e
                    log(f"Попытка {attempt + 1}/{self.max_retries} для {source_name} не удалась: {e}", "DEBUG")
                    
                    if attempt < self.max_retries - 1:
                        if "403" in str(e):
                            sleep_time = self.retry_delay * (2 ** attempt)
                        else:
                            sleep_time = self.retry_delay * (attempt + 1)
                        
                        time.sleep(sleep_time)
                        self.set_status(f"Повтор попытки {attempt + 2}/{self.max_retries} для {source_name}...")

            # Все попытки для этого источника неудачны
            log(f"Источник {source_name} недоступен: {last_error}", "WARNING")
            self.failed_sources.add(source_index)
            self.set_status(f"Источник {source_name} недоступен, пробуем следующий...")

        # Все источники исчерпаны
        log("Все источники недоступны", "ERROR")
        raise last_error or Exception("Все резервные источники недоступны")
    
    def _download_strategy_sync(self, strategy_id: str) -> str | None:
        """Синхронная версия скачивания стратегии с поддержкой резервных источников."""
        try:
            strategies = self.get_strategies_list()
            if strategy_id not in strategies:
                self.set_status(f"Стратегия {strategy_id} не найдена")
                return None

            info = strategies[strategy_id]
            remote_path = info.get("file_path", f"{strategy_id}.bat")
            filename = os.path.basename(remote_path)
            local_path = os.path.join(self.local_dir, filename)
            need_download = True

            # Проверка версии / времени
            if os.path.isfile(local_path):
                if "version" in info:
                    local_ver = self.get_local_strategy_version(local_path, strategy_id)
                    if local_ver == info["version"]:
                        need_download = False
                else:
                    age = time.time() - os.path.getmtime(local_path)
                    if age < 3600:
                        need_download = False

            if not need_download:
                self.set_status(f"Локальная копия {strategy_id} актуальна")
                return local_path

            # Скачивание с резервных источников
            self.set_status(f"Скачивание {strategy_id}…")
            
            # Пробуем источники в порядке приоритета
            for source_index, source in enumerate(self.url_sources):
                if source_index in self.failed_sources:
                    continue
                    
                url = source["raw_template"].format(remote_path)
                source_name = source["name"]
                
                log(f"Скачиваем {strategy_id} с {source_name}", "DEBUG")
                
                last_error = None
                for attempt in range(self.max_retries):
                    try:
                        session = requests.Session()
                        session.headers.update({
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': '*/*',
                            'Connection': 'close'
                        })
                        
                        response = session.get(
                            url, 
                            timeout=(15, 45),
                            stream=True  # Для больших файлов
                        )
                        response.raise_for_status()
                        
                        if not response.content:
                            raise RuntimeError("Получен пустой файл")

                        with open(local_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)

                        if "version" in info:
                            self.save_strategy_version(local_path, info)

                        self.set_status(f"{strategy_id} скачана с {source_name}")
                        log(f"{strategy_id} OK с {source_name} ({len(response.content)} B)", "INFO")
                        return local_path

                    except Exception as e:
                        last_error = e
                        log(f"Попытка {attempt + 1} скачивания {strategy_id} с {source_name}: {e}", "DEBUG")
                        
                        if attempt < self.max_retries - 1:
                            if "403" in str(e):
                                sleep_time = self.retry_delay * (2 ** attempt)
                            else:
                                sleep_time = self.retry_delay
                            time.sleep(sleep_time)

                # Все попытки для этого источника неудачны
                log(f"Не удалось скачать {strategy_id} с {source_name}: {last_error}", "WARNING")

            # Все источники исчерпаны
            raise Exception(f"Не удалось скачать {strategy_id} ни с одного источника")

        except Exception as e:
            log(f"{strategy_id} DL error: {e}", "ERROR")
            self.set_status(f"Ошибка загрузки {strategy_id}: {e}")
            return local_path if os.path.isfile(local_path) else None
        
    # ────────────────────────── свойства / util ───────────────────────
    @property
    def already_loaded(self) -> bool:
        """True после первой успешной preload_strategies()."""
        return self._loaded

    def set_status(self, text: str) -> None:
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)

    # ─────────────────────── index.json (GET) ─────────────────────────
    def get_strategies_list(self, *, force_update: bool = False) -> dict:
        """
        Возвращает словарь стратегий с ПРАВИЛЬНЫМ кэшированием.
        """

        # После первой успешной загрузки index.json — возвращаем только из памяти
        if self._loaded and self.strategies_cache and not force_update:
            log("get_strategies_list: уже загружено, возвращаю из кеша", "DEBUG")
            return self.strategies_cache

        # ПЕРВЫЙ ПРИОРИТЕТ: Если кэш уже загружен и не нужно принудительное обновление
        if self.cache_loaded and self.strategies_cache and not force_update:
            return self.strategies_cache

        # ВТОРОЙ ПРИОРИТЕТ: Проверяем автозагрузку (только если еще не загружены)
        if not force_update and not self.cache_loaded:
            from config.reg import get_strategy_autoload
            if not get_strategy_autoload():
                return self._load_local_cache()

        # ТРЕТИЙ ПРИОРИТЕТ: Проверяем нужна ли загрузка по времени
        if not force_update and self.cache_loaded:
            now = time.time()
            if (now - self.last_update_time) <= self.update_interval:
                return self.strategies_cache

        # ТОЛЬКО ЗДЕСЬ загружаем с сервера
        return self._download_and_cache()
    
    def _load_local_cache(self) -> dict:
        """Загружает локальный кэш index.json ОДИН РАЗ."""
        # Если уже загружен в память - возвращаем сразу
        if self.cache_loaded and self.strategies_cache:
            return self.strategies_cache
            
        index_file = os.path.join(self.local_dir, "index.json")
        if os.path.isfile(index_file):
            try:
                with open(index_file, encoding="utf-8") as f:
                    self.strategies_cache = json.load(f)
                self.cache_loaded = True
                self._loaded = True
                self.last_update_time = os.path.getmtime(index_file)
                log("Загружен локальный index.json", "INFO")
                return self.strategies_cache
            except Exception as e:
                log(f"Ошибка чтения локального индекса: {e}", "ERROR")
        
        self.strategies_cache = {}
        self.cache_loaded = True
        return self.strategies_cache

    def _download_and_cache(self) -> dict:
        """Скачивает данные с сервера и кэширует ОДИН РАЗ."""
        log("Обновление списка стратегий...", "INFO")
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(self._download_strategies_index)
                result = future.result(timeout=self.download_timeout * len(self.url_sources))
                
                # УБИРАЕМ дублирование - кэш уже сохранен в _download_strategies_index()
                return result
            except Exception as e:
                log(f"Ошибка загрузки: {e}", "ERROR")
                return self._load_local_cache()

    def check_strategy_version_status(self, strategy_id: str) -> str:
        """
        Проверяет статус версии стратегии.
        Возвращает: 'current', 'outdated', 'not_downloaded', 'unknown'
        """
        try:
            strategies = self.get_strategies_list()
            if strategy_id not in strategies:
                return 'unknown'
                
            info = strategies[strategy_id]
            remote_path = info.get("file_path", f"{strategy_id}.bat")
            filename = os.path.basename(remote_path)
            local_path = os.path.join(self.local_dir, filename)
            
            # Если файл не скачан
            if not os.path.isfile(local_path):
                return 'not_downloaded'
                
            # Если есть информация о версии
            if "version" in info:
                local_ver = self.get_local_strategy_version(local_path, strategy_id)
                remote_ver = info["version"]
                
                if local_ver is None:
                    return 'unknown'
                elif local_ver == remote_ver:
                    return 'current'
                else:
                    return 'outdated'
            else:
                # Проверяем по времени модификации (если нет версии)
                age = time.time() - os.path.getmtime(local_path)
                if age > 86400:  # старше суток
                    return 'outdated'
                else:
                    return 'current'
                    
        except Exception as e:
            log(f"Ошибка проверки версии стратегии {strategy_id}: {e}", "DEBUG")
            return 'unknown'
    
    def save_strategies_index(self, data: dict = None) -> bool:
        """Сохраняет index.json на диск"""
        cache_data = data or self.strategies_cache
        if not cache_data:
            return False
        try:
            with open(os.path.join(self.local_dir, "index.json"),
                      "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log(f"index.json save error: {e}", "ERROR")
            return False

    # ───────────────────────── preload () ─────────────────────────────
    def preload_strategies(self) -> None:
        """
        Скачивает только index.json (без bat-файлов).
        Повторный вызов после успешной загрузки делает ничего.
        """
        if self._loaded:
            log("preload_strategies(): уже загружено – пропуск", "DEBUG")
            return

        from config.reg import get_strategy_autoload
        if not get_strategy_autoload():
            log("Автозагрузка стратегий отключена - пропуск preload", "INFO")
            self.set_status("Автозагрузка стратегий отключена")
            return

        log("Preload стратегий (только индекс)…", "INFO")
        strategies = self.get_strategies_list()
        if not strategies:
            log("Список стратегий пуст – preload отменён", "ERROR")
            return

        self._loaded = True
        log("Preload индекса завершён", "INFO")
    
    # ─────────────────────── download 1 strategy ──────────────────────
    def download_strategy(self, strategy_id: str) -> str | None:
        """
        Скачивает стратегию с улучшенной обработкой зависаний.
        """
        # Для загрузки отдельных стратегий проверяем настройку только если это не принудительная загрузка
        # (например, из GUI пользователь может захотеть скачать стратегию даже при отключенной автозагрузке)
    
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(self._download_strategy_sync, strategy_id)
                return future.result(timeout=self.download_timeout)
            except TimeoutError:
                log(f"Таймаут при скачивании {strategy_id}", "ERROR")
                self.set_status(f"Таймаут скачивания {strategy_id}")
                
                # Возвращаем локальную копию если есть
                strategies = self.strategies_cache or self._load_local_cache()
                if strategy_id in strategies:
                    info = strategies[strategy_id]
                    remote_path = info.get("file_path", f"{strategy_id}.bat")
                    filename = os.path.basename(remote_path)
                    local_path = os.path.join(self.local_dir, filename)
                    return local_path if os.path.isfile(local_path) else None
                return None

    # ─────────────────────────── version util ─────────────────────────
    def get_local_strategy_version(self, file_path, strategy_id):
        try:
            meta = os.path.join(self.local_dir, "strategy_versions.json")
            if os.path.isfile(meta):
                with open(meta, encoding="utf-8") as f:
                    versions = json.load(f)
                if strategy_id in versions:
                    return versions[strategy_id]

            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "VERSION:" in line:
                        return line.split("VERSION:")[1].strip()
        except Exception as e:
            log(f"ver check error: {e}", "DEBUG")
        return None

    def save_strategy_version(self, file_path, info) -> bool:
        try:
            sid = next((k for k, v in self.strategies_cache.items()
                        if v == info), None)
            if not sid:
                return False

            meta = os.path.join(self.local_dir, "strategy_versions.json")
            vers = {}
            if os.path.isfile(meta):
                with open(meta, encoding="utf-8") as f:
                    vers = json.load(f)
            vers[sid] = info.get("version", "1.0")
            with open(meta, "w", encoding="utf-8") as f:
                json.dump(vers, f, ensure_ascii=False, indent=2)

            # добавляем ремарку в .bat
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                header = (
                    "@echo off\n"
                    f"REM Стратегия {info.get('name', sid)}\n"
                    f"REM VERSION: {info.get('version', '1.0')}\n\n"
                )
                if not content.startswith("@echo off"):
                    content = header + content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                log(f"bat header warn: {e}", "DEBUG")

            return True
        except Exception as e:
            log(f"save ver error: {e}", "ERROR")
            return False

    def check_sources_availability(self) -> dict:
        """Проверяет доступность всех источников"""
        results = {}
        
        for i, source in enumerate(self.url_sources):
            source_name = source["name"]
            test_url = source["json_url"]
            
            try:
                self.set_status(f"Проверка {source_name}...")
                
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Connection': 'close'
                })
                
                response = session.get(test_url, timeout=(10, 20))
                response.raise_for_status()
                
                results[source_name] = {
                    "status": "OK",
                    "response_time": response.elapsed.total_seconds(),
                    "size": len(response.content)
                }
                
                # Убираем из списка неудачных если проверка прошла
                if i in self.failed_sources:
                    self.failed_sources.discard(i)
                    
            except Exception as e:
                results[source_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                self.failed_sources.add(i)
        
        self.set_status("Проверка источников завершена")
        return results