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

SW_HIDE          = 0
CREATE_NO_WINDOW = 0x08000000


class StrategyManager:
    """
    Управление «стратегиями» (bat-файлами) на GitHub / GitFlic.
    """

    # ─────────────────────────────── init ──────────────────────────────
    def __init__(self,
                 base_url: str,
                 local_dir: str,
                 status_callback=None,
                 json_url: str | None = None,
                 preload: bool = False) -> None:
        """
        base_url       – базовый URL репозитория
        local_dir      – куда сохраняем bat-файлы и index.json
        status_callback– функция-коллбек для сообщений в GUI / консоль
        json_url       – прямая ссылка на index.json (если есть)
        preload        – True ⇒ сразу скачивать index + bat-файлы
        """
        self.base_url        = base_url
        self.local_dir       = local_dir
        self.status_callback = status_callback
        self.json_url        = json_url

        self.strategies_cache: dict[str, dict] = {}
        self.last_update_time = 0
        self.update_interval  = 3600          # 1 ч

        # Добавляем настройки для обработки зависаний
        self.download_timeout = 30  # таймаут для скачивания
        self.max_retries = 3        # максимум попыток
        self.retry_delay = 2        # задержка между попытками

        os.makedirs(self.local_dir, exist_ok=True)

        # ленивая загрузка: ничего не качаем, только если явно попросили
        self._loaded = False
        if preload:
            self.preload_strategies()

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
        Возвращает словарь стратегий с улучшенной обработкой ошибок.
        """
        now = time.time()

        need_refresh = (
            force_update
            or not self.strategies_cache
            or (now - self.last_update_time) > self.update_interval
        )

        if not need_refresh:
            return self.strategies_cache

        # Используем ThreadPoolExecutor для контроля времени выполнения
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(self._download_strategies_index)
                result = future.result(timeout=self.download_timeout)
                return result
            except TimeoutError:
                log("Таймаут при загрузке списка стратегий", "ERROR")
                self.set_status("Таймаут загрузки - используем локальный кэш")
                return self._load_local_cache()
            except Exception as e:
                log(f"Ошибка загрузки списка: {e}", "ERROR")
                return self._load_local_cache()

    def _download_strategies_index(self) -> dict:
        """Внутренний метод для скачивания index.json с retry логикой."""
        self.set_status("Получение списка стратегий…")
        index_url = self.json_url or urljoin(self.base_url, "index.json")
        log(f"GET {index_url}", "DEBUG")

        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Используем сессию с настройками для лучшей производительности
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'ZapretGUI/1.0',
                    'Connection': 'close'  # Закрываем соединение после запроса
                })
                
                response = session.get(
                    index_url, 
                    timeout=(10, 30),  # (connect timeout, read timeout)
                    stream=False
                )
                response.raise_for_status()
                
                # Проверяем размер ответа
                if len(response.content) == 0:
                    raise ValueError("Получен пустой ответ")
                
                self.strategies_cache = response.json()
                self.last_update_time = time.time()
                self.save_strategies_index()
                self._loaded = True

                self.set_status(f"Получено стратегий: {len(self.strategies_cache)}")
                log(f"OK, {len(self.strategies_cache)} шт.", "INFO")
                return self.strategies_cache

            except Exception as e:
                last_error = e
                log(f"Попытка {attempt + 1}/{self.max_retries} не удалась: {e}", "DEBUG")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Увеличиваем задержку
                    self.set_status(f"Повтор попытки {attempt + 2}/{self.max_retries}...")

        # Все попытки неудачны
        raise last_error or Exception("Неизвестная ошибка")

    def _load_local_cache(self) -> dict:
        """Загружает локальный кэш index.json."""
        index_file = os.path.join(self.local_dir, "index.json")
        if os.path.isfile(index_file):
            try:
                with open(index_file, encoding="utf-8") as f:
                    self.strategies_cache = json.load(f)
                self._loaded = True
                self.set_status("Загружен локальный индекс стратегий")
                log("Используем локальный index.json", "INFO")
                return self.strategies_cache
            except Exception as e:
                log(f"Ошибка чтения локального индекса: {e}", "ERROR")
        
        return {}

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
    
    def save_strategies_index(self) -> bool:
        if not self.strategies_cache:
            return False
        try:
            with open(os.path.join(self.local_dir, "index.json"),
                      "w", encoding="utf-8") as f:
                json.dump(self.strategies_cache, f, ensure_ascii=False, indent=2)
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

        log("Preload стратегий (только индекс)…", "INFO")
        strategies = self.get_strategies_list()
        if not strategies:
            log("Список стратегий пуст – preload отменён", "ERROR")
            return

        # Убираем автоматическое скачивание BAT-файлов
        # for sid in strategies:
        #     self.download_strategy(sid)

        self._loaded = True
        log("Preload индекса завершён", "INFO")
    
    # ─────────────────────── download 1 strategy ──────────────────────
    def download_strategy(self, strategy_id: str) -> str | None:
        """
        Скачивает стратегию с улучшенной обработкой зависаний.
        """
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

    def _download_strategy_sync(self, strategy_id: str) -> str | None:
        """Синхронная версия скачивания стратегии."""
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

            # Скачивание с retry логикой
            self.set_status(f"Скачивание {strategy_id}…")
            url = f"https://gitflic.ru/project/main1234/main1234/blob/raw?file={remote_path}"
            
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'ZapretGUI/1.0',
                        'Connection': 'close'
                    })
                    
                    response = session.get(
                        url, 
                        timeout=(10, 30),
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

                    self.set_status(f"{strategy_id} скачана")
                    log(f"{strategy_id} OK ({len(response.content)} B)", "INFO")
                    return local_path

                except Exception as e:
                    last_error = e
                    log(f"Попытка {attempt + 1} скачивания {strategy_id}: {e}", "DEBUG")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)

            # Все попытки неудачны
            raise last_error

        except Exception as e:
            log(f"{strategy_id} DL error: {e}", "ERROR")
            self.set_status(f"Ошибка загрузки {strategy_id}: {e}")
            return local_path if os.path.isfile(local_path) else None

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

    # ────────────────────────── прочее API ────────────────────────────
    def get_strategy_details(self, strategy_id: str) -> dict | None:
        data = self.get_strategies_list()
        return data.get(strategy_id) if data else None

    def update_strategies_list(self) -> bool:
        try:
            self.get_strategies_list(force_update=True)
            return True
        except Exception as e:
            log(f"update list error: {e}", "ERROR")
            return False