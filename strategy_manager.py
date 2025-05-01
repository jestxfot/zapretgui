import os
import requests
import json
import subprocess
import time
from urllib.parse import urljoin
from log import log

# Исправление проблемы с импортом win32con
# Вместо импорта из внешнего модуля определяем константы напрямую
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000

class StrategyManager:
    """Класс для управления стратегиями GitHub."""
    
    def __init__(self, base_url, local_dir, status_callback=None, json_url=None):
        """
        Инициализирует менеджер стратегий.
        
        Args:
            base_url (str): Базовый URL для скачивания стратегий
            local_dir (str): Локальная директория для хранения стратегий
            status_callback (callable, optional): Функция обратного вызова для отображения статуса
            json_url (str, optional): Прямой URL к JSON-файлу со списком стратегий
        """
        self.base_url = base_url
        self.local_dir = local_dir
        self.status_callback = status_callback
        self.json_url = json_url
        self.strategies_cache = {}
        self.last_update_time = 0
        self.update_interval = 3600  # 1 час
        
        # Создаем директорию если не существует
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir, exist_ok=True)
    
    def set_status(self, text):
        """Отображает статусное сообщение."""
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)
            
    def get_strategies_list(self, force_update=False):
        """
        Получает список доступных стратегий с сервера.
        
        Args:
            force_update (bool): Принудительное обновление списка
            
        Returns:
            dict: Словарь доступных стратегий
        """
        current_time = time.time()
        
        # Проверяем, нужно ли обновить кэш
        if (force_update or 
            not self.strategies_cache or 
            current_time - self.last_update_time > self.update_interval):
            
            try:
                self.set_status("Получение списка стратегий...")
                
                # Используем прямую ссылку на JSON, если она указана
                if self.json_url:
                    index_url = self.json_url
                else:
                    # Иначе формируем URL по старому алгоритму
                    index_url = urljoin(self.base_url, "index.json")
                
                # Выводим URL для отладки
                log(f"Запрос JSON по URL: {index_url}", level="DEBUG")
                
                # Запрашиваем индексный файл со списком стратегий
                response = requests.get(index_url, timeout=5)
                response.raise_for_status()  # Вызовет исключение при HTTP-ошибках
                
                # Проверяем, что ответ содержит валидный JSON
                try:
                    self.strategies_cache = response.json()
                    self.last_update_time = current_time
                    
                    self.set_status(f"Получено {len(self.strategies_cache)} стратегий")
                    log(f"Загружено {len(self.strategies_cache)} стратегий с сервера")
                    
                    # Сохраняем полученный индекс локально
                    self.save_strategies_index()
                except json.JSONDecodeError as json_error:
                    error_msg = f"Ошибка при разборе JSON: {str(json_error)}"
                    log(error_msg, level="ERROR")
                    log(f"Содержимое ответа: {response.text[:500]}...", level="DEBUG")  # первые 500 символов для отладки
                    self.set_status(error_msg)
                    
            except Exception as e:
                error_msg = f"Ошибка при получении списка стратегий: {str(e)}"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                
                # Если есть локальный кэш индекса, загружаем его
                index_file = os.path.join(self.local_dir, "index.json")
                if os.path.exists(index_file):
                    try:
                        with open(index_file, 'r', encoding='utf-8') as f:
                            self.strategies_cache = json.load(f)
                        log("Загружен локальный индекс стратегий")
                        self.set_status("Загружен локальный индекс стратегий")
                    except Exception as local_error:
                        log(f"Ошибка при загрузке локального индекса: {str(local_error)}", level="ERROR")
        
        return self.strategies_cache
    
    def preload_strategies(self):
        """
        Загружает все доступные стратегии при инициализации.
        """
        log("Запуск предварительной загрузки стратегий...", level="INFO")
        strategies = self.get_strategies_list()
        
        if not strategies:
            log("Не удалось получить список стратегий для предзагрузки", level="ERROR")
            return
            
        for strategy_id, strategy_info in strategies.items():
            try:
                #log(f"Предзагрузка стратегии: {strategy_id}", level="INFO")
                file_path = self.download_strategy(strategy_id)
                if file_path:
                    #log(f"Стратегия {strategy_id} предзагружена: {file_path}", level="INFO")
                    self.set_status(f"Стратегия {strategy_id} предзагружена")
                else:
                    log(f"Не удалось предзагрузить стратегию: {strategy_id}", level="WARNING")
            except Exception as e:
                log(f"Ошибка при предзагрузке стратегии {strategy_id}: {str(e)}", level="ERROR")

    def download_strategy(self, strategy_id):
        """
        Скачивает стратегию с сервера.
        
        Args:
            strategy_id (str): Идентификатор стратегии
            
        Returns:
            str: Путь к локальному файлу стратегии или None при ошибке
        """
        try:
            #log(f"Запрос на скачивание стратегии: {strategy_id}", level="DEBUG")
            strategies = self.get_strategies_list()
            
            if not strategies:
                error_msg = "Список стратегий пуст или не получен"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return None
                
            #log(f"Доступные стратегии: {list(strategies.keys())}", level="DEBUG")
            
            if strategy_id not in strategies:
                error_msg = f"Стратегия {strategy_id} не найдена в списке"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                return None
            
            strategy_info = strategies[strategy_id]
            #log(f"Информация о стратегии {strategy_id}: {strategy_info}", level="DEBUG")
            
            # Используем file_path из JSON, если указан
            if 'file_path' in strategy_info:
                strategy_url_path = strategy_info['file_path']
                # Извлекаем только имя файла для локального сохранения
                strategy_filename = os.path.basename(strategy_url_path)
                #log(f"Используется file_path из JSON: {strategy_url_path}", level="DEBUG")
            else:
                strategy_url_path = f"{strategy_id}.bat"
                strategy_filename = f"{strategy_id}.bat"
                #log(f"file_path не указан, используется ID: {strategy_url_path}", level="DEBUG")
            
            # Сохраняем в папку bin
            local_path = os.path.join(self.local_dir, strategy_filename)
            
            try:
                # Проверяем, нужно ли скачивать файл
                should_download = True
                
                if os.path.exists(local_path):
                    # Проверка версий если есть
                    if 'version' in strategy_info:
                        current_version = strategy_info['version']
                        local_version = self.get_local_strategy_version(local_path, strategy_id)
                        
                        if local_version and local_version == current_version:
                            #log(f"Локальная версия стратегии {strategy_id} ({local_version}) совпадает с версией на сервере", level="INFO")
                            should_download = False
                        else:
                            log(f"Требуется обновление стратегии {strategy_id}: локальная версия {local_version}, серверная версия {current_version}", level="INFO")
                    else:
                        # Если нет информации о версии, проверка по времени
                        file_age = time.time() - os.path.getmtime(local_path)
                        if file_age < 3600:  # 1 час
                            should_download = False
                
                if should_download:
                    self.set_status(f"Скачивание стратегии {strategy_id}...")
                    
                    # Формируем прямой URL для Gitflic
                    # Правильный формат: https://gitflic.ru/project/main1234/main1234/blob/raw?file=имя_файла.bat
                    strategy_url = f"https://gitflic.ru/project/main1234/main1234/blob/raw?file={strategy_url_path}"
                    #log(f"Скачивание стратегии с URL: {strategy_url}", level="DEBUG")
                    
                    # Скачиваем файл
                    response = requests.get(strategy_url, timeout=10)
                    response.raise_for_status()
                    
                    # Проверяем размер ответа
                    if len(response.content) == 0:
                        raise Exception("Получен пустой файл стратегии")
                    
                    # Сохраняем файл
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Если есть информация о версии, добавляем её в BAT-файл
                    if 'version' in strategy_info:
                        self.save_strategy_version(local_path, strategy_info)
                    
                    self.set_status(f"Стратегия {strategy_id} успешно скачана")
                    log(f"Стратегия {strategy_id} успешно скачана из {strategy_url}", level="INFO")
                else:
                    self.set_status(f"Используется локальная копия стратегии {strategy_id}")
                    #log(f"Используется локальная копия стратегии {strategy_id}", level="INFO")
                
                return local_path
                
            except Exception as e:
                error_msg = f"Ошибка при скачивании стратегии {strategy_id}: {str(e)}"
                log(error_msg, level="ERROR")
                self.set_status(error_msg)
                
                # Если файл существует локально, возвращаем его путь
                if os.path.exists(local_path):
                    self.set_status(f"Используется локальная копия стратегии {strategy_id}")
                    return local_path
                
                return None
        except Exception as e:
            error_msg = f"Неожиданная ошибка при загрузке стратегии {strategy_id}: {str(e)}"
            log(error_msg, level="ERROR")
            self.set_status(error_msg)
            return None
    
    def get_local_strategy_version(self, file_path, strategy_id):
        """
        Получает версию локально сохраненной стратегии из файла.
        
        Args:
            file_path (str): Путь к файлу стратегии
            strategy_id (str): Идентификатор стратегии
            
        Returns:
            str: Версия стратегии или None если версия не найдена
        """
        try:
            # Сначала проверяем версию в метаданных JSON
            meta_file = os.path.join(self.local_dir, "strategy_versions.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        versions = json.load(f)
                        if strategy_id in versions:
                            return versions[strategy_id]
                except:
                    pass
            
            # Если метаданных нет, ищем версию в самом BAT-файле
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # Ищем строку комментария с версией
                        if "REM VERSION:" in line or ":: VERSION:" in line:
                            return line.split("VERSION:")[1].strip()
            except:
                pass
                
            return None
        except Exception as e:
            log(f"Ошибка при получении версии стратегии: {str(e)}", level="ERROR")
            return None

    def save_strategy_version(self, file_path, strategy_info):
        """
        Сохраняет информацию о версии стратегии.
        
        Args:
            file_path (str): Путь к файлу стратегии
            strategy_info (dict): Информация о стратегии
            
        Returns:
            bool: True при успешном сохранении, False при ошибке
        """
        try:
            strategy_id = next((k for k, v in self.strategies_cache.items() if v == strategy_info), None)
            if not strategy_id:
                return False
                
            # Сохраняем версию в метаданных JSON
            meta_file = os.path.join(self.local_dir, "strategy_versions.json")
            versions = {}
            
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        versions = json.load(f)
                except:
                    pass
            
            versions[strategy_id] = strategy_info.get('version', '1.0')
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(versions, f, ensure_ascii=False, indent=2)
            
            # Также добавляем версию в сам BAT-файл
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Добавляем заголовок с информацией о стратегии
                header = f"@echo off\n"
                header += f"REM Стратегия {strategy_info.get('name', strategy_id)}\n"
                header += f"REM VERSION: {strategy_info.get('version', '1.0')}\n"
                
                if 'updated' in strategy_info:
                    header += f"REM Дата обновления: {strategy_info['updated']}\n"
                    
                header += "\n"
                
                # Если в файле уже есть заголовок @echo off, заменяем его
                if content.strip().startswith("@echo off"):
                    lines = content.split("\n")
                    found_rem = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith("REM VERSION:"):
                            found_rem = True
                            lines[i] = f"REM VERSION: {strategy_info.get('version', '1.0')}"
                    
                    if not found_rem:
                        content = header + content[content.find("\n")+1:]
                    else:
                        content = "\n".join(lines)
                else:
                    content = header + content
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
            except Exception as e:
                log(f"Не удалось добавить версию в BAT-файл: {str(e)}", level="WARNING")
            
            return True
        except Exception as e:
            log(f"Ошибка при сохранении версии стратегии: {str(e)}", level="ERROR")
            return False
    
    def get_strategy_details(self, strategy_id):
        """
        Получает информацию о стратегии.
        
        Args:
            strategy_id (str): Идентификатор стратегии
            
        Returns:
            dict: Информация о стратегии или None при ошибке
        """
        strategies = self.get_strategies_list()
        
        if not strategies or strategy_id not in strategies:
            return None
        
        return strategies[strategy_id]
    
    def save_strategies_index(self):
        """
        Сохраняет индекс стратегий локально.
        
        Returns:
            bool: True при успешном сохранении, False при ошибке
        """
        if not self.strategies_cache:
            return False
        
        try:
            index_file = os.path.join(self.local_dir, "index.json")
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.strategies_cache, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            log(f"Ошибка при сохранении индекса стратегий: {str(e)}", level="ERROR")
            return False
    
    def update_strategies_list(self):
        """
        Обновляет список стратегий с сервера.
        
        Returns:
            bool: True при успешном обновлении, False при ошибке
        """
        try:
            self.get_strategies_list(force_update=True)
            return True
        except Exception as e:
            log(f"Ошибка при обновлении стратегий: {str(e)}", level="ERROR")
            return False