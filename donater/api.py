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

    def get_status(self) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(self._url("status"), timeout=self.timeout)
            return r.json() if r.status_code == 200 else (r.json() if r.content else None)
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
            data = r.json() if r.content else None
            if isinstance(data, dict):
                data["_nonce"] = nonce
                data["_http_status"] = r.status_code
            return (data if isinstance(data, dict) else None, nonce)
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
            data = r.json() if r.content else None
            if isinstance(data, dict):
                data["_nonce"] = nonce
                data["_http_status"] = r.status_code
            return (data if isinstance(data, dict) else None, nonce)
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
            data = r.json() if r.content else None
            if isinstance(data, dict):
                data["_nonce"] = nonce
                data["_http_status"] = r.status_code
            return (data if isinstance(data, dict) else None, nonce)
        except Exception:
            return (None, nonce)
