"""
Отдельный бот для отправки полных логов пользователями.
Используется только при ручной отправке через меню.
Выбор бота зависит от канала сборки (stable/test).
"""

from __future__ import annotations
from pathlib import Path
import requests
import time
import base64
from typing import Optional

# Группа для логов
LOG_CHAT_ID = -1003005847271

# Топик по умолчанию зависит от канала: test → 10854, stable → 1
def _get_default_topic() -> int:
    from config.build_info import CHANNEL
    return 10854 if CHANNEL == "test" else 1

# прод-бот (stable)
_PROD_ENC = "c3h+fnp8fn58enEKCgMyHnMRHAZ4fSxmOx4cHCIuMSYxIT8jfQoEfDgAKAAgDg=="
_PROD_XOR = 0x4B
_PROD_SUM = 527

# dev-бот (test)
_DEV_ENC = "ZGhoZW5tZWVobGYdHRs1ZCopGxgvN2sSHi0EbWwmGDpxamopPnEtbRhqEWoQMw=="
_DEV_XOR = 0x5C
_DEV_SUM = 530


def _decode_token(encoded: str, xor_key: int, checksum: int) -> str:
    """Декодирует токен бота"""
    try:
        decoded = base64.b64decode(encoded)
        value = ''.join(chr(b ^ xor_key) for b in decoded)

        # Проверка контрольной суммы первых 10 символов
        calc_sum = sum(ord(c) for c in value[:10])
        if calc_sum != checksum:
            return ""

        return value
    except:
        return ""


# Кэшированный токен
_token_cache = None


def _get_bot_token() -> str:
    """Возвращает токен бота в зависимости от канала сборки"""
    global _token_cache

    if _token_cache is None:
        from config.build_info import CHANNEL

        if CHANNEL == "stable":
            _token_cache = _decode_token(_PROD_ENC, _PROD_XOR, _PROD_SUM)
        else:
            _token_cache = _decode_token(_DEV_ENC, _DEV_XOR, _DEV_SUM)

    return _token_cache


# Настройки
TIMEOUT = 30
MAX_RETRIES = 3
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB максимальный размер файла


def _get_log_api() -> str:
    """API endpoint для бота"""
    return f"https://api.telegram.org/bot{_get_bot_token()}"


def _safe_api_call(method: str, *, data=None, files=None) -> Optional[dict]:
    """
    Безопасный вызов Telegram API с обработкой flood-wait (тихий режим).
    """
    from .tg_sender import _set_flood_cooldown

    for attempt in range(MAX_RETRIES + 1):
        try:
            url = f"{_get_log_api()}/{method}"
            response = requests.post(url, data=data, files=files, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            if e.response and e.response.status_code == 429:
                try:
                    result = e.response.json()
                    retry_after = result.get("parameters", {}).get("retry_after", 60)
                except Exception:
                    retry_after = 60

                wait_time = int(retry_after) + 1
                if attempt < MAX_RETRIES:
                    time.sleep(wait_time)
                    continue
                else:
                    _set_flood_cooldown()
                    return None
            _set_flood_cooldown()
            return None
        except Exception:
            _set_flood_cooldown()
            return None

    _set_flood_cooldown()
    return None


def send_log_file(file_path: str | Path, caption: str = "", topic_id: int = None) -> tuple[bool, Optional[str]]:
    """
    Отправляет файл лога через бота в группу с топиком (тихий режим).

    Args:
        file_path: путь к файлу лога
        caption: подпись к файлу
        topic_id: ID топика (если None - выбирается по каналу: test→10854, stable→1)

    Returns:
        (success, error_message)
    """
    from .tg_sender import is_in_flood_cooldown, _set_flood_cooldown

    if topic_id is None:
        topic_id = _get_default_topic()

    if is_in_flood_cooldown():
        return False, None

    try:
        token = _get_bot_token()
        if not token:
            return False, None

        path = Path(file_path)
        if not path.exists():
            return False, None

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, None

        with path.open("rb") as file:
            files = {"document": file}
            data = {
                "chat_id": LOG_CHAT_ID,
                "message_thread_id": topic_id,
                "caption": caption[:1024] if caption else path.name
            }
            result = _safe_api_call("sendDocument", data=data, files=files)

        if result and result.get("ok"):
            return True, None
        return False, None

    except Exception:
        _set_flood_cooldown()
        return False, None


def check_bot_connection() -> bool:
    """
    Проверяет доступность бота для логов (тихий режим).
    """
    try:
        token = _get_bot_token()
        if not token:
            return False

        result = _safe_api_call("getMe")
        return result is not None and result.get("ok", False)
    except Exception:
        return False
