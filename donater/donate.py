# donate_handler.py - упрощенное клиентское приложение для HTTP API

import requests
import json
import winreg
import hashlib
import platform
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
REGISTRY_KEY = r"SOFTWARE\ZapretGUI"
DEVICE_ID_VALUE = "DeviceID"
KEY_VALUE = "ActivationKey"
LAST_CHECK_VALUE = "LastCheck"

# API сервер
API_BASE_URL = "http://88.210.21.236:6666/api"
DEFAULT_TIMEOUT = 30
CACHE_DURATION = 300  # 5 минут


@dataclass
class ActivationStatus:
    """Статус активации"""
    is_activated: bool
    days_remaining: Optional[int]
    expires_at: Optional[str]
    status_message: str
    subscription_level: str = "–"
    is_auto_renewal: bool = False
    source: str = "unknown"
    
    def get_formatted_expiry(self) -> str:
        """Получить отформатированную информацию об истечении"""
        if not self.is_activated:
            return "Не активировано"
        
        if self.is_auto_renewal:
            return "Автопродление ⚡"
        
        if self.days_remaining is not None:
            if self.days_remaining == 0:
                return "Истекает сегодня"
            elif self.days_remaining == 1:
                return "1 день"
            else:
                return f"{self.days_remaining} дн."
        
        return "Активировано"

class RegistryManager:
    """Менеджер для работы с реестром Windows"""
    
    @staticmethod
    def get_device_id() -> str:
        """Получить или создать уникальный ID устройства"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                device_id, _ = winreg.QueryValueEx(key, DEVICE_ID_VALUE)
                logger.debug(f"Device ID из реестра: {device_id[:8]}...")
                return device_id
        except:
            pass
        
        # Генерируем новый ID
        machine_info = f"{platform.machine()}-{platform.processor()}-{platform.node()}"
        device_id = hashlib.md5(machine_info.encode()).hexdigest()
        
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                winreg.SetValueEx(key, DEVICE_ID_VALUE, 0, winreg.REG_SZ, device_id)
            logger.info(f"Создан новый Device ID: {device_id[:8]}...")
        except Exception as e:
            logger.error(f"Ошибка сохранения device_id: {e}")
        
        return device_id
    
    @staticmethod
    def save_key(activation_key: str) -> bool:
        """Сохранить ключ активации"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                winreg.SetValueEx(key, KEY_VALUE, 0, winreg.REG_SZ, activation_key)
            logger.info(f"Ключ сохранен: {activation_key[:4]}****")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения ключа: {e}")
            return False
    
    @staticmethod
    def get_key() -> Optional[str]:
        """Получить сохраненный ключ"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                activation_key, _ = winreg.QueryValueEx(key, KEY_VALUE)
                return activation_key
        except:
            return None
    
    @staticmethod
    def delete_key() -> bool:
        """Удалить сохраненный ключ"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, KEY_VALUE)
            logger.info("Ключ удален из реестра")
            return True
        except:
            return True
    
    @staticmethod
    def save_last_check(timestamp: datetime):
        """Сохранить время последней проверки"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                winreg.SetValueEx(key, LAST_CHECK_VALUE, 0, winreg.REG_SZ, timestamp.isoformat())
        except:
            pass
    
    @staticmethod
    def get_last_check() -> Optional[datetime]:
        """Получить время последней проверки"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
                value, _ = winreg.QueryValueEx(key, LAST_CHECK_VALUE)
                return datetime.fromisoformat(value)
        except:
            return None

class APIClient:
    """Клиент для работы с API сервером"""
    
    def __init__(self, base_url: str = API_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.device_id = RegistryManager.get_device_id()
        self._cache = {}
        self._cache_time = {}
        
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Выполнить запрос к API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API ошибка {endpoint}: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Ответ сервера: {error_data}")
                except:
                    pass
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с {url}: {e}")
        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса к {url}")
        except Exception as e:
            logger.error(f"Ошибка запроса {endpoint}: {e}")
        
        return None
    
    def test_connection(self) -> Tuple[bool, str]:
        """Проверить соединение с сервером"""
        result = self._make_request("status")
        
        if result and result.get('success'):
            version = result.get('version', 'unknown')
            message = f"API сервер доступен (v{version})"
            return True, message
        
        return False, "Сервер недоступен"

    def activate_key(self, key: str) -> Tuple[bool, str]:
        """Активировать ключ с повторными попытками"""
        max_attempts = 3
        retry_delay = 2
        
        for attempt in range(max_attempts):
            try:
                success, message = self._activate_key_attempt(key)
                if success:
                    return success, message
                
                # Если не последняя попытка, ждем перед повтором
                if attempt < max_attempts - 1:
                    logger.info(f"Попытка {attempt + 1} неудачна, повтор через {retry_delay}с...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logger.error(f"Ошибка при попытке {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(retry_delay)
        
        return False, f"Не удалось активировать ключ после {max_attempts} попыток"
    
    def _activate_key_attempt(self, key: str) -> Tuple[bool, str]:
        """Активировать ключ"""
        device_info = {
            "platform": platform.system(),
            "node": platform.node(),
            "machine": platform.machine(),
            "version": platform.version()
        }
        
        logger.info(f"Активация ключа {key[:4]}****")
        
        result = self._make_request("activate_key", "POST", {
            "key": key,
            "device_id": self.device_id,
            "device_info": device_info
        })
        
        if result and result.get('success'):
            # Сохраняем ключ локально
            RegistryManager.save_key(key)
            # Очищаем весь кеш после активации
            self.clear_cache()

            # Также очистите кеш валидности ключа
            cache_key = f"key_{key}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                del self._cache_time[cache_key]

            message = result.get('message', 'Ключ успешно активирован')
            logger.info(f"Успешная активация: {message}")
            return True, message
        
        error_msg = result.get('error', 'Ошибка активации') if result else 'Сервер недоступен'
        logger.error(f"Ошибка активации: {error_msg}")
        return False, error_msg
    
    def check_key_validity(self, key: str) -> Tuple[bool, Dict]:
        """Проверить валидность ключа"""
        # Проверяем кеш
        cache_key = f"key_{key}"
        if cache_key in self._cache:
            cache_age = time.time() - self._cache_time[cache_key]
            if cache_age < CACHE_DURATION:
                logger.debug("Используем кешированный результат проверки ключа")
                return self._cache[cache_key]
        
        result = self._make_request("check_key", "POST", {"key": key})
        
        if result and result.get('success'):
            data = result.get('data', {})
            is_valid = data.get('valid', False)
            
            # Кешируем результат
            cache_result = (is_valid, data)
            self._cache[cache_key] = cache_result
            self._cache_time[cache_key] = time.time()
            
            return is_valid, data
        
        return False, {'error': 'Ошибка проверки ключа'}
    
    def check_device_status(self, use_cache: bool = True) -> ActivationStatus:
        """Проверить статус устройства"""
        # Проверяем кеш
        cache_key = f"device_{self.device_id}"
        if use_cache and cache_key in self._cache:
            cache_age = time.time() - self._cache_time[cache_key]
            if cache_age < CACHE_DURATION:
                logger.debug("Используем кешированный статус устройства")
                return self._cache[cache_key]
        
        logger.info("Проверка статуса устройства")
        
        result = self._make_request("check_device", "POST", {"device_id": self.device_id})
        
        if result and result.get('success'):
            is_activated = result.get('activated', False)
            
            if is_activated:
                days_remaining = result.get('days_remaining')
                
                # Проверяем автопродление: None или 99999 дней
                is_auto_renewal = days_remaining is None or days_remaining == 99999
                
                # Если автопродление, не показываем количество дней
                display_days = None if is_auto_renewal else days_remaining
                
                status = ActivationStatus(
                    is_activated=True,
                    days_remaining=display_days,  # None для автопродления
                    expires_at=result.get('expires_at'),
                    status_message=result.get('message', 'Активировано'),
                    subscription_level=result.get('subscription_level', 'zapretik'),
                    is_auto_renewal=is_auto_renewal,
                    source='api'
                )
                
                # Обновляем сообщение статуса для автопродления
                if is_auto_renewal:
                    status.status_message = 'Активировано (автопродление)'
                
                logger.info(f"Устройство активировано: {status.status_message}")
            else:
                status = ActivationStatus(
                    is_activated=False,
                    days_remaining=None,
                    expires_at=None,
                    status_message=result.get('message', 'Не активировано'),
                    subscription_level='–',
                    is_auto_renewal=False,
                    source='api'
                )
                
                logger.info(f"Устройство не активировано: {status.status_message}")
            
            # Кешируем результат
            self._cache[cache_key] = status
            self._cache_time[cache_key] = time.time()
            
            # Сохраняем время проверки
            RegistryManager.save_last_check(datetime.now())
            
            return status
        
        # Offline режим - проверяем локально сохраненный ключ
        logger.warning("API недоступен, проверяем локальный ключ")
        
        saved_key = RegistryManager.get_key()
        if saved_key:
            return ActivationStatus(
                is_activated=True,
                days_remaining=None,
                expires_at=None,
                status_message='Активировано (offline режим)',
                subscription_level='zapretik',
                is_auto_renewal=False,
                source='offline'
            )
        
        return ActivationStatus(
            is_activated=False,
            days_remaining=None,
            expires_at=None,
            status_message='Не активировано',
            subscription_level='–',
            is_auto_renewal=False,
            source='offline'
        )
    
    def get_statistics(self) -> Optional[Dict]:
        """Получить статистику с сервера"""
        result = self._make_request("stats")
        if result and result.get('success'):
            return result.get('stats')
        return None
    
    def clear_cache(self):
        """Очистить кеш"""
        self._cache.clear()
        self._cache_time.clear()
        logger.debug("Кеш очищен")

class SimpleDonateChecker:
    """Основной класс для проверки подписки (совместимость со старым кодом)"""
    
    def __init__(self):
        self.api_client = APIClient()
        self.device_id = RegistryManager.get_device_id()
        logger.info(f"Using device_id: {self.device_id[:8]}...")
        self.timeout = self.api_client.timeout
    
    def activate(self, key: str) -> Tuple[bool, str]:
        """Активировать ключ"""
        return self.api_client.activate_key(key)
    
    def check_device_activation(self) -> Dict[str, Any]:
        """Проверить активацию устройства"""
        status = self.api_client.check_device_status()
        
        # Преобразуем в старый формат для совместимости
        return {
            'found': status.is_activated or RegistryManager.get_key() is not None,
            'activated': status.is_activated,
            'days_remaining': status.days_remaining,
            'status': status.status_message,
            'expires_at': status.expires_at,
            'level': 'Premium' if status.subscription_level != '–' else '–',
            'auto_payment': status.is_auto_renewal,
            'subscription_level': status.subscription_level,
            'source': status.source
        }

    # Функция для быстрой проверки (не используется вообще)
    def check_premium_access(self, email: str = None) -> Tuple[bool, Optional[int]]:
        """Быстрая проверка премиум доступа"""
        try:
            result = self.check_device_activation()
            return result['activated'], result['days_remaining']
        except Exception as e:
            logger.error(f"Ошибка проверки премиум: {e}")
            return False, None
        
    def get_full_subscription_info(self):
        """
        Получает полную информацию о подписке включая автопродление.
        
        Returns:
            dict: {
                'is_premium': bool,
                'status_msg': str,
                'days_remaining': int или None,
                'is_auto_renewal': bool,
                'subscription_level': str
            }
        """
        try:
            device_info = self.check_device_activation()
            
            return {
                'is_premium': device_info.get('activated', False),
                'status_msg': device_info.get('status', 'Неизвестно'),
                'days_remaining': device_info.get('days_remaining'),
                'is_auto_renewal': device_info.get('auto_payment', False),
                'subscription_level': device_info.get('subscription_level', '–')
            }
        except Exception as e:
            from log import log
            log(f"Ошибка получения информации о подписке: {e}", "❌ ERROR")
            return {
                'is_premium': False,
                'status_msg': 'Ошибка проверки',
                'days_remaining': None,
                'is_auto_renewal': False,
                'subscription_level': '–'
            }
        
    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str, Optional[int]]:
        """Проверить статус подписки"""
        status = self.api_client.check_device_status(use_cache)
        return status.is_activated, status.status_message, status.days_remaining
    
    def test_connection(self) -> Tuple[bool, str]:
        """Проверить соединение"""
        return self.api_client.test_connection()
    
    def save_key_to_registry(self, key: str) -> bool:
        """Сохранить ключ в реестр"""
        return RegistryManager.save_key(key)
    
    def get_key_from_registry(self) -> Optional[str]:
        """Получить ключ из реестра"""
        return RegistryManager.get_key()
    
    def clear_saved_key(self) -> bool:
        """Удалить сохраненный ключ"""
        self.api_client.clear_cache()
        return RegistryManager.delete_key()
    
    def clear_cache(self):
        """Очистить кеш"""
        self.api_client.clear_cache()

# Алиас для совместимости
DonateChecker = SimpleDonateChecker