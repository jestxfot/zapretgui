# donater/service.py

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple

from .api import PremiumApiClient
from .crypto import verify_signed_response
from .storage import PremiumStorage
from .types import ActivationStatus


API_BASE_URL = "http://185.114.116.232:6666/api"
REQUEST_TIMEOUT = 10


class PremiumService:
    """
    Minimal "actor" service:
    - One lock for all premium operations (activate/check/clear).
    - Single storage (premium.ini).
    """

    def __init__(self, *, api_base_url: str = API_BASE_URL, timeout: int = REQUEST_TIMEOUT):
        self._lock = threading.Lock()
        self._api = PremiumApiClient(base_url=api_base_url, timeout=timeout)

    @property
    def device_id(self) -> str:
        return PremiumStorage.get_device_id()

    def test_connection(self) -> Tuple[bool, str]:
        with self._lock:
            result = self._api.get_status()
            if result and result.get("success"):
                version = result.get("version", "unknown")
                return True, f"API сервер доступен (v{version})"
            return False, "Сервер недоступен"

    def activate(self, key: str) -> Tuple[bool, str]:
        key = (key or "").strip()
        if not key:
            return False, "Введите ключ"

        with self._lock:
            device_id = PremiumStorage.get_device_id()
            raw, nonce = self._api.post_activate(key=key, device_id=device_id)
            if not raw:
                return False, "Сервер недоступен"

            signed = verify_signed_response(raw, expected_device_id=device_id, expected_nonce=nonce)
            if not signed or signed.get("type") != "zapret_premium_activation" or signed.get("activated") is not True:
                err = (raw.get("error") if isinstance(raw, dict) else None) or "Ошибка активации"
                return False, str(err)

            token = str(signed.get("device_token") or "").strip()
            if not token:
                return False, "Сервер не вернул device_token"

            ok = PremiumStorage.store_after_activation(
                device_id=device_id,
                device_token=token,
                activation_key=key,
                signed_payload=signed,
                kid=raw.get("kid") if isinstance(raw, dict) else None,
                sig=raw.get("sig") if isinstance(raw, dict) else None,
            )
            if not ok:
                return False, "Не удалось сохранить premium.ini"

            return True, str(signed.get("message") or "Ключ активирован")

    def clear_activation(self) -> bool:
        with self._lock:
            PremiumStorage.clear_device_token()
            PremiumStorage.clear_premium_cache()
            PremiumStorage.save_last_check()
            return True

    def check_status(self) -> ActivationStatus:
        with self._lock:
            device_id = PremiumStorage.get_device_id()
            device_token = PremiumStorage.get_device_token() or ""
            raw, nonce = self._api.post_check(device_id=device_id, device_token=device_token)

            if raw:
                signed = verify_signed_response(raw, expected_device_id=device_id, expected_nonce=nonce)
                if signed and signed.get("type") == "zapret_premium_status":
                    activated = bool(signed.get("activated"))
                    if activated:
                        PremiumStorage.store_status_active(
                            signed_payload=signed,
                            kid=raw.get("kid") if isinstance(raw, dict) else None,
                            sig=raw.get("sig") if isinstance(raw, dict) else None,
                        )
                    else:
                        PremiumStorage.apply_status_inactive(message=str(signed.get("message") or ""))
                    return ActivationStatus(
                        is_activated=activated,
                        days_remaining=signed.get("days_remaining"),
                        expires_at=signed.get("expires_at"),
                        status_message=str(signed.get("message") or ("Активировано" if activated else "Не активировано")),
                        subscription_level=str(signed.get("subscription_level") or ("zapretik" if activated else "–")),
                    )

            # Offline cache path
            cache = PremiumStorage.get_premium_cache()
            if isinstance(cache, dict):
                cached_resp = {"kid": cache.get("kid"), "sig": cache.get("sig"), "signed": cache.get("signed")}
                cached_signed = verify_signed_response(cached_resp, expected_device_id=device_id, expected_nonce=None)
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

    # Back-compat helpers used around the app:
    def check_device_activation(self) -> Dict[str, Any]:
        st = self.check_status()
        return {
            "found": PremiumStorage.get_device_token() is not None,
            "activated": st.is_activated,
            "is_premium": st.is_activated,
            "days_remaining": st.days_remaining,
            "status": st.status_message,
            "expires_at": st.expires_at,
            "level": "Premium" if st.subscription_level != "–" else "–",
            "subscription_level": st.subscription_level,
        }

    def get_full_subscription_info(self) -> Dict[str, Any]:
        info = self.check_device_activation()
        is_premium = bool(info.get("activated"))
        status_msg = info.get("status") or ("Premium активен" if is_premium else "Не активировано")
        return {
            "is_premium": is_premium,
            "status_msg": status_msg,
            "days_remaining": info["days_remaining"] if is_premium else None,
            "subscription_level": info["subscription_level"] if is_premium else "–",
        }


_SERVICE: Optional[PremiumService] = None


def get_premium_service() -> PremiumService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = PremiumService()
    return _SERVICE

