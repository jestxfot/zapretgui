# donater/donate.py
"""
Back-compat facade.

Вся бизнес-логика живет в `donater/` (storage/api/crypto/service).
Снаружи можно продолжать импортировать DonateChecker, а также использовать
`_verify_signed_response` в тестах.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import crypto as _crypto
from .crypto import TRUSTED_PUBLIC_KEYS_B64
from .service import PremiumService, get_premium_service
from .storage import PremiumStorage as RegistryManager


def _verify_signed_response(resp: Dict, *, expected_device_id: str, expected_nonce: Optional[str] = None) -> Optional[Dict]:
    # Important for tests: allow patching donater.donate.TRUSTED_PUBLIC_KEYS_B64 at runtime.
    return _crypto.verify_signed_response(
        resp,
        expected_device_id=expected_device_id,
        expected_nonce=expected_nonce,
        trusted_public_keys_b64=TRUSTED_PUBLIC_KEYS_B64,
    )


class DonateChecker:
    """
    Back-compat wrapper for legacy call sites.
    Internally uses a single PremiumService instance.
    """

    def __init__(self):
        self._svc = get_premium_service()
        self.device_id = self._svc.device_id

    def activate(self, key: str) -> Tuple[bool, str]:
        return self._svc.activate(key)

    def check_device_activation(self) -> Dict[str, Any]:
        return self._svc.check_device_activation()

    def get_full_subscription_info(self) -> Dict[str, Any]:
        return self._svc.get_full_subscription_info()

    def check_subscription_status(self, use_cache: bool = True) -> Tuple[bool, str, Optional[int]]:
        info = self.get_full_subscription_info()
        return (bool(info["is_premium"]), str(info["status_msg"]), info.get("days_remaining"))

    def test_connection(self) -> Tuple[bool, str]:
        return self._svc.test_connection()

    def clear_saved_key(self) -> bool:
        # Keep activation key for convenience; clear only token+cache.
        return self._svc.clear_activation()


# More explicit modern names (preferred)
get_service = get_premium_service
