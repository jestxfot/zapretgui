import requests
import json
import uuid
import hashlib
import os, time, tempfile
from typing import Optional, Dict, Any, Tuple
from log import log

class DonateChecker:
    """
    Класс для проверки статуса подписки пользователя через удаленный сервер.
    Проверяет UUID пользователя против JSON файла на сервере без использования реестра.
    """
    
    def __init__(self, server_url: str = "https://gitflic.ru/project/megacompacy/test/blob/raw?file=donate.json"):
        """
        Инициализация проверяльщика подписки.
        
        Args:
            server_url: URL сервера с JSON файлом подписчиков
        """
        self.server_url = server_url
        self.local_uuid = self._get_machine_uuid()

        # Создаем путь к файлу кэша в папке temp
        temp_dir = tempfile.gettempdir()
        self.cache_file = os.path.join(temp_dir, "zapret_subscription_cache.json")
        
        self.cache_timeout = 3600  # 1 час в секундах

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
        Загружает данные подписчиков с сервера.
        
        Returns:
            Словарь с данными подписчиков или None при ошибке
        """
        try:
            log(f"Запрос данных подписки с сервера: {self.server_url}", level="DEBUG")
            
            headers = {
                'User-Agent': 'Zapret-Subscription-Checker/1.0',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                self.server_url, 
                timeout=10,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                log("Данные подписки успешно получены", level="DEBUG")
                return data
            else:
                log(f"Ошибка HTTP {response.status_code} при получении данных подписки", level="WARNING")
                return None
                
        except requests.exceptions.RequestException as e:
            log(f"Ошибка сети при получении данных подписки: {e}", level="WARNING")
            return None
        except json.JSONDecodeError as e:
            log(f"Ошибка парсинга JSON: {e}", level="ERROR")
            return None
        except Exception as e:
            log(f"Неожиданная ошибка при получении данных подписки: {e}", level="ERROR")
            return None
    
    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str]:
        """
        Проверяет статус подписки пользователя.
        
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
                    log("Использую кэшированные данные подписки", level="DEBUG")
            
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
                            log("Используем устаревший кэш как запасной вариант", level="INFO")
            
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
                log(f"UUID {self.local_uuid} не найден в данных подписчиков", level="INFO")
                return False, "Подписка не найдена"
            
            # Валидируем данные подписки
            if not self._validate_subscription_data(user_data, self.local_uuid):
                return False, "Недействительные данные подписки"
            
            # Проверяем статус premium
            if not user_data.get('premium', False):
                return False, "Подписка неактивна"
            
            log(f"Подписка активна для UUID {self.local_uuid}", level="INFO")
            return True, "Подписка активна"
            
        except Exception as e:
            log(f"Ошибка при проверке статуса подписки: {e}", level="ERROR")
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

def check_premium_access(server_url: str = "https://gitflic.ru/project/megacompacy/test/blob/raw?file=donate.json") -> bool:
    """
    Упрощенная функция для быстрой проверки премиум доступа.
    
    Args:
        server_url: URL сервера с данными подписчиков
        
    Returns:
        bool: True если пользователь имеет активную подписку
    """
    try:
        checker = DonateChecker(server_url)
        is_premium, _ = checker.check_subscription_status()
        return is_premium
    except Exception as e:
        log(f"Ошибка при проверке премиум доступа: {e}", level="ERROR")
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