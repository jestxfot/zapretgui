# tgram/tg_sender.py
"""
Мини-обёртка для отправки лога (текст / файл) в Telegram-бота.

Зависимостей, кроме requests, нет – поэтому работает синхронно
и не создаёт предупреждений вида
    RuntimeWarning: coroutine 'Bot.send_document' was never awaited
"""

from __future__ import annotations
from pathlib import Path
import requests
import time 

# ------------------------------------------------------------------
# общие данные берём из tg_log_delta
# ------------------------------------------------------------------
from .tg_log_delta import TOKEN, CHAT_ID, _tg_api as _call_tg_api

TIMEOUT = 30           # секунд
MAX_RETRIES = 3         # сколько раз повторять при flood-wait
FLOOD_COOLDOWN = 300   # 5 минут cooldown после flood-wait

# Глобальный cooldown после flood-wait (время до которого блокируем отправки)
_flood_cooldown_until = 0.0

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _cut_to_4k(text: str, limit: int = 4000) -> str:
    """Обрезаем строку до последних 4 000 символов (лимит Telegram)."""
    return text[-limit:] if len(text) > limit else text

def is_in_flood_cooldown() -> bool:
    """Проверяет, находимся ли мы в режиме cooldown после flood-wait."""
    return time.time() < _flood_cooldown_until


def get_flood_cooldown_remaining() -> float:
    """Возвращает оставшееся время cooldown в секундах."""
    remaining = _flood_cooldown_until - time.time()
    return max(0.0, remaining)


def _set_flood_cooldown():
    """Устанавливает cooldown после flood-wait."""
    global _flood_cooldown_until
    _flood_cooldown_until = time.time() + FLOOD_COOLDOWN
    from log import log
    log(f"[TG] Установлен cooldown на {FLOOD_COOLDOWN // 60} мин после flood-wait", "⚠ WARNING")


def _safe_call_tg_api(method: str, *, data=None, files=None):
    """
    Обёртка, которая корректно обрабатывает 429 (Too Many Requests).
    Повторяет запрос MAX_RETRIES раз, каждый раз дожидаясь retry_after.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _call_tg_api(method, data=data, files=files)
        except requests.HTTPError as e:
            # Telegram отвечает 429 и JSON вида:
            # { "ok":false, "error_code":429,
            #   "description":"Too Many Requests: retry after 23" }
            if e.response is not None and e.response.status_code == 429:
                try:
                    retry_after = e.response.json().get("parameters", {}) \
                                               .get("retry_after", 1)
                except Exception:
                    retry_after = 1
                # запас +1 с, чтобы не промахнуться
                wait = int(retry_after) + 1
                from log import log
                log(f"[TG] Flood-wait {wait}s (attempt {attempt+1})", "⚠ WARNING")
                time.sleep(wait)
                continue      # повторяем запрос
            raise            # если это не 429 → бросаем дальше
    # если дошли сюда ─ повторы кончились, устанавливаем cooldown
    _set_flood_cooldown()
    raise RuntimeError("Не удалось отправить сообщение после flood-wait")

# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------
def send_log_to_tg(log_path: str | Path, caption: str = "") -> None:
    # Проверяем cooldown перед отправкой
    if is_in_flood_cooldown():
        remaining = get_flood_cooldown_remaining()
        from log import log
        log(f"[TG] Пропуск отправки: cooldown ещё {remaining:.0f}с", "⚠ WARNING")
        return

    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    text = _cut_to_4k(path.read_text(encoding="utf-8-sig", errors="replace"))
    data = {"chat_id": CHAT_ID,
            "text": f"{caption}\n\n{text}" if caption else text,
            "parse_mode": "HTML"}
    _safe_call_tg_api("sendMessage", data=data)


def send_file_to_tg(file_path: str | Path, caption: str = "") -> bool:
    """Возвращает True при успешной отправке, False при ошибке"""
    # Проверяем cooldown перед отправкой
    if is_in_flood_cooldown():
        remaining = get_flood_cooldown_remaining()
        from log import log
        log(f"[TG] Пропуск отправки: cooldown ещё {remaining:.0f}с", "⚠ WARNING")
        return False

    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")

        with path.open("rb") as fh:
            files = {"document": fh}
            data = {"chat_id": CHAT_ID, "caption": caption or path.name}
            _safe_call_tg_api("sendDocument", data=data, files=files)

        return True  # успех
    except Exception as e:
        from log import log
        log(f"[TG] Ошибка отправки файла: {e}", "❌ ERROR")
        return False  # ошибка