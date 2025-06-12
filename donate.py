import requests
import json
import uuid
import hashlib
import os, time, tempfile
from typing import Optional, Dict, Any, Tuple
from log import log
from config.donate_urls import DONATE_URL_SOURCES, PRIMARY_DONATE_URL, BACKUP_DONATE_URL

class DonateChecker:
    """
    Класс для проверки статуса подписки пользователя через удаленный сервер.
    Проверяет UUID пользователя против JSON файла на сервере без использования реестра.
    """
    
    def __init__(self, server_url: str = None):
        """
        Инициализация проверяльщика подписки.
        
        Args:
            server_url: URL сервера с JSON файлом подписчиков (если None, используется конфигурация)
        """
        # Если URL передан явно, используем только его, иначе используем конфигурацию
        if server_url:
            self.url_sources = [{"name": "Custom", "url": server_url}]
        else:
            self.url_sources = DONATE_URL_SOURCES
            
        self.local_uuid = self._get_machine_uuid()
        self.failed_sources = set()  # Источники, которые не работают
        self.current_source_index = 0

        # Создаем путь к файлу кэша в папке temp
        temp_dir = tempfile.gettempdir()
        self.cache_file = os.path.join(temp_dir, "zapret_subscription_cache.json")
        
        self.cache_timeout = 3600  # 1 час в секундах
        self.max_retries = 2  # Меньше попыток для donate
        self.retry_delay = 1  # Быстрее переключение
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о кэше подписки.
        
        Returns:
            Dict с информацией о кэше
        """
        try:
            info = {
                'cache_file': self.cache_file,
                'exists': os.path.exists(self.cache_file),
                'size': 0,
                'last_modified': None,
                'age_seconds': None
            }
            
            if info['exists']:
                stat = os.stat(self.cache_file)
                info['size'] = stat.st_size
                info['last_modified'] = time.ctime(stat.st_mtime)
                info['age_seconds'] = int(time.time() - stat.st_mtime)
            
            return info
            
        except Exception as e:
            log(f"Ошибка при получении информации о кэше: {e}", level="ERROR")
            return {'error': str(e)}
           
    def _get_machine_uuid(self) -> str:
        """
        Получает уникальный UUID машины на основе аппаратных характеристик.
        
        Returns:
            str: UUID машины
        """
        try:
            # Получаем UUID на основе MAC адреса
            mac = hex(uuid.getnode())
            
            # Получаем имя компьютера для дополнительной уникальности
            import socket
            hostname = socket.gethostname()
            
            # Создаем уникальный идентификатор
            unique_string = f"{mac}-{hostname}"
            machine_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))
            
            log(f"Сгенерирован UUID машины: {machine_uuid}", level="DEBUG")
            return machine_uuid
            
        except Exception as e:
            log(f"Ошибка при получении UUID машины: {e}", level="ERROR")
            # Fallback к случайному UUID
            return str(uuid.uuid4())
    
    def _validate_subscription_data(self, data: Dict[str, Any], user_uuid: str) -> bool:
        """
        Проверяет валидность данных подписки с использованием соли.
        
        Args:
            data: Данные пользователя из JSON
            user_uuid: UUID пользователя
            
        Returns:
            bool: True если данные валидны
        """
        try:
            if not isinstance(data, dict):
                return False
                
            required_fields = ['uuid', 'salt', 'premium', 'expires']
            if not all(field in data for field in required_fields):
                return False
            
            # Проверяем UUID
            if data['uuid'] != user_uuid:
                return False
            
            # Проверяем подпись с солью
            salt = data.get('salt', '')
            expected_hash = hashlib.sha256(f"{user_uuid}{salt}premium".encode()).hexdigest()
            
            # Ищем хеш в данных (может быть в поле 'signature' или 'hash')
            actual_hash = data.get('signature') or data.get('hash')
            
            if not actual_hash or actual_hash != expected_hash:
                log(f"Неверная подпись для UUID {user_uuid}", level="WARNING")
                return False
            
            # Проверяем срок действия если указан
            expires = data.get('expires')
            if expires and expires != 'never':
                try:
                    from datetime import datetime
                    expire_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                    if datetime.now() > expire_date.replace(tzinfo=None):
                        log(f"Подписка истекла для UUID {user_uuid}", level="INFO")
                        return False
                except ValueError:
                    log(f"Неверный формат даты истечения: {expires}", level="WARNING")
                    return False
            
            return True
            
        except Exception as e:
            log(f"Ошибка при валидации данных подписки: {e}", level="ERROR")
            return False
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """
        Загружает кэшированные данные подписки.
        
        Returns:
            Кэшированные данные или None
        """
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем время кэша
            if time.time() - cache_data.get('timestamp', 0) > self.cache_timeout:
                log("Кэш подписки устарел", level="DEBUG")
                return None
                
            return cache_data.get('data')
            
        except Exception as e:
            log(f"Ошибка при загрузке кэша: {e}", level="DEBUG")
            return None
    
    def _save_cache(self, data: Dict[str, Any]) -> None:
        """
        Сохраняет данные в кэш.
        
        Args:
            data: Данные для сохранения
        """
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log(f"Ошибка при сохранении кэша: {e}", level="DEBUG")
    
    def _fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """
        Загружает данные подписчиков с сервера с поддержкой резервных источников.
        
        Returns:
            Словарь с данными подписчиков или None при ошибке
        """
        # Пробуем все доступные источники
        for source_index, source in enumerate(self.url_sources):
            if source_index in self.failed_sources:
                continue
                
            url = source["url"]
            source_name = source["name"]
            
            log(f"Запрос данных подписки с {source_name}: {url}", "DEBUG")
            
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                    
                    response = requests.get(
                        url, 
                        timeout=10,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        log(f"Данные подписки успешно получены с {source_name}", "DEBUG")
                        
                        # Обновляем текущий рабочий источник
                        self.current_source_index = source_index
                        return data
                    else:
                        raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    last_error = e
                    log(f"Попытка {attempt + 1}/{self.max_retries} для {source_name} не удалась: {e}", "DEBUG")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
                except json.JSONDecodeError as e:
                    last_error = e
                    log(f"Ошибка парсинга JSON с {source_name}: {e}", "ERROR")
                    break  # Не повторяем при ошибке парсинга
                    
                except Exception as e:
                    last_error = e
                    log(f"Неожиданная ошибка с {source_name}: {e}", "ERROR")
                    break
            
            # Все попытки для этого источника неудачны
            log(f"Источник {source_name} недоступен: {last_error}", "WARNING")
            self.failed_sources.add(source_index)
        
        # Все источники исчерпаны
        log("Все источники данных подписки недоступны", "ERROR")
        return None

    def get_current_source_info(self) -> dict:
        """Возвращает информацию о текущем активном источнике"""
        if 0 <= self.current_source_index < len(self.url_sources):
            return self.url_sources[self.current_source_index]
        return {"name": "Неизвестно", "url": ""}
    
    def check_sources_availability(self) -> dict:
        """Проверяет доступность всех источников donate"""
        results = {}
        
        for i, source in enumerate(self.url_sources):
            source_name = source["name"]
            test_url = source["url"]
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                response = requests.get(test_url, timeout=10, headers=headers)
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
        
        return results
    
    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str]:
        """
        Проверяет статус подписки пользователя с поддержкой резервных источников.
        
        Args:
            use_cache: Использовать ли кэш для проверки
            
        Returns:
            Tuple[bool, str]: (активна ли подписка, сообщение о статусе)
        """
        try:
            # Сначала пробуем загрузить из кэша
            subscription_data = None
            if use_cache:
                subscription_data = self._load_cache()
                if subscription_data:
                    log("Использую кэшированные данные подписки", "DEBUG")
            
            # Если кэш пуст или не используется, загружаем с сервера
            if not subscription_data:
                subscription_data = self._fetch_subscription_data()
                if subscription_data:
                    self._save_cache(subscription_data)
                else:
                    # Если не удалось загрузить с сервера, пробуем кэш как fallback
                    if not use_cache:
                        subscription_data = self._load_cache()
                        if subscription_data:
                            log("Используем устаревший кэш как запасной вариант", "INFO")
            
            if not subscription_data:
                return False, "Не удалось получить данные подписки"
            
            # Проверяем наш UUID в данных
            user_data = None
            
            # Поддерживаем разные форматы JSON
            if isinstance(subscription_data, dict):
                if 'subscribers' in subscription_data:
                    # Формат: {"subscribers": [{"uuid": "...", ...}, ...]}
                    subscribers = subscription_data['subscribers']
                elif 'users' in subscription_data:
                    # Формат: {"users": [{"uuid": "...", ...}, ...]}
                    subscribers = subscription_data['users']
                else:
                    # Формат: {"uuid1": {...}, "uuid2": {...}}
                    user_data = subscription_data.get(self.local_uuid)
                    if user_data:
                        user_data['uuid'] = self.local_uuid  # Добавляем UUID для валидации
                
                # Если данные в виде списка
                if not user_data and 'subscribers' in locals():
                    for subscriber in subscribers:
                        if subscriber.get('uuid') == self.local_uuid:
                            user_data = subscriber
                            break
            
            if not user_data:
                log(f"UUID {self.local_uuid} не найден в данных подписчиков", "INFO")
                return False, "Подписка не найдена"
            
            # Валидируем данные подписки
            if not self._validate_subscription_data(user_data, self.local_uuid):
                return False, "Недействительные данные подписки"
            
            # Проверяем статус premium
            if not user_data.get('premium', False):
                return False, "Подписка неактивна"
            
            current_source = self.get_current_source_info()
            log(f"Подписка активна для UUID {self.local_uuid} (источник: {current_source['name']})", "INFO")
            return True, "Подписка активна"
            
        except Exception as e:
            log(f"Ошибка при проверке статуса подписки: {e}", "ERROR")
            return False, f"Ошибка проверки: {str(e)}"
    
    def get_machine_uuid(self) -> str:
        """
        Возвращает UUID текущей машины.
        
        Returns:
            str: UUID машины
        """
        return self.local_uuid
    
    def clear_cache(self) -> None:
        """
        Очищает кэш подписки.
        """
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                log(f"Кэш подписки очищен: {self.cache_file}", level="INFO")
            else:
                log("Файл кэша не существует", level="DEBUG")
        except Exception as e:
            log(f"Ошибка при очистке кэша: {e}", level="WARNING")

def check_premium_access(server_url: str = None) -> bool:
    """
    Упрощенная функция для быстрой проверки премиум доступа с поддержкой резервных источников.
    
    Args:
        server_url: URL сервера с данными подписчиков (если None, используется конфигурация)
        
    Returns:
        bool: True если пользователь имеет активную подписку
    """
    try:
        checker = DonateChecker(server_url)
        is_premium, _ = checker.check_subscription_status()
        return is_premium
    except Exception as e:
        log(f"Ошибка при проверке премиум доступа: {e}", "ERROR")
        return False

def get_current_machine_uuid() -> str:
    """
    Возвращает UUID текущей машины.
    
    Returns:
        str: UUID машины
    """
    try:
        checker = DonateChecker()
        return checker.get_machine_uuid()
    except Exception as e:
        log(f"Ошибка при получении UUID машины: {e}", level="ERROR")
        return "Ошибка получения UUID"