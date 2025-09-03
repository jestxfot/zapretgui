# strategy_menu/manager.py

import os, time, json, requests, subprocess
from log import log
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from config.backup_urls import URL_SOURCES
from config import INDEXJSON_FOLDER
SW_HIDE          = 0
CREATE_NO_WINDOW = 0x08000000


class StrategyManager:
    """
    Управление «стратегиями» (bat-файлами) на GitHub / GitFlic.
    """

    # ─────────────────────────────── init ──────────────────────────────
    def __init__(self, local_dir: str, json_dir: str, status_callback=None, **kwargs):
        """
        local_dir      – где хранятся bat-файлы
        json_dir       – где хранится index.json
        status_callback– функция для сообщений в GUI
        """
        self.local_dir = local_dir
        self.json_dir = json_dir
        self.status_callback = status_callback
        
        self.strategies_cache: dict[str, dict] = {}
        self.cache_loaded = False
        self._loaded = False
        
        os.makedirs(self.local_dir, exist_ok=True)
        
        # Сразу загружаем локальный кэш при инициализации
        self._load_local_cache()
        log(f"Strategy Manager инициализирован (без загрузки из интернета)", "INFO")

    @property
    def already_loaded(self) -> bool:
        """True после загрузки локального кэша."""
        return self._loaded

    def set_status(self, text: str) -> None:
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)

    def get_local_strategies_only(self) -> dict:
        """Возвращает только локальные стратегии"""
        return self.get_strategies_list()
    
    def download_strategies_index_from_internet(self) -> dict:
        """ЗАГЛУШКА: загрузка из интернета отключена"""
        log("Загрузка из интернета отключена", "⚠ WARNING")
        return self.strategies_cache
    
    def download_single_strategy_bat(self, strategy_id: str) -> str | None:
        """ЗАГЛУШКА: загрузка из интернета отключена"""
        log(f"Загрузка стратегии {strategy_id} из интернета отключена", "⚠ WARNING")
        return None
    
    def preload_strategies(self) -> None:
        """Загружает локальный кэш стратегий."""
        if self._loaded:
            log("Стратегии уже загружены", "DEBUG")
            return
        
        self._load_local_cache()
        log(f"Preload завершён: {len(self.strategies_cache)} стратегий", "⚙ manager")

    def _get_next_working_source(self):
        """Находит следующий рабочий источник"""
        for i, source in enumerate(self.url_sources):
            if i not in self.failed_sources:
                return i, source
        return None, None

    def _download_strategies_index(self) -> dict:
        """Внутренний метод для скачивания index.json с резервными источниками."""
        # Проверяем настройку автозагрузки

        self.set_status("Получение списка стратегий…")
        
        last_error = None  # Инициализируем переменную ДО циклов
        
        # Пробуем все доступные источники
        for source_index, source in enumerate(self.url_sources):
            if source_index in self.failed_sources:
                continue
                
            index_url = source["json_url"]
            source_name = source["name"]
            
            log(f"Пробуем источник {source_name}: {index_url}", "DEBUG")
            self.set_status(f"Подключение к {source_name}...")

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
                    
                    # Декодируем контент с учетом BOM
                    content = response.content
                    
                    # Удаляем BOM если он есть
                    if content.startswith(b'\xef\xbb\xbf'):
                        content = content[3:]
                    
                    # Декодируем и парсим JSON
                    import json
                    text = content.decode('utf-8')
                    result = json.loads(text)
                    
                    self.strategies_cache = result
                    self.cache_loaded = True
                    self.last_update_time = time.time()
                    self._loaded = True
                    
                    # Сохраняем на диск
                    self.save_strategies_index(result)
                    
                    # Обновляем текущий рабочий источник
                    self.current_source_index = source_index
                    
                    self.set_status(f"Получено стратегий: {len(result)} ({source_name})")
                    log(f"OK с {source_name}, {len(result)} шт.", "⚙ manager")
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
            log(f"Источник {source_name} недоступен: {last_error}", "⚠ WARNING")
            self.failed_sources.add(source_index)
            self.set_status(f"Источник {source_name} недоступен, пробуем следующий...")

        # Все источники исчерпаны
        log("Все источники недоступны", "❌ ERROR")
        if last_error:
            raise last_error
        else:
            raise Exception("Все резервные источники недоступны")

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
            
            last_error = None  # Инициализируем переменную ДО циклов
            
            # Пробуем источники в порядке приоритета
            for source_index, source in enumerate(self.url_sources):
                if source_index in self.failed_sources:
                    continue
                    
                url = source["raw_template"].format(remote_path)
                source_name = source["name"]
                
                log(f"Скачиваем {strategy_id} с {source_name}", "DEBUG")
                
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

                        total_size = 0
                        with open(local_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    total_size += len(chunk)

                        if "version" in info:
                            self.save_strategy_version(local_path, info)

                        self.set_status(f"{strategy_id} скачана с {source_name}")
                        log(f"{strategy_id} OK с {source_name} ({total_size} B)", "⚙ manager")
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
                log(f"Не удалось скачать {strategy_id} с {source_name}: {last_error}", "⚠ WARNING")

            # Все источники исчерпаны
            if last_error:
                raise Exception(f"Не удалось скачать {strategy_id} ни с одного источника: {last_error}")
            else:
                raise Exception(f"Не удалось скачать {strategy_id} ни с одного источника")

        except Exception as e:
            log(f"{strategy_id} DL error: {e}", "❌ ERROR")
            self.set_status(f"Ошибка загрузки {strategy_id}: {e}")
            return local_path if os.path.isfile(local_path) else None
        
    def get_strategies_list(self, force_update: bool = False) -> dict:
        """Возвращает словарь локальных стратегий."""
        if self._loaded and self.strategies_cache and not force_update:
            return self.strategies_cache
        
        return self._load_local_cache()
    
    def _load_local_cache(self) -> dict:
        """Загружает локальный index.json."""
        # Если уже загружен - возвращаем
        if self.cache_loaded and self.strategies_cache:
            return self.strategies_cache
            
        index_file = os.path.join(self.json_dir, "index.json")
        
        if os.path.isfile(index_file):
            try:
                with open(index_file, encoding="utf-8-sig") as f:
                    self.strategies_cache = json.load(f)
                self.cache_loaded = True
                self._loaded = True
                log(f"Загружено {len(self.strategies_cache)} локальных стратегий", "⚙ manager")
                return self.strategies_cache
            except Exception as e:
                log(f"Ошибка чтения index.json: {e}", "❌ ERROR")
        else:
            log(f"Файл index.json не найден: {index_file}", "⚠ WARNING")
        
        # Возвращаем пустой словарь если нет файла
        self.strategies_cache = {}
        self.cache_loaded = True
        self._loaded = True
        return self.strategies_cache

    def check_strategy_version_status(self, strategy_id: str, strategies_cache: dict = None) -> str:
        """Проверяет статус локальной стратегии."""
        try:
            strategies = strategies_cache if strategies_cache is not None else self.get_strategies_list()
            
            if strategy_id not in strategies:
                return 'unknown'
                
            info = strategies[strategy_id]
            remote_path = info.get("file_path", f"{strategy_id}.bat")
            filename = os.path.basename(remote_path)
            local_path = os.path.join(self.local_dir, filename)
            
            # Проверяем наличие файла
            if os.path.isfile(local_path):
                return 'current'
            else:
                return 'not_downloaded'
                    
        except Exception as e:
            log(f"Ошибка проверки стратегии {strategy_id}: {e}", "DEBUG")
            return 'unknown'
    
    def save_strategies_index(self, data: dict = None) -> bool:
        """Сохраняет index.json на диск"""
        cache_data = data or self.strategies_cache
        if not cache_data:
            return False
        try:
            with open(os.path.join(self.json_dir, "index.json"),
                      "w", encoding="utf-8-sig") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log(f"index.json save error: {e}", "❌ ERROR")
            return False

    def download_strategy(self, strategy_id: str) -> str | None:
        """ЗАГЛУШКА: загрузка из интернета отключена"""
        log(f"Загрузка стратегии {strategy_id} из интернета отключена", "⚠ WARNING")
        return None

    # ─────────────────────────── version util ─────────────────────────
    def get_local_strategy_version(self, file_path, strategy_id):
        try:
            meta = os.path.join(self.json_dir, "strategy_versions.json")
            if os.path.isfile(meta):
                with open(meta, encoding="utf-8-sig") as f:
                    versions = json.load(f)
                if strategy_id in versions:
                    return versions[strategy_id]

            with open(file_path, encoding="utf-8-sig", errors="ignore") as f:
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

            meta = os.path.join(self.json_dir, "strategy_versions.json")
            vers = {}
            if os.path.isfile(meta):
                with open(meta, encoding="utf-8-sig") as f:
                    vers = json.load(f)
            vers[sid] = info.get("version", "1.0")
            with open(meta, "w", encoding="utf-8-sig") as f:
                json.dump(vers, f, ensure_ascii=False, indent=2)

            # добавляем ремарку в .bat
            try:
                with open(file_path, encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read()
                header = (
                    "@echo off\n"
                    f"REM Стратегия {info.get('name', sid)}\n"
                    f"REM VERSION: {info.get('version', '1.0')}\n\n"
                )
                if not content.startswith("@echo off"):
                    content = header + content
                with open(file_path, "w", encoding="utf-8-sig") as f:
                    f.write(content)
            except Exception as e:
                log(f"bat header warn: {e}", "DEBUG")

            return True
        except Exception as e:
            log(f"save ver error: {e}", "❌ ERROR")
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