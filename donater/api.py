# donater/api.py

from __future__ import annotations

import secrets
from typing import Any, Dict, Optional, Tuple

import requests


class PremiumApiClient:
    def __init__(self, *, base_url: str, timeout: int = 10):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = int(timeout)

    def _url(self, endpoint: str) -> str:
        endpoint = (endpoint or "").lstrip("/")
        return f"{self.base_url}/{endpoint}"

    @staticmethod
    def _truncate_text(s: str, limit: int = 400) -> str:
        s = (s or "").strip()
        if not s:
            return ""
        if len(s) <= limit:
            return s
        return s[: limit - 3] + "..."

    @staticmethod
    def _response_to_dict(r: requests.Response, *, nonce: str) -> Dict[str, Any]:
        """Best-effort convert HTTP response into a dict with debug metadata."""
        data: Dict[str, Any]
        try:
            parsed = r.json() if r.content else None
        except Exception:
            parsed = None

        if isinstance(parsed, dict):
            data = parsed
        else:
            data = {
                "success": False,
                "error": "Некорректный ответ сервера",
            }

        # Attach metadata for debugging (client-side only).
        try:
            data.setdefault("_nonce", nonce)
            data.setdefault("_http_status", int(getattr(r, "status_code", 0) or 0))
            if not data.get("_http_text"):
                data["_http_text"] = PremiumApiClient._truncate_text(getattr(r, "text", "") or "")
        except Exception:
            pass

        return data

    def get_status(self) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(self._url("status"), timeout=self.timeout)
            # Always return dict with HTTP metadata when possible.
            nonce = ""  # no nonce for GET
            data = self._response_to_dict(r, nonce=nonce)
            return data
        except Exception:
            return None

    def post_activate(self, *, key: str, device_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # Legacy endpoint (removed in new pairing architecture).
        nonce = secrets.token_urlsafe(16)
        return (None, nonce)

    def post_pair_start(self, *, device_id: str, device_name: str | None = None) -> Tuple[Optional[Dict[str, Any]], str]:
        nonce = secrets.token_urlsafe(16)
        try:
            r = requests.post(
                self._url("pair_start"),
                json={"device_id": device_id, "device_name": device_name, "nonce": nonce},
                timeout=self.timeout,
            )
            return (self._response_to_dict(r, nonce=nonce), nonce)
        except Exception:
            return (None, nonce)

    def post_pair_finish(self, *, device_id: str, pair_code: str) -> Tuple[Optional[Dict[str, Any]], str]:
        nonce = secrets.token_urlsafe(16)
        try:
            r = requests.post(
                self._url("pair_finish"),
                json={"device_id": device_id, "pair_code": pair_code, "nonce": nonce},
                timeout=self.timeout,
            )
            return (self._response_to_dict(r, nonce=nonce), nonce)
        except Exception:
            return (None, nonce)

    def post_check(self, *, device_id: str, device_token: str) -> Tuple[Optional[Dict[str, Any]], str]:
        nonce = secrets.token_urlsafe(16)
        try:
            r = requests.post(
                self._url("check_device"),
                json={"device_id": device_id, "device_token": device_token, "nonce": nonce},
                timeout=self.timeout,
            )
            return (self._response_to_dict(r, nonce=nonce), nonce)
        except Exception:
            return (None, nonce)
