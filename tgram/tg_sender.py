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

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _cut_to_4k(text: str, limit: int = 4000) -> str:
    """Обрезаем строку до последних 4 000 символов (лимит Telegram)."""
    return text[-limit:] if len(text) > limit else text

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
                log(f"[TG] Flood-wait {wait}s (attempt {attempt+1})", "WARNING")
                time.sleep(wait)
                continue      # повторяем запрос
            raise            # если это не 429 → бросаем дальше
    # если дошли сюда ─ повторы кончились
    raise RuntimeError("Не удалось отправить сообщение после flood-wait")

# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------
def send_log_to_tg(log_path: str | Path, caption: str = "") -> None:
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    text = _cut_to_4k(path.read_text(encoding="utf-8", errors="replace"))
    data = {"chat_id": CHAT_ID,
            "text": f"{caption}\n\n{text}" if caption else text,
            "parse_mode": "HTML"}
    _safe_call_tg_api("sendMessage", data=data)


def send_file_to_tg(file_path: str | Path, caption: str = "") -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    with path.open("rb") as fh:
        files = {"document": fh}
        data = {"chat_id": CHAT_ID, "caption": caption or path.name}
        _safe_call_tg_api("sendDocument", data=data, files=files)