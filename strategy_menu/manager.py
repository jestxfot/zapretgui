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
        Возвращает словарь стратегий.  По истечении update_interval
        или при force_update скачивает index.json.
        """
        now = time.time()

        need_refresh = (
            force_update
            or not self.strategies_cache
            or (now - self.last_update_time) > self.update_interval
        )

        if not need_refresh:
            return self.strategies_cache

        # --- пробуем скачать ------------------------------------------------
        try:
            self.set_status("Получение списка стратегий…")
            index_url = self.json_url or urljoin(self.base_url, "index.json")
            log(f"GET {index_url}", "DEBUG")

            for attempt in range(3):
                try:
                    r = requests.get(index_url, timeout=8)
                    r.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == 2:           # последняя попытка
                        raise
                    time.sleep(2)              # пауза и ещё раз

            self.strategies_cache = r.json()

            self.last_update_time = now
            self.save_strategies_index()
            self._loaded = True

            self.set_status(f"Получено стратегий: {len(self.strategies_cache)}")
            log(f"OK, {len(self.strategies_cache)} шт.", "INFO")

        except Exception as e:
            # сеть не доступна → пытаемся взять локальный cache
            log(f"index.json error: {e}", "ERROR")
            self.set_status(f"Ошибка загрузки списка стратегий: {e}")

            index_file = os.path.join(self.local_dir, "index.json")
            if os.path.isfile(index_file):
                try:
                    with open(index_file, encoding="utf-8") as f:
                        self.strategies_cache = json.load(f)
                    self._loaded = True
                    self.set_status("Загружен локальный индекс стратегий")
                    log("Используем локальный index.json", "INFO")
                except Exception as e2:
                    log(f"local index.json read error: {e2}", "ERROR")

        return self.strategies_cache

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
        Скачивает index.json (если ещё нет) + все bat-файлы.
        Повторный вызов после успешной загрузки делает ничего.
        """
        if self._loaded:
            log("preload_strategies(): уже загружено – пропуск", "DEBUG")
            return

        log("Preload стратегий…", "INFO")
        strategies = self.get_strategies_list()
        if not strategies:
            log("Список стратегий пуст – preload отменён", "ERROR")
            return

        for sid in strategies:
            self.download_strategy(sid)   # логи и статусы внутри

        self._loaded = True
        log("Preload завершён", "INFO")

    # ─────────────────────── download 1 strategy ──────────────────────
    def download_strategy(self, strategy_id: str) -> str | None:
        """
        Скачивает (или переиспользует локальную) стратегию .bat
        и возвращает путь к файлу.
        """
        try:
            strategies = self.get_strategies_list()
            if strategy_id not in strategies:
                self.set_status(f"Стратегия {strategy_id} не найдена")
                return None

            info          = strategies[strategy_id]
            remote_path   = info.get("file_path", f"{strategy_id}.bat")
            filename      = os.path.basename(remote_path)
            local_path    = os.path.join(self.local_dir, filename)
            need_download = True

            # проверка версии / времени
            if os.path.isfile(local_path):
                if "version" in info:
                    local_ver = self.get_local_strategy_version(local_path,
                                                                strategy_id)
                    if local_ver == info["version"]:
                        need_download = False
                else:
                    age = time.time() - os.path.getmtime(local_path)
                    if age < 3600:        # <1 ч
                        need_download = False

            if not need_download:
                self.set_status(f"Локальная копия {strategy_id} актуальна")
                return local_path

            # --- скачиваем ---------------------------------------------------
            self.set_status(f"Скачивание {strategy_id}…")
            url = (
                f"https://gitflic.ru/project/main1234/main1234/"
                f"blob/raw?file={remote_path}"
            )
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            if not r.content:
                raise RuntimeError("Получен пустой файл")

            with open(local_path, "wb") as f:
                f.write(r.content)

            if "version" in info:
                self.save_strategy_version(local_path, info)

            self.set_status(f"{strategy_id} скачана")
            log(f"{strategy_id} OK ({len(r.content)} B)", "INFO")
            return local_path

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