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

# ------------------------------------------------------------------
# общие данные берём из tg_log_delta
# ------------------------------------------------------------------
from tgram.tg_log_delta import TOKEN, CHAT_ID, _tg_api as _call_tg_api

TIMEOUT = 30           # секунд

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _cut_to_4k(text: str, limit: int = 4000) -> str:
    """Обрезаем строку до последних 4 000 символов (лимит Telegram)."""
    return text[-limit:] if len(text) > limit else text


# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------
def send_log_to_tg(log_path: str | Path, caption: str = "") -> None:
    """
    Отправляет содержимое лог-файла текстовым сообщением.

    Если лог > 4 000 символов, берутся последние 4 000.
    """
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    text = path.read_text(encoding="utf-8", errors="replace")
    text = _cut_to_4k(text)

    data = {
        "chat_id": CHAT_ID,
        "text": f"{caption}\n\n{text}" if caption else text,
        "parse_mode": "HTML",
    }
    _call_tg_api("sendMessage", data=data)


def send_file_to_tg(file_path: str | Path, caption: str = "") -> None:
    """
    Отправляет файл (document) через Telegram Bot API.

    Удобно для «полного» лога, когда превышен лимит 4 000 символов.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    with path.open("rb") as fh:
        files = {"document": fh}
        data = {
            "chat_id": CHAT_ID,
            "caption": caption or path.name,
        }
        _call_tg_api("sendDocument", files=files, data=data)