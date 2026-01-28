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

    def pair_start(self, *, device_name: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create 8-char pairing code (TTL ~10 min). User sends this code to Telegram bot.
        """
        with self._lock:
            device_id = PremiumStorage.get_device_id()
            raw, nonce = self._api.post_pair_start(device_id=device_id, device_name=device_name)
            if not raw:
                return False, "Сервер недоступен", None

            signed = verify_signed_response(raw, expected_device_id=device_id, expected_nonce=nonce)
            if not signed or signed.get("type") != "zapret_pair_start":
                err = (raw.get("error") if isinstance(raw, dict) else None) or "Ошибка создания кода"
                return False, str(err), None

            code = str(signed.get("pair_code") or "").strip().upper()
            expires_at = signed.get("pair_expires_at")
            try:
                expires_at_i = int(expires_at)
            except Exception:
                expires_at_i = 0

            if not code or expires_at_i <= 0:
                return False, "Сервер вернул некорректный код", None

            PremiumStorage.set_pair_code(code=code, expires_at=expires_at_i)
            return True, str(signed.get("message") or "Код создан"), code

    def clear_activation(self) -> bool:
        with self._lock:
            PremiumStorage.clear_device_token()
            PremiumStorage.clear_premium_cache()
            PremiumStorage.clear_pair_code()
            PremiumStorage.clear_activation_key()
            PremiumStorage.save_last_check()
            return True

    def check_status(self) -> ActivationStatus:
        with self._lock:
            device_id = PremiumStorage.get_device_id()
            device_token = PremiumStorage.get_device_token() or ""

            # If token is missing, but we have a pending pair code, try to finish pairing first.
            if not device_token:
                code = PremiumStorage.get_pair_code()
                exp = PremiumStorage.get_pair_expires_at() or 0
                if code and int(exp) >= int(time.time()):
                    raw2, nonce2 = self._api.post_pair_finish(device_id=device_id, pair_code=code)
                    if raw2:
                        signed2 = verify_signed_response(raw2, expected_device_id=device_id, expected_nonce=nonce2)
                        if signed2 and signed2.get("type") == "zapret_premium_activation" and signed2.get("activated") is True:
                            token = str(signed2.get("device_token") or "").strip()
                            if token:
                                PremiumStorage.store_after_pairing(
                                    device_id=device_id,
                                    device_token=token,
                                    signed_payload=signed2,
                                    kid=raw2.get("kid") if isinstance(raw2, dict) else None,
                                    sig=raw2.get("sig") if isinstance(raw2, dict) else None,
                                )
                                device_token = token

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
