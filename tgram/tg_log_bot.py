"""
Отдельный бот для отправки полных логов пользователями.
Используется только при ручной отправке через меню.
Выбор бота зависит от канала сборки (stable/test).
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Optional

import requests

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
    """Декодирует токен бота."""
    try:
        decoded = base64.b64decode(encoded)
        value = "".join(chr(b ^ xor_key) for b in decoded)

        calc_sum = sum(ord(c) for c in value[:10])
        if calc_sum != checksum:
            return ""

        return value
    except Exception:
        return ""


_token_cache: Optional[str] = None


def _get_bot_token() -> str:
    """Возвращает токен бота в зависимости от канала сборки."""
    global _token_cache

    if _token_cache is None:
        from config.build_info import CHANNEL

        if CHANNEL == "stable":
            _token_cache = _decode_token(_PROD_ENC, _PROD_XOR, _PROD_SUM)
        else:
            _token_cache = _decode_token(_DEV_ENC, _DEV_XOR, _DEV_SUM)

    return _token_cache or ""


TIMEOUT = 30
MAX_RETRIES = 3
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Flood cooldown (только для 429): ручная отправка не должна блокироваться из‑за сетевых ошибок
FLOOD_COOLDOWN = 1800  # 30 минут
_flood_cooldown_until = 0.0


def _set_flood_cooldown(seconds: int = FLOOD_COOLDOWN) -> None:
    global _flood_cooldown_until
    _flood_cooldown_until = time.time() + max(0, int(seconds))


def is_in_flood_cooldown() -> bool:
    return time.time() < _flood_cooldown_until


def _mask_token(text: str) -> str:
    token = _get_bot_token()
    if token and token in text:
        return text.replace(token, "***MASKED***")
    return text


def _shorten(text: str, limit: int = 180) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _looks_like_proxy_error(msg: str) -> bool:
    s = (msg or "").lower()
    return any(k in s for k in ("proxy", "прокси", "socks", "localhost", "127.0.0.1"))


def _get_log_api() -> str:
    """API endpoint для бота."""
    return f"https://api.telegram.org/bot{_get_bot_token()}"


def _safe_api_call(method: str, *, data=None, files=None) -> tuple[Optional[dict], Optional[str]]:
    """
    Безопасный вызов Telegram API с обработкой flood-wait.

    Returns:
        (result_dict, error_message) - result_dict если успех, иначе (None, error_message)
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            url = f"{_get_log_api()}/{method}"
            response = requests.post(url, data=data, files=files, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json(), None

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

                _set_flood_cooldown(wait_time)
                return None, f"Слишком много запросов. Подождите {retry_after} секунд"

            status_code = e.response.status_code if e.response else "неизвестен"
            if status_code == 401:
                return None, "Неверный токен бота (HTTP 401)"
            if status_code == 403:
                return None, "Доступ запрещён (HTTP 403)"
            return None, f"Ошибка HTTP {status_code}"

        except requests.ConnectionError as e:
            raw = _mask_token(str(e))
            raw_short = _shorten(raw)

            if _looks_like_proxy_error(raw):
                return None, f"Не удалось подключиться к прокси (проверьте HTTP_PROXY/HTTPS_PROXY): {raw_short}"

            error_str = raw.lower()
            if any(k in error_str for k in ("connection refused", "connection reset", "forcibly closed")):
                return None, f"Соединение сброшено/отклонено при подключении к Telegram API: {raw_short}"

            # Частая ситуация: Telegram-клиент работает (MTProto), а Bot API по HTTPS недоступен/блокируется
            return None, f"Не удалось подключиться к Telegram Bot API (api.telegram.org): {raw_short}"

        except requests.Timeout:
            return None, "Превышено время ожидания при подключении к Telegram Bot API (api.telegram.org)"

        except Exception as e:
            error_str = str(e).lower()
            if "missing dependencies for socks support" in error_str:
                return None, (
                    "Обнаружен SOCKS-прокси, но не установлена поддержка SOCKS (PySocks). "
                    "Установите PySocks или отключите HTTP_PROXY/HTTPS_PROXY."
                )

            raw = _mask_token(str(e))
            raw_short = _shorten(raw, 120)
            if _looks_like_proxy_error(raw):
                return None, f"Ошибка прокси (HTTP_PROXY/HTTPS_PROXY): {raw_short}"
            if any(k in error_str for k in ("ssl", "certificate", "tls")):
                return None, f"Ошибка TLS/сертификата при подключении к Telegram API: {raw_short}"
            return None, f"Ошибка сети: {raw_short}"

    return None, "Превышено количество попыток"


def send_log_file(
    file_path: str | Path,
    caption: str = "",
    topic_id: int | None = None,
) -> tuple[bool, Optional[str]]:
    """
    Отправляет файл лога через бота в группу с топиком.

    Args:
        file_path: путь к файлу лога
        caption: подпись к файлу
        topic_id: ID топика (если None - выбирается по каналу: test→10854, stable→1)

    Returns:
        (success, error_message)
    """
    if topic_id is None:
        topic_id = _get_default_topic()

    if is_in_flood_cooldown():
        return False, "Слишком частые запросы. Подождите несколько минут"

    try:
        token = _get_bot_token()
        if not token:
            return False, "Ошибка конфигурации бота"

        path = Path(file_path)
        if not path.exists():
            return False, f"Файл лога не найден: {path.name}"

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            return False, f"Файл слишком большой ({size_mb:.1f} МБ). Максимум: 50 МБ"

        if file_size == 0:
            return False, "Файл лога пуст"

        with path.open("rb") as file:
            files = {"document": file}
            data = {
                "chat_id": LOG_CHAT_ID,
                "message_thread_id": topic_id,
                "caption": caption[:1024] if caption else path.name,
            }
            result, error_msg = _safe_api_call("sendDocument", data=data, files=files)

        if result and result.get("ok"):
            return True, None

        if result and not result.get("ok"):
            api_error = result.get("description", "Неизвестная ошибка API")
            return False, f"Telegram API: {api_error}"

        return False, error_msg or "Не удалось отправить файл"

    except PermissionError:
        return False, "Нет доступа к файлу лога"
    except Exception as e:
        return False, f"Ошибка: {_shorten(_mask_token(str(e)), 120)}"


def check_bot_connection() -> bool:
    """Проверяет доступность бота для логов (тихий режим)."""
    try:
        ok, _ = check_bot_connection_detailed()
        return ok
    except Exception:
        return False


def check_bot_connection_detailed() -> tuple[bool, str]:
    """
    Проверяет доступность бота для логов и возвращает человекочитаемую причину ошибки.

    Returns:
        (ok, error_message) - error_message пустая строка при ok=True.
    """
    token = _get_bot_token()
    if not token:
        return False, "Токен бота не найден (ошибка конфигурации)"

    result, error_msg = _safe_api_call("getMe")
    if result is not None and result.get("ok", False):
        return True, ""

    if error_msg:
        return False, error_msg

    if result is not None and not result.get("ok", True):
        api_error = result.get("description", "Неизвестная ошибка API")
        return False, f"Telegram API: {api_error}"

    return False, "Не удалось подключиться к Telegram API"


def get_bot_connection_info() -> tuple[bool, str, str]:
    """
    Расширенная проверка доступности бота.

    Returns:
        (ok, error_message, kind)
        kind ∈ {"config", "network", "unknown"}
    """
    ok, error_msg = check_bot_connection_detailed()
    if ok:
        return True, "", "unknown"

    msg = (error_msg or "").lower()
    if any(key in msg for key in ("токен", "конфигурац", "http 401", "http 403")):
        return False, error_msg, "config"

    if any(
        key in msg
        for key in (
            "telegram",
            "vpn",
            "dpi",
            "timeout",
            "время ожидания",
            "нет подключения",
            "ошибка сети",
            "прокси",
            "proxy",
            "http",
        )
    ):
        return False, error_msg, "network"

    return False, error_msg, "unknown"
