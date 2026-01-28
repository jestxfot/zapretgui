# donater/donate.py

import base64
import json
import logging
import secrets
import time
import hashlib
import platform
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

import requests, winreg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
from config import REGISTRY_PATH_GUI
DEVICE_ID_VALUE = "DeviceID"
KEY_VALUE = "ActivationKey"  # legacy (no longer trusted for premium status)
LAST_CHECK_VALUE = "LastCheck"
DEVICE_TOKEN_VALUE = "DeviceToken"
PREMIUM_CACHE_VALUE = "PremiumCacheV1"

#
# API server validates subscription locally (on bot server) and talks to remote keys storage itself.
# The Windows client should point to the bot server API host, not to the keys storage host.
#
# API server host (this is the keys server in current setup).
API_BASE_URL = "http://185.114.116.232:6666/api"
REQUEST_TIMEOUT = 10

FALLBACK_API_BASE_URLS = [
    API_BASE_URL,
]

# ============== CRYPTO / SIGNATURES ==============

# kid -> base64(raw 32-byte Ed25519 public key)
TRUSTED_PUBLIC_KEYS_B64 = {
    # Generated 2026-01-28 (must match server ACTIVE_SIGNING_KID)
    "v1": "ZnAipafIOF9CFCxclD7cdPJIzP+HO/4OzjHzwwLIEfI=",
}


def _canonical_json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64url_decode(data: str) -> bytes:
    data = (data or "").strip()
    if not data:
        return b""
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _b64_decode(data: str) -> bytes:
    return base64.b64decode((data or "").strip())


def _verify_signed_response(resp: Dict, *, expected_device_id: str, expected_nonce: Optional[str] = None) -> Optional[Dict]:
    """
    Verify server response signature.

    Returns the signed payload dict when valid; otherwise None.
    """
    try:
        if not isinstance(resp, dict):
            return None

        signed = resp.get("signed")
        kid = (resp.get("kid") or "").strip()
        sig = (resp.get("sig") or "").strip()

        if not isinstance(signed, dict) or not kid or not sig:
            return None

        pub_b64 = TRUSTED_PUBLIC_KEYS_B64.get(kid)
        if not pub_b64:
            return None

        pub_raw = _b64_decode(pub_b64)
        if len(pub_raw) != 32:
            return None

        sig_bytes = _b64url_decode(sig)
        if len(sig_bytes) != 64:
            return None

        pub = Ed25519PublicKey.from_public_bytes(pub_raw)
        pub.verify(sig_bytes, _canonical_json(signed))

        if str(signed.get("device_id") or "") != str(expected_device_id):
            return None

        if expected_nonce is not None and str(signed.get("nonce") or "") != str(expected_nonce):
            return None

        return signed
    except Exception:
        return None

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
    def get_device_token() -> Optional[str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                value, _ = winreg.QueryValueEx(key, DEVICE_TOKEN_VALUE)
                value = (value or "").strip()
                return value or None
        except Exception:
            return None

    @staticmethod
    def set_device_token(token: str) -> bool:
        try:
            token = (token or "").strip()
            if not token:
                return False
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                winreg.SetValueEx(key, DEVICE_TOKEN_VALUE, 0, winreg.REG_SZ, token)
            return True
        except Exception:
            return False

    @staticmethod
    def clear_device_token() -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, DEVICE_TOKEN_VALUE)
            return True
        except Exception:
            return True

    @staticmethod
    def get_premium_cache() -> Optional[Dict]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                raw, _ = winreg.QueryValueEx(key, PREMIUM_CACHE_VALUE)
            raw = (raw or "").strip()
            if not raw:
                return None
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    @staticmethod
    def set_premium_cache(cache: Dict) -> bool:
        try:
            if not isinstance(cache, dict):
                return False
            raw = json.dumps(cache, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI) as key:
                winreg.SetValueEx(key, PREMIUM_CACHE_VALUE, 0, winreg.REG_SZ, raw)
            return True
        except Exception:
            return False

    @staticmethod
    def clear_premium_cache() -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH_GUI, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, PREMIUM_CACHE_VALUE)
            return True
        except Exception:
            return True


# ============== API CLIENT ==============

class APIClient:
    """Клиент для API сервера"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_urls = []
        self.base_urls.extend([u for u in FALLBACK_API_BASE_URLS if u and u not in self.base_urls])
        self.base_url = self.base_urls[0] if self.base_urls else base_url
        self._last_good_base_url: Optional[str] = None
        self._host_failures: Dict[str, Tuple[int, float]] = {}  # base_url -> (fail_count, fail_until_ts)
        self._rr_cursor: int = 0
        self.device_id = RegistryManager.get_device_id()
        self.device_token = RegistryManager.get_device_token()
        try:
            logger.info(f"API hosts: {', '.join(self.base_urls) or self.base_url}")
        except Exception:
            pass
        logger.info(f"Device ID: {self.device_id[:8]}...")

    def _record_host_failure(self, base_url: str, *, is_network: bool) -> None:
        """
        Записывает неудачу хоста и выставляет backoff.
        - Для сетевых ошибок/таймаутов — агрессивнее.
        - Для HTTP 5xx — умеренно.
        """
        try:
            fail_count, fail_until = self._host_failures.get(base_url, (0, 0.0))
            fail_count = min(fail_count + 1, 10)

            # Экспоненциальная задержка с потолком.
            # Network: быстрее уходим на другие хосты, чтобы не "залипать".
            base_delay = 5 if is_network else 3
            max_delay = 120 if is_network else 60
            delay = min(int(base_delay * (2 ** (fail_count - 1))), max_delay)
            self._host_failures[base_url] = (fail_count, time.time() + delay)
        except Exception:
            pass

    def _record_host_success(self, base_url: str) -> None:
        try:
            self._host_failures.pop(base_url, None)
            self._last_good_base_url = base_url
        except Exception:
            pass

    def _iter_base_urls(self) -> list[str]:
        """
        Возвращает список base_url в порядке попыток:
        - сначала last_good (если есть и не в backoff),
        - затем round-robin по остальным,
        - пропускаем хосты на backoff.
        """
        urls = list(self.base_urls or ([self.base_url] if self.base_url else []))
        if not urls:
            return []

        now = time.time()

        def is_blocked(u: str) -> bool:
            entry = self._host_failures.get(u)
            return bool(entry and now < float(entry[1]))

        ordered: list[str] = []

        if self._last_good_base_url and self._last_good_base_url in urls and not is_blocked(self._last_good_base_url):
            ordered.append(self._last_good_base_url)

        remaining = [u for u in urls if u not in ordered and not is_blocked(u)]
        if not remaining:
            # Если все на backoff — попробуем хотя бы по одному (чтобы не зависнуть навсегда).
            remaining = [u for u in urls if u not in ordered]

        if remaining:
            start = self._rr_cursor % len(remaining)
            ordered.extend(remaining[start:] + remaining[:start])
            self._rr_cursor = (self._rr_cursor + 1) % max(len(remaining), 1)

        return ordered
    
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

    def _signed_post_best(self, endpoint: str, data: Dict, *, nonce: str, prefer_activated: bool) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
        """
        Try all base URLs and return the best signed payload.

        - If prefer_activated=True, prefer a valid signed payload with activated=True.
        - Otherwise return the first valid signed payload.
        """
        best: Optional[Dict] = None
        best_resp: Optional[Dict] = None
        best_url: Optional[str] = None

        # If we don't get a valid signed payload, we still want to return the most
        # informative error response (HTTP error beats network error).
        best_error_resp: Optional[Dict] = None
        best_error_url: Optional[str] = None

        last_resp: Optional[Dict] = None
        last_url: Optional[str] = None

        for base_url in self._iter_base_urls():
            resp = self._request_once(base_url, endpoint, "POST", data)
            if isinstance(resp, dict):
                last_resp = resp
                last_url = base_url
                http_status = resp.get("_http_status")
                if http_status is not None:
                    # Prefer any HTTP response over connection/timeout (None).
                    if best_error_resp is None or best_error_resp.get("_http_status") is None:
                        best_error_resp = resp
                        best_error_url = base_url
            signed = _verify_signed_response(resp or {}, expected_device_id=self.device_id, expected_nonce=nonce)
            if not signed:
                continue

            if prefer_activated and signed.get("activated") is True:
                self.base_url = base_url
                self._record_host_success(base_url)
                return signed, resp, base_url

            if best is None:
                best = signed
                best_resp = resp
                best_url = base_url

        if best_url:
            self.base_url = best_url
            self._record_host_success(best_url)
            return best, best_resp, best_url

        # No valid signature received. Still return the last response (usually contains a helpful error),
        # so the UI doesn't misleadingly show "server unavailable" when the server is reachable.
        chosen_resp = best_error_resp or last_resp
        chosen_url = best_error_url or last_url
        if chosen_url:
            self.base_url = chosen_url
        return best, chosen_resp, chosen_url

    def _request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """
        Request with fallback URLs.

        If we hit a host that doesn't have local subscriptions, it often returns 403 with
        'У вас нет активной подписки' even for valid users. In that case try the next host.
        """
        last = None
        for base_url in self._iter_base_urls():
            resp = self._request_once(base_url, endpoint, method, data)
            last = resp
            if not isinstance(resp, dict):
                continue
            http_status = resp.get("_http_status")
            is_success = resp.get("success") is True

            # Prefer a working host if possible.
            if is_success:
                self.base_url = base_url
                self._record_host_success(base_url)
                return resp

            err = (resp.get("error") or "").lower()

            # If the host doesn't have local subscriptions/keys, it might answer with a "no subscription"
            # error even when another host would validate successfully. Retry on the next host.
            if "нет активной подписки" in err or "no active subscription" in err:
                continue

            # Network errors / timeouts: try next host.
            if http_status is None:
                self._record_host_failure(base_url, is_network=True)
                continue

            # Server errors: try next host.
            try:
                if int(http_status) >= 500:
                    self._record_host_failure(base_url, is_network=False)
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

        nonce = secrets.token_urlsafe(16)
        signed, result, _ = self._signed_post_best(
            "activate_key",
            {
            "key": key,
            "device_id": self.device_id,
            "nonce": nonce,
            },
            nonce=nonce,
            prefer_activated=True,
        )
        if signed and signed.get("type") == "zapret_premium_activation" and signed.get("activated") is True:
            token = str(signed.get("device_token") or "").strip()
            if not token:
                return False, "Сервер не вернул device_token"

            RegistryManager.set_device_token(token)
            self.device_token = token

            # Cache signed payload for offline (7 days max enforced by server via valid_until)
            RegistryManager.set_premium_cache(
                {
                    "kid": result.get("kid"),
                    "sig": result.get("sig"),
                    "signed": signed,
                    "cached_at": int(time.time()),
                }
            )

            # We no longer store activation key on disk for security.
            RegistryManager.delete_key()

            RegistryManager.save_last_check()
            message = str(signed.get("message") or "Ключ активирован")
            logger.info(f"✅ Activation successful: {message}")
            return True, message
        
        error = result.get('error', 'Ошибка активации') if result else 'Сервер недоступен'
        logger.error(f"❌ Activation failed: {error}")
        return False, error
    
    def check_device_status(self) -> ActivationStatus:
        """Проверка статуса устройства"""
        # Try API first (if response is validly signed, it overrides/clears cache immediately).
        nonce = secrets.token_urlsafe(16)
        self.device_token = RegistryManager.get_device_token()
        signed, result, _ = self._signed_post_best(
            "check_device",
            {"device_id": self.device_id, "device_token": self.device_token, "nonce": nonce},
            nonce=nonce,
            prefer_activated=True,
        )
        if signed and signed.get("type") == "zapret_premium_status":
            RegistryManager.save_last_check()

            activated = bool(signed.get("activated"))
            if activated:
                RegistryManager.set_premium_cache(
                    {
                        "kid": result.get("kid"),
                        "sig": result.get("sig"),
                        "signed": signed,
                        "cached_at": int(time.time()),
                    }
                )
            else:
                RegistryManager.clear_premium_cache()
                # If server says token is bad, force re-activation.
                msg = str(signed.get("message") or "")
                if "активац" in msg.lower():
                    RegistryManager.clear_device_token()

            return ActivationStatus(
                is_activated=activated,
                days_remaining=signed.get("days_remaining"),
                expires_at=signed.get("expires_at"),
                status_message=str(signed.get("message") or ("Активировано" if activated else "Не активировано")),
                subscription_level=str(signed.get("subscription_level") or ("zapretik" if activated else "–")),
            )

        # API unreachable or signature invalid -> offline cache (up to signed.valid_until, max 7 days)
        cache = RegistryManager.get_premium_cache()
        if isinstance(cache, dict):
            cached_resp = {"kid": cache.get("kid"), "sig": cache.get("sig"), "signed": cache.get("signed")}
            cached_signed = _verify_signed_response(cached_resp, expected_device_id=self.device_id, expected_nonce=None)
            if cached_signed and cached_signed.get("activated") is True:
                valid_until = cached_signed.get("valid_until")
                try:
                    if int(valid_until) >= int(time.time()):
                        return ActivationStatus(
                            is_activated=True,
                            days_remaining=cached_signed.get("days_remaining"),
                            expires_at=cached_signed.get("expires_at"),
                            status_message="Активировано (offline)",
                            subscription_level=str(cached_signed.get("subscription_level") or "zapretik"),
                        )
                except Exception:
                    pass

        return ActivationStatus(
            is_activated=False,
            days_remaining=None,
            expires_at=None,
            status_message="Не активировано",
            subscription_level="–",
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
            'found': RegistryManager.get_device_token() is not None,
            'activated': status.is_activated,
            'is_premium': status.is_activated,
            'days_remaining': status.days_remaining,
            'status': status.status_message,
            'expires_at': status.expires_at,
            'level': 'Premium' if status.subscription_level != '–' else '–',
            'subscription_level': status.subscription_level
        }
    
    def get_full_subscription_info(self) -> Dict:
        """Полная информация о подписке"""
        info = self.check_device_activation()
        is_premium = bool(info.get("activated"))
        status_msg = info.get("status") or ("Premium активен" if is_premium else "Не активировано")
        
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
        RegistryManager.clear_device_token()
        RegistryManager.clear_premium_cache()
        return RegistryManager.delete_key()


# Алиас для совместимости
DonateChecker = SimpleDonateChecker
