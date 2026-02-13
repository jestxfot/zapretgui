"""tgram/tg_log_bot.py

Upload full log files to the Support Panel HTTP API.
The panel forwards files to Telegram for storage and indexes them in SQLite.

This removes the need for a Telegram group/channel in the client.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests


TIMEOUT = 30
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# Default can be overridden with env var ZAPRET_LOG_UPLOAD_URL.
# Example:
#   http://panel.84.54.30.233.nip.io:50608/api/logs/upload
DEFAULT_UPLOAD_URL = "http://panel.84.54.30.233.nip.io:50608/api/logs/upload"


def _get_upload_url() -> str:
    url = (os.getenv("ZAPRET_LOG_UPLOAD_URL") or DEFAULT_UPLOAD_URL or "").strip()
    return url.rstrip("/")


def _get_upload_token() -> str:
    return (os.getenv("ZAPRET_LOG_UPLOAD_TOKEN") or "").strip()


def _source_from_topic(topic_id: Optional[int]) -> str:
    """Map legacy forum topic IDs to panel sources."""
    if topic_id == 43927:
        return "orchestrator"
    if topic_id == 10852:
        return "connection_test"
    return "dev_logs"


def _shorten(text: str, limit: int = 200) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _ping_url(upload_url: str) -> str:
    if upload_url.endswith("/api/logs/upload"):
        return upload_url[: -len("/api/logs/upload")] + "/api/ping"
    return upload_url.rstrip("/") + "/api/ping"


def send_log_file(
    file_path: str | Path,
    caption: str = "",
    topic_id: int | None = None,
) -> tuple[bool, Optional[str]]:
    """Upload a log file to the support panel.

    Args:
        file_path: path to log file
        caption: extra text
        topic_id: legacy topic id (mapped to a source)

    Returns:
        (success, error_message)
    """

    upload_url = _get_upload_url()
    if not upload_url:
        return False, "Не настроен адрес панели (ZAPRET_LOG_UPLOAD_URL)"

    path = Path(file_path)
    if not path.exists():
        return False, f"Файл лога не найден: {path.name}"

    file_size = path.stat().st_size
    if file_size == 0:
        return False, "Файл лога пуст"
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        return False, f"Файл слишком большой ({size_mb:.1f} МБ). Максимум: 50 МБ"

    source = _source_from_topic(topic_id)
    token = _get_upload_token()
    headers = {}
    if token:
        headers["X-Log-Token"] = token

    try:
        with path.open("rb") as fh:
            files = {"document": (path.name, fh)}
            data = {
                "source": source,
                "caption": (caption or "")[:2000],
            }
            resp = requests.post(upload_url, data=data, files=files, headers=headers, timeout=TIMEOUT)

        if 200 <= resp.status_code < 300:
            try:
                js = resp.json()
                if js.get("ok") is True:
                    return True, None
            except Exception:
                pass
            return True, None

        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        return False, f"Ошибка панели ({resp.status_code}): {_shorten(str(detail or ''), 220)}"

    except requests.Timeout:
        return False, "Панель не отвечает (timeout)"
    except requests.ConnectionError as e:
        return False, f"Не удалось подключиться к панели: {_shorten(str(e), 220)}"
    except Exception as e:
        return False, f"Ошибка: {_shorten(str(e), 220)}"


def check_bot_connection() -> bool:
    try:
        ok, _ = check_bot_connection_detailed()
        return ok
    except Exception:
        return False


def check_bot_connection_detailed() -> tuple[bool, str]:
    upload_url = _get_upload_url()
    if not upload_url:
        return False, "Адрес панели не настроен (ZAPRET_LOG_UPLOAD_URL)"

    try:
        r = requests.get(_ping_url(upload_url), timeout=10)
        if 200 <= r.status_code < 300:
            return True, ""
        return False, f"Панель недоступна (HTTP {r.status_code})"
    except requests.Timeout:
        return False, "Панель не отвечает (timeout)"
    except Exception as e:
        return False, f"Ошибка подключения к панели: {_shorten(str(e), 180)}"


def get_bot_connection_info() -> tuple[bool, str, str]:
    ok, error_msg = check_bot_connection_detailed()
    if ok:
        return True, "", "unknown"

    msg = (error_msg or "").lower()
    if any(k in msg for k in ("не настроен", "адрес", "url")):
        return False, error_msg, "config"
    return False, error_msg, "network"
