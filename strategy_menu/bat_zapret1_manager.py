# strategy_menu/bat_zapret1_manager.py

"""
Менеджер стратегий для BAT режима (Zapret 1).
Сканирует .bat файлы напрямую и читает метаданные из REM комментариев.

Формат REM комментариев в .bat файле:
    @echo off
    REM NAME: Название стратегии
    REM VERSION: 1.0
    REM DESCRIPTION: Описание стратегии
    REM LABEL: recommended
    ... команды ...
"""

import os
import re
from typing import Optional, Callable

from log import log


class BatZapret1Manager:
    """
    Управление стратегиями (bat-файлами).
    Сканирует папку напрямую, метаданные читаются из REM комментариев.
    """

    def __init__(self, local_dir: str, json_dir: str = None, status_callback: Callable[[str], None] = None, **kwargs):
        """
        Args:
            local_dir       – папка с .bat файлами
            json_dir        – устарел, игнорируется (оставлен для совместимости)
            status_callback – функция для сообщений в GUI
        """
        self.local_dir = local_dir
        self.status_callback = status_callback

        # Кэш стратегий
        self.strategies_cache: dict[str, dict] = {}
        self.cache_loaded = False
        self._loaded = False

        os.makedirs(self.local_dir, exist_ok=True)

        # Сканируем .bat файлы при инициализации
        self._scan_bat_files()
        log(f"Strategy Manager инициализирован: {len(self.strategies_cache)} стратегий из {local_dir}", "INFO")

    @property
    def already_loaded(self) -> bool:
        """True после загрузки стратегий."""
        return self._loaded

    def set_status(self, text: str) -> None:
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)

    def get_local_strategies_only(self) -> dict:
        """Возвращает словарь стратегий."""
        return self.get_strategies_list()

    # ───────────────────────── сканирование .bat файлов ─────────────────────────

    def _scan_bat_files(self) -> dict:
        """Сканирует папку и собирает информацию о .bat файлах."""
        if self.cache_loaded and self.strategies_cache:
            return self.strategies_cache

        self.strategies_cache = {}
        
        if not os.path.isdir(self.local_dir):
            log(f"Папка стратегий не найдена: {self.local_dir}", "⚠ WARNING")
            self.cache_loaded = True
            self._loaded = True
            return self.strategies_cache

        try:
            bat_files = [f for f in os.listdir(self.local_dir) if f.lower().endswith('.bat')]
            log(f"Найдено .bat файлов: {len(bat_files)}", "DEBUG")
            
            for bat_file in bat_files:
                file_path = os.path.join(self.local_dir, bat_file)
                strategy_id = os.path.splitext(bat_file)[0]  # ID = имя без расширения
                
                # Парсим метаданные из REM комментариев
                metadata = self._parse_bat_metadata(file_path)
                
                # Если имя не указано в REM, используем имя файла
                if not metadata.get('name'):
                    metadata['name'] = strategy_id.replace('_', ' ').title()
                
                # Обязательные поля
                metadata['file_path'] = bat_file
                metadata['id'] = strategy_id
                
                self.strategies_cache[strategy_id] = metadata
                
            log(f"Загружено {len(self.strategies_cache)} стратегий из .bat файлов", "⚙ manager")
            
        except Exception as e:
            log(f"Ошибка сканирования .bat файлов: {e}", "❌ ERROR")

        self.cache_loaded = True
        self._loaded = True
        return self.strategies_cache

    def _parse_bat_metadata(self, file_path: str) -> dict:
        """
        Парсит REM комментарии в начале .bat файла для извлечения метаданных.
        
        Поддерживаемые поля:
            REM NAME: Название стратегии
            REM VERSION: 1.0
            REM DESCRIPTION: Описание стратегии
            REM LABEL: recommended | deprecated | experimental
            REM AUTHOR: Автор стратегии
            REM DATE: Дата создания/обновления (YYYY-MM-DD)
        """
        metadata = {
            'name': None,
            'version': None,
            'description': None,
            'label': None,
            'author': None,
            'date': None,
        }
        
        # Паттерны для парсинга
        patterns = {
            'name': re.compile(r'^REM\s+NAME:\s*(.+)$', re.IGNORECASE),
            'version': re.compile(r'^REM\s+VERSION:\s*(.+)$', re.IGNORECASE),
            'description': re.compile(r'^REM\s+DESCRIPTION:\s*(.+)$', re.IGNORECASE),
            'label': re.compile(r'^REM\s+LABEL:\s*(.+)$', re.IGNORECASE),
            'author': re.compile(r'^REM\s+AUTHOR:\s*(.+)$', re.IGNORECASE),
            'date': re.compile(r'^REM\s+DATE:\s*(.+)$', re.IGNORECASE),
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                # Читаем только первые 50 строк для поиска метаданных
                for i, line in enumerate(f):
                    if i > 50:
                        break
                    
                    line = line.strip()
                    
                    # Пропускаем пустые строки и @echo off
                    if not line or line.lower().startswith('@echo'):
                        continue
                    
                    # Если строка не REM комментарий после первых REM - прекращаем
                    if not line.upper().startswith('REM') and any(metadata.values()):
                        break
                    
                    # Парсим каждый паттерн
                    for key, pattern in patterns.items():
                        match = pattern.match(line)
                        if match:
                            metadata[key] = match.group(1).strip()
                            break
                            
        except Exception as e:
            log(f"Ошибка чтения метаданных из {file_path}: {e}", "DEBUG")
        
        return metadata

    def preload_strategies(self) -> None:
        """Загружает стратегии (сканирует .bat файлы)."""
        if self._loaded:
            log("Стратегии уже загружены", "DEBUG")
            return

        self._scan_bat_files()
        log(f"Preload завершён: {len(self.strategies_cache)} стратегий", "⚙ manager")

    def get_strategies_list(self, force_update: bool = False) -> dict:
        """Возвращает словарь стратегий."""
        if self._loaded and self.strategies_cache and not force_update:
            return self.strategies_cache
        return self._scan_bat_files()

    def refresh_strategies(self) -> dict:
        """Принудительно пересканирует папку с .bat файлами."""
        self.cache_loaded = False
        self._loaded = False
        self.strategies_cache = {}
        return self._scan_bat_files()

    def get_strategy_by_name(self, name: str) -> Optional[dict]:
        """Находит стратегию по имени."""
        strategies = self.get_strategies_list()
        for sid, sinfo in strategies.items():
            if sinfo.get('name') == name:
                return sinfo
        return None

    def get_strategy_by_file(self, filename: str) -> Optional[dict]:
        """Находит стратегию по имени файла."""
        strategies = self.get_strategies_list()
        for sid, sinfo in strategies.items():
            if sinfo.get('file_path') == filename:
                return sinfo
        return None

    def get_recommended_strategy(self) -> Optional[dict]:
        """Возвращает рекомендуемую стратегию (с label='recommended')."""
        strategies = self.get_strategies_list()
        for sid, sinfo in strategies.items():
            if sinfo.get('label') == 'recommended':
                return sinfo
        # Если рекомендуемой нет, возвращаем первую
        if strategies:
            return next(iter(strategies.values()))
        return None

    # ───────────────────────── заглушки для совместимости ─────────────────────────

    def download_strategies_index_from_internet(self) -> dict:
        """ЗАГЛУШКА: загрузка из интернета отключена."""
        log("Загрузка из интернета отключена - используются локальные .bat файлы", "⚠ WARNING")
        return self.strategies_cache

    def download_single_strategy_bat(self, strategy_id: str) -> str | None:
        """ЗАГЛУШКА: загрузка из интернета отключена."""
        log(f"Загрузка стратегии {strategy_id} из интернета отключена", "⚠ WARNING")
        return None

    def check_strategy_version_status(self, strategy_id: str, strategies_cache: dict = None) -> str:
        """Проверяет статус стратегии."""
        strategies = strategies_cache if strategies_cache is not None else self.get_strategies_list()
        if strategy_id not in strategies:
            return 'unknown'
        
        info = strategies[strategy_id]
        file_path = info.get('file_path')
        if file_path:
            full_path = os.path.join(self.local_dir, file_path)
            if os.path.isfile(full_path):
                return 'current'
        return 'not_found'
