"""
Отдельный бот для отправки полных логов пользователями.
Используется только при ручной отправке через меню.
"""

from __future__ import annotations
from pathlib import Path
import requests
import time
from typing import Optional

# ─── Настройки бота для логов ───────────────────────────────
LOG_BOT_TOKEN = "8254416280:AAFKCebglBLvkmp7e0pJ3Ees477oKCDHqLg"  # Замените на токен вашего лог-бота
LOG_BOT_CHAT_ID = "-1003005847271"  # ID чата/канала для логов

# Настройки
TIMEOUT = 30
MAX_RETRIES = 3
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB максимальный размер файла

# API endpoint
LOG_API = f"https://api.telegram.org/bot{LOG_BOT_TOKEN}"

def _safe_api_call(method: str, *, data=None, files=None) -> dict:
    """
    Безопасный вызов Telegram API с обработкой flood-wait.
    """
    from log import log
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            url = f"{LOG_API}/{method}"
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
                    raise RuntimeError(f"Превышен лимит ожидания: {wait_time}s")
            raise
            
    raise RuntimeError("Не удалось отправить после всех попыток")

def send_log_file(file_path: str | Path, caption: str = "") -> tuple[bool, Optional[str]]:
    """
    Отправляет файл лога через отдельного бота.
    
    Returns:
        (success, error_message)
    """
    from log import log
    
    try:
        # Проверяем настройки
        if not LOG_BOT_TOKEN or not LOG_BOT_CHAT_ID:
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
                "chat_id": LOG_BOT_CHAT_ID,
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
        if not LOG_BOT_TOKEN:
            return False
            
        result = _safe_api_call("getMe")
        return result.get("ok", False)
        
    except Exception:
        return False