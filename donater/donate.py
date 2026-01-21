# donater/donate.py

import requests, winreg, hashlib, platform, logging
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
from config import REGISTRY_PATH_GUI
DEVICE_ID_VALUE = "DeviceID"
KEY_VALUE = "ActivationKey"
LAST_CHECK_VALUE = "LastCheck"

#
# API server validates subscription locally (on bot server) and talks to remote keys storage itself.
# The Windows client should point to the bot server API host, not to the keys storage host.
#
# You can override the URL via registry:
#   HKCU\\<REGISTRY_PATH_GUI>\\ApiBaseUrl
#
# Default points to the bot server (where subscriptions are stored locally).
API_BASE_URL = "http://31.192.111.158:6666/api"
REQUEST_TIMEOUT = 10

API_BASE_URL_REGISTRY_VALUE = "ApiBaseUrl"
FALLBACK_API_BASE_URLS = [
    API_BASE_URL,
    "http://84.54.30.233:6666/api",
]

# ============== DATA CLASSES ==============

@dataclass
class ActivationStatus:
    """Статус активации"""
    is_activated: bool
    days_remaining: Optional[int]
    expires_at: Optional[str]
    status_message: str
    subscription_level: str = "–"
    
    def get_formatted_expiry(self) -> str:
        """Форматированная информация об истечении"""
        if not self.is_activated:
            return "Не активировано"
        
        if self.days_remaining is not None:
            if self.days_remaining == 0:
                return "Истекает сегодня"
            elif self.days_remaining == 1:
                return "1 день"
            else:
                return f"{self.days_remaining} дн."
        
        return "Активировано"


# ============== REGISTRY MANAGER ==============

class RegistryManager:
    """Работа с реестром Windows"""
    
    @staticmethod
    def get_device_id() -> str:
        """Получить или создать Device ID"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                device_id, _ = winreg.QueryValueEx(key, DEVICE_ID_VALUE)
                return device_id
        except:
            pass
        
        # Генерируем новый
        machine_info = f"{platform.machine()}-{platform.processor()}-{platform.node()}"
        device_id = hashlib.md5(machine_info.encode()).hexdigest()
        
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                winreg.SetValueEx(key, DEVICE_ID_VALUE, 0, winreg.REG_SZ, device_id)
            logger.info(f"Created Device ID: {device_id[:8]}...")
        except Exception as e:
            logger.error(f"Error saving device_id: {e}")
        
        return device_id
    
    @staticmethod
    def save_key(key: str) -> bool:
        """Сохранить ключ"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as reg_key:
                winreg.SetValueEx(reg_key, KEY_VALUE, 0, winreg.REG_SZ, key)
            logger.info(f"Key saved: {key[:4]}****")
            return True
        except Exception as e:
            logger.error(f"Error saving key: {e}")
            return False
    
    @staticmethod
    def get_key() -> Optional[str]:
        """Получить сохраненный ключ"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                value, _ = winreg.QueryValueEx(key, KEY_VALUE)
                return value
        except:
            return None
    
    @staticmethod
    def delete_key() -> bool:
        """Удалить ключ"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, KEY_VALUE)
            logger.info("Key deleted")
            return True
        except:
            return True
    
    @staticmethod
    def save_last_check() -> bool:
        """Сохранить время последней проверки"""
        try:
            timestamp = datetime.now().isoformat()
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as reg_key:
                winreg.SetValueEx(reg_key, LAST_CHECK_VALUE, 0, winreg.REG_SZ, timestamp)
            logger.debug(f"Last check saved: {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error saving last_check: {e}")
            return False
    
    @staticmethod
    def get_last_check() -> Optional[datetime]:
        """Получить время последней проверки"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                timestamp_str, _ = winreg.QueryValueEx(key, LAST_CHECK_VALUE)
                return datetime.fromisoformat(timestamp_str)
        except:
            return None

    @staticmethod
    def get_api_base_url() -> Optional[str]:
        """Get API base URL override from registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                value, _ = winreg.QueryValueEx(key, API_BASE_URL_REGISTRY_VALUE)
                value = (value or "").strip()
                return value or None
        except Exception:
            return None

    @staticmethod
    def set_api_base_url(base_url: str) -> bool:
        """Persist API base URL to registry (best-effort)."""
        try:
            base_url = (base_url or "").strip()
            if not base_url:
                return False
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                winreg.SetValueEx(key, API_BASE_URL_REGISTRY_VALUE, 0, winreg.REG_SZ, base_url)
            return True
        except Exception:
            return False


# ============== API CLIENT ==============

class APIClient:
    """Клиент для API сервера"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        override = RegistryManager.get_api_base_url()
        self.base_urls = []
        if override:
            self.base_urls.append(override)
        self.base_urls.extend([u for u in FALLBACK_API_BASE_URLS if u and u not in self.base_urls])
        self.base_url = self.base_urls[0] if self.base_urls else base_url
        self.device_id = RegistryManager.get_device_id()
        logger.info(f"Device ID: {self.device_id[:8]}...")
    
    def _request_once(self, base_url: str, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Выполнить HTTP запрос"""
        url = f"{base_url}/{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            # Пытаемся получить JSON даже при ошибке (сервер может вернуть описание ошибки)
            try:
                result = response.json()
            except:
                result = None
            
            if response.status_code == 200:
                if isinstance(result, dict):
                    result["_http_status"] = response.status_code
                    result["_api_base_url"] = base_url
                return result
            else:
                logger.error(f"HTTP {response.status_code}: {endpoint}")
                # Возвращаем результат с ошибкой если он есть
                if result:
                    if isinstance(result, dict):
                        result["_http_status"] = response.status_code
                        result["_api_base_url"] = base_url
                    return result
                return {'success': False, 'error': f'Ошибка сервера: {response.status_code}', '_http_status': response.status_code, '_api_base_url': base_url}
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: {url}")
            return {'success': False, 'error': 'Нет подключения к серверу', '_http_status': None, '_api_base_url': base_url}
        except requests.exceptions.Timeout:
            logger.error(f"Timeout: {url}")
            return {'success': False, 'error': 'Превышено время ожидания', '_http_status': None, '_api_base_url': base_url}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {'success': False, 'error': f'Ошибка запроса: {e}', '_http_status': None, '_api_base_url': base_url}
        
        return None

    def _request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """
        Request with fallback URLs.

        If we hit a host that doesn't have local subscriptions, it often returns 403 with
        'У вас нет активной подписки' even for valid users. In that case try the next host.
        """
        last = None
        for base_url in (self.base_urls or [self.base_url]):
            resp = self._request_once(base_url, endpoint, method, data)
            last = resp
            if not isinstance(resp, dict):
                continue
            http_status = resp.get("_http_status")
            is_success = resp.get("success") is True

            # Prefer a working host if possible.
            if is_success:
                self.base_url = base_url
                RegistryManager.set_api_base_url(base_url)
                return resp

            err = (resp.get("error") or "").lower()

            # If the host doesn't have local subscriptions/keys, it might answer with a "no subscription"
            # error even when another host would validate successfully. Retry on the next host.
            if "нет активной подписки" in err or "no active subscription" in err:
                continue

            # Network errors / timeouts: try next host.
            if http_status is None:
                continue

            # Server errors: try next host.
            try:
                if int(http_status) >= 500:
                    continue
            except Exception:
                pass

            # Endpoint not found / method not allowed on this host: try next host.
            if http_status in (404, 405):
                continue

            # Rate limited: try next host.
            if http_status == 429:
                continue

            # success or other error: stick to this base_url
            return resp

        return last
    
    def test_connection(self) -> Tuple[bool, str]:
        """Проверка соединения"""
        result = self._request("status")
        
        if result and result.get('success'):
            version = result.get('version', 'unknown')
            return True, f"API сервер доступен (v{version})"
        
        return False, "Сервер недоступен"
    
    def activate_key(self, key: str) -> Tuple[bool, str]:
        """Активация ключа"""
        logger.info(f"Activating key: {key[:4]}****")
        
        result = self._request("activate_key", "POST", {
            "key": key,
            "device_id": self.device_id
        })
        
        if result and result.get('success'):
            # Сохраняем ключ локально
            RegistryManager.save_key(key)
            # Сохраняем время проверки
            RegistryManager.save_last_check()
            
            message = result.get('message', 'Ключ активирован')
            logger.info(f"✅ Activation successful: {message}")
            return True, message
        
        error = result.get('error', 'Ошибка активации') if result else 'Сервер недоступен'
        logger.error(f"❌ Activation failed: {error}")
        return False, error
    
    def check_device_status(self) -> ActivationStatus:
        """Проверка статуса устройства"""
        # Пробуем API
        result = self._request("check_device", "POST", {"device_id": self.device_id})
        
        if result and result.get('success'):
            # Сохраняем время проверки при успешном ответе
            RegistryManager.save_last_check()
            
            if result.get('activated'):
                # Активировано
                return ActivationStatus(
                    is_activated=True,
                    days_remaining=result.get('days_remaining'),
                    expires_at=result.get('expires_at'),
                    status_message=result.get('message', 'Активировано'),
                    subscription_level=result.get('subscription_level', 'zapretik')
                )
            else:
                # Не активировано
                return ActivationStatus(
                    is_activated=False,
                    days_remaining=None,
                    expires_at=None,
                    status_message=result.get('message', 'Не активировано'),
                    subscription_level='–'
                )
        
        # API недоступен - offline режим
        logger.warning("API unavailable, using offline mode")
        
        saved_key = RegistryManager.get_key()
        if saved_key:
            # Если есть ключ - считаем что активировано
            return ActivationStatus(
                is_activated=True,
                days_remaining=None,
                expires_at=None,
                status_message='Активировано (offline)',
                subscription_level='zapretik'
            )
        
        # Нет ключа
        return ActivationStatus(
            is_activated=False,
            days_remaining=None,
            expires_at=None,
            status_message='Не активировано',
            subscription_level='–'
        )


# ============== MAIN CLASS ==============

class SimpleDonateChecker:
    """Главный класс (совместимость со старым кодом)"""
    
    def __init__(self):
        self.api_client = APIClient()
        self.device_id = self.api_client.device_id
    
    def activate(self, key: str) -> Tuple[bool, str]:
        """Активировать ключ"""
        return self.api_client.activate_key(key)
    
    def check_device_activation(self) -> Dict:
        """Проверить активацию устройства"""
        status = self.api_client.check_device_status()
        
        return {
            'found': RegistryManager.get_key() is not None,
            'activated': status.is_activated,
            'days_remaining': status.days_remaining,
            'status': status.status_message,
            'expires_at': status.expires_at,
            'level': 'Premium' if status.subscription_level != '–' else '–',
            'subscription_level': status.subscription_level
        }
    
    def get_full_subscription_info(self) -> Dict:
        """Полная информация о подписке"""
        info = self.check_device_activation()
        
        # ✅ Premium только если ЕСТЬ локальный ключ И сервер подтвердил активацию
        # Это синхронизирует логику с premium_page.py
        has_local_key = RegistryManager.get_key() is not None
        is_premium = info['activated'] and has_local_key
        
        # Если сервер говорит activated, но ключа нет локально - статус "требуется активация"
        if info['activated'] and not has_local_key:
            status_msg = "Требуется активация (введите ключ)"
        else:
            status_msg = info['status']
        
        return {
            'is_premium': is_premium,
            'status_msg': status_msg,
            'days_remaining': info['days_remaining'] if is_premium else None,
            'subscription_level': info['subscription_level'] if is_premium else '–'
        }
    
    # ✅ МЕТОД ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str, Optional[int]]:
        """
        Проверка статуса подписки (старый API для обратной совместимости)
        
        Args:
            use_cache: Игнорируется (для совместимости со старым API)
            
        Returns:
            Tuple[bool, str, Optional[int]]: (is_premium, status_message, days_remaining)
        """
        try:
            info = self.get_full_subscription_info()
            
            return (
                info['is_premium'],
                info['status_msg'],
                info['days_remaining']
            )
        except Exception as e:
            logger.error(f"Error in check_subscription_status: {e}")
            return (False, f"Ошибка проверки: {e}", None)
    
    def test_connection(self) -> Tuple[bool, str]:
        """Проверка соединения"""
        return self.api_client.test_connection()
    
    def clear_saved_key(self) -> bool:
        """Удалить сохраненный ключ"""
        return RegistryManager.delete_key()


# Алиас для совместимости
DonateChecker = SimpleDonateChecker
