"""
Отдельный бот для отправки полных логов пользователями.
Используется только при ручной отправке через меню.
"""

from __future__ import annotations
from pathlib import Path
import requests
import time
import base64
from typing import Optional

# Обфусцированные данные (многоуровневое шифрование)
_INLINE_A_PARTS = [
    ("Ymhvbm5rbGhiamAb", 0x5A, 0),
    ("fHhbClZaD2lJDnc=", 0x3D, 12),
    ("Sk5mRn8fQ25yb0ZC", 0x27, 23),
    ("0snz+drY+YfUydo=", 0xB1, 35),
]

_INLINE_A_SUM = 520  # контроль первых символов

_INLINE_B_ENC = "U09OTk1OTktGSklMSU8="
_INLINE_B_XOR = 0x7E
_INLINE_B_SUM = 241


def _rebuild_inline_a() -> str:
    """Собирает строку из частей"""
    try:
        result = [''] * 46
        
        for encoded, xor_key, offset in _INLINE_A_PARTS:
            decoded = base64.b64decode(encoded)
            for i, byte in enumerate(decoded):
                if offset + i < len(result):
                    result[offset + i] = chr(byte ^ xor_key)
        
        value = ''.join(result).rstrip('\x00')
        
        checksum = sum(ord(c) for c in value[:10])
        if checksum != _INLINE_A_SUM:
            return ""
        
        return value
    except:
        return ""


def _rebuild_inline_b() -> str:
    """Деобфусцирует строку"""
    try:
        decoded = base64.b64decode(_INLINE_B_ENC)
        value = ''.join(chr(b ^ _INLINE_B_XOR) for b in decoded)
        
        checksum = sum(ord(c) for c in value[:5])
        if checksum != _INLINE_B_SUM:
            return ""
        
        return value
    except:
        return ""


# Кэшированные значения (ленивая инициализация)
_inline_a_cache = None
_inline_b_cache = None


def _get_inline_a() -> str:
    """Возвращает строку A (с кэшированием)"""
    global _inline_a_cache
    if _inline_a_cache is None:
        _inline_a_cache = _rebuild_inline_a()
    return _inline_a_cache


def _get_inline_b() -> str:
    """Возвращает строку B (с кэшированием)"""
    global _inline_b_cache
    if _inline_b_cache is None:
        _inline_b_cache = _rebuild_inline_b()
    return _inline_b_cache


# Настройки
TIMEOUT = 30
MAX_RETRIES = 3
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB максимальный размер файла

# API endpoint (формируется динамически)
def _get_log_api() -> str:
    return f"https://api.telegram.org/bot{_get_inline_a()}"

def _safe_api_call(method: str, *, data=None, files=None) -> dict:
    """
    Безопасный вызов Telegram API с обработкой flood-wait.
    """
    from log import log
    from .tg_sender import _set_flood_cooldown

    for attempt in range(MAX_RETRIES + 1):
        try:
            url = f"{_get_log_api()}/{method}"
            response = requests.post(url, data=data, files=files, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            if e.response and e.response.status_code == 429:
                # Обработка flood-wait
                try:
                    result = e.response.json()
                    retry_after = result.get("parameters", {}).get("retry_after", 60)
                except Exception:
                    retry_after = 60

                wait_time = int(retry_after) + 1
                log(f"[LogBot] Flood-wait {wait_time}s (попытка {attempt+1})", "⚠ WARNING")

                if attempt < MAX_RETRIES:
                    time.sleep(wait_time)
                    continue
                else:
                    _set_flood_cooldown()  # Устанавливаем cooldown
                    raise RuntimeError(f"Превышен лимит ожидания: {wait_time}s")
            raise

    _set_flood_cooldown()  # Устанавливаем cooldown
    raise RuntimeError("Не удалось отправить после всех попыток")

def send_log_file(file_path: str | Path, caption: str = "") -> tuple[bool, Optional[str]]:
    """
    Отправляет файл лога через отдельного бота.

    Returns:
        (success, error_message)
    """
    from log import log
    from .tg_sender import is_in_flood_cooldown, get_flood_cooldown_remaining

    # Проверяем глобальный cooldown
    if is_in_flood_cooldown():
        remaining = get_flood_cooldown_remaining()
        msg = f"Cooldown после flood-wait: ещё {remaining:.0f}с"
        log(f"[LogBot] {msg}", "⚠ WARNING")
        return False, msg

    try:
        # Проверяем настройки
        key_a = _get_inline_a()
        key_b = _get_inline_b()
        if not key_a or not key_b:
            return False, "Бот для логов не настроен"
            
        path = Path(file_path)
        if not path.exists():
            return False, f"Файл не найден: {path}"
            
        # Проверяем размер файла
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"Файл слишком большой: {file_size / 1024 / 1024:.1f} MB"
            
        # Отправляем файл
        with path.open("rb") as file:
            files = {"document": file}
            data = {
                "chat_id": key_b,
                "caption": caption[:1024] if caption else path.name
            }
            
            result = _safe_api_call("sendDocument", data=data, files=files)
            
        if result.get("ok"):
            log(f"[LogBot] Лог успешно отправлен", "✅ INFO")
            return True, None
        else:
            error = result.get("description", "Неизвестная ошибка")
            log(f"[LogBot] Ошибка отправки: {error}", "❌ ERROR")
            return False, error
            
    except RuntimeError as e:
        # Flood-wait или превышен лимит попыток
        error_msg = str(e)
        log(f"[LogBot] {error_msg}", "❌ ERROR")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Неожиданная ошибка: {e}"
        log(f"[LogBot] {error_msg}", "❌ ERROR")
        return False, error_msg

def check_bot_connection() -> bool:
    """
    Проверяет доступность бота для логов.
    """
    try:
        if not _get_inline_a():
            return False
            
        result = _safe_api_call("getMe")
        return result.get("ok", False)
        
    except Exception:
        return False