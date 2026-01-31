"""
Адаптеры для различных источников стратегий.

Предоставляет унифицированный интерфейс для работы со стратегиями
из разных источников: BAT файлы, JSON файлы, комбинированные источники.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

from log import log
from config import BAT_FOLDER, INDEXJSON_FOLDER
from strategy_menu.strategy_info import StrategyInfo
from utils.bat_parser import parse_bat_file


class BaseStrategyAdapter(ABC):
    """
    Абстрактный базовый класс для адаптеров стратегий.

    Определяет интерфейс для получения стратегий из различных источников.
    """

    @abstractmethod
    def get_all_strategies(self) -> List[StrategyInfo]:
        """
        Получает все стратегии из источника.

        Returns:
            Список объектов StrategyInfo
        """
        pass

    @abstractmethod
    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyInfo]:
        """
        Получает стратегию по её идентификатору.

        Args:
            strategy_id: Уникальный идентификатор стратегии

        Returns:
            StrategyInfo или None если не найдена
        """
        pass

    def refresh(self) -> None:
        """
        Перезагружает стратегии из источника.

        Очищает кэш и заново загружает данные.
        По умолчанию ничего не делает - переопределяется в наследниках.
        """
        pass


class BatStrategyAdapter(BaseStrategyAdapter):
    """
    Адаптер для загрузки стратегий из BAT файлов.

    Парсит .bat файлы в указанной папке, извлекает метаданные
    из REM комментариев и создаёт объекты StrategyInfo.
    """

    def __init__(self, bat_folder: str):
        """
        Инициализирует адаптер.

        Args:
            bat_folder: Путь к папке с .bat файлами
        """
        self._bat_folder = bat_folder
        self._cache: Optional[List[StrategyInfo]] = None
        self._cache_by_id: Optional[Dict[str, StrategyInfo]] = None

    def get_all_strategies(self) -> List[StrategyInfo]:
        """
        Получает все стратегии из BAT файлов.

        Returns:
            Список объектов StrategyInfo
        """
        if self._cache is not None:
            return self._cache

        self._load_strategies()
        return self._cache or []

    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyInfo]:
        """
        Получает стратегию по ID.

        Args:
            strategy_id: Идентификатор стратегии

        Returns:
            StrategyInfo или None
        """
        if self._cache_by_id is None:
            self._load_strategies()

        return self._cache_by_id.get(strategy_id) if self._cache_by_id else None

    def refresh(self) -> None:
        """Перезагружает стратегии из BAT файлов."""
        self._cache = None
        self._cache_by_id = None
        self._load_strategies()

    def _load_strategies(self) -> None:
        """Загружает и парсит все BAT файлы."""
        self._cache = []
        self._cache_by_id = {}

        if not os.path.exists(self._bat_folder):
            log(f"BAT папка не найдена: {self._bat_folder}", "WARNING")
            return

        try:
            bat_files = [
                f for f in os.listdir(self._bat_folder)
                if f.lower().endswith('.bat')
            ]
        except OSError as e:
            log(f"Ошибка чтения папки BAT: {e}", "ERROR")
            return

        for bat_file in bat_files:
            try:
                file_path = os.path.join(self._bat_folder, bat_file)
                strategy = self._parse_bat_file(file_path)

                if strategy:
                    self._cache.append(strategy)
                    self._cache_by_id[strategy.id] = strategy

            except Exception as e:
                log(f"Ошибка парсинга BAT файла {bat_file}: {e}", "ERROR")

        log(f"BatStrategyAdapter: загружено {len(self._cache)} стратегий из {self._bat_folder}", "DEBUG")

    def _parse_bat_file(self, file_path: str) -> Optional[StrategyInfo]:
        """
        Парсит отдельный BAT файл.

        Args:
            file_path: Полный путь к файлу

        Returns:
            StrategyInfo или None при ошибке
        """
        try:
            metadata = self._extract_metadata(file_path)
            metadata['file_path'] = file_path

            # Извлекаем аргументы через bat_parser
            parsed = parse_bat_file(file_path)
            if parsed:
                exe_path, args = parsed
                # Сохраняем аргументы в многострочном формате (один аргумент на строку)
                metadata['args'] = '\n'.join(args) if args else ''

            return StrategyInfo.from_bat_metadata(metadata)

        except Exception as e:
            log(f"Ошибка создания StrategyInfo из {file_path}: {e}", "ERROR")
            return None

    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Извлекает метаданные из REM комментариев BAT файла.

        Поддерживаемые комментарии:
            REM NAME: Название стратегии
            REM VERSION: 1.0
            REM DESCRIPTION: Описание
            REM LABEL: recommended|deprecated|experimental|game
            REM AUTHOR: Автор

        Args:
            file_path: Путь к BAT файлу

        Returns:
            Словарь с метаданными
        """
        metadata = {}

        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()

                # Парсим REM комментарии
                if line.upper().startswith('REM '):
                    content = line[4:].strip()

                    # Ищем паттерн KEY: VALUE
                    if ':' in content:
                        key, value = content.split(':', 1)
                        key = key.strip().upper()
                        value = value.strip()

                        if key in ('NAME', 'VERSION', 'DESCRIPTION', 'LABEL', 'AUTHOR', 'COMMENT'):
                            metadata[key] = value

                # Также поддерживаем # комментарии (новый формат)
                elif line.startswith('#') and ':' in line:
                    content = line[1:].strip()
                    key, value = content.split(':', 1)
                    key = key.strip().upper()
                    value = value.strip()

                    if key in ('NAME', 'VERSION', 'DESCRIPTION', 'LABEL', 'AUTHOR', 'COMMENT'):
                        metadata[key] = value

            # Если имя не найдено - используем имя файла
            if 'NAME' not in metadata:
                metadata['NAME'] = os.path.splitext(os.path.basename(file_path))[0]

        except Exception as e:
            log(f"Ошибка извлечения метаданных из {file_path}: {e}", "ERROR")
            metadata['NAME'] = os.path.splitext(os.path.basename(file_path))[0]

        return metadata


class JsonStrategyAdapter(BaseStrategyAdapter):
    """
    Адаптер для загрузки стратегий из JSON файлов.

    Загружает стратегии из JSON файлов в указанной папке.
    Поддерживает фильтрацию по категории (category_key).
    """

    def __init__(self, json_folder: str, category_key: str = None):
        """
        Инициализирует адаптер.

        Args:
            json_folder: Путь к папке с JSON файлами
            category_key: Ключ категории для фильтрации (tcp, quic, udp и т.д.)
                         Если None - загружает все файлы
        """
        self._json_folder = json_folder
        self._category_key = category_key
        self._cache: Optional[List[StrategyInfo]] = None
        self._cache_by_id: Optional[Dict[str, StrategyInfo]] = None

    def get_all_strategies(self) -> List[StrategyInfo]:
        """
        Получает все стратегии из JSON файлов.

        Returns:
            Список объектов StrategyInfo
        """
        if self._cache is not None:
            return self._cache

        self._load_strategies()
        return self._cache or []

    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyInfo]:
        """
        Получает стратегию по ID.

        Args:
            strategy_id: Идентификатор стратегии

        Returns:
            StrategyInfo или None
        """
        if self._cache_by_id is None:
            self._load_strategies()

        return self._cache_by_id.get(strategy_id) if self._cache_by_id else None

    def refresh(self) -> None:
        """Перезагружает стратегии из JSON файлов."""
        self._cache = None
        self._cache_by_id = None
        self._load_strategies()

    def _load_strategies(self) -> None:
        """Загружает стратегии из JSON файлов."""
        self._cache = []
        self._cache_by_id = {}

        if not os.path.exists(self._json_folder):
            log(f"JSON папка не найдена: {self._json_folder}", "WARNING")
            return

        try:
            if self._category_key:
                # Загружаем только указанный файл
                json_files = [f"{self._category_key}.json"]
            else:
                # Загружаем все JSON файлы
                json_files = [
                    f for f in os.listdir(self._json_folder)
                    if f.lower().endswith('.json')
                ]
        except OSError as e:
            log(f"Ошибка чтения папки JSON: {e}", "ERROR")
            return

        for json_file in json_files:
            try:
                file_path = os.path.join(self._json_folder, json_file)

                if not os.path.exists(file_path):
                    continue

                # Определяем category_key из имени файла
                category = os.path.splitext(json_file)[0]

                strategies = self._load_json_file(file_path, category)

                for strategy in strategies:
                    self._cache.append(strategy)
                    self._cache_by_id[strategy.id] = strategy

            except Exception as e:
                log(f"Ошибка загрузки JSON файла {json_file}: {e}", "ERROR")

        log(f"JsonStrategyAdapter: загружено {len(self._cache)} стратегий из {self._json_folder}", "DEBUG")

    def _load_json_file(self, file_path: str, category_key: str) -> List[StrategyInfo]:
        """
        Загружает стратегии из одного JSON файла.

        Args:
            file_path: Путь к JSON файлу
            category_key: Ключ категории

        Returns:
            Список StrategyInfo
        """
        strategies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Поддерживаем разные форматы JSON
            # Формат 1: {"strategies": [...]}
            if isinstance(data, dict) and 'strategies' in data:
                items = data['strategies']
            # Формат 2: [...]
            elif isinstance(data, list):
                items = data
            # Формат 3: {"strategy_id": {...}, ...}
            elif isinstance(data, dict):
                items = [
                    {**v, 'id': k} if isinstance(v, dict) else {'id': k, 'name': str(v)}
                    for k, v in data.items()
                    if k not in ('meta', 'version', 'category', 'description')
                ]
            else:
                log(f"Неизвестный формат JSON в {file_path}", "WARNING")
                return []

            for item in items:
                if not isinstance(item, dict):
                    continue

                try:
                    # Добавляем file_path к данным
                    item['file_path'] = file_path
                    strategy = StrategyInfo.from_json_strategy(item, category_key)
                    strategies.append(strategy)
                except Exception as e:
                    log(f"Ошибка создания StrategyInfo из {item.get('id', 'unknown')}: {e}", "ERROR")

        except json.JSONDecodeError as e:
            log(f"Ошибка парсинга JSON {file_path}: {e}", "ERROR")
        except Exception as e:
            log(f"Ошибка чтения JSON {file_path}: {e}", "ERROR")

        return strategies


class CombinedStrategyAdapter(BaseStrategyAdapter):
    """
    Комбинированный адаптер, объединяющий несколько источников.

    Агрегирует стратегии из нескольких адаптеров в единый интерфейс.
    """

    def __init__(self, adapters: List[BaseStrategyAdapter]):
        """
        Инициализирует комбинированный адаптер.

        Args:
            adapters: Список адаптеров для объединения
        """
        self._adapters = adapters
        self._cache: Optional[List[StrategyInfo]] = None
        self._cache_by_id: Optional[Dict[str, StrategyInfo]] = None

    def get_all_strategies(self) -> List[StrategyInfo]:
        """
        Получает все стратегии из всех адаптеров.

        Returns:
            Объединённый список StrategyInfo из всех источников
        """
        if self._cache is not None:
            return self._cache

        self._load_strategies()
        return self._cache or []

    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyInfo]:
        """
        Ищет стратегию по ID во всех адаптерах.

        Args:
            strategy_id: Идентификатор стратегии

        Returns:
            StrategyInfo или None
        """
        if self._cache_by_id is None:
            self._load_strategies()

        return self._cache_by_id.get(strategy_id) if self._cache_by_id else None

    def refresh(self) -> None:
        """Перезагружает стратегии из всех адаптеров."""
        # Сначала обновляем все вложенные адаптеры
        for adapter in self._adapters:
            try:
                adapter.refresh()
            except Exception as e:
                log(f"Ошибка обновления адаптера {type(adapter).__name__}: {e}", "ERROR")

        # Затем очищаем собственный кэш
        self._cache = None
        self._cache_by_id = None
        self._load_strategies()

    def _load_strategies(self) -> None:
        """Загружает стратегии из всех адаптеров."""
        self._cache = []
        self._cache_by_id = {}

        for adapter in self._adapters:
            try:
                strategies = adapter.get_all_strategies()

                for strategy in strategies:
                    # Проверяем на дубликаты по ID
                    if strategy.id in self._cache_by_id:
                        log(f"Дубликат стратегии ID={strategy.id}, пропускаем", "DEBUG")
                        continue

                    self._cache.append(strategy)
                    self._cache_by_id[strategy.id] = strategy

            except Exception as e:
                log(f"Ошибка получения стратегий из {type(adapter).__name__}: {e}", "ERROR")

        log(f"CombinedStrategyAdapter: всего загружено {len(self._cache)} стратегий", "DEBUG")

    def add_adapter(self, adapter: BaseStrategyAdapter) -> None:
        """
        Добавляет новый адаптер.

        Args:
            adapter: Адаптер для добавления
        """
        self._adapters.append(adapter)
        # Инвалидируем кэш
        self._cache = None
        self._cache_by_id = None

    def remove_adapter(self, adapter: BaseStrategyAdapter) -> bool:
        """
        Удаляет адаптер.

        Args:
            adapter: Адаптер для удаления

        Returns:
            True если адаптер был удалён
        """
        if adapter in self._adapters:
            self._adapters.remove(adapter)
            # Инвалидируем кэш
            self._cache = None
            self._cache_by_id = None
            return True
        return False


# Вспомогательные функции для создания адаптеров с настройками по умолчанию

def create_default_bat_adapter() -> BatStrategyAdapter:
    """
    Создаёт адаптер BAT с папкой по умолчанию.

    Returns:
        BatStrategyAdapter с BAT_FOLDER из config
    """
    return BatStrategyAdapter(BAT_FOLDER)


def create_default_json_adapter(category_key: str = None) -> JsonStrategyAdapter:
    """
    Создаёт адаптер JSON с папкой по умолчанию.

    Args:
        category_key: Опциональный ключ категории

    Returns:
        JsonStrategyAdapter с INDEXJSON_FOLDER/strategies/builtin из config
    """
    json_folder = os.path.join(INDEXJSON_FOLDER, "strategies", "builtin")
    return JsonStrategyAdapter(json_folder, category_key)


def create_combined_adapter() -> CombinedStrategyAdapter:
    """
    Создаёт комбинированный адаптер с BAT и JSON источниками.

    Returns:
        CombinedStrategyAdapter с адаптерами по умолчанию
    """
    adapters = [
        create_default_bat_adapter(),
        create_default_json_adapter(),
    ]
    return CombinedStrategyAdapter(adapters)
